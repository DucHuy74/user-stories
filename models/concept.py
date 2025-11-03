from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Concept(Base):
    """Bảng lưu trữ concepts (Phase 2 output)"""
    __tablename__ = 'concepts'

    concept_id = Column(Integer, primary_key=True, autoincrement=True)
    usid = Column(Integer, ForeignKey('user_stories.usid'), nullable=False)
    term = Column(String(255), nullable=False)
    is_feature = Column(Boolean, default=False)
    frequency = Column(Integer, default=1)
    domain = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    user_story = relationship("UserStory", back_populates="concepts")
