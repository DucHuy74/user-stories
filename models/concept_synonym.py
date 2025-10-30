import uuid
from sqlalchemy import Column, String, DateTime
from datetime import datetime
from .base import Base


class ConceptSynonym(Base):
    """Bảng lưu trữ synonyms từ WordNet"""
    __tablename__ = 'concept_synonyms'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_concept = Column(String(255), nullable=False)
    synonym = Column(String(255), nullable=False)
    source = Column(String(50), default='wordnet')
    created_at = Column(DateTime, default=datetime.utcnow)
