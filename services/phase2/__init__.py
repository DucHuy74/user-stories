import logging
from typing import Dict
from database import DatabaseSession, get_database_manager
from .helpers import count_concept_frequency, attach_frequency_to_concepts, save_concepts
from models import ProcessingSession


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
                # generate final output from phase1 concepts
                self._generate_final_output()
                # compute frequency across final_output texts
                self.object_frequency = count_concept_frequency(self.final_output)
                # attach frequencies to final_output
                self.final_output = attach_frequency_to_concepts(self.final_output, self.object_frequency)
                # persist concepts based on final_output
                for rec in self.final_output:
                    user_story_db_id = rec.get('user_story_db_id') or rec.get('db_id') or rec.get('id')
                    save_concepts(session, user_story_db_id, [rec])
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
            external_id = concept_item.get("id")
            user_story_db_id = concept_item.get("db_id")
            original_text = concept_item.get("original_text")
            role = concept_item.get("role")
            action = concept_item.get("action")
            obj = concept_item.get("object")

            if action:
                self.final_output.append({
                    "usid_text": f"{external_id}: {original_text}",
                    "user_story_db_id": user_story_db_id,
                    "text": action,
                    "concept_and_domain": "feature",
                    "0 - feature flag": 0,
                    "1 - value flag": None
                })

            if role:
                self.final_output.append({
                    "usid_text": f"{external_id}: {original_text}",
                    "user_story_db_id": user_story_db_id,
                    "text": role,
                    "concept_and_domain": "role (general)",
                    "0 - feature flag": None,
                    "1 - value flag": 1
                })

            if obj:
                self.final_output.append({
                    "usid_text": f"{external_id}: {original_text}",
                    "user_story_db_id": user_story_db_id,
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
