from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

class Concept(Base):
    __tablename__ = "concepts"
    
    concept_id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id",ondelete="CASCADE"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    prerequisites = Column(JSON, default=[])  # concept_ids
    common_misconceptions = Column(JSON, default=[])
    difficulty_level = Column(Integer, default=1)
    
    topic = relationship("Topic", back_populates="concepts", passive_deletes=True)
    templates = relationship("Template", back_populates="concept", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="concept", cascade="all, delete-orphan")
    masteries = relationship("UserMastery", back_populates="concept", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("topic_id", "name", name="uq_topic_concept"),
    )