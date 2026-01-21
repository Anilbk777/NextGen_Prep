import logging
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.presentation.dependencies import get_db, get_current_user
from app.presentation.schemas.practice_schemas import (
    PracticeSessionStartIn,
    PracticeSessionStartOut,
    PracticeQuestionOut,
    PracticeAnswerIn,
    PracticeAnswerOut,
    PracticeSessionSummaryOut
)

from app.infrastructure.services.practice_session_service import PracticeSessionService
from app.infrastructure.repositories.practice_session_repo import PracticeSessionRepository
from app.infrastructure.repositories.question_repo import QuestionRepository
from app.infrastructure.repositories.attempt_repo import AttemptRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/practice",
    tags=["Practice"]
)


@router.post(
    "/sessions",
    response_model=PracticeSessionStartOut,
    status_code=status.HTTP_201_CREATED
)
def start_session(
    payload: PracticeSessionStartIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        service = PracticeSessionService(
            session_repo=PracticeSessionRepository(db),
            question_repo=QuestionRepository(db),
            attempt_repo=AttemptRepository(db),
            db=db
        )
        return service.start_session(user_id=current_user.get("user_id"), topic_id=payload.topic_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error starting session for user {current_user.get("user_id")}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/sessions/{session_id}/current-question",
    response_model=PracticeQuestionOut
)
def get_current_question(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        service = PracticeSessionService(
            session_repo=PracticeSessionRepository(db),
            question_repo=QuestionRepository(db),
            attempt_repo=AttemptRepository(db),
            db=db
        )
        return service.get_current_question(session_id=session_id, user_id=current_user.get("user_id"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching current question for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/sessions/{session_id}/answer",
    response_model=PracticeAnswerOut
)
def submit_answer(
    session_id: int,
    payload: PracticeAnswerIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        service = PracticeSessionService(
            session_repo=PracticeSessionRepository(db),
            question_repo=QuestionRepository(db),
            attempt_repo=AttemptRepository(db),
            db=db
        )
        return service.submit_answer(
            session_id=session_id,
            user_id=current_user.get("user_id"),
            question_id=payload.question_id,
            selected_option_id=payload.selected_option_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error submitting answer for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/sessions/{session_id}/summary",
    response_model=PracticeSessionSummaryOut
)
def get_session_summary(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        service = PracticeSessionService(
            session_repo=PracticeSessionRepository(db),
            question_repo=QuestionRepository(db),
            attempt_repo=AttemptRepository(db),
            db=db
        )
        return service.get_summary(session_id=session_id, user_id=current_user.get("user_id"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching summary for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
