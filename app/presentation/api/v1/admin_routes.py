from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from presentation.schemas.mcq_schema import MCQCreate, MCQOut
from presentation.schemas.mock_test_schema import MockTestCreate, MockTestOut
from presentation.schemas.bulk_mcq_schema import MCQBulkUploadMeta, BulkUploadResponse
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.mcq_repo_impl import create_mcq
from infrastructure.repositories.mock_test_repo_impl import create_mock_test
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/mcqs", response_model=MCQOut)
def add_mcq(mcq: MCQCreate, db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    try:
        logger.info(f"Admin {admin['user_id']} is creating a new MCQ for subject: {mcq.subject}")
        result = create_mcq(db, mcq, admin["user_id"])
        logger.info(f"MCQ created successfully with ID: {result.id}")
        return result
    except ValueError as e:
        logger.warning(f"Validation error during MCQ creation by admin {admin['user_id']}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during MCQ creation by admin {admin['user_id']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/mock-tests", response_model=MockTestOut)
def add_mock_test(data: MockTestCreate, db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    try:
        logger.info(f"Admin {admin['user_id']} is creating a mock test: {data.title}")
        result = create_mock_test(db, data)
        return MockTestOut(
            id=result.id,
            title=result.title,
            subject=result.subject,
            total_questions=len(result.questions)
        )
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating mock test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/bulk-upload", response_model=BulkUploadResponse)
def bulk_upload_mcqs(meta: MCQBulkUploadMeta, db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    # Placeholder for actual file processing logic
    # In a real scenario, we'd accept a file and parse it.
    # For now, we'll return a success message since the logic for parsing isn't provided.
    logger.info(f"Admin {admin['user_id']} initiated bulk upload for subject: {meta.subject}")
    return BulkUploadResponse(total_rows=0, inserted=0, failed=0, errors=["Bulk file processing logic not implemented"])
    
