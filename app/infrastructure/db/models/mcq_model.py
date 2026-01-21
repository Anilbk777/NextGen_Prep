from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text,Enum, String, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base
from .mock_test_model import mock_test_mcq_association
import enum

class PracticeMCQ(Base):
    __tablename__ = "practice_mcqs"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String, nullable=True,default="medium")
    topic_id = Column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    topic = relationship("Topic", back_populates="mcqs")
    options = relationship(
        "OptionModel", back_populates="mcq", cascade="all, delete-orphan"
    )
    attempts = relationship("AttemptModel", back_populates="mcq")
    
    practice_session_questions = relationship(
    "PracticeSessionQuestionModel",
    back_populates="mcq",
    cascade="all, delete-orphan"
)


class OptionModel(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    mcq_id = Column(
        Integer, ForeignKey("practice_mcqs.id", ondelete="CASCADE"), nullable=False
    )
    option_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    # Relationship
    mcq = relationship("PracticeMCQ", back_populates="options")


class MockTestMCQ(Base):
    __tablename__ = "mock_test_mcqs"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    subject_id = Column(
        Integer, ForeignKey("mock_test_subjects.id", ondelete="CASCADE")
    )
    mock_test_id = Column(Integer, ForeignKey("mock_tests.id", ondelete="CASCADE"))

    # Relationships
    subject = relationship("MockTestSubject", back_populates="mcqs")
    mock_tests = relationship(
        "MockTestModel", secondary=mock_test_mcq_association, back_populates="questions"
    )
    options = relationship(
        "MockTestOption", back_populates="mcq", cascade="all, delete-orphan"
    )


class MockTestOption(Base):
    __tablename__ = "mock_test_options"

    id = Column(Integer, primary_key=True, index=True)
    mcq_id = Column(
        Integer, ForeignKey("mock_test_mcqs.id", ondelete="CASCADE"), nullable=False
    )
    option_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    mcq = relationship("MockTestMCQ", back_populates="options")
