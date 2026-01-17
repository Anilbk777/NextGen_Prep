from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base
from .mock_test_model import mock_test_mcqs

class MCQModel(Base):
    __tablename__ = "mcqs"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    explanation = Column(String, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)  # Optional for mock tests
    difficulty = Column(String, nullable=True)  # Only for practice
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_practice_only = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    options = relationship("OptionModel", back_populates="mcq", cascade="all, delete-orphan")
    author = relationship("UserModel")
    subject = relationship("Subject", back_populates="mcqs",passive_deletes=True)
    topic = relationship("Topic", back_populates="mcqs",passive_deletes=True)
    attempts = relationship("AttemptModel", back_populates="mcq")
    mock_tests = relationship("MockTestModel", secondary=mock_test_mcqs, back_populates="questions")



class OptionModel(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    mcq_id = Column(Integer, ForeignKey("mcqs.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    # Relationships
    mcq = relationship("MCQModel", back_populates="options")
