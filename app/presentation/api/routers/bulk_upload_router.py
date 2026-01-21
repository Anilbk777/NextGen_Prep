from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from presentation.dependencies import get_db, admin_required

from presentation.schemas.practice_bulk_schema import (
    PracticeBulkUploadMeta,
    PracticeBulkUploadResponse,
)
from infrastructure.repositories.practice_bulk_repo_impl import PracticeBulkRepository
from infrastructure.repositories.mock_test_repo_impl import MockTestRepository
from presentation.schemas.mock_test_schema import (
    MockTestOut,
    MockTestBulkCreate,
    QuestionCreate,
    OptionCreate
)

import logging
import pandas as pd
import io
from pydantic import ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bulk-upload", tags=["bulk_uplod_mcqs"])

@router.post("/practice", response_model=PracticeBulkUploadResponse)
async def bulk_upload_practice(
    topic_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(admin_required),
):
    try:
        logger.info(
            f"Admin {admin['user_id']} bulk uploading practice MCQs for topic_id: {topic_id}"
        )

        file_content = await file.read()
        repo = PracticeBulkRepository(db)
        return repo.process_bulk_upload(
            file_content, file.filename, topic_id, admin["user_id"]
        )

    except ValueError as e:
        logger.warning(f"Bulk upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Bulk upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/mock-test", response_model=MockTestOut)
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
        required_cols = [
            "subject",
            "question_text",
            "option1",
            "option2",
            "option3",
            "option4",
            "correct_answer",
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            raise ValueError(
                f"Missing required columns in file: {', '.join(missing_cols)}. "
                f"Expected columns: {', '.join(required_cols)}"
            )

        # Basic data cleaning: drop completely empty rows and handle NaNs
        df = df.dropna(subset=["question_text", "correct_answer"], how="any")
        questions_data = df.to_dict("records")

        if not questions_data:
            raise ValueError("File contains no valid data rows (question_text and correct_answer are required)")

        logger.info(f"Parsed {len(questions_data)} valid questions from file")

        # Call repository method to create mock test
        try:
            # Prepare validated data for repository
            validated_questions = []
            for q in questions_data:
                # Helper to get string safely
                def get_str(key):
                    val = q.get(key)
                    return str(val).strip() if not pd.isna(val) else ""

                # Determine which option is correct
                correct_val = get_str("correct_answer")
                
                options = []
                for i in range(1, 5):
                    opt_text = get_str(f"option{i}")
                    # Correct if matches "1", "2", "3", "4" or exact text
                    # We handle the case where correct_val might be "1.0" from Excel
                    is_correct = False
                    try:
                        if float(correct_val) == float(i):
                            is_correct = True
                    except ValueError:
                        if correct_val == opt_text:
                            is_correct = True
                    
                    options.append(OptionCreate(text=opt_text, is_correct=is_correct))
                
                validated_questions.append(QuestionCreate(
                    subject=get_str("subject"),
                    question_text=get_str("question_text"),
                    options=options
                ))
            
            bulk_data = MockTestBulkCreate(title=mock_test_title, questions=validated_questions)
            
            repo = MockTestRepository(db)
            mock_test = repo.bulk_create_mock_test(
                data=bulk_data,
                admin_id=admin["user_id"]
            )
            
            return MockTestOut(
                id=mock_test.id,
                title=mock_test.title,
                total_questions=len(mock_test.questions),
            )
        except ValidationError as e:
            logger.warning(f"Schema validation error: {e}")
            # Format Pydantic errors for easier reading
            errors = []
            for error in e.errors():
                loc = " -> ".join(str(l) for l in error['loc'])
                errors.append(f"{loc}: {error['msg']}")
            raise HTTPException(status_code=400, detail={"msg": "Data validation failed", "errors": errors})

    except ValueError as e:
        logger.warning(f"Bulk upload validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
