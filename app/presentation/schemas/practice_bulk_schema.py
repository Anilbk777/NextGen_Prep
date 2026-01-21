from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class PracticeBulkUploadMeta(BaseModel):
    topic_id: int

class PracticeBulkUploadResponse(BaseModel):
    total_rows: int     
    inserted: int
    failed: int
    skipped: int = 0
    errors: List[str] = []

# class PracticeBulkRow(BaseModel):
#     question_text: str = Field(..., min_length=1)
#     option1: str = Field(..., min_length=1)
#     option2: str = Field(..., min_length=1)
#     option3: str = Field(..., min_length=1)
#     option4: str = Field(..., min_length=1)
#     correct_answer: str = Field(..., min_length=1)
#     explanation: Optional[str] = None
#     difficulty: Optional[str] = None

#     # validate correct_answer is from option1, option2, option3, or  option4
#     @field_validator("correct_answer")
#     def validate_correct_answer(cls, v):
#         if v not in ["option1", "option2", "option3", "option4"]:
#             raise ValueError("correct_answer must be from option1, option2, option3, or option4")
#         return v

