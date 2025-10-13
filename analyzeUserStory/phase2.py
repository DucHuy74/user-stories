import json
from typing import Dict, List, Any
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import UserStory, Concept, ConceptFrequency, ImportantConceptDomain, ProcessingSession
from database import DatabaseSession, get_database_manager
import logging

class Phase2:
    def __init__(self, session_id: str = None):
        self.input_data = {}
        self.object_frequency = {}
        self.final_output = []
        self.session_id = session_id
        self.db_manager = get_database_manager()

    def analyze_concepts(self, phase1_data: Dict = None) -> Dict:
        """Phân tích concepts từ Phase 1 data hoặc load từ database"""
        
        if phase1_data:
            self.input_data = phase1_data
            self.session_id = phase1_data.get("session_id")
        elif self.session_id:
            # Load từ database
            self.input_data = self._load_from_database()
        else:
            raise ValueError("Cần cung cấp phase1_data hoặc session_id")
        
        try:
            with DatabaseSession(self.db_manager) as session:
                # Tính tần suất và lưu vào database
                self._calculate_object_frequency()
                self._save_frequency_to_database(session)
                
                # Tạo final output và lưu vào database
                self._generate_final_output()
                self._save_important_concept_domains_to_database(session)
                
                # Cập nhật processing session
                self._update_processing_session(session, 2, "completed")
                
            logging.info(f"✅ Phase 2 completed: Analyzed {len(self.final_output)} records")
            
        except Exception as e:
            logging.error(f"❌ Phase 2 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                self._update_processing_session(session, 2, "failed")
            raise

        results = {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output,
            "session_id": self.session_id
        }
        return results

    def _calculate_object_frequency(self):
        all_concepts = []
        for concept_item in self.input_data.get("concepts", []):
            if concept_item.get("role"):
                role = concept_item["role"].split(' ', 1)[-1] if concept_item["role"].split(' ', 1)[0] in ('a', 'an', 'the') else concept_item["role"]
                all_concepts.append(role)
            if concept_item.get("object"):
                obj = concept_item["object"].split(' ', 1)[-1] if concept_item["object"].split(' ', 1)[0] in ('a', 'an', 'the') else concept_item["object"]
                all_concepts.append(obj)
        self.object_frequency = dict(Counter(all_concepts))
        print(f"📊 Tần suất khái niệm: {self.object_frequency}")

    def _generate_final_output(self):
        
        for concept_item in self.input_data.get("concepts", []):
            usid = concept_item.get("id")
            original_text = concept_item.get("original_text")
            role = concept_item.get("role")
            action = concept_item.get("action")
            obj = concept_item.get("object")

            if action:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": action,
                    "concept_and_domain": "feature",
                    "0 - feature flag": 0,
                    "1 - value flag": None
                })
            
            if role:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": role,
                    "concept_and_domain": "role (general)",
                    "0 - feature flag": None,
                    "1 - value flag": 1
                })
            
            if obj:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": obj,
                    "concept_and_domain": "object (general)",
                    "0 - feature flag": None,
                    "1 - value flag": 1
                })

        for i, record in enumerate(self.final_output):
            record["indices"] = i + 1


    def export_json(self, filename: str = "phase2_output.json") -> str:
        results = {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            return ""

    def _load_from_database(self) -> Dict:
        """Load dữ liệu Phase 1 từ database"""
        with DatabaseSession(self.db_manager) as session:
            # Load processing session
            processing_session = session.query(ProcessingSession).filter_by(
                id=self.session_id
            ).first()
            
            if not processing_session:
                raise ValueError(f"Session ID {self.session_id} not found")
            
            # Load user stories và concepts
            user_stories = session.query(UserStory).all()
            results = []
            
            for user_story in user_stories:
                concept = session.query(Concept).filter_by(
                    user_story_id=user_story.id
                ).first()
                
                if concept:
                    concept_dict = {
                        "id": user_story.story_id,
                        "original_text": user_story.original_text,
                        "role": concept.role or "",
                        "action": concept.action or "",
                        "object": concept.object or "",
                    }
                    results.append(concept_dict)
            
            return {"concepts": results}
    
    def _save_frequency_to_database(self, session: Session):
        """Lưu tần suất concepts vào database"""
        for concept_text, frequency in self.object_frequency.items():
            # Kiểm tra xem concept đã tồn tại chưa
            existing = session.query(ConceptFrequency).filter_by(
                concept_text=concept_text
            ).first()
            
            if existing:
                existing.frequency = frequency
                from datetime import datetime
                existing.updated_at = datetime.utcnow()
            else:
                concept_freq = ConceptFrequency(
                    concept_text=concept_text,
                    frequency=frequency,
                    concept_type="mixed"  # Có thể phân loại chi tiết hơn
                )
                session.add(concept_freq)
    
    def _save_important_concept_domains_to_database(self, session: Session):
        """Lưu Important Concept Domains vào database theo lưu đồ"""
        for record in self.final_output:
            # Tìm user story và concept tương ứng
            usid = record["usid_text"].split(":", 1)[0].strip()
            user_story = session.query(UserStory).filter_by(story_id=usid).first()
            
            if user_story:
                # Tìm concept tương ứng với text
                concept = session.query(Concept).filter_by(
                    user_story_id=user_story.id
                ).first()
                
                if concept:
                    # Tính importance score dựa trên frequency
                    importance_score = self.object_frequency.get(record.get("text"), 1) / len(self.final_output)
                    
                    important_concept = ImportantConceptDomain(
                        concept_id=concept.id,
                        domain_type=record.get("concept_and_domain"),
                        importance_score=importance_score,
                        is_feature=record.get("0 - feature flag"),
                        classification=record.get("concept_and_domain"),
                        session_id=self.session_id
                    )
                    session.add(important_concept)
    
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
        """Load dữ liệu Phase 2 từ database"""
        self.session_id = session_id
        
        with DatabaseSession(self.db_manager) as session:
            # Load frequency data
            frequencies = session.query(ConceptFrequency).all()
            self.object_frequency = {f.concept_text: f.frequency for f in frequencies}
            
            # Load important concept domains
            domains = session.query(ImportantConceptDomain).join(Concept).join(UserStory).all()
            self.final_output = []
            
            for i, domain in enumerate(domains):
                # Lấy text từ concept
                concept = domain.concept
                text = ""
                if domain.classification == "feature":
                    text = concept.action
                elif "role" in domain.classification:
                    text = concept.role
                elif "object" in domain.classification:
                    text = concept.object
                
                record_dict = {
                    "indices": i + 1,
                    "usid_text": f"{concept.user_story.story_id}: {concept.user_story.original_text}",
                    "text": text,
                    "concept_and_domain": domain.classification,
                    "0 - feature flag": domain.is_feature if domain.classification == "feature" else None,
                    "1 - value flag": 1 if domain.classification != "feature" else None
                }
                self.final_output.append(record_dict)
            
            return {
                "object_frequency": self.object_frequency,
                "final_output": self.final_output,
                "session_id": self.session_id
            }

    def get_results(self):
        return {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output,
            "session_id": self.session_id
        }