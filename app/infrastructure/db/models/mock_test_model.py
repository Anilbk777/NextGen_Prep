from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

# Association table for many-to-many relationship between MockTest and MCQ
mock_test_mcqs = Table(
    "mock_test_mcqs",
    Base.metadata,
    Column("mock_test_id", Integer, ForeignKey("mock_tests.id", ondelete="CASCADE"), primary_key=True),
    Column("mcq_id", Integer, ForeignKey("mcqs.id", ondelete="CASCADE"), primary_key=True)
)

class MockTestModel(Base):
    __tablename__ = "mock_tests"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    questions = relationship("MCQModel", secondary=mock_test_mcqs)
