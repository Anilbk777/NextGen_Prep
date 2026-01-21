from pydantic import BaseModel,Field, field_validator
from typing import Optional

# ------------------ Topic Schemas ------------------

class TopicCreate(BaseModel):
    name: str = Field(..., min_length=1,max_length=300)

    # convert the name of the topic to title case 
    @field_validator("name", mode="before")
    def title_case(cls, v):
        return v.title()

    

class TopicOut(BaseModel):
    id: int 
    name: str = Field(..., min_length=1,max_length=300)
    subject_id: int = Field(..., gt=0)

    # convert the name of the topic to title case 
    @field_validator("name", mode="before")
    def title_case(cls, v):
        return v.title()

    class Config:
        from_attributes = True
