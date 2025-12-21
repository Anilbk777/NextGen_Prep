# mcq_schema.py
from pydantic import BaseModel
from typing import List

class OptionCreate(BaseModel):
    option_text: str
    is_correct: bool

class OptionOut(BaseModel):
    id: int
    option_text: str

class MCQCreate(BaseModel):
    question_text: str
    explanation: str = None
    subject: str
    is_practice_only: bool = False
    options: List[OptionCreate]

class OptionPracticeOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool

class MCQUserPracticeOut(BaseModel):
    id: int
    question_text: str
    explanation: str = None
    subject: str
    options: List[OptionPracticeOut]

    class Config:
        from_attributes = True

class MCQUserMockOut(BaseModel):
    id: int
    question_text: str
    explanation: str = None
    subject: str
    options: List[OptionOut]

    class Config:
        from_attributes = True

class MCQOut(BaseModel):
    id: int
    question_text: str
    explanation: str = None
    subject: str
    is_practice_only: bool
    options: List[OptionCreate] # Admin sees everything

    class Config:
        from_attributes = True
