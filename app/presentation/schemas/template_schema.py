from pydantic import BaseModel
from typing import Optional, Dict, Any

class TemplateBase(BaseModel):
    learning_objective: Optional[str] = None
    target_difficulty: Optional[float] = 0.5
    question_style: Optional[str] = "conceptual"
    answer_format: Optional[str] = "MCQ"
    config_metadata: Optional[Dict[str, Any]] = {}

class TemplateCreate(TemplateBase):
    concept_id: int
    topic_id: int

class TemplateOut(TemplateBase):
    template_id: int
    concept_id: int
    topic_id: int

    class Config:
        from_attributes = True
