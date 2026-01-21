import logging
from sqlalchemy.orm import Session
from ..db.models import AttemptModel
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class AttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        session_id: int,
        mcq_id: int,
        selected_option_id: int,
        is_correct: bool
    ) -> AttemptModel:
        """Record an answer attempt."""
        try:
            attempt = AttemptModel(
                user_id=user_id,
                practice_session_id=session_id,
                mcq_id=mcq_id,
                selected_option_id=selected_option_id,
                is_correct=is_correct,
                mode="practice"
            )
            self.db.add(attempt)
            self.db.commit()
            self.db.refresh(attempt)
            return attempt
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating attempt for user {user_id}, session {session_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not record attempt")

    def get_by_session(self, session_id: int, user_id: int):
        """Fetch all attempts of a session for a user."""
        try:
            return (
                self.db.query(AttemptModel)
                .filter(
                    AttemptModel.practice_session_id == session_id,
                    AttemptModel.user_id == user_id
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching attempts for session {session_id}, user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not fetch attempts")
