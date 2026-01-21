from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

# class AttemptModel(Base):
#     __tablename__ = "attempts"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     mcq_id = Column(Integer, ForeignKey("practice_mcqs.id"), nullable=False)
#     selected_option_id = Column(Integer, ForeignKey("options.id"), nullable=False)
#     is_correct = Column(Boolean, nullable=False) # Computed at time of attempt
#     mode = Column(String, nullable=False) # 'practice' or 'mock_test'
#     attempted_at = Column(DateTime(timezone=True), server_default=func.now())

#     # Relationships
#     user = relationship("UserModel")
#     mcq = relationship("PracticeMCQ", back_populates="attempts")
#     selected_option = relationship("OptionModel")


class AttemptModel(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    practice_session_id = Column(
        Integer,
        ForeignKey("practice_sessions.id"),
        nullable=True
    )

    mcq_id = Column(Integer, ForeignKey("practice_mcqs.id"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("options.id"), nullable=False)

    is_correct = Column(Boolean, nullable=False)
    mode = Column(String, nullable=False)  # 'practice' | 'mock_test'

    attempted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("UserModel")
    mcq = relationship("PracticeMCQ", back_populates="attempts")
    selected_option = relationship("OptionModel")
    practice_session = relationship("PracticeSessionModel", back_populates="attempts")
