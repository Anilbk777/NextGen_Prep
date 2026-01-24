from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    func,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from ..base import Base


class PracticeSubject(Base):
    __tablename__ = "practice_subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Topics cascade when subject is deleted
    topics = relationship(
        "Topic", back_populates="subject", cascade="all, delete-orphan"
    )

    user_subjects = relationship("UserSubject", back_populates="subject", cascade="all, delete-orphan",passive_deletes=True)
    sessions = relationship("LearningSession", back_populates="subject", cascade="all, delete-orphan")

class MockTestSubject(Base):
    __tablename__ = "mock_test_subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    mock_test_id = Column(
        Integer, ForeignKey("mock_tests.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    mock_test = relationship("MockTestModel", back_populates="subjects")
    mcqs = relationship(
        "MockTestMCQ", back_populates="subject", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("mock_test_id", "name", name="uq_mocktest_subject"),
    )
