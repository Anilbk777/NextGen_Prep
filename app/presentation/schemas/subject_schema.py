from pydantic import BaseModel,Field, field_validator
from typing import Optional

# ------------------ Subject Schemas ------------------

class PracticeSubjectCreate(BaseModel):
    name: str = Field(..., min_length=1,max_length=300)
    description: Optional[str] = None

    # convert the name of the subject to title case 
    @field_validator("name", mode="before")
    def title_case(cls, v):
        return v.title()

class PracticeSubjectOut(BaseModel):
    id: int
    name: str = Field(..., min_length=1,max_length=300)
    description: Optional[str] = None

    # convert the name of the subject to title case
    @field_validator("name", mode="before")
    def title_case(cls, v):
        return v.title()

    class Config:
        from_attributes = True
