from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

# ---------------------------
# 4. User-Selected Subjects
# ---------------------------
class UserSubject(Base):
    __tablename__ = "user_subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("practice_subjects.id", ondelete="CASCADE"))
    selected_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserModel", back_populates="subjects")
    subject = relationship("PracticeSubject", back_populates="user_subjects")

    __table_args__ = (
        UniqueConstraint("user_id", "subject_id", name="uq_user_subject"),
    )


