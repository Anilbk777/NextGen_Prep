from pydantic import BaseModel
from typing import List, Optional

class ConceptBase(BaseModel):
    name: str
    description: Optional[str] = None
    prerequisites: Optional[List[int]] = []

class ConceptCreate(ConceptBase):
    topic_id: int

class ConceptOut(ConceptBase):
    concept_id: int
    topic_id: int

    class Config:
        from_attributes = True
