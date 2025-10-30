import uuid
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from .base import Base


class ConceptFrequency(Base):
    """Bảng lưu trữ tần suất concepts từ Phase 2"""
    __tablename__ = 'concept_frequency'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_text = Column(String(255), unique=True, nullable=False)
    frequency = Column(Integer, default=1)
    concept_type = Column(String(50))  # 'role', 'object', 'action'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
