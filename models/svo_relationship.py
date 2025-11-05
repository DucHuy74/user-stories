from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from .base import Base


class SvoRelationship(Base):
    __tablename__ = 'svo_relationships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    a = Column(String(255), nullable=False)
    b = Column(String(255), nullable=False)
    similarity = Column(Float)
    type = Column(String(50))  # e.g., 'object', 'subject'
    method = Column(String(50))  # 'combined', 'wup', 'word2vec'
    domain_label = Column(String(100))  # optional cluster/domain label
    created_at = Column(DateTime, default=datetime.utcnow)
