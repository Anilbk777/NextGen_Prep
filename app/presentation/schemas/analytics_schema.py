from typing import List, Optional
from pydantic import BaseModel


class DailyPoint(BaseModel):
    date: str
    accuracy: float
    attempts: int


class SubjectProgress(BaseModel):
    subject_name: Optional[str]
    series: List[DailyPoint]
