from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from infrastructure.db.models.mcq_model import PracticeMCQ, OptionModel, MockTestMCQ
from infrastructure.db.models.attempt_model import AttemptModel
from infrastructure.db.models.mock_test_model import MockTestModel
from presentation.schemas.mcq_schema import PracticeMCQOut, MockTestMCQOut
from presentation.schemas.mock_test_schema import MockTestOut
from presentation.dependencies import get_db, get_current_user
from infrastructure.repositories.mock_test_repo_impl import MockTestRepository

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["User (MCQs)"])


@router.get("/mcqs", response_model=List[PracticeMCQOut])
def list_mcqs(db: Session = Depends(get_db)):
    try:
        mcqs = db.query(PracticeMCQ).all()
        logger.info(f"Fetched {len(mcqs)} practice MCQs")
        return mcqs
    except Exception as e:
        logger.error(f"Error fetching MCQs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")



@router.get("/mock-tests", response_model=List[MockTestOut])
def list_mock_tests(
    db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    try:
        logger.info(f"User {user['user_id']} fetching all mock tests")
        tests = db.query(MockTestModel).all()
        return [
            MockTestOut(
                id=t.id,
                title=t.title,
                total_questions=len(t.questions),
            )
            for t in tests
        ]
    except Exception as e:
        logger.error(f"Error fetching mock tests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/mock-tests/{test_id}/mcqs", response_model=List[MockTestMCQOut])
def get_mock_test_questions(
    test_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)
):
    try:
        logger.info(
            f"User {user['user_id']} fetching questions for mock test {test_id}"
        )
        repo = MockTestRepository(db)
        test = repo.get_mock_test_with_questions(test_id)
        return test.questions
    except ValueError as e:
        logger.warning(f"Mock test not found: {test_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching mock test questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/mcqs/{mcq_id}/attempt")
def attempt_mcq(
    mcq_id: int,
    option_id: int,
    mode: str = "practice",
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        logger.info(
            f"User {user['user_id']} attempting MCQ {mcq_id} with option {option_id}"
        )
        # Attempting either PracticeMCQ or MockTestMCQ? 
        # For now let's assume practice as per old code structure
        mcq = db.query(PracticeMCQ).filter(PracticeMCQ.id == mcq_id).first()
        option = (
            db.query(OptionModel)
            .filter(OptionModel.id == option_id, OptionModel.mcq_id == mcq_id)
            .first()
        )

        if not mcq or not option:
            logger.warning(
                f"Attempt failed: MCQ {mcq_id} or option {option_id} not found"
            )
            raise HTTPException(status_code=404, detail="MCQ or option not found")

        attempt = AttemptModel(
            user_id=user["user_id"],
            mcq_id=mcq_id,
            selected_option_id=option.id,
            is_correct=option.is_correct,
            mode=mode,
            attempted_at=datetime.utcnow(),
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        logger.info(
            f"User {user['user_id']} completed attempt for MCQ {mcq_id}. Correct: {option.is_correct}"
        )
        return {"is_correct": option.is_correct}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error recording attempt for MCQ {mcq_id} by user {user['user_id']}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")
