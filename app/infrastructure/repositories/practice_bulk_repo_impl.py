import pandas as pd
import io
import logging
from typing import Tuple, List
from sqlalchemy.orm import Session
from infrastructure.db.models.mcq_model import PracticeMCQ, OptionModel
from infrastructure.db.models.topic_model import Topic
from presentation.schemas.mcq_schema import PracticeMCQCreate, PracticeOptionCreate
from presentation.schemas.practice_bulk_schema import PracticeBulkUploadResponse
from infrastructure.repositories.mcq_repo_impl import create_mcq

logger = logging.getLogger(__name__)

class PracticeBulkRepository:
    def __init__(self, db: Session):
        self.db = db

    def process_bulk_upload(
        self,
        file_content: bytes,
        filename: str,
        topic_id: int,
        admin_id: int,
    ):
        """Process bulk upload for practice mode"""
        try:
            # 1. Verify Topic exists
            topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                raise ValueError(f"Target Topic with ID {topic_id} does not exist.")

            df = self._read_and_clean_df(file_content, filename)
            
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
            self._validate_columns(df, required_cols)

            response = self._process_rows(
                df, topic_id, admin_id
            )
            return response
        except Exception as e:
            logger.error(f"Bulk upload error: {e}", exc_info=True)
            raise

    def _read_and_clean_df(self, file_content: bytes, filename: str) -> pd.DataFrame:
        if filename.endswith(".csv"):
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

    def _validate_columns(self, df: pd.DataFrame, required_cols: List[str]):
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Missing required columns for practice mode: {', '.join(missing_cols)}"
            )

    def _process_rows(
        self,
        df: pd.DataFrame,
        topic_id: int,
        admin_id: int,
    ) -> PracticeBulkUploadResponse:
        inserted = 0
        failed = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Basic row cleaning
                def get_val(key):
                    val = row.get(key)
                    return str(val).strip() if not pd.isna(val) else ""

                # Create options
                options = [
                    PracticeOptionCreate(option_text=get_val("option1"), is_correct=False),
                    PracticeOptionCreate(option_text=get_val("option2"), is_correct=False),
                    PracticeOptionCreate(option_text=get_val("option3"), is_correct=False),
                    PracticeOptionCreate(option_text=get_val("option4"), is_correct=False),
                ]

                # Determine correct answer
                correct_val = get_val("correct_answer")
                correct_idx = -1
                
                # Check if it's a numeric index (1-4)
                try:
                    num_val = int(float(correct_val))
                    if 1 <= num_val <= 4:
                        correct_idx = num_val - 1
                except (ValueError, TypeError):
                    # Match by text
                    for i, opt in enumerate(options):
                        if opt.option_text == correct_val:
                            correct_idx = i
                            break

                if correct_idx < 0:
                    raise ValueError(f"Invalid correct_answer: '{correct_val}' does not match any option or 1-4 index")

                options[correct_idx].is_correct = True

                # Explanation and Difficulty
                expl = get_val("explanation") or None
                diff = get_val("difficulty").lower() or None

                mcq_data = PracticeMCQCreate(
                    question_text=get_val("question_text"),
                    explanation=expl,
                    topic_id=topic_id,
                    difficulty=diff,
                    options=options,
                )

                # Use the existing create_mcq function which handles the DB storage
                create_mcq(self.db, topic_id, mcq_data)
                inserted += 1

            except Exception as e:
                failed += 1
                errors.append(f"Row {index + 2}: {str(e)}")
                logger.error(f"Error processing row {index + 2}: {e}")

        return PracticeBulkUploadResponse(
            total_rows=len(df),
            inserted=inserted,
            failed=failed,
            skipped=0,
            errors=errors,
        )
