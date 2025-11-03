from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class UserStory(Base):
    """Bảng lưu trữ user stories gốc (Phase 1 output)"""
    __tablename__ = 'user_stories'

    usid = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    role = Column(String(255))
    object = Column(String(255))
    verb = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    concepts = relationship("Concept", back_populates="user_story")
