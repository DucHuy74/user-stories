import json
import spacy
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import UserStory, Concept, ProcessingSession
from database import DatabaseSession, get_database_manager
import logging
import re
import uuid

class Phase1:
    def __init__(self, model_name: str = "en_core_web_sm", session_name: str = None):
        try:
            self.nlp = spacy.load(model_name)
            print(f"Loaded spaCy model: {model_name}")
        except OSError:
            print(f"Downloading spaCy model '{model_name}'...")
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)

        self.user_stories = []
        self.extracted_concepts = {}
        # session name includes timestamp and a uuid to ensure uniqueness
        self.session_name = session_name or f"phase1_session_{self._get_timestamp()}_{uuid.uuid4().hex}"
        self.db_manager = get_database_manager()

        # Khởi tạo database nếu chưa có
        self.db_manager.create_tables()
        
    def _get_timestamp(self) -> str:
        """Tạo timestamp cho session name"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def process_text(self, user_stories: List[str]) -> Dict:
        self.user_stories = user_stories
        results = []
        
        # Tạo processing session
        processing_session = self._create_processing_session(len(user_stories))
        
        try:
            with DatabaseSession(self.db_manager) as session:
                for i, story in enumerate(self.user_stories):
                    if not story.strip():
                        continue

                    # Trích xuất components
                    role, action, obj = self._extract_components(story)
                    
                    role = role.lower().strip() if role else ""
                    action = action.lower().strip() if action else ""
                    obj = obj.lower().strip() if obj else ""

                    # Use UUID for story id
                    story_id = str(uuid.uuid4())
                    
                    # Tạo concept dictionary cho return
                    concept = {
                        "id": story_id,
                        "original_text": story.strip(),
                        "role": role,
                        "action": action,
                        "object": obj,
                    }
                    results.append(concept)
                    
                    # Lưu vào database  
                    user_story_id = self._save_to_database(session, story_id, story.strip(), role, action, obj)
                    
                    # Lưu Visual Narrator results
                    visual_result = self._visual_narrator_processing(story)
                    if visual_result:
                        self._save_visual_narrator_result(session, user_story_id, visual_result, processing_session.id)
                
                # Cập nhật processing session
                self._update_processing_session(session, processing_session.id, 1, "completed")
                
            logging.info(f"✅ Phase 1 completed: Processed {len(results)} user stories")
            
        except Exception as e:
            logging.error(f"❌ Phase 1 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                self._update_processing_session(session, processing_session.id, 1, "failed")
            raise

        roles = sorted(list(set([c["role"] for c in results if c["role"]])))
        actions = sorted(list(set([c["action"] for c in results if c["action"]])))
        objects = sorted(list(set([c["object"] for c in results if c["object"]])))

        self.extracted_concepts = {
            "concepts": results,
            "roles": roles,
            "actions": actions,
            "objects": objects,
            "session_id": processing_session.id
        }
        return self.extracted_concepts

    def _extract_components(self, story: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Sử dụng spaCy và Visual Narrator để trích xuất role, action, và object."""
        story_core = story.split("so that", 1)[0]
        doc = self.nlp(story_core.strip())
        
        # Phương pháp spaCy (hiện tại)
        role = self._find_role(doc)
        action, obj = self._find_action_and_object(doc)
        
        # Phương pháp Visual Narrator (theo lưu đồ)
        visual_narrator_result = self._visual_narrator_processing(story)
        
        # Kết hợp kết quả từ cả hai phương pháp
        if visual_narrator_result:
            # Ưu tiên kết quả từ Visual Narrator nếu confidence cao
            if visual_narrator_result.get('confidence_score', 0) > 0.8:
                role = visual_narrator_result.get('role') or role
                action = visual_narrator_result.get('action') or action
                obj = visual_narrator_result.get('object') or obj
        
        return role, action, obj

    def _find_role(self, doc) -> Optional[str]:
        for i, token in enumerate(doc):
            if token.lower_ == "as" and i + 1 < len(doc) and doc[i+1].lower_ in ("a", "an"):
                role_tokens = []
                for j in range(i + 2, len(doc)):
                    if doc[j].pos_ in ("PUNCT", "VERB", "CCONJ"):
                        break
                    role_tokens.append(doc[j].text)
                return " ".join(role_tokens) if role_tokens else None

        for token in doc:
            if token.dep_ in ("nsubj", "nsubjpass") and token.head.dep_ == "ROOT":
                return " ".join([t.text for t in token.subtree if not t.is_punct])

        return None

    def _find_action_and_object(self, doc) -> Tuple[Optional[str], Optional[str]]:
        
        action = None
        obj = None

        main_verb = None
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                main_verb = token
                break

        if main_verb and main_verb.lemma_ in ("want", "like"):
            for child in main_verb.children:
                if child.dep_ == "xcomp" and child.pos_ == "VERB":
                    main_verb = child
                    break
        
        if not main_verb:
            for token in doc:
                if token.pos_ == "VERB" and token.dep_ in ("ccomp", "advcl"):
                    main_verb = token
                    break

        if main_verb:
            action = main_verb.lemma_
            
            for child in main_verb.children:
                if child.dep_ == "dobj":
                    obj = " ".join([t.text for t in child.subtree if not t.is_punct])
                    break
            
            if obj is None:
                for child in main_verb.children:
                    if child.dep_ == "prep":
                        for grandchild in child.children:
                            if grandchild.dep_ == "pobj":
                                obj = " ".join([t.text for t in grandchild.subtree if not t.is_punct])
                                break
                    if obj: break
        if not action and not obj:
            first_token = doc[0]
            if first_token.pos_ in ("NOUN", "DET", "PROPN"):
                obj = " ".join([t.text for t in doc if not t.is_punct])

        return action, obj

    def _visual_narrator_processing(self, story: str) -> Dict:
        """Visual Narrator processing theo lưu đồ"""
        try:
            # Pattern matching cho standard user story format
            # "As a [role], I want [action] [object] so that [benefit]"
            user_story_pattern = r"As an?\s+(.*?),\s*I\s+want\s+to\s+(.*?)\s+(.*?)\s*(?:so that|in order to|because)?"
            
            match = re.search(user_story_pattern, story, re.IGNORECASE)
            
            if match:
                role = match.group(1).strip()
                action = match.group(2).strip()
                obj = match.group(3).strip()
                
                # Phân tích entities và relationships
                doc = self.nlp(story)
                entities = []
                relationships = []
                
                for ent in doc.ents:
                    entities.append({
                        'text': ent.text,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char
                    })
                
                # Phân tích dependency relationships
                for token in doc:
                    if token.dep_ in ['nsubj', 'dobj', 'pobj']:
                        relationships.append({
                            'head': token.head.text,
                            'relation': token.dep_,
                            'child': token.text
                        })
                
                return {
                    'role': role,
                    'action': action,
                    'object': obj,
                    'entities': entities,
                    'relationships': relationships,
                    'confidence_score': 0.9,  # High confidence for pattern match
                    'parsed_structure': {
                        'format': 'standard_user_story',
                        'components': {
                            'role': role,
                            'action': action,
                            'object': obj
                        }
                    }
                }
            else:
                # Fallback analysis với confidence thấp hơn
                doc = self.nlp(story)
                entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents]
                
                return {
                    'role': None,
                    'action': None,
                    'object': None,
                    'entities': entities,
                    'relationships': [],
                    'confidence_score': 0.3,
                    'parsed_structure': {
                        'format': 'free_text',
                        'entities': entities
                    }
                }
                
        except Exception as e:
            logging.error(f"Visual Narrator processing failed: {e}")
            return None

    def _save_visual_narrator_result(self, session: Session, user_story_id: str, 
                                   visual_result: Dict, session_id: str):
        """Lưu kết quả Visual Narrator vào database"""
    # Simplified: store visual narrator result inside Concept.metadata_json
        try:
            concept = session.query(Concept).filter_by(user_story_id=user_story_id).first()
            if concept:
                meta = concept.metadata_json or {}
                meta.update({
                    'visual_narrator': visual_result,
                    'visual_session': session_id
                })
                concept.metadata_json = meta
                session.add(concept)
        except Exception as e:
            logging.error(f"Failed to save visual narrator result to concept metadata: {e}")

    def _create_processing_session(self, total_stories: int) -> ProcessingSession:
        """Tạo processing session mới"""
        with DatabaseSession(self.db_manager) as session:
            processing_session = ProcessingSession(
                session_name=self.session_name,
                total_stories=total_stories,
                phase_completed=0,
                status="started"
            )
            session.add(processing_session)
            session.flush()  # Để lấy ID
            return processing_session
    
    def _update_processing_session(self, session: Session, session_id: str, 
                                 phase_completed: int, status: str):
        """Cập nhật processing session"""
        processing_session = session.query(ProcessingSession).filter_by(id=session_id).first()
        if processing_session:
            processing_session.phase_completed = phase_completed
            processing_session.status = status
            if status == "completed":
                from datetime import datetime
                processing_session.completed_at = datetime.utcnow()
    
    def _save_to_database(self, session: Session, story_id: str, original_text: str, 
                         role: str, action: str, obj: str) -> str:
        """Lưu user story và concept vào database, return user_story_id"""
        # Tạo user story
        user_story = UserStory(
            story_id=story_id,
            original_text=original_text
        )
        session.add(user_story)
        session.flush()  # Để lấy ID
        
        # Tạo concept
        concept = Concept(
            user_story_id=user_story.id,
            role=role if role else None,
            action=action if action else None,
            object=obj if obj else None
        )
        session.add(concept)
        
        return user_story.id
    
    def load_from_database(self, session_name: str = None) -> Dict:
        """Load dữ liệu từ database"""
        session_name = session_name or self.session_name
        
        with DatabaseSession(self.db_manager) as session:
            # Tìm processing session
            processing_session = session.query(ProcessingSession).filter_by(
                session_name=session_name
            ).first()
            
            if not processing_session:
                logging.warning(f"Session '{session_name}' not found")
                return {}
            
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
            
            roles = sorted(list(set([c["role"] for c in results if c["role"]])))
            actions = sorted(list(set([c["action"] for c in results if c["action"]])))
            objects = sorted(list(set([c["object"] for c in results if c["object"]])))
            
            self.extracted_concepts = {
                "concepts": results,
                "roles": roles,
                "actions": actions,
                "objects": objects,
                "session_id": processing_session.id
            }
            
            return self.extracted_concepts

    def export_json(self, filename: str = "phase1_raw.json") -> str:
        """Xuất kết quả đã trích xuất ra file JSON."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_concepts, f, indent=2, ensure_ascii=False)
            print(f"Exported to {filename}")
            return filename
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return ""