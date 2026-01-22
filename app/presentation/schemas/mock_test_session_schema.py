from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class OptionSchema(BaseModel):
    id: int
    option_text: str = Field(..., alias="option_text")
    is_correct: Optional[bool] = Field(None, alias="is_correct")
    
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class AnswerRequest(BaseModel):
    mcq_id: int
    selected_option_id: Optional[int] = Field(None, description="None if skipped or cleared")

class QuestionResponse(BaseModel):
    mcq_id: int
    question_text: str
    options: List[OptionSchema]
    answered_option_id: Optional[int] = None
    order_index: int
    subject_name: str

    model_config = ConfigDict(from_attributes=True)

class MockTestResultResponse(BaseModel):
    total_questions: int
    correct: int
    incorrect: int
    skipped: int

class StartSessionResponse(BaseModel):
    session_id: int = Field(..., alias="id")
    ends_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
