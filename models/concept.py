from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Concept(Base):
    """Concepts in Phase 2 with simplified fields per new spec."""
    __tablename__ = 'concepts'

    concept_id = Column(Integer, primary_key=True, autoincrement=True)
    # Map to existing DB column 'usid' but expose attribute as 'indices'
    indices = Column('usid', Integer, ForeignKey('user_stories.usid'), nullable=False)
    # New fields to match requested export/model shape
    text_userrole = Column(String(255))
    text_object_as_concept_domain = Column(String(255))
    feature_flag = Column(Integer)
    value_flag = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_story = relationship("UserStory", back_populates="concepts", primaryjoin="Concept.indices==UserStory.usid")
