from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from sqlalchemy import UniqueConstraint

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject_id = Column(
        Integer, ForeignKey("practice_subjects.id", ondelete="CASCADE"), nullable=False
    )
    order_index = Column(Integer, default=0)
    
    # Relationships
    subject = relationship(
        "PracticeSubject", back_populates="topics", passive_deletes=True
    )
    mcqs = relationship(
        "PracticeMCQ", back_populates="topic", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", back_populates="topic", cascade="all, delete-orphan"
    )

    concepts = relationship(
        "Concept", back_populates="topic", cascade="all, delete-orphan",passive_deletes=True
    )
    user_topics = relationship(
        "UserTopic", back_populates="topic", cascade="all, delete-orphan",passive_deletes=True
    )
    templates = relationship(
        "Template", back_populates="topic", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "LearningSession", back_populates="topic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("order_index", "subject_id", name="uq_topic_order_subject_id"),
    )
