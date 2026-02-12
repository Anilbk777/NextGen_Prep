
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime

# ---------------------------
# 9. Questions
# ---------------------------
class Question(Base):
    __tablename__ = "questions"
    
    question_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.template_id", ondelete="CASCADE"))
    question_text = Column(Text, nullable=False)
    options = Column(JSON)  # list of MCQ options
    correct_option = Column(Integer)  # index of correct option
    explanation = Column(Text)

    template = relationship("Template", back_populates="questions", passive_deletes=True)
    responses = relationship("UserResponse", back_populates="question", cascade="all, delete-orphan")
