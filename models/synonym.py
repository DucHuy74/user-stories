from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from datetime import datetime
from .base import Base


class Synonym(Base):
    """Bảng synonyms (phụ) lưu từ đồng nghĩa của concept"""
    __tablename__ = 'synonyms'

    syn_id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey('concepts.concept_id'), nullable=False)
    synonym_term = Column(String(255), nullable=False)
    source = Column(String(50))  # WordNet / word2vec
    similarity_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
