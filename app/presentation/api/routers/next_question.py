from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict
import asyncio
import logging

from app.infrastructure.adaptive_system.adaptive_engine import AdaptiveLearningEngine
from app.presentation.schemas.adaptive_schemas import (
    NextQuestionRequest,
    NextQuestionResponse,
    ResponseSubmission,
    SubmissionResult,
    AdaptiveStats,
    LearningSessionCreate,
    LearningSessionSchema,
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
    Returns the next adaptive MCQ for the authenticated user within the given session.
    Enforces a 20-second timeout to prevent hanging on slow LLM generation.
    """
    user_id = current_user["user_id"]
    
    logger.info(
        f"Next question request received from user_id={user_id}, session_id={request.session_id}"
    )

    try:
        # Fetch session to get topic_id and verify ownership
        logger.debug(f"Fetching session_id={request.session_id} for verification")
        session_repo = engine._sessions
        session = session_repo.get_session_by_id(request.session_id)

        if not session:
            logger.warning(f"Session not found: session_id={request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found",
            )

        # Verify session belongs to current user
        if session.user_id != user_id:
            logger.warning(
                f"Session ownership mismatch: session_id={request.session_id}, "
                f"session.user_id={session.user_id}, current_user_id={user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to current user",
            )

        logger.info(
            f"Session verified: session_id={request.session_id}, topic_id={session.topic_id}"
        )

        # Get next question for this session's topic with 20-second timeout
        try:
            logger.debug(
                f"Starting question generation for user_id={user_id}, topic_id={session.topic_id}"
            )
            question = await asyncio.wait_for(
                asyncio.to_thread(engine.get_next_question, user_id, session.topic_id),
                timeout=20.0
            )
            logger.info(
                f"Question generation successful: question_id={question.get('question_id')}, "
                f"template_id={question.get('template_id')}"
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Question generation timeout (20s exceeded) for user_id={user_id}, "
                f"session_id={request.session_id}, topic_id={session.topic_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Question generation is taking longer than expected. Please try again in a moment.",
            )

        # Normalize options into the API shape (list of dicts) expected by
        # NextQuestionResponse. The engine/DB may store them as a list of
        # plain strings (e.g. fallback questions) or already as dicts.
        raw_options = question.get("options", [])
        if raw_options and isinstance(raw_options[0], str):
            logger.debug("Normalizing string options to dict format")
            question["options"] = [
                {"id": idx, "text": opt} for idx, opt in enumerate(raw_options)
            ]

        logger.info(
            "Next question successfully prepared",
            extra={
                "user_id": user_id,
                "session_id": request.session_id,
                "template_id": question.get("template_id"),
                "concept_id": question.get("concept_id"),
            },
        )

        # Engine already includes session_id in the payload; avoid passing it twice.
        return NextQuestionResponse(**question)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            f"Invalid state for next question: {e}",
            extra={"user_id": user_id, "session_id": request.session_id},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Adaptive engine failure for user_id={user_id}, session_id={request.session_id}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while generating question. Please try again.",
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
        # Verify session belongs to current user
        session_repo = engine._sessions
        session = session_repo.get_session_by_id(payload.session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {payload.session_id} not found"
            )
        
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to current user"
            )
        
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
                "session_id": payload.session_id,
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

    except HTTPException:
        raise

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
    Ensures the session exists and belongs to the current user.
    """
    user_id = current_user["user_id"]

    try:
        # Verify session exists and belongs to the current user
        session_repo = engine._sessions
        session = session_repo.get_session_by_id(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session does not belong to current user",
            )

        session_data = engine.end_session(session_id)
        return LearningSessionSchema(**session_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Failed to end session", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error ending learning session",
        )
