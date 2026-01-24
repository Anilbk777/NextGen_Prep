from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from infrastructure.db.models.mcq_model import PracticeMCQ
from presentation.schemas.mcq_schema import PracticeMCQCreate, PracticeMCQOut, PracticeMCQUpdate
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.mcq_repo_impl import create_mcq, get_mcqs_by_topic_id, delete_mcq_by_id, update_mcq_by_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcqs", tags=["MCQs"])



#count the numbers of practice mcqs
@router.get("/count", response_model=int)
def count_mcqs(db: Session = Depends(get_db)):
    return db.query(PracticeMCQ).count()


@router.post("", response_model=PracticeMCQOut)
def add_mcq(
    topic_id: int,
    mcq: PracticeMCQCreate, db: Session = Depends(get_db)
):
    try:
        logger.info(
            f"creating MCQ for topic {topic_id}"
        )
        result = create_mcq(db, topic_id, mcq)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# get all mcqs by topic id
@router.get("/{topic_id}", response_model=list[PracticeMCQOut])
def get_mcqs(
    topic_id: int, db: Session = Depends(get_db)
):
    try:
        logger.info(
            f"getting MCQs for topic {topic_id}"
        )
        result = get_mcqs_by_topic_id(db, topic_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# update mcq
@router.patch("/{mcq_id}", response_model=PracticeMCQOut)
def update_mcq(
    mcq_id: int,
    mcq: PracticeMCQUpdate,
    db: Session = Depends(get_db)
):
    try:
        logger.info(
            f"updating MCQ {mcq_id}"
        )
        result = update_mcq_by_id(db, mcq_id, mcq)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# delete mcq
@router.delete("/{mcq_id}")
def delete_mcq(
    mcq_id: int,
    db: Session = Depends(get_db)
):
    try:
        logger.info(
            f"deleting MCQ {mcq_id}"
        )
        result = delete_mcq_by_id(db, mcq_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


