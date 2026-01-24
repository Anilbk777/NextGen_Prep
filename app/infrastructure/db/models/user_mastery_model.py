
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

# ---------------------------
# 10. User Mastery
# ---------------------------
class UserMastery(Base):
    __tablename__ = "user_mastery"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"))
    mastery = Column(Float, default=0.0)  # 0-1
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("UserModel", back_populates="masteries")
    concept = relationship("Concept", back_populates="masteries")

    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_user_concept_mastery"),
    )
