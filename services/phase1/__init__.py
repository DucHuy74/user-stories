import uuid
import logging
from typing import List, Dict
from database import DatabaseSession, get_database_manager
from .helpers import (
    create_processing_session,
    save_to_database,
    update_processing_session,
    get_timestamp,
    extract_components,
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

        self.session_name = session_name or f"phase1_session_{get_timestamp()}_{uuid.uuid4().hex}"
        self.db_manager = get_database_manager()
        self.db_manager.create_tables()

    def process_text(self, user_stories: List[str]) -> Dict:
        processing_session = create_processing_session(self.db_manager, self.session_name, len(user_stories))
        results = []

        with DatabaseSession(self.db_manager) as session:
            for story in filter(str.strip, user_stories):
                role, action, obj = extract_components(story, self.nlp)
                story_id = str(uuid.uuid4())

                user_story_id = save_to_database(session, story_id, story.strip(), role, action, obj, nlp=self.nlp)

                results.append({
                    "id": story_id,
                    "db_id": user_story_id,
                    "original_text": story.strip(),
                    "role": role or "",
                    "action": action or "",
                    "object": obj or "",
                })

            update_processing_session(session, processing_session.id, 1, "completed")
        logging.info(f"✅ Phase 1 completed: Processed {len(results)} user stories")
        

        roles = sorted({c["role"] for c in results if c["role"]})
        actions = sorted({c["action"] for c in results if c["action"]})
        objects = sorted({c["object"] for c in results if c["object"]})


        return {
            "concepts": results,
            "roles": roles,
            "actions": actions,
            "objects": objects,
            "session_id": processing_session.id,
        }


    # nếu như sau này cần kết quả từ những lần phân tích trước đó thì có thể dùng hiện tại thì sẽ không
    # def load_from_database(self, session_name: str = None) -> Dict:
    #     session_name = session_name or self.session_name
    #     with DatabaseSession(self.db_manager) as session:
    #         processing_session = session.query(ProcessingSession).filter_by(session_name=session_name).first()
    #         if not processing_session:
    #             logging.warning(f"Session '{session_name}' not found")
    #             return {}
    #         # TODO: Implement actual loading if needed later
    #         return {}
