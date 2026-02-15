import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from presentation.dependencies import get_db, get_current_user
from infrastructure.services.mock_test_session_service import MockTestSessionService
from infrastructure.repositories.mock_test_conc_repo import MockTestRepositoryImpl
from presentation.schemas.mock_test_session_schema import (
    AnswerRequest,
    QuestionResponse,
    MockTestResultResponse,
    StartSessionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock-tests", tags=["Mock Tests"])


# --------------------------------------------------
# Dependency injection factory
# --------------------------------------------------
def get_service(db: Session = Depends(get_db)) -> MockTestSessionService:
    repo = MockTestRepositoryImpl(db)
    return MockTestSessionService(db, repo)


# --------------------------------------------------
# 1. Start / resume session
# --------------------------------------------------
@router.post(
    "/{mock_test_id}/start",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_session(
    mock_test_id: int,
    current_user: dict = Depends(get_current_user),
    service: MockTestSessionService = Depends(get_service),
):
    """
    Starts a new mock test session or resumes an existing active one for the current user.
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"User {user_id} starting session for mock test {mock_test_id}")
        session = service.start_session(user_id, mock_test_id)
        return session
    except ValueError as e:
        logger.warning(
            f"Validation error starting session for user {current_user.get('user_id')}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error starting session for user {current_user.get('user_id')}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


# --------------------------------------------------
# 2. Get session questions
# --------------------------------------------------
@router.get("/sessions/{session_id}/questions", response_model=List[QuestionResponse])
def get_questions(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    service: MockTestSessionService = Depends(get_service),
):
    """
    Fetches all questions for a given session, including any previously answered options.
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"User {user_id} fetching questions for session {session_id}")
        questions = service.get_questions(session_id, user_id)

        response = []
        for q in questions:
            # Determine which option (if any) was selected by the user for this question
            # user_selected_id = None
            # if getattr(q, "answer", None):
            #     user_selected_id = getattr(q.answer, "selected_option_id", None)

            # Find the correct option id for the MCQ (if any)
            correct_option_id = None
            for o in q.mcq.options:
                if getattr(o, "is_correct", False):
                    correct_option_id = o.id
                    break

            # Build OptionSchema list and mark selected + include is_correct
            options = []
            for o in q.mcq.options:
                opt = {
                    "id": o.id,
                    "option_text": o.option_text,
                    "is_correct": bool(getattr(o, "is_correct", False))
                    # "selected": (user_selected_id == o.id),
                }
                options.append(opt)

            response.append(
                QuestionResponse(
                    mcq_id=q.mcq.id,
                    question_text=q.mcq.question_text,
                    options=options,
                    answered_option_id=correct_option_id,
                    order_index=q.order_index,
                    subject_name=q.subject.name,
                )
            )
        return response
    except ValueError as e:
        logger.warning(
            f"Validation error fetching questions for session {session_id}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error fetching questions for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


# --------------------------------------------------
# 3. Save / update an answer
# --------------------------------------------------
@router.post("/sessions/{session_id}/answers", status_code=status.HTTP_200_OK)
def save_answer(
    session_id: int,
    answer: AnswerRequest,
    current_user: dict = Depends(get_current_user),
    service: MockTestSessionService = Depends(get_service),
):
    """
    Updates or saves an answer for a specific question in a session.
    """
    try:
        user_id = current_user.get("user_id")
        service.save_answer(
            session_id=session_id,
            user_id=user_id,
            mcq_id=answer.mcq_id,
            selected_option_id=answer.selected_option_id,
        )
        return {"message": "Answer saved successfully"}
    except ValueError as e:
        logger.warning(f"Validation error saving answer for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error saving answer for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


# --------------------------------------------------
# 4. Final submission
# --------------------------------------------------
@router.post("/sessions/{session_id}/submit", response_model=MockTestResultResponse)
def submit_session(
    session_id: int,
    current_user: dict = Depends(get_current_user),
    service: MockTestSessionService = Depends(get_service),
):
    """
    Manually submits a mock test session and returns calculation results.
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"User {user_id} submitting session {session_id}")
        result = service.submit(session_id, user_id)
        return result
    except ValueError as e:
        logger.warning(f"Validation error submitting session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error submitting session {session_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


# --------------------------------------------------
# 5. Get result (after submission)
# --------------------------------------------------
@router.get("/sessions/{session_id}/result", response_model=MockTestResultResponse)
def get_result(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    service: MockTestSessionService = Depends(get_service),
):
    """
    Retrieves the result of a previously submitted session.
    """
    user_id = current_user.get("user_id")
    session = service.repo.get_session_by_id(db, session_id)

    if not session or session.user_id != user_id:
        logger.warning(
            f"Result lookup failed: Session {session_id} not found or unauthorized for user {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if not session.is_submitted:
        logger.warning(
            f"Result lookup failed: Session {session_id} is not yet submitted"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Session not yet submitted"
        )

    try:
        result = service._evaluate(session.id)
        return result
    except Exception as e:
        logger.error(
            f"Unexpected error evaluating result for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
