from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict
import logging

from app.infrastructure.adaptive_system.adaptive_engine import AdaptiveLearningEngine
from app.presentation.schemas.adaptive_schemas import (
    NextQuestionRequest,
    NextQuestionResponse,
    ResponseSubmission,
    SubmissionResult,
    AdaptiveStats,
    LearningSessionCreate,
    LearningSessionSchema
)
from app.presentation.dependencies import get_current_user, get_adaptive_engine

router = APIRouter(prefix="/learning", tags=["Adaptive Learning"])
logger = logging.getLogger(__name__)

@router.post(
    "/start-session",
    response_model=LearningSessionSchema,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    request: LearningSessionCreate,
    current_user: Dict = Depends(get_current_user),
    engine: AdaptiveLearningEngine = Depends(get_adaptive_engine),
):
    """
    Initializes a new learning session for a specific subject and topic.
    """
    user_id = current_user["user_id"]
    try:
        session = engine.start_session(
            user_id=user_id,
            subject_id=request.subject_id,
            topic_id=request.topic_id
        )
        return LearningSessionSchema(**session, questions_attempted=0, questions_correct=0)
    except Exception as e:
        logger.error("Failed to start session", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error starting learning session",
        )

@router.post(
    "/next-question",
    response_model=NextQuestionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_next_question(
    request: NextQuestionRequest,
    current_user: Dict = Depends(get_current_user),
    engine: AdaptiveLearningEngine = Depends(get_adaptive_engine),
):
    """
    Returns the next adaptive MCQ for the authenticated user and given topic.
    """
    user_id = current_user["user_id"]

    try:
        # Note: request.topic_id is used for filtering candidates
        question = engine.get_next_question(user_id, request.topic_id)

        logger.info(
            "Next question generated",
            extra={
                "user_id": user_id,
                "template_id": question.get("template_id"),
                "concept_id": question.get("concept_id"),
            },
        )

        return NextQuestionResponse(**question)

    except ValueError as e:
        logger.warning("Invalid state for next question", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Adaptive engine failure", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal adaptive engine error",
        )

@router.post(
    "/submit-response",
    response_model=SubmissionResult,
    status_code=status.HTTP_200_OK,
)
async def submit_response(
    payload: ResponseSubmission,
    current_user: Dict = Depends(get_current_user),
    engine: AdaptiveLearningEngine = Depends(get_adaptive_engine),
):
    """
    Submits a user's answer and returns adaptive feedback and updated stats.
    """
    user_id = current_user["user_id"]

    try:
        feedback = engine.process_response(
            user_id=user_id,
            question_id=payload.question_id,
            template_id=payload.template_id,
            concept_id=payload.concept_id,
            selected_option_index=payload.selected_option_index,
            response_time=payload.response_time,
            session_id=payload.session_id
        )

        logger.info(
            "Response processed",
            extra={
                "user_id": user_id,
                "question_id": payload.question_id,
                "correct": feedback["correct"],
            },
        )

        return SubmissionResult(
            correct=feedback["correct"],
            correct_option_index=feedback["correct_option_index"],
            explanation=feedback["explanation"],
            stats=AdaptiveStats(
                global_ability=feedback["global_ability"],
                concept_mastery=feedback["updated_mastery"],
                misconception_detected=feedback.get("misconception"),
                suggested_review=feedback["suggested_review"]
            ),
            session_id=payload.session_id
        )

    except ValueError as e:
        logger.warning("Invalid response submission", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Failed to process response", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing adaptive response",
        )

@router.post(
    "/end-session/{session_id}",
    response_model=LearningSessionSchema,
    status_code=status.HTTP_200_OK,
)
async def end_session(
    session_id: int,
    current_user: Dict = Depends(get_current_user),
    engine: AdaptiveLearningEngine = Depends(get_adaptive_engine),
):
    """
    Finalizes a learning session and returns final metrics.
    """
    try:
        session_data = engine.end_session(session_id)
        return LearningSessionSchema(**session_data, subject_id=0, topic_id=0) # IDs are in internal data but not in end_session return yet
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to end session", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error ending learning session",
        )
