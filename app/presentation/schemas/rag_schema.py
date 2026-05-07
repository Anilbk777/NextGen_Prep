from pydantic import BaseModel
from typing import List, Optional

class RAGQuery(BaseModel):
    query: str

class RAGResponse(BaseModel):
    final_answer: str
    succeeded: bool
    revision_attempt: int
    best_score: float
    retrieval_used: bool
    current_query: str

class ChatHistoryResponse(BaseModel):
    id: int
    user_query: str
    content: str
    created_at: str

    class Config:
        from_attributes = True
