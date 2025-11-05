from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from .base import Base


class SvoRaw(Base):
    """Raw SVO triples extracted from user stories (Phase 1 output)."""
    __tablename__ = 'svo_raw'

    id = Column(Integer, primary_key=True, autoincrement=True)
    usid = Column(Integer, ForeignKey('user_stories.usid'), nullable=False)
    subject = Column(String(255))
    verb = Column(String(255))
    object = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
