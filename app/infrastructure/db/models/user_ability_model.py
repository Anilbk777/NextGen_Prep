from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

# ---------------------------
# 2. User Ability (global ability θ)
# ---------------------------
class UserAbility(Base):
    __tablename__ = "user_abilities"
    
    ability_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    global_ability = Column(Float, default=0.5)  # IRT θ
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("UserModel", back_populates="abilities")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_ability"),
    )
    
    