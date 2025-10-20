import logging
from typing import Dict, List
from database import DatabaseSession, get_database_manager
from .helpers import generate_synonym_records, save_synonyms
from models import ProcessingSession


class Phase3:
    def __init__(self, session_id: str = None):
        self.input_data = {}
        self.synonyms = {}
        self.similarities = []
        self.final_output = {}
        self.session_id = session_id
        self.db_manager = get_database_manager()

    def process_wordnet(self, phase2_data: Dict = None) -> Dict:
        if phase2_data:
            self.input_data = phase2_data
            self.session_id = phase2_data.get("session_id")

        try:
            with DatabaseSession(self.db_manager) as session:
                concepts = [r.get('text') for r in self.input_data.get('final_output', []) if r.get('text')]
                synonym_records = generate_synonym_records([{'name': c} for c in concepts])
                save_synonyms(session, self.session_id, synonym_records)

                # simplified similarity logic left in module for future expansion
                self._create_final_output()
                self._update_processing_session(session, 3, "completed")

            logging.info("✅ Phase 3 completed")
        except Exception as e:
            logging.error(f"❌ Phase 3 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                self._update_processing_session(session, 3, "failed")
            raise

        return self.final_output

    def _create_final_output(self):
        all_records = self.input_data.get("final_output", [])
        roles = list(set([r.get("text") for r in all_records if "role" in r.get("concept_and_domain", "") and r.get("text")]))
        objects = list(set([r.get("text") for r in all_records if "object" in r.get("concept_and_domain", "") and r.get("text")]))
        verbs = list(set([r.get("text") for r in all_records if r.get("concept_and_domain") == "feature" and r.get("text")]))

        story_map = {}
        for record in all_records:
            usid = record.get("usid_text", "").split(":", 1)[0].strip()
            ent = story_map.setdefault(usid, {"subject": "", "verb": "", "object": "", "usid": usid})
            if "role" in record.get("concept_and_domain", ""):
                ent["subject"] = record.get("text", "")
            elif "object" in record.get("concept_and_domain", ""):
                ent["object"] = record.get("text", "")
            elif record.get("concept_and_domain") == "feature":
                ent["verb"] = record.get("text", "")

        svo_relationships = [v for v in story_map.values() if v.get("subject") or v.get("verb") or v.get("object")]

        self.final_output = {
            "user_roles": [r for r in roles if r],
            "objects": [o for o in objects if o],
            "verbs": [v for v in verbs if v],
            "subject_verb_object": svo_relationships,
            "pairwise_relationships": [],
            "synonyms": {},
            "session_id": self.session_id
        }

    def _update_processing_session(self, session, phase_completed: int, status: str):
        processing_session = session.query(ProcessingSession).filter_by(id=self.session_id).first()
        if processing_session:
            processing_session.phase_completed = phase_completed
            processing_session.status = status
            if status == "completed":
                from datetime import datetime
                processing_session.completed_at = datetime.utcnow()

    def get_results(self):
        return self.final_output
