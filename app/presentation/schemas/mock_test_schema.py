from pydantic import BaseModel
from typing import List


class MockTestCreate(BaseModel):
    title: str
    subject: str
    mcq_ids: List[int]


class MockTestOut(BaseModel):
    id: int
    title: str
    subject: str
    total_questions: int
