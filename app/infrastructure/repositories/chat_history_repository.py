from sqlalchemy.orm import Session
from ..db.models.chat_history_model import ChatHistoryModel
from typing import List

class ChatHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user_id: int, user_query: str, content: str) -> ChatHistoryModel:
        """
        Add a new chat record to the database.
        """
        chat_entry = ChatHistoryModel(
            user_id=user_id,
            user_query=user_query,
            content=content
        )
        self.db.add(chat_entry)
        self.db.commit()
        self.db.refresh(chat_entry)
        return chat_entry

    def get_by_user_id(self, user_id: int, limit: int = 50) -> List[ChatHistoryModel]:
        """
        Fetch chat history for a specific user, ordered by most recent first.
        """
        return (
            self.db.query(ChatHistoryModel)
            .filter(ChatHistoryModel.user_id == user_id)
            .order_by(ChatHistoryModel.created_at.desc())
            .limit(limit)
            .all()
        )
