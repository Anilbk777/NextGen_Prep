
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..base import Base
from datetime import datetime
from sqlalchemy import UniqueConstraint

class UserTopic(Base):
    __tablename__ = "user_topics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"))
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("UserModel", back_populates="user_topics")
    topic = relationship("Topic", back_populates="user_topics")

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic"),
    )