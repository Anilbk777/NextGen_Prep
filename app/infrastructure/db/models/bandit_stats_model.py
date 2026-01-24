
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

# ---------------------------
# 12. Bandit Stats
# ---------------------------
class BanditStats(Base):
    __tablename__ = "bandit_stats"
    
    bandit_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("templates.template_id"))
    alpha = Column(Float, default=1.0)
    beta = Column(Float, default=1.0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("UserModel", back_populates="bandit_stats")
    template = relationship("Template", back_populates="bandit_stats",passive_deletes=True)

    __table_args__ = (
        UniqueConstraint("user_id", "template_id", name="uq_user_template_bandit_stats"),
    )
    