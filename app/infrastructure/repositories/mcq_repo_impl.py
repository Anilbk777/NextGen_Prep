from infrastructure.db.models.mcq_model import PracticeMCQ, OptionModel
from infrastructure.db.models.topic_model import Topic
from sqlalchemy.orm import Session
import logging
from presentation.schemas.mcq_schema import PracticeMCQCreate, PracticeMCQUpdate

logger = logging.getLogger(__name__)

def create_mcq(db: Session, topic_id: int, mcq_data: PracticeMCQCreate) -> PracticeMCQ:
    try:
        # Verify topic exists
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            logger.warning(f"MCQ creation failed: Topic {topic_id} not found")
            raise ValueError(f"Topic with ID {topic_id} does not exist.")

        logger.info(f"Creating PracticeMCQ")
        mcq = PracticeMCQ(
            question_text=mcq_data.question_text,
            explanation=mcq_data.explanation,
            difficulty=mcq_data.difficulty,
            topic_id=topic_id,
        )
        db.add(mcq)
        db.flush()  

        logger.info(f"Adding {len(mcq_data.options)} options for MCQ {mcq.id}")
        for o in mcq_data.options:
            option = OptionModel(
                mcq_id=mcq.id,
                option_text=o.option_text,
                is_correct=o.is_correct
                )
            db.add(option)

        db.commit()
        db.refresh(mcq)
        logger.info(f"Successfully committed MCQ {mcq.id} to database")
        return mcq
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Database error during MCQ creation: {e}", exc_info=True)
        db.rollback()
        raise

# get mcqs by topic id 
def get_mcqs_by_topic_id(db: Session, topic_id: int) -> list[PracticeMCQ]:
    try:
        mcqs = db.query(PracticeMCQ).filter(PracticeMCQ.topic_id == topic_id).all()
        return mcqs

    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MCQ retrieval by topic ID {topic_id}: {e}", exc_info=True)
        raise

# update mcqs 

def update_mcq_by_id(
    db:Session,
    mcq_id:int,
    data:PracticeMCQUpdate,
) -> PracticeMCQ:
    try:
        mcq = db.query(PracticeMCQ).filter(PracticeMCQ.id == mcq_id).first()
        if not mcq:
            logger.warning(f"MCQ update failed: MCQ {mcq_id} not found")
            raise ValueError(f"MCQ with ID {mcq_id} does not exist.")

        # Update scalar fields
        for field in ["question_text", "explanation", "difficulty"]:
            value = getattr(data, field)
            if value is not None:
                setattr(mcq, field, value)

        #delete old options
        db.query(OptionModel).filter(OptionModel.mcq_id == mcq_id).delete()

        for opt in data.options:
            db.add(
                OptionModel(
                    option_text = opt.option_text,
                    is_correct = opt.is_correct,
                    mcq_id = mcq.id
                )
            )
        db.commit()
        db.refresh(mcq)
        logger.info(f"Successfully committed MCQ {mcq.id} to database")
        return mcq
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MCQ update: {e}", exc_info=True)
        raise


# delete mcq

def delete_mcq_by_id(db: Session, mcq_id: int) -> None:
    try:
        mcq = db.query(PracticeMCQ).filter(PracticeMCQ.id == mcq_id).first()
        if not mcq:
            logger.warning(f"MCQ deletion failed: MCQ {mcq_id} not found")
            raise ValueError(f"MCQ with ID {mcq_id} does not exist.")

        db.delete(mcq)
        db.commit()
        logger.info(f"Successfully deleted MCQ {mcq_id}")
        return {"message": f"MCQ '{mcq_id}' deleted successfully"}

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MCQ deletion: {e}", exc_info=True)
        db.rollback()
        raise

