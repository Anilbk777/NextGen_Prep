# mock_test_schema.py
# from pydantic import BaseModel
# from typing import List, Optional


# class MockTestCreate(BaseModel):
#     title: str
#     subject_id: Optional[int] = None
#     mcq_ids: List[int]

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class MockTestCreate(BaseModel):
    title: str = Field(..., min_length=3)
    mcq_ids: List[int] = Field(..., min_length=1)

    @field_validator("mcq_ids")
    @classmethod
    def validate_mcq_ids(cls, mcq_ids):
        if len(set(mcq_ids)) != len(mcq_ids):
            raise ValueError("Duplicate MCQ IDs are not allowed")
        return mcq_ids


class MockTestOut(BaseModel):
    id: int
    title: str
    total_questions: int

    class Config:
        from_attributes = True


# ==================== Detailed Schemas for GET endpoint ====================

class OptionDetailOut(BaseModel):
    """Option with correct answer indicated"""
    id: int
    option_text: str
    is_correct: bool
    
    class Config:
        from_attributes = True


class QuestionDetailOut(BaseModel):
    """Question with all details including subject, options, and correct answer"""
    id: int
    question_text: str
    subject_name: str  # Subject name instead of just ID
    subject_id: int
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    options: List[OptionDetailOut]
    
    class Config:
        from_attributes = True


class MockTestDetailOut(BaseModel):
    """Detailed mock test with all questions and their details"""
    id: int
    title: str
    total_questions: int
    questions: List[QuestionDetailOut]
    
    class Config:
        from_attributes = True
