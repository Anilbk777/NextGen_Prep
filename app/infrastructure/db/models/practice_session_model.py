from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

class PracticeSessionModel(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    total_questions = Column(Integer, default=10)
    current_index = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("UserModel")
    topic = relationship("Topic")

    attempts = relationship(
        "AttemptModel",
        back_populates="practice_session",
        cascade="all, delete-orphan"
    )

    questions = relationship(
        "PracticeSessionQuestionModel",
        back_populates="practice_session",
        cascade="all, delete-orphan",
        order_by="PracticeSessionQuestionModel.order_index"
    )


from sqlalchemy import UniqueConstraint

class PracticeSessionQuestionModel(Base):
    __tablename__ = "practice_session_questions"

    id = Column(Integer, primary_key=True)

    practice_session_id = Column(
        Integer, ForeignKey("practice_sessions.id"), nullable=False
    )
    mcq_id = Column(Integer, ForeignKey("practice_mcqs.id"), nullable=False)

    order_index = Column(Integer, nullable=False)  # 0–9

    __table_args__ = (
        UniqueConstraint(
            "practice_session_id", "mcq_id",
            name="uq_session_mcq"
        ),
        UniqueConstraint(
            "practice_session_id", "order_index",
            name="uq_session_order"
        ),
    )

    # Relationships
    practice_session = relationship(
        "PracticeSessionModel",
        back_populates="questions"
    )

    mcq = relationship(
        "PracticeMCQ",
        back_populates="practice_session_questions"
    )
    
