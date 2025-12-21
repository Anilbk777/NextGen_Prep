import pandas as pd
from typing import List
from infrastructure.repositories.mcq_repo_impl import create_mcq
from presentation.schemas.mcq_schema import MCQCreate, OptionCreate
from presentation.schemas.bulk_mcq_schema import MCQBulkUploadMeta
from sqlalchemy.orm import Session
import logging
import io

logger = logging.getLogger(__name__)

def process_bulk_upload(db: Session, file_content: bytes, filename: str, meta: MCQBulkUploadMeta, admin_id: int):
    try:
        logger.info(f"Processing bulk upload: {filename} for subject {meta.subject}")
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            raise ValueError("Unsupported file format. Please upload CSV or XLSX.")

        # Clean column names
        df.columns = [c.strip().lower() for c in df.columns]
        
        required_cols = ['question_text', 'option1', 'option2', 'option3', 'option4', 'correct_answer']
        # Note: explanation is only mandatory for practice if the user wants it, 
        # but we'll check it if it's practice mode as per user request.
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        inserted = 0
        failed = 0
        errors = []

        for index, row in df.iterrows():
            try:
                options = [
                    OptionCreate(option_text=str(row['option1']), is_correct=False),
                    OptionCreate(option_text=str(row['option2']), is_correct=False),
                    OptionCreate(option_text=str(row['option3']), is_correct=False),
                    OptionCreate(option_text=str(row['option4']), is_correct=False),
                ]

                # correct_answer can be 1, 2, 3, 4 (as index) or the text itself
                correct_val = str(row['correct_answer']).strip()
                correct_idx = -1
                
                # Check if it's a number 1-4
                if correct_val in ['1', '2', '3', '4', '1.0', '2.0', '3.0', '4.0']:
                    correct_idx = int(float(correct_val)) - 1
                else:
                    # try to match text exactly
                    for i, opt in enumerate(options):
                        if opt.option_text == correct_val:
                            correct_idx = i
                            break
                
                if correct_idx < 0 or correct_idx >= 4:
                    raise ValueError(f"Correct answer '{correct_val}' not valid (must be 1-4 or match an option text)")
                
                options[correct_idx].is_correct = True

                explanation_val = None
                if 'explanation' in df.columns and not pd.isna(row['explanation']):
                    explanation_val = str(row['explanation'])

                mcq_data = MCQCreate(
                    question_text=str(row['question_text']),
                    explanation=explanation_val if meta.is_practice_only else None, # Only store for practice mode
                    subject=meta.subject,
                    is_practice_only=meta.is_practice_only,
                    options=options
                )

                create_mcq(db, mcq_data, admin_id)
                inserted += 1
            except Exception as e:
                failed += 1
                errors.append(f"Row {index + 2}: {str(e)}")

        logger.info(f"Bulk upload finished. Inserted: {inserted}, Failed: {failed}")
        return {
            "total_rows": len(df),
            "inserted": inserted,
            "failed": failed,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Bulk upload process failed: {e}", exc_info=True)
        raise
