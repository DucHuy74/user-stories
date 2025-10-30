import uuid
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class UserStory(Base):
    """Bảng lưu trữ user stories gốc"""
    __tablename__ = 'user_stories'
    
    # Use UUID strings for primary key and external story identifier
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    story_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    original_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    concepts = relationship("Concept", back_populates="user_story")
    svo_relationships = relationship("SVORelationship", back_populates="user_story")
