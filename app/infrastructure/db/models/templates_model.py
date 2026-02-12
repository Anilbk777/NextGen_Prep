from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime

# ---------------------------
# 8. Templates
# ---------------------------
# class Template(Base):
#     __tablename__ = "templates"
    
#     template_id = Column(Integer, primary_key=True, index=True)
#     concept_id = Column(Integer, ForeignKey("concepts.concept_id"))
#     topic_id = Column(Integer, ForeignKey("topics.id"))
#     learning_objective = Column(Text)
#     target_difficulty = Column(Float, default=0.5)  # 0-1
#     question_style = Column(String(50))  # "conceptual", "numerical", etc.
#     answer_format = Column(String(50), default="MCQ")
#     config_metadata = Column(JSON, default={})
#     created_at = Column(DateTime, default=datetime.utcnow)
    
#     concept = relationship("Concept", back_populates="templates")
#     questions = relationship("Question", back_populates="template")
#     topic = relationship("Topic", back_populates="templates")
#     bandit_stats = relationship("BanditStats", back_populates="template", cascade="all, delete-orphan")
#     responses = relationship("UserResponse", back_populates="template", cascade="all, delete-orphan")

#     __table_args__ = (
#         UniqueConstraint("concept_id", "topic_id", name="uq_concept_topic_template"),
#     )


class Template(Base):
    __tablename__ = "templates"

    template_id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id", ondelete="CASCADE"))

    # What the question is about
    intent = Column(String(200))  
    learning_objective = Column(Text)

    # How the question should behave
    question_style = Column(String(50))  # conceptual / numerical / cause-effect
    target_difficulty = Column(Float, default=0.5)

    # Correctness logic (not literal answer)
    correct_reasoning = Column(Text)

    # Misconception patterns used for distractors
    misconception_patterns = Column(JSON)  
    # Example:
    # ["force_needed_for_motion", "confuse_velocity_acceleration", "ignores_inertia"]

    answer_format = Column(String(20), default="MCQ")

    # NOTE:
    # IRT item parameters (difficulty / discrimination / guessing)
    # are currently stored on the Question model, not Template.
    # Columns were removed here to stay in sync with the existing DB
    # schema and avoid selecting non-existent fields.

    created_at = Column(DateTime, default=datetime.utcnow)

    concept = relationship("Concept", back_populates="templates")

    responses = relationship("UserResponse", back_populates="template", cascade="all, delete-orphan")

    questions = relationship(
        "Question",
        back_populates="template",
        cascade="all, delete-orphan"
    )
    bandit_stats = relationship(
        "BanditStats",
        back_populates="template",
        cascade="all, delete-orphan"
    )

