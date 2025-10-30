import logging
from typing import Dict, List
from database import DatabaseSession, get_database_manager
from .helpers import count_concept_frequency, attach_frequency_to_concepts, save_concepts
from models.models import ProcessingSession


class Phase2:
    def __init__(self, session_id: str = None):
        self.input_data = {}
        self.object_frequency = {}
        self.final_output = []
        self.session_id = session_id
        self.db_manager = get_database_manager()

    def analyze_concepts(self, phase1_data: Dict = None) -> Dict:
        if phase1_data:
            self.input_data = phase1_data
            self.session_id = phase1_data.get("session_id")

        try:
            with DatabaseSession(self.db_manager) as session:
                concepts = self.input_data.get("concepts", [])
                self.object_frequency = count_concept_frequency(concepts)
                enriched = attach_frequency_to_concepts(concepts, self.object_frequency)
                # persist concepts
                for c in enriched:
                    user_story_db_id = c.get('db_id') or c.get('id')
                    save_concepts(session, user_story_db_id, [c])

                # generate final output
                self._generate_final_output()
                self._update_processing_session(session, 2, "completed")

            logging.info(f"✅ Phase 2 completed: Analyzed {len(self.final_output)} records")
        except Exception as e:
            logging.error(f"❌ Phase 2 failed: {e}")
            with DatabaseSession(self.db_manager) as session:
                self._update_processing_session(session, 2, "failed")
            raise

        return {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output,
            "session_id": self.session_id
        }

    def _generate_final_output(self):
        self.final_output = []
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

    def _update_processing_session(self, session, phase_completed: int, status: str):
        processing_session = session.query(ProcessingSession).filter_by(id=self.session_id).first()
        if processing_session:
            processing_session.phase_completed = phase_completed
            processing_session.status = status
            if status == "completed":
                from datetime import datetime
                processing_session.completed_at = datetime.utcnow()

    def get_results(self):
        return {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output,
            "session_id": self.session_id
        }
