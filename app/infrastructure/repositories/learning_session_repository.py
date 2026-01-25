from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from ..db.models import LearningSession

class LearningSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int, subject_id: int, topic_id: int) -> LearningSession:
        session = LearningSession(
            user_id=user_id,
            subject_id=subject_id,
            topic_id=topic_id,
            start_time=datetime.utcnow(),
            questions_attempted=0,
            questions_correct=0
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_session(self, user_id: int, topic_id: int) -> Optional[LearningSession]:
        return (
            self.db.query(LearningSession)
            .filter(
                LearningSession.user_id == user_id,
                LearningSession.topic_id == topic_id,
                LearningSession.end_time == None
            )
            .order_by(LearningSession.start_time.desc())
            .first()
        )

    def get_session_by_id(self, session_id: int) -> Optional[LearningSession]:
        return self.db.query(LearningSession).filter(LearningSession.session_id == session_id).first()

    def update_session_metrics(self, session_id: int, correct: bool) -> None:
        session = self.get_session_by_id(session_id)
        if session:
            session.questions_attempted += 1
            if correct:
                session.questions_correct += 1
            self.db.commit()

    def end_session(self, session_id: int) -> Optional[LearningSession]:
        session = self.get_session_by_id(session_id)
        if session:
            session.end_time = datetime.utcnow()
            self.db.commit()
            self.db.refresh(session)
        return session
