from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject_id = Column(
        Integer, ForeignKey("practice_subjects.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    subject = relationship(
        "PracticeSubject", back_populates="topics", passive_deletes=True
    )
    mcqs = relationship(
        "PracticeMCQ", back_populates="topic", cascade="all, delete-orphan"
    )
    notes = relationship("Note", back_populates="topic", cascade="all, delete-orphan")
