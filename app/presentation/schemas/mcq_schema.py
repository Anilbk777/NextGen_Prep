from pydantic import BaseModel, Field, model_validator
from typing import List, Optional

class PracticeOptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1,max_length=300)
    is_correct: bool = Field(...)


class PracticeOptionOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool

    class Config:
        from_attributes = True


class PracticeMCQCreate(BaseModel):
    question_text: str = Field(...,min_length=1, max_length=300, description="MCQ question text")
    explanation: Optional[str] = Field(
        None, max_length=300, description="Optional explanation for the answer"
    )
    difficulty: Optional[str] = Field(
        None, description="Difficulty level (easy, medium, hard)"
    )
    options: List[PracticeOptionCreate] = Field(
        ..., min_length=4, max_length=4, description="Exactly 4 options required"
    )

    @model_validator(mode="after")
    def validate_correct_option(self):
        correct_count = sum(option.is_correct for option in self.options )
        if correct_count != 1:
            raise ValueError("Exactly one option must be marked as correct")
        return self

# ===========================update mcq========================================

class OptionUpdate(BaseModel):
    option_text: str = Field(..., min_length=1)
    is_correct: bool


class PracticeMCQUpdate(BaseModel):
    question_text: Optional[str]
    explanation: Optional[str]
    difficulty: Optional[str]
    # topic_id: Optional[int]
    options: Optional[List[OptionUpdate]]

    @model_validator(mode="after")
    def validate_options(self):
        if self.options is None:
            return self  # options not being updated

        if len(self.options) != 4:
            raise ValueError("Exactly 4 options are required")

        correct_count = sum(opt.is_correct for opt in self.options)
        if correct_count != 1:
            raise ValueError("Exactly one option must be correct")

        return self

# ================================Mock test=======================================================

class MockTestOptionCreate(BaseModel):
    option_text: str
    is_correct: bool 


class MockTestOptionOut(BaseModel):
    id: int
    option_text: str

    class Config:
        from_attributes = True


class MockTestOptionResultOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool  


class PracticeMCQOut(BaseModel):
    id: int
    question_text: str
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    topic_id: int
    options: List[PracticeOptionOut]

    class Config:
        from_attributes = True


class MockTestMCQOut(BaseModel):
    id: int
    question_text: str
    subject_id: Optional[int]
    options: List[MockTestOptionOut]

    class Config:
        from_attributes = True
