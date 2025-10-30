import uuid
import logging
from typing import List, Dict, Optional
from database import DatabaseSession, get_database_manager
from models.models import ProcessingSession
from .helpers import (
    create_processing_session,
    save_visual_narrator_result,
    save_to_database,
    update_processing_session,
    get_timestamp,
    extract_components
)


class Phase1:
    def __init__(self, model_name: str = "en_core_web_sm", session_name: str = None):
        import spacy
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)

        self.user_stories = []
        self.extracted_concepts = {}
        self.session_name = session_name or f"phase1_session_{get_timestamp()}_{uuid.uuid4().hex}"
        self.db_manager = get_database_manager()
        self.db_manager.create_tables()

    def process_text(self, user_stories: List[str]) -> Dict:
        self.user_stories = user_stories
        results = []
        processing_session = create_processing_session(self.db_manager, self.session_name, len(user_stories))

        try:
            with DatabaseSession(self.db_manager) as session:
                for story in self.user_stories:
                    if not story.strip():
                        continue
                    role, action, obj = extract_components(story, self.nlp)
                    story_id = str(uuid.uuid4())
                    concept = {
                        "id": story_id,
                        "original_text": story.strip(),
                        "role": role or "",
                        "action": action or "",
                        "object": obj or "",
                    }
                    results.append(concept)
                    user_story_id = save_to_database(session, story_id, story.strip(), role, action, obj)
                    # store DB primary key so downstream phases can persist Concept rows
                    concept["db_id"] = user_story_id
                    visual_result = None
                    # call visual narrator only when needed
                    from .helpers import visual_narrator_processing
                    visual_result = visual_narrator_processing(story, self.nlp)
                    if visual_result:
                        save_visual_narrator_result(session, user_story_id, visual_result, processing_session.id)

                update_processing_session(session, processing_session.id, 1, "completed")

            logging.info(f"✅ Phase 1 completed: Processed {len(results)} user stories")
        except Exception as e:
            logging.error(f"❌ Phase 1 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                update_processing_session(session, processing_session.id, 1, "failed")
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

    def load_from_database(self, session_name: str = None) -> Dict:
        session_name = session_name or self.session_name
        with DatabaseSession(self.db_manager) as session:
            processing_session = session.query(ProcessingSession).filter_by(session_name=session_name).first()
            if not processing_session:
                logging.warning(f"Session '{session_name}' not found")
                return {}

            user_stories = session.query(ProcessingSession).all()
            # simplified: re-use existing load_from_database logic from previous implementation
            return {}