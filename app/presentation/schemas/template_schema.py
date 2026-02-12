from pydantic import BaseModel
from typing import Optional, List

class TemplateBase(BaseModel):
    intent: Optional[str] = None
    learning_objective: Optional[str] = None
    question_style: Optional[str] = "conceptual"
    target_difficulty: Optional[float] = 0.5
    correct_reasoning: Optional[str] = None
    misconception_patterns: Optional[List[str]] = []
    answer_format: Optional[str] = "MCQ"

class TemplateCreate(TemplateBase):
    concept_id: int

class TemplateOut(TemplateBase):
    template_id: int
    concept_id: int

    class Config:
        from_attributes = True
