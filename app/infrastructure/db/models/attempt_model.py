from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base

class AttemptModel(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mcq_id = Column(Integer, ForeignKey("mcqs.id"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("options.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False) # Computed at time of attempt
    mode = Column(String, nullable=False) # 'practice' or 'mock_test'
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("UserModel")
    mcq = relationship("MCQModel")
    selected_option = relationship("OptionModel")
