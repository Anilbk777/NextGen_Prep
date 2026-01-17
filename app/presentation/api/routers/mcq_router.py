from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from presentation.schemas.mcq_schema import MCQCreate, MCQOut
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.mcq_repo_impl import create_mcq
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcqs", tags=["MCQs"])


@router.post("", response_model=MCQOut)
def add_mcq(
    mcq: MCQCreate, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    try:
        logger.info(
            f"Admin {admin['user_id']} creating MCQ for subject {mcq.subject_id}"
        )
        result = create_mcq(db, mcq, admin["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
