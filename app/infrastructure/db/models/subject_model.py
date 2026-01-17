from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from ..base import Base

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    is_from_mock_test = Column(Boolean, default=False, nullable=False)  # Flag for mock test subjects

    # Relationships with cascade delete
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    mcqs = relationship("MCQModel", back_populates="subject", cascade="all, delete-orphan")
