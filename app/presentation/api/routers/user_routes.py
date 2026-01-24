from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from infrastructure.db.models.mcq_model import PracticeMCQ, OptionModel, MockTestMCQ
from infrastructure.db.models.attempt_model import AttemptModel
from infrastructure.db.models.mock_test_model import MockTestModel
from infrastructure.db.models.user_model import UserModel
from presentation.schemas.mcq_schema import PracticeMCQOut, MockTestMCQOut
from presentation.schemas.mock_test_schema import MockTestOut
from presentation.dependencies import get_db, get_current_user, admin_required
from infrastructure.repositories.mock_test_repo_impl import MockTestRepository

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mock-tests"])


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

# delete the secific mock test by admin only
@router.delete("/mock-tests/{test_id}")
def delete_mock_test(
    test_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    try:
        logger.info(f"Admin {admin['user_id']} deleting mock test {test_id}")
        repo = MockTestRepository(db)
        repo.delete_mock_test(test_id)
        return {"message": "Mock test deleted successfully"}
    except ValueError as e:
        logger.warning(f"Mock test not found: {test_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting mock test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


#count the numbers of mock tests
@router.get("/count", response_model=int)
def count_mock_tests(db: Session = Depends(get_db)):
    return db.query(MockTestModel).count()

# count the numbers of users but don't count admin
@router.get("/users/count", response_model=int)
def count_users(db: Session = Depends(get_db)):
    return db.query(UserModel).filter(UserModel.role != "ADMIN").count()