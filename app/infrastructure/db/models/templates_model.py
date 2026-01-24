from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime

# ---------------------------
# 8. Templates
# ---------------------------
class Template(Base):
    __tablename__ = "templates"
    
    template_id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    learning_objective = Column(Text)
    target_difficulty = Column(Float, default=0.5)  # 0-1
    question_style = Column(String(50))  # "conceptual", "numerical", etc.
    answer_format = Column(String(50), default="MCQ")
    config_metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    concept = relationship("Concept", back_populates="templates")
    questions = relationship("Question", back_populates="template")
    topic = relationship("Topic", back_populates="templates")
    bandit_stats = relationship("BanditStats", back_populates="template", cascade="all, delete-orphan")
    responses = relationship("UserResponse", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("concept_id", "topic_id", name="uq_concept_topic_template"),
    )