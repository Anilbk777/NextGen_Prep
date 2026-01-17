import pandas as pd
from typing import List, Tuple
from infrastructure.repositories.mcq_repo_impl import create_mcq
from presentation.schemas.mcq_schema import MCQCreate, OptionCreate
from sqlalchemy.orm import Session
import logging
import io

logger = logging.getLogger(__name__)

from presentation.schemas.bulk_mcq_schema import (
    PracticeBulkUploadMeta,
    MockTestBulkUploadMeta,
    BulkUploadResponse,
)
from infrastructure.repositories.mock_test_repo_impl import create_mock_test
from presentation.schemas.mock_test_schema import MockTestCreate


def process_practice_bulk_upload(
    db: Session,
    file_content: bytes,
    filename: str,
    meta: PracticeBulkUploadMeta,
    admin_id: int,
):
    """Process bulk upload for practice mode"""
    df = _read_and_clean_df(file_content, filename)

    # Strict validation for practice mode
    required_cols = [
        "question_text",
        "option1",
        "option2",
        "option3",
        "option4",
        "correct_answer",
        "explanation",
        "difficulty",
    ]
    _validate_columns(df, required_cols, "practice")

    response, _created_ids = _process_rows(
        db, df, meta.subject_id, meta.topic_id, True, None, admin_id
    )
    return response


def process_mock_bulk_upload(
    db: Session,
    file_content: bytes,
    filename: str,
    meta: MockTestBulkUploadMeta,
    admin_id: int,
):
    # This function replaces the placeholder above
    df = _read_and_clean_df(file_content, filename)
    required_cols = [
        "question_text",
        "option1",
        "option2",
        "option3",
        "option4",
        "correct_answer",
    ]
    _validate_columns(df, required_cols, "mock test")

    fallback_subject_id = meta.subject_id if meta.subject_id else 1

    # Process rows
    response, created_ids = _process_rows(
        db, df, fallback_subject_id, None, False, None, admin_id
    )

    if created_ids:
        mock_test_data = MockTestCreate(
            title=meta.mock_test_title, subject_id=meta.subject_id, mcq_ids=created_ids
        )
        create_mock_test(db, mock_test_data)
        logger.info(
            f"Created mocked test '{meta.mock_test_title}' with {len(created_ids)} MCQs"
        )

    return response


def _read_and_clean_df(file_content: bytes, filename: str) -> pd.DataFrame:
    if filename.endswith(".csv"):
        # Robust CSV parsing
        try:
            df = pd.read_csv(
                io.BytesIO(file_content), on_bad_lines="skip", engine="python"
            )
        except Exception as e:
            raise ValueError(f"Error parsing CSV: {e}")
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_content))
    else:
        raise ValueError("Unsupported file format. Please upload CSV or XLSX.")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    return df


def _validate_columns(df: pd.DataFrame, required_cols: list[str], mode: str):
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns for {mode} mode: {', '.join(missing_cols)}"
        )


def _process_rows(
    db: Session,
    df: pd.DataFrame,
    subject_id: int,
    topic_id: int | None,
    is_practice: bool,
    difficulty: str | None,
    admin_id: int,
) -> Tuple[BulkUploadResponse, list]:
    inserted = 0
    failed = 0
    errors = []
    created_mcq_ids = []

    for index, row in df.iterrows():
        try:
            # Create options
            options = [
                OptionCreate(option_text=str(row["option1"]), is_correct=False),
                OptionCreate(option_text=str(row["option2"]), is_correct=False),
                OptionCreate(option_text=str(row["option3"]), is_correct=False),
                OptionCreate(option_text=str(row["option4"]), is_correct=False),
            ]

            # Determine correct answer
            correct_val = str(row["correct_answer"]).strip()
            correct_idx = -1
            if correct_val in ["1", "2", "3", "4", "1.0", "2.0", "3.0", "4.0"]:
                correct_idx = int(float(correct_val)) - 1
            else:
                for i, opt in enumerate(options):
                    if opt.option_text == correct_val:
                        correct_idx = i
                        break

            if correct_idx < 0 or correct_idx >= 4:
                raise ValueError(f"Invalid correct_answer: {correct_val}")

            options[correct_idx].is_correct = True

            # Get explanation/difficulty only provided in df (handled in validation)
            expl = (
                str(row["explanation"])
                if "explanation" in df.columns and not pd.isna(row["explanation"])
                else None
            )
            diff = (
                str(row["difficulty"])
                if "difficulty" in df.columns and not pd.isna(row["difficulty"])
                else None
            )

            mcq_data = MCQCreate(
                question_text=str(row["question_text"]),
                explanation=expl,
                subject_id=subject_id,
                topic_id=topic_id,
                difficulty=diff,
                is_practice_only=is_practice,
                options=options,
            )

            created_mcq = create_mcq(db, mcq_data, admin_id)
            created_mcq_ids.append(created_mcq.id)
            inserted += 1

        except Exception as e:
            failed += 1
            errors.append(f"Row {index + 2}: {str(e)}")
            logger.error(f"Error processing row {index + 2}: {e}")

    # For mock upload, we might need these IDs, but BulkUploadResponse doesn't support returning them yet.
    # We can add a specialized response or just handle it.
    # For now, let's just return the standard response.
    # UPDATE: We need to return IDs for mock test creation!
    # Let's attach them to the response object dynamically or return a tuple?
    # To keep it clean, let's return the response object.
    # The caller (mock process function) needs the IDs.
    # Wait, `process_mock_bulk_upload` calls this.

    response = BulkUploadResponse(
        total_rows=len(df),
        inserted=inserted,
        failed=failed,
        skipped=0,  # Simplified for now
        errors=errors,
    )

    return response, created_mcq_ids
