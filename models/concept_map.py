from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from datetime import datetime
from .base import Base


class ConceptMap(Base):
    """Bảng lưu mối quan hệ giữa các concepts (Phase 3 output)"""
    __tablename__ = 'concept_map'

    map_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_concept_id = Column(Integer, ForeignKey('concepts.concept_id'), nullable=False)
    verb = Column(String(255))
    object_concept_id = Column(Integer, ForeignKey('concepts.concept_id'), nullable=False)
    relation_type = Column(String(50))  # e.g., 'SVO', 'synonym', 'similarity'
    similarity_score = Column(Float)
    source = Column(String(50))  # WordNet / word2vec / Wu-Palmer / phase3
    created_at = Column(DateTime, default=datetime.utcnow)
