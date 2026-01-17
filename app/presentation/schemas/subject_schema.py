from pydantic import BaseModel
from typing import Optional

# ------------------ Subject Schemas ------------------

class SubjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SubjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_from_mock_test: bool = False

    class Config:
        from_attributes = True
