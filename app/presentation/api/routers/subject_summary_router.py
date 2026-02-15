from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from infrastructure.repositories.subject_summary import SubjectSummaryRepository
from presentation.dependencies import get_db, get_current_user
from presentation.schemas.subject_summary_schemas import SubjectSummaryResponse
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["mobile app dashboard"])


@router.get("/subject-summary", response_model=List[SubjectSummaryResponse])
def subejct_summary(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):

    user_id = current_user["user_id"]

    try:
        summary_obj = SubjectSummaryRepository(db)
        return summary_obj.fetch_subject_summary(user_id)

    except Exception as e:
        logger.error(
            f"Unexpected error occured when generating subjects summary :{str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error when generating subjects summary",
        )


