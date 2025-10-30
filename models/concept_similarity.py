import uuid
from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from .base import Base


class ConceptSimilarity(Base):
    """Bảng lưu trữ similarity scores từ Phase 3"""
    __tablename__ = 'concept_similarities'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept1 = Column(String(255), nullable=False)
    concept2 = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)
    similarity_type = Column(String(50), default='Wu-Palmer')
    created_at = Column(DateTime, default=datetime.utcnow)
