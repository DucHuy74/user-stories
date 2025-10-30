import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Concept(Base):
    """Bảng lưu trữ concepts từ Phase 1"""
    __tablename__ = 'concepts'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_story_id = Column(String(36), ForeignKey('user_stories.id'), nullable=False)
    role = Column(String(255))
    action = Column(String(255))
    object = Column(String(255))
    # 'metadata' is a reserved attribute on Declarative Base, use attribute name 'metadata_json'
    metadata_json = Column('metadata', JSON)  # store visual narrator / parsed info
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="concepts")
