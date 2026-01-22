from abc import ABC, abstractmethod
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

class MockTestRepository(ABC):

    @abstractmethod
    def get_mock_test_with_subjects(self, db: Session, mock_test_id: int):
        pass

    @abstractmethod
    def create_session(
        self,
        db: Session,
        user_id: int,
        mock_test_id: int,
        started_at: datetime,
        expires_at: datetime,
    ):
        pass

    @abstractmethod
    def add_session_questions(
        self,
        db: Session,
        session_id: int,
        questions_data: list[dict],
    ):
        pass

    @abstractmethod
    def get_active_session(
        self, db: Session, session_id: int, user_id: int
    ):
        pass

    @abstractmethod
    def get_active_session_for_user_test(
        self, db: Session, user_id: int, mock_test_id: int
    ):
        pass

    @abstractmethod
    def get_session_questions(
        self, db: Session, session_id: int
    ):
        pass

    @abstractmethod
    def upsert_answer(
        self,
        db: Session,
        session_id: int,
        mcq_id: int,
        selected_option_id: Optional[int],
    ):
        pass

    @abstractmethod
    def get_session_answers(self, db: Session, session_id: int):
        pass

    @abstractmethod
    def mark_session_submitted(
        self, db: Session, session_id: int
    ):
        pass
    
    @abstractmethod
    def get_session_by_id(self, db: Session, session_id: int):
        pass
