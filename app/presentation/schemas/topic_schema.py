from pydantic import BaseModel
from typing import Optional

# ------------------ Topic Schemas ------------------

class TopicCreate(BaseModel):
    name: str
    subject_id: int

class TopicOut(BaseModel):
    id: int
    name: str
    subject_id: int

    class Config:
        from_attributes = True
