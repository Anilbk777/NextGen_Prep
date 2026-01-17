from pydantic import BaseModel, Field
from typing import Optional

class NoteCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Title of the note"
    )

class NoteResponse(BaseModel):
    id:int
    topic_id: int
    title:str
    file_path: str
    file_size: int
    mime_type:str

    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Updated title of the note"
    )

    file_path: Optional[str] = Field(
        None, description="Updated file path (internal use only)"
    )

    file_size: Optional[int] = Field(
        None, gt=0, description="Updated file size in bytes"
    )

    mime_type: Optional[str] = Field(
        None, max_length=100, description="Updated MIME type of the note file"
    )

    class Config:
        extra = "forbid"  # reject unknown fields
