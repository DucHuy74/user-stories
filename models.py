from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class UserStory(Base):
    """Bảng lưu trữ user stories gốc"""
    __tablename__ = 'user_stories'
    
    id = Column(Integer, primary_key=True)
    story_id = Column(String(50), unique=True, nullable=False)  # US_001, US_002, etc.
    original_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    concepts = relationship("Concept", back_populates="user_story")
    phase2_records = relationship("Phase2Record", back_populates="user_story")
    svo_relationships = relationship("SVORelationship", back_populates="user_story")

class Concept(Base):
    """Bảng lưu trữ concepts từ Phase 1"""
    __tablename__ = 'concepts'
    
    id = Column(Integer, primary_key=True)
    user_story_id = Column(Integer, ForeignKey('user_stories.id'), nullable=False)
    role = Column(String(255))
    action = Column(String(255))
    object = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="concepts")

class ConceptFrequency(Base):
    """Bảng lưu trữ tần suất concepts từ Phase 2"""
    __tablename__ = 'concept_frequency'
    
    id = Column(Integer, primary_key=True)
    concept_text = Column(String(255), unique=True, nullable=False)
    frequency = Column(Integer, default=1)
    concept_type = Column(String(50))  # 'role', 'object', 'action'
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Phase2Record(Base):
    """Bảng lưu trữ kết quả phân loại từ Phase 2"""
    __tablename__ = 'phase2_records'
    
    id = Column(Integer, primary_key=True)
    user_story_id = Column(Integer, ForeignKey('user_stories.id'), nullable=False)
    indices = Column(Integer)
    text = Column(String(255))
    concept_and_domain = Column(String(100))
    feature_flag = Column(Integer)
    value_flag = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="phase2_records")

class ConceptSynonym(Base):
    """Bảng lưu trữ synonyms từ WordNet"""
    __tablename__ = 'concept_synonyms'
    
    id = Column(Integer, primary_key=True)
    original_concept = Column(String(255), nullable=False)
    synonym = Column(String(255), nullable=False)
    source = Column(String(50), default='wordnet')
    created_at = Column(DateTime, default=datetime.utcnow)

class ConceptSimilarity(Base):
    """Bảng lưu trữ similarity scores từ Phase 3"""
    __tablename__ = 'concept_similarities'
    
    id = Column(Integer, primary_key=True)
    concept1 = Column(String(255), nullable=False)
    concept2 = Column(String(255), nullable=False)
    similarity_score = Column(Float, nullable=False)
    similarity_type = Column(String(50), default='Wu-Palmer')
    created_at = Column(DateTime, default=datetime.utcnow)

class SVORelationship(Base):
    """Bảng lưu trữ Subject-Verb-Object relationships"""
    __tablename__ = 'svo_relationships'
    
    id = Column(Integer, primary_key=True)
    user_story_id = Column(Integer, ForeignKey('user_stories.id'), nullable=False)
    subject = Column(String(255))
    verb = Column(String(255))
    object = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory", back_populates="svo_relationships")

class PairwiseRelationship(Base):
    """Bảng lưu trữ pair-wise relationships theo lưu đồ"""
    __tablename__ = 'pairwise_relationships'
    
    id = Column(Integer, primary_key=True)
    concept1_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    concept2_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    relationship_type = Column(String(50))  # semantic, syntactic, etc.
    strength_score = Column(Float, nullable=False)
    method = Column(String(50))  # wu-palmer, word2vec, etc.
    session_id = Column(Integer, ForeignKey('processing_sessions.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    concept1 = relationship("Concept", foreign_keys=[concept1_id])
    concept2 = relationship("Concept", foreign_keys=[concept2_id])
    session = relationship("ProcessingSession")

class ImportantConceptDomain(Base):
    """Bảng lưu trữ Important Concept Domain từ Phase 2 theo lưu đồ"""
    __tablename__ = 'important_concept_domains'
    
    id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    domain_type = Column(String(100))  # feature, role, object, etc.
    importance_score = Column(Float)
    is_feature = Column(Integer)  # 0 = feature, 1 = value
    classification = Column(String(100))  # role(general), object(general), feature
    session_id = Column(Integer, ForeignKey('processing_sessions.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    concept = relationship("Concept")
    session = relationship("ProcessingSession")

class VisualNarratorResult(Base):
    """Bảng lưu trữ kết quả Visual Narrator processing"""
    __tablename__ = 'visual_narrator_results'
    
    id = Column(Integer, primary_key=True)
    user_story_id = Column(Integer, ForeignKey('user_stories.id'), nullable=False)
    parsed_structure = Column(JSON)  # Cấu trúc được parse
    entities = Column(JSON)  # Các entities được nhận diện
    relationships = Column(JSON)  # Mối quan hệ giữa entities
    confidence_score = Column(Float)
    session_id = Column(Integer, ForeignKey('processing_sessions.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_story = relationship("UserStory")
    session = relationship("ProcessingSession")

class NormalCheckExclude(Base):
    """Bảng lưu trữ kết quả Normal Check Exclude filtering"""
    __tablename__ = 'normal_check_excludes'
    
    id = Column(Integer, primary_key=True)
    concept_id = Column(Integer, ForeignKey('concepts.id'), nullable=False)
    is_excluded = Column(Integer, default=0)  # 0 = included, 1 = excluded
    exclusion_reason = Column(String(255))
    filter_type = Column(String(50))  # frequency_filter, domain_filter, etc.
    session_id = Column(Integer, ForeignKey('processing_sessions.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    concept = relationship("Concept")
    session = relationship("ProcessingSession")

class ProcessingSession(Base):
    """Bảng theo dõi các session xử lý"""
    __tablename__ = 'processing_sessions'
    
    id = Column(Integer, primary_key=True)
    session_name = Column(String(100))
    phase_completed = Column(Integer, default=0)  # 0, 1, 2, 3
    total_stories = Column(Integer)
    status = Column(String(50), default='started')  # started, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    metadata_info = Column(JSON)  # Lưu thêm thông tin nếu cần