from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

class MCQModel(Base):
    __tablename__ = "mcqs"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, nullable=False)
    explanation = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_practice_only = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    options = relationship("OptionModel", back_populates="mcq", cascade="all, delete-orphan")
    author = relationship("UserModel")

class OptionModel(Base):
    __tablename__ = "options"

    id = Column(Integer, primary_key=True, index=True)
    mcq_id = Column(Integer, ForeignKey("mcqs.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    # Relationships
    mcq = relationship("MCQModel", back_populates="options")
