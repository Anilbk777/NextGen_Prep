from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

# Association Table for many-to-many relationship
mock_test_mcq_association = Table(
    "mock_test_mcq_association",
    Base.metadata,
    Column(
        "mock_test_id",
        Integer,
        ForeignKey("mock_tests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "mcq_id",
        Integer,
        ForeignKey("mock_test_mcqs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class MockTestModel(Base):
    __tablename__ = "mock_tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subjects = relationship(
        "MockTestSubject", back_populates="mock_test", cascade="all, delete-orphan"
    )
    questions = relationship(
        "MockTestMCQ", secondary=mock_test_mcq_association, back_populates="mock_tests"
    )
