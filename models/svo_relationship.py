import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class SVORelationship(Base):
    """Bảng lưu trữ Subject-Verb-Object relationships"""
    __tablename__ = 'svo_relationships'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_story_id = Column(String(36), ForeignKey('user_stories.id'), nullable=False)
    subject = Column(String(255))
    verb = Column(String(255))
    object = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="svo_relationships")
