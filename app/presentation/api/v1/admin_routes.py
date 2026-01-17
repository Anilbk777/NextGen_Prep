from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from presentation.schemas.mcq_schema import MCQCreate, MCQOut
from presentation.schemas.mock_test_schema import MockTestCreate, MockTestOut, MockTestDetailOut
from presentation.schemas.topic_schema import TopicCreate, TopicOut
from presentation.schemas.subject_schema import SubjectCreate, SubjectOut
from presentation.dependencies import get_db, admin_required
from infrastructure.repositories.mcq_repo_impl import create_mcq
from infrastructure.repositories.mock_test_repo_impl import create_mock_test
from infrastructure.repositories.subject_repo_impl import (
    create_subject,
    get_all_subjects,
    get_subject_by_id,
    update_subject,
    delete_subject,
)
from infrastructure.repositories.topic_repo_impl import (
    create_topic,
    get_topics_by_subject,
    get_all_topics,
    get_topic_by_id,
    update_topic,
    delete_topic,
)
from application.admin.bulk_upload_usecase import (
    process_practice_bulk_upload,
    process_mock_bulk_upload,
)
from presentation.schemas.bulk_mcq_schema import (
    PracticeBulkUploadMeta,
    MockTestBulkUploadMeta,
    BulkUploadResponse,
)
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/mcqs", response_model=MCQOut)
def add_mcq(
    mcq: MCQCreate, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    
    try:
        logger.info(
            f"Admin {admin['user_id']} is creating a new MCQ for subject_id: {mcq.subject_id}"
        )
        result = create_mcq(db, mcq, admin["user_id"])
        logger.info(f"MCQ created successfully with ID: {result.id}")
        return result
    except ValueError as e:
        logger.warning(
            f"Validation error during MCQ creation by admin {admin['user_id']}: {e}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Unexpected error during MCQ creation by admin {admin['user_id']}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/bulk-upload/practice", response_model=BulkUploadResponse)
async def bulk_upload_practice(
    subject_id: int = Form(...),
    topic_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        logger.info(
            f"Admin {admin['user_id']} bulk uploading practice MCQs for subject_id: {subject_id}"
        )

        meta = PracticeBulkUploadMeta(
            subject_id=subject_id, topic_id=topic_id, is_practice_only=True
        )

        file_content = await file.read()
        return process_practice_bulk_upload(
            db, file_content, file.filename, meta, admin["user_id"]
        )

    except ValueError as e:
        logger.warning(f"Bulk upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bulk upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/bulk-upload/mock-test", response_model=MockTestOut)
async def bulk_upload_mock_test(
    mock_test_title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """
    Bulk upload mock test with questions from CSV/XLSX file.
    
    Expected file columns:
    - subject: Subject name (will be auto-created if it doesn't exist)
    - question_text: The question text
    - option1, option2, option3, option4: The four options
    - correct_answer: Either "1", "2", "3", "4" or the exact text of the correct option
    """
    try:
        logger.info(
            f"Admin {admin['user_id']} bulk uploading mock test: {mock_test_title}"
        )
        
        # Read and parse file
        file_content = await file.read()
        
        # Parse based on file type
        import pandas as pd
        import io
        
        if file.filename.endswith(".csv"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_content), on_bad_lines="skip", engine="python"
                )
            except Exception as e:
                logger.error(f"Error parsing CSV: {e}")
                raise ValueError(f"Error parsing CSV file: {str(e)}")
        elif file.filename.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(io.BytesIO(file_content))
            except Exception as e:
                logger.error(f"Error parsing Excel: {e}")
                raise ValueError(f"Error parsing Excel file: {str(e)}")
        else:
            raise ValueError("Unsupported file format. Please upload CSV or XLSX file.")
        
        # Normalize column names
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        
        # Validate required columns
        required_cols = ["subject", "question_text", "option1", "option2", "option3", "option4", "correct_answer"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(
                f"Missing required columns in file: {', '.join(missing_cols)}. "
                f"Expected columns: {', '.join(required_cols)}"
            )
        
        # Convert DataFrame to list of dicts
        questions_data = df.to_dict("records")
        
        if not questions_data:
            raise ValueError("File contains no data rows")
        
        logger.info(f"Parsed {len(questions_data)} questions from file")
        
        # Call repository method to create mock test
        from infrastructure.repositories.mock_test_repo_impl import bulk_create_mock_test
        
        mock_test = bulk_create_mock_test(
            db=db,
            title=mock_test_title,
            questions_data=questions_data,
            admin_id=admin["user_id"]
        )
        
        return MockTestOut(
            id=mock_test.id,
            title=mock_test.title,
            total_questions=len(mock_test.questions),
        )

    except ValueError as e:
        logger.warning(f"Bulk upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bulk upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== SUBJECT MANAGEMENT ====================


@router.post("/subjects", response_model=SubjectOut)
def add_subject(
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Create a new subject"""
    try:
        logger.info(f"Admin {admin['user_id']} creating subject: {subject.name}")
        result = create_subject(db, subject)
        return result
    except ValueError as e:
        logger.warning(f"Subject creation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Subject creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), admin: dict = Depends(admin_required)):
    """Get all subjects"""
    try:
        logger.info(f"Admin {admin['user_id']} fetching all subjects")
        subjects = get_all_subjects(db)
        return subjects
    except Exception as e:
        logger.error(f"Error fetching subjects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/subjects/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Get a specific subject by ID"""
    try:
        logger.info(f"Admin {admin['user_id']} fetching subject {subject_id}")
        subject = get_subject_by_id(db, subject_id)
        return subject
    except ValueError as e:
        logger.warning(f"Subject not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching subject: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put("/subjects/{subject_id}", response_model=SubjectOut)
def modify_subject(
    subject_id: int,
    subject: SubjectCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Update a subject"""
    try:
        logger.info(f"Admin {admin['user_id']} updating subject {subject_id}")
        result = update_subject(db, subject_id, subject)
        return result
    except ValueError as e:
        logger.warning(f"Subject update error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating subject: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/subjects/{subject_id}")
def remove_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Delete a subject (will fail if topics/MCQs/mock tests are associated with it)"""
    try:
        logger.info(f"Admin {admin['user_id']} deleting subject {subject_id}")
        result = delete_subject(db, subject_id)
        return result
    except ValueError as e:
        logger.warning(f"Subject deletion error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting subject: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==================== TOPIC MANAGEMENT ====================


@router.post("/topics", response_model=TopicOut)
def add_topic(
    topic: TopicCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Create a new topic for organizing MCQs"""
    try:
        logger.info(
            f"Admin {admin['user_id']} creating topic: {topic.name} for subject_id: {topic.subject_id}"
        )
        result = create_topic(db, topic)
        return result
    except ValueError as e:
        logger.warning(f"Topic creation validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Topic creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/topics", response_model=list[TopicOut])
def list_topics(
    subject_id: int | None = Query(None),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Get all topics, optionally filtered by subject_id"""
    try:
        if subject_id:
            logger.info(
                f"Admin {admin['user_id']} fetching topics for subject_id: {subject_id}"
            )
            topics = get_topics_by_subject(db, subject_id)
        else:
            logger.info(f"Admin {admin['user_id']} fetching all topics")
            topics = get_all_topics(db)
        return topics
    except Exception as e:
        logger.error(f"Error fetching topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/topics/{topic_id}", response_model=TopicOut)
def get_topic(
    topic_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    """Get a specific topic by ID"""
    try:
        logger.info(f"Admin {admin['user_id']} fetching topic {topic_id}")
        topic = get_topic_by_id(db, topic_id)
        return topic
    except ValueError as e:
        logger.warning(f"Topic not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put("/topics/{topic_id}", response_model=TopicOut)
def modify_topic(
    topic_id: int,
    topic: TopicCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    """Update a topic"""
    try:
        logger.info(f"Admin {admin['user_id']} updating topic {topic_id}")
        result = update_topic(db, topic_id, topic)
        return result
    except ValueError as e:
        logger.warning(f"Topic update error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/topics/{topic_id}")
def remove_topic(
    topic_id: int, db: Session = Depends(get_db), admin: dict = Depends(admin_required)
):
    """Delete a topic (will fail if MCQs are associated with it)"""
    try:
        logger.info(f"Admin {admin['user_id']} deleting topic {topic_id}")
        result = delete_topic(db, topic_id)
        return result
    except ValueError as e:
        logger.warning(f"Topic deletion error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting topic: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


