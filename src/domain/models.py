import uuid
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

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

class Concept(Base):
    """Bảng lưu trữ concepts từ Phase 1"""
    __tablename__ = 'concepts'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_story_id = Column(String(36), ForeignKey('user_stories.id'), nullable=False)
    role = Column(String(255))
    action = Column(String(255))
    object = Column(String(255))
    # 'metadata' is a reserved attribute on Declarative Base, use attribute name 'metadata_json'
    metadata_json = Column('metadata', JSON)  # store visual narrator / parsed info
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="concepts")

class ConceptFrequency(Base):
    """Bảng lưu trữ tần suất concepts từ Phase 2"""
    __tablename__ = 'concept_frequency'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_text = Column(String(255), unique=True, nullable=False)
    frequency = Column(Integer, default=1)
    concept_type = Column(String(50))  # 'role', 'object', 'action'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class ConceptSynonym(Base):
    """Bảng lưu trữ synonyms từ WordNet"""
    __tablename__ = 'concept_synonyms'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_concept = Column(String(255), nullable=False)
    synonym = Column(String(255), nullable=False)
    source = Column(String(50), default='wordnet')
    created_at = Column(DateTime, default=datetime.utcnow)

class ConceptSimilarity(Base):
    """Bảng lưu trữ similarity scores từ Phase 3"""
    __tablename__ = 'concept_similarities'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept1 = Column(String(255), nullable=False)
    concept2 = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)
    similarity_type = Column(String(50), default='Wu-Palmer')
    created_at = Column(DateTime, default=datetime.utcnow)

class SVORelationship(Base):
    """Bảng lưu trữ Subject-Verb-Object relationships"""
    __tablename__ = 'svo_relationships'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_story_id = Column(String(36), ForeignKey('user_stories.id'), nullable=False)
    subject = Column(String(255))
    verb = Column(String(255))
    object = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="svo_relationships")

# Removed several auxiliary tables for simplification. Keep a lightweight ProcessingSession
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
