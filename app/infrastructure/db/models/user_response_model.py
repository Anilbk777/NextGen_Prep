
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Boolean, String, UniqueConstraint
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint


# ---------------------------
# 11. User Responses
# ---------------------------
class UserResponse(Base):
    __tablename__ = "user_responses"
    
    response_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("learning_sessions.session_id"), nullable=True)
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    template_id = Column(Integer, ForeignKey("templates.template_id"))
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"))
    selected_option = Column(Integer)
    correct = Column(Boolean)
    misconception_detected = Column(String(200))
    response_time = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserModel", back_populates="responses")
    session = relationship("LearningSession", back_populates="responses")
    question = relationship("Question", back_populates="responses")
    template = relationship("Template", back_populates="responses")
    concept = relationship("Concept", back_populates="responses")

    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_response"),
    )
