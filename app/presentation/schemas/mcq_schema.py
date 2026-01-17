from pydantic import BaseModel
from typing import List, Optional

# ------------------ Option Schemas ------------------

class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool  # Admin sets this

class OptionOut(BaseModel):
    id: int
    option_text: str  # User sees this

class OptionPracticeOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool  # Practice user sees correct instantly

# ------------------ MCQ Schemas ------------------

class MCQCreate(BaseModel):
    question_text: str
    explanation: Optional[str] = None
    subject_id: int
    topic_id: Optional[int] = None  # Optional for mock tests
    difficulty: Optional[str] = None   # Only for practice
    is_practice_only: bool = False
    options: List[OptionCreate]

class MCQOut(BaseModel):
    id: int
    question_text: str
    topic_id: Optional[int] = None
    explanation: Optional[str] = None
    subject_id: int
    is_practice_only: bool
    options: List[OptionCreate]  # Admin sees everything
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True

# ------------------ User View Schemas ------------------

class MCQUserPracticeOut(BaseModel):
    id: int
    question_text: str
    explanation: Optional[str] = None
    subject_id: int
    difficulty: Optional[str] = None  # Only practice
    options: List[OptionPracticeOut]

    class Config:
        from_attributes = True

class MCQUserMockOut(BaseModel):
    id: int
    question_text: str
    explanation: Optional[str] = None
    subject_id: int
    options: List[OptionOut]  # Correct answer hidden

    class Config:
        from_attributes = True
