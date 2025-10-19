import json
from typing import Dict, List, Any
from collections import defaultdict
import nltk
from nltk.corpus import wordnet as wn
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import (UserStory, ConceptSynonym, ConceptSimilarity, 
                   SVORelationship, ProcessingSession, Concept)
from database import DatabaseSession, get_database_manager
import logging
import numpy as np

# Try to import word2vec libraries
try:
    from gensim.models import Word2Vec
    from sklearn.metrics.pairwise import cosine_similarity
    WORD2VEC_AVAILABLE = True
except ImportError:
    WORD2VEC_AVAILABLE = False
    logging.warning("Word2Vec libraries not available. Install gensim and scikit-learn for full functionality.")

class Phase3:
    def __init__(self, session_id: str = None):
        self.input_data = {}
        self.synonyms = defaultdict(list)
        self.similarities = []
        self.final_output = {}
        self.session_id = session_id
        self.db_manager = get_database_manager()

        try:
            wn.synsets('test')
        except LookupError:
            nltk.download('wordnet')

    def process_wordnet(self, phase2_data: Dict = None) -> Dict:
        """Xử lý WordNet từ Phase 2 data hoặc load từ database"""
        
        if phase2_data:
            self.input_data = phase2_data
            self.session_id = phase2_data.get("session_id")
        elif self.session_id:
            # Load từ database
            self.input_data = self._load_from_database()
        else:
            raise ValueError("Cần cung cấp phase2_data hoặc session_id")
        
        try:
            with DatabaseSession(self.db_manager) as session:
                # Tạo synonyms và lưu vào database
                self._generate_synonyms()
                self._save_synonyms_to_database(session)
                
                # Tính similarity và lưu vào database
                self._calculate_similarity()
                self._save_similarities_to_database(session)
                
                # Tạo final output và lưu SVO relationships
                self._create_final_output()
                self._save_svo_relationships_to_database(session)
                
                # Lưu pair-wise relationships
                self._save_pairwise_relationships_to_database(session)
                
                # Cập nhật processing session
                self._update_processing_session(session, 3, "completed")
                
            logging.info(f"✅ Phase 3 completed: Generated {len(self.synonyms)} synonym groups and {len(self.similarities)} similarities")
            
        except Exception as e:
            logging.error(f"❌ Phase 3 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                self._update_processing_session(session, 3, "failed")
            raise
            
        return self.final_output
    
    def _get_concepts_from_phase2_output(self) -> List[str]:
        all_concepts = []
        for record in self.input_data.get("final_output", []):
            text_value = record.get("text")
            if text_value:
                all_concepts.append(text_value)
        return list(set(all_concepts))

    def _generate_synonyms(self):
        all_concepts = self._get_concepts_from_phase2_output()
        for concept in all_concepts:
            concept_synsets = wn.synsets(concept.lower().replace(" ", "_"), pos=wn.NOUN)
            
            if not concept_synsets:
                concept_synsets = wn.synsets(concept.lower().replace(" ", "_"), pos=wn.VERB)
            
            if concept_synsets:
                for synset in concept_synsets:
                    for lemma in synset.lemmas():
                        lemma_name = lemma.name().replace('_', ' ')
                        if lemma_name.lower() not in [s.lower() for s in self.synonyms[concept]] and lemma_name.lower() != concept.lower():
                            self.synonyms[concept].append(lemma_name)

    def _calculate_similarity(self):
        all_concepts = self._get_concepts_from_phase2_output()
        
        # Wu-Palmer similarity (WordNet)
        for i, concept1 in enumerate(all_concepts):
            for j, concept2 in enumerate(all_concepts):
                if i < j:
                    wu_palmer_score = self._compute_wu_palmer_similarity(concept1, concept2)
                    if wu_palmer_score is not None and wu_palmer_score > 0.5:
                        self.similarities.append({
                            "concept1": concept1,
                            "concept2": concept2,
                            "similarity": wu_palmer_score,
                            "type": "Wu-Palmer"
                        })
                    
                    # Word2Vec similarity nếu có
                    if WORD2VEC_AVAILABLE:
                        word2vec_score = self._compute_word2vec_similarity(concept1, concept2)
                        if word2vec_score is not None and word2vec_score > 0.6:
                            self.similarities.append({
                                "concept1": concept1,
                                "concept2": concept2,
                                "similarity": word2vec_score,
                                "type": "word2vec"
                            })

    def _compute_wu_palmer_similarity(self, concept1: str, concept2: str) -> float:
        synsets1 = wn.synsets(concept1.lower().replace(" ", "_"))
        synsets2 = wn.synsets(concept2.lower().replace(" ", "_"))
        if not synsets1 or not synsets2:
            return None
        max_score = 0.0
        for s1 in synsets1:
            for s2 in synsets2:
                similarity = s1.wup_similarity(s2)
                if similarity is not None and similarity > max_score:
                    max_score = similarity
        return max_score

    def _compute_word2vec_similarity(self, concept1: str, concept2: str) -> float:
        """Tính similarity sử dụng word2vec"""
        if not WORD2VEC_AVAILABLE:
            return None
            
        try:
            # Tạo word2vec model từ concepts (simplified implementation)
            all_concepts = self._get_concepts_from_phase2_output()
            sentences = [[concept.lower().split()] for concept in all_concepts]
            
            # Flatten sentences for word2vec
            flat_sentences = []
            for sentence_list in sentences:
                for sentence in sentence_list:
                    flat_sentences.append(sentence)
            
            if len(flat_sentences) < 2:
                return None
                
            # Tạo simple word2vec model
            model = Word2Vec([flat_sentences], vector_size=100, window=5, min_count=1, workers=1)
            
            concept1_words = concept1.lower().split()
            concept2_words = concept2.lower().split()
            
            # Tính average vector cho mỗi concept
            def get_concept_vector(words):
                vectors = []
                for word in words:
                    if word in model.wv:
                        vectors.append(model.wv[word])
                if vectors:
                    return np.mean(vectors, axis=0)
                return None
            
            vec1 = get_concept_vector(concept1_words)
            vec2 = get_concept_vector(concept2_words)
            
            if vec1 is not None and vec2 is not None:
                similarity = cosine_similarity([vec1], [vec2])[0][0]
                return float(similarity)
            
        except Exception as e:
            logging.error(f"Word2Vec similarity calculation failed: {e}")
            
        return None

    def _generate_pairwise_relationships(self):
        """Tạo pair-wise relationships theo lưu đồ"""
        pairwise_relationships = []
        
        for sim in self.similarities:
            pairwise_relationships.append({
                "concept1": sim["concept1"],
                "concept2": sim["concept2"],
                "relationship_type": f"semantic_{sim['type']}",
                "strength": sim["similarity"]
            })
        
        return pairwise_relationships

    def _create_final_output(self):
        all_records = self.input_data.get("final_output", [])
        
        roles = list(set([r.get("text") for r in all_records if "role" in r.get("concept_and_domain", "") and r.get("text")]))
        objects = list(set([r.get("text") for r in all_records if "object" in r.get("concept_and_domain", "") and r.get("text")]))
        verbs = list(set([r.get("text") for r in all_records if r.get("concept_and_domain") == "feature" and r.get("text")]))
        
        svo_relationships = []
        story_map = defaultdict(lambda: {"subject": "", "verb": "", "object": "", "usid": ""})

        for record in all_records:
            usid = record.get("usid_text", "").split(":", 1)[0].strip()
            
            if "role" in record.get("concept_and_domain", ""):
                story_map[usid]["subject"] = record.get("text", "")
                story_map[usid]["usid"] = usid
            elif "object" in record.get("concept_and_domain", ""):
                story_map[usid]["object"] = record.get("text", "")
                story_map[usid]["usid"] = usid
            elif record.get("concept_and_domain") == "feature":
                story_map[usid]["verb"] = record.get("text", "")
                story_map[usid]["usid"] = usid

        svo_relationships = [v for v in story_map.values() if v.get("subject") or v.get("verb") or v.get("object")]

        pairwise_relationships = []
        for sim in self.similarities:
            pairwise_relationships.append({
                "concept1": sim["concept1"],
                "concept2": sim["concept2"],
                "relationship_type": sim["type"],
                "strength": sim["similarity"]
            })
        
        self.final_output = {
            "user_roles": [r for r in roles if r],
            "objects": [o for o in objects if o],
            "verbs": [v for v in verbs if v],
            "subject_verb_object": svo_relationships,
            "pairwise_relationships": pairwise_relationships,
            "synonyms": dict(self.synonyms)
        }

    def export_json(self, filename: str = "phase3_wordnet.json") -> str:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.final_output, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            return ""

    def _load_from_database(self) -> Dict:
        """Load dữ liệu Phase 2 từ database"""
        with DatabaseSession(self.db_manager) as session:
            # Load processing session
            processing_session = session.query(ProcessingSession).filter_by(
                id=self.session_id
            ).first()
            
            if not processing_session:
                raise ValueError(f"Session ID {self.session_id} not found")
            
            # Load concepts and construct final_output from Concept.metadata_json
            concepts = session.query(Concept).join(UserStory).all()
            final_output = []
            for i, concept in enumerate(concepts):
                meta = concept.metadata_json or {}
                classification = meta.get("classification") or (
                    "feature" if concept.action else ("role" if concept.role else ("object" if concept.object else "unknown"))
                )
                if classification == "feature":
                    text = concept.action
                elif "role" in classification:
                    text = concept.role
                elif "object" in classification:
                    text = concept.object
                else:
                    text = concept.action or concept.role or concept.object or ""

                record_dict = {
                    "indices": i + 1,
                    "usid_text": f"{concept.user_story.story_id}: {concept.user_story.original_text}",
                    "text": text,
                    "concept_and_domain": classification,
                    "0 - feature flag": meta.get("is_feature") if classification == "feature" else None,
                    "1 - value flag": meta.get("value_flag") if classification != "feature" else None
                }
                final_output.append(record_dict)

            return {"final_output": final_output}
    
    def _save_synonyms_to_database(self, session: Session):
        """Lưu synonyms vào database"""
        for original_concept, synonym_list in self.synonyms.items():
            for synonym in synonym_list:
                # Kiểm tra xem đã tồn tại chưa
                existing = session.query(ConceptSynonym).filter_by(
                    original_concept=original_concept,
                    synonym=synonym
                ).first()
                
                if not existing:
                    concept_synonym = ConceptSynonym(
                        original_concept=original_concept,
                        synonym=synonym,
                        source="wordnet"
                    )
                    session.add(concept_synonym)
    
    def _save_similarities_to_database(self, session: Session):
        """Lưu similarity scores vào database"""
        for sim in self.similarities:
            # Kiểm tra xem đã tồn tại chưa
            existing = session.query(ConceptSimilarity).filter_by(
                concept1=sim["concept1"],
                concept2=sim["concept2"]
            ).first()
            
            if not existing:
                concept_similarity = ConceptSimilarity(
                    concept1=sim["concept1"],
                    concept2=sim["concept2"],
                    similarity_score=sim["similarity"],
                    similarity_type=sim["type"]
                )
                session.add(concept_similarity)
    
    def _save_svo_relationships_to_database(self, session: Session):
        """Lưu SVO relationships vào database"""
        for svo in self.final_output.get("subject_verb_object", []):
            if svo.get("usid"):
                # Tìm user story tương ứng
                user_story = session.query(UserStory).filter_by(
                    story_id=svo["usid"]
                ).first()
                
                if user_story:
                    # Kiểm tra xem đã tồn tại chưa
                    existing = session.query(SVORelationship).filter_by(
                        user_story_id=user_story.id
                    ).first()
                    
                    if existing:
                        # Cập nhật
                        existing.subject = svo.get("subject")
                        existing.verb = svo.get("verb")
                        existing.object = svo.get("object")
                    else:
                        # Tạo mới
                        svo_relationship = SVORelationship(
                            user_story_id=user_story.id,
                            subject=svo.get("subject"),
                            verb=svo.get("verb"),
                            object=svo.get("object")
                        )
                        session.add(svo_relationship)

    def _save_pairwise_relationships_to_database(self, session: Session):
        """Lưu pair-wise relationships vào database"""
        # Schema simplified: we don't persist pairwise relationships to DB anymore.
        # Pairwise relationships are returned in final_output under 'pairwise_relationships'.
        return

    def _update_processing_session(self, session: Session, phase_completed: int, status: str):
        """Cập nhật processing session"""
        processing_session = session.query(ProcessingSession).filter_by(
            id=self.session_id
        ).first()
        
        if processing_session:
            processing_session.phase_completed = phase_completed
            processing_session.status = status
            if status == "completed":
                from datetime import datetime
                processing_session.completed_at = datetime.utcnow()
    
    def load_from_database(self, session_id: str) -> Dict:
        """Load dữ liệu Phase 3 từ database"""
        self.session_id = session_id
        
        with DatabaseSession(self.db_manager) as session:
            # Load synonyms
            synonyms_query = session.query(ConceptSynonym).all()
            synonyms_dict = defaultdict(list)
            for syn in synonyms_query:
                synonyms_dict[syn.original_concept].append(syn.synonym)
            
            # Load similarities
            similarities_query = session.query(ConceptSimilarity).all()
            pairwise_relationships = []
            for sim in similarities_query:
                pairwise_relationships.append({
                    "concept1": sim.concept1,
                    "concept2": sim.concept2,
                    "relationship_type": sim.similarity_type,
                    "strength": sim.similarity_score
                })
            
            # Load SVO relationships
            svo_query = session.query(SVORelationship).join(UserStory).all()
            svo_relationships = []
            user_roles = set()
            objects = set()
            verbs = set()
            
            for svo in svo_query:
                svo_dict = {
                    "usid": svo.user_story.story_id,
                    "subject": svo.subject,
                    "verb": svo.verb,
                    "object": svo.object
                }
                svo_relationships.append(svo_dict)
                
                if svo.subject:
                    user_roles.add(svo.subject)
                if svo.verb:
                    verbs.add(svo.verb)
                if svo.object:
                    objects.add(svo.object)
            
            self.final_output = {
                "user_roles": list(user_roles),
                "objects": list(objects),
                "verbs": list(verbs),
                "subject_verb_object": svo_relationships,
                "pairwise_relationships": pairwise_relationships,
                "synonyms": dict(synonyms_dict),
                "session_id": self.session_id
            }
            
            return self.final_output

    def get_results(self):
        return self.final_output