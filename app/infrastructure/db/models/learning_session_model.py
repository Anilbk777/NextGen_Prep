
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime

# ---------------------------
# Update Learning Session to use Topic instead of Chapter
# ---------------------------
class LearningSession(Base):
    __tablename__ = "learning_sessions"
    
    session_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("practice_subjects.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    questions_attempted = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    
    user = relationship("UserModel", back_populates="sessions")
    subject = relationship("PracticeSubject", back_populates="sessions")
    topic = relationship("Topic", back_populates="sessions")
    responses = relationship("UserResponse", back_populates="session", cascade="all, delete-orphan")

    