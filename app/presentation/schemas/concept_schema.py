from pydantic import BaseModel
from typing import List, Optional, Any

class ConceptBase(BaseModel):
    name: str
    description: Optional[str] = None
    prerequisites: Optional[List[int]] = []
    common_misconceptions: Optional[List[str]] = []
    difficulty_level: Optional[int] = 1

class ConceptCreate(ConceptBase):
    topic_id: int

class ConceptOut(ConceptBase):
    concept_id: int
    topic_id: int

    class Config:
        from_attributes = True
