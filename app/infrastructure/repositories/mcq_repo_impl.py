from infrastructure.db.models.mcq_model import MCQModel, OptionModel
from sqlalchemy.orm import Session
import logging
from presentation.schemas.mcq_schema import MCQCreate

logger = logging.getLogger(__name__)

def create_mcq(db: Session, mcq_data: MCQCreate, admin_id: int) -> MCQModel:
    try:
        if len(mcq_data.options) < 2:
            raise ValueError("MCQ must have at least 2 options")
        if sum(o.is_correct for o in mcq_data.options) != 1:
            raise ValueError("MCQ must have exactly 1 correct option")

        logger.info(f"Creating MCQModel for admin {admin_id}")
        mcq = MCQModel(
            question_text=mcq_data.question_text,
            explanation=mcq_data.explanation,
            subject=mcq_data.subject,
            is_practice_only=mcq_data.is_practice_only,
            created_by=admin_id
        )
        db.add(mcq)
        db.flush()  # get mcq.id

        logger.info(f"Adding {len(mcq_data.options)} options for MCQ {mcq.id}")
        for o in mcq_data.options:
            option = OptionModel(option_text=o.option_text, is_correct=o.is_correct, mcq_id=mcq.id)
            db.add(option)

        db.commit()
        db.refresh(mcq)
        logger.info(f"Successfully committed MCQ {mcq.id} to database")
        return mcq
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Database error during MCQ creation by admin {admin_id}: {e}", exc_info=True)
        db.rollback()
        raise
