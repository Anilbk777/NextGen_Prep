from pydantic import BaseModel, Field, field_validator
from typing import List


class OptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1, max_length=300)
    is_correct: bool = Field(...)


class QuestionCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    question_text: str = Field(..., min_length=1, max_length=500)
    options: List[OptionCreate] = Field(..., min_items=4, max_items=4)

    @field_validator("options")
    def validate_options(cls, v):
        correct_count = sum(opt.is_correct for opt in v)
        if correct_count != 1:
            raise ValueError("Exactly one option must be marked as correct")
        return v
        
    @field_validator("subject")
    def validate_subject(cls, v):
        if not v:
            raise ValueError("Subject cannot be empty")
        v = v.strip().title()
        return v


class MockTestBulkCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    questions: List[QuestionCreate] = Field(..., min_items=1)


class MockTestOut(BaseModel):
    id: int
    title: str
    total_questions: int

    class Config:
        from_attributes = True
