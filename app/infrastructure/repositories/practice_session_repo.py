import logging
from sqlalchemy.orm import Session
from ..db.models import PracticeSessionModel, PracticeSessionQuestionModel
from fastapi import HTTPException
from datetime import datetime

logger = logging.getLogger(__name__)

class PracticeSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, topic_id: int) -> PracticeSessionModel:
        """Create a new session."""
        try:
            session = PracticeSessionModel(
                user_id=user_id,
                topic_id=topic_id
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating practice session for user {user_id}, topic {topic_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not create practice session")

    def add_questions(self, session_id: int, mcqs: list[object]):
        """Add ordered MCQs to session."""
        try:
            mappings = [
                PracticeSessionQuestionModel(
                    practice_session_id=session_id,
                    mcq_id=mcq.id,
                    order_index=i
                )
                for i, mcq in enumerate(mcqs)
            ]
            self.db.add_all(mappings)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding questions to session {session_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not add questions to session")

    def get_active(self, session_id: int, user_id: int) -> PracticeSessionModel:
        """Fetch active session for a user."""
        try:
            session = (
                self.db.query(PracticeSessionModel)
                .filter(
                    PracticeSessionModel.id == session_id,
                    PracticeSessionModel.user_id == user_id,
                    PracticeSessionModel.is_active == True
                )
                .first()
            )
            if not session:
                logger.warning(f"Active session {session_id} not found for user {user_id}")
                raise HTTPException(status_code=404, detail="Active session not found")
            return session
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching active session {session_id} for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error while fetching session")

    def close(self, session: PracticeSessionModel):
        try:
            session.is_active = False
            session.ended_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error closing session {session.id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Could not close session")
