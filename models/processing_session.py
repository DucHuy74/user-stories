import uuid
from sqlalchemy import Column, String, Integer, DateTime, JSON
from datetime import datetime
from .base import Base


class ProcessingSession(Base):
    """Lightweight processing session tracking"""
    __tablename__ = 'processing_sessions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_name = Column(String(100))
    phase_completed = Column(Integer, default=0)
    total_stories = Column(Integer)
    status = Column(String(50), default='started')
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    metadata_info = Column(JSON)
