#user_model.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..base import Base
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "ADMIN" or "USER"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    abilities = relationship("UserAbility", back_populates="user")
    subjects = relationship("UserSubject", back_populates="user")
    responses = relationship("UserResponse", back_populates="user")
    masteries = relationship("UserMastery", back_populates="user")
    bandit_stats = relationship("BanditStats", back_populates="user")
    sessions = relationship("LearningSession", back_populates="user")
    user_topics = relationship("UserTopic", back_populates="user")

    __table_args__ = (
        UniqueConstraint("email", name="uq_email_user"),
    )
