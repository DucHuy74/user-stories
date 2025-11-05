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
        self.important_objects = []
        self.object_verbs = {}
        self.session_id = session_id
        self.db_manager = get_database_manager()

    def analyze_concepts(self, phase1_data: Dict = None) -> Dict:
        if phase1_data:
            self.input_data = phase1_data
            self.session_id = phase1_data.get("session_id")

        with DatabaseSession(self.db_manager) as session:

            self._generate_final_output()
            
            self.object_verbs = self._build_object_verbs_from_phase1()
            
            self.object_frequency = count_concept_frequency(self.final_output)
            
            self.final_output = attach_frequency_to_concepts(self.final_output, self.object_frequency, self.object_verbs, threshold=3)
            # derive important objects summary (freq >= 3)
            threshold = 3
            imp = []
            for c in self.final_output:
                if c.get('concept_type') == 'Object' and int(c.get('frequency') or 0) >= threshold:
                    imp.append({
                        'object': c.get('text') or c.get('name'),
                        'frequency': int(c.get('frequency') or 0),
                        'verbs': sorted(list(self.object_verbs.get((c.get('text') or c.get('name') or '').lower(), set()))),
                        'flag': c.get('flag'),
                    })
            # sort important by frequency desc then name
            self.important_objects = sorted(imp, key=lambda x: (-x['frequency'], x['object'] or ''))
            # persist concepts based on final_output (internal Subject/Verb/Object records)
            for rec in self.final_output:
                user_story_db_id = rec.get('user_story_db_id') or rec.get('db_id') or rec.get('usid')
                save_concepts(session, user_story_db_id, [rec])

            # Build API response rows in the new shape (one row per Object)
            role_by_usid = {}
            for r in self.input_data.get("concepts", []):
                uid = r.get("db_id") or r.get("usid")
                if uid and r.get("role") and int(uid) not in role_by_usid:
                    role_by_usid[int(uid)] = r.get("role")

            response_rows = []
            for rec in self.final_output:
                if rec.get('concept_type') != 'Object':
                    continue
                uid = rec.get('user_story_db_id') or rec.get('db_id') or rec.get('usid')
                if not uid:
                    continue
                is_feature = bool(rec.get('is_feature', False))
                response_rows.append({
                    'indices': int(uid),
                    'text_userrole': role_by_usid.get(int(uid), ''),
                    'text_object_as_concept_domain': rec.get('text') or rec.get('name') or '',
                    'feature_flag': 1 if is_feature else 0,
                    'value_flag': 0 if is_feature else 1,
                })

            # Replace final_output with the new model shape
            self.final_output = response_rows
            self._update_processing_session(session, 2, "completed")

        logging.info(f"✅ Phase 2 completed: Analyzed {len(self.final_output)} records")


        return {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output,
            "important_objects": self.important_objects,
            "object_verbs": {k: sorted(list(v)) for k, v in self.object_verbs.items()},
            "session_id": self.session_id
        }

    def _generate_final_output(self):
        self.final_output = []
        # derive concepts from Phase1 'concepts' entries
        for r in self.input_data.get("concepts", []):
            usid = r.get("db_id") or r.get("usid")
            subj = r.get("role")
            verb = r.get("action")
            obj = r.get("object")
            if subj:
                self.final_output.append({
                    "usid": usid,
                    "db_id": usid,
                    "text": subj,
                    "concept_type": "Subject"
                })
            if verb:
                self.final_output.append({
                    "usid": usid,
                    "db_id": usid,
                    "text": verb,
                    "concept_type": "Verb"
                })
            if obj:
                self.final_output.append({
                    "usid": usid,
                    "db_id": usid,
                    "text": obj,
                    "concept_type": "Object"
                })

        for i, record in enumerate(self.final_output):
            record["indices"] = i + 1

    def _build_object_verbs_from_phase1(self) -> Dict[str, set]:
        """Build mapping object -> set(verbs) using Phase1 concepts list.

        This approximates object-verb grouping by pairing each story's object with its action.
        """
        mapping: Dict[str, set] = {}
        for r in self.input_data.get("concepts", []):
            obj = (r.get("object") or "").strip().lower()
            verb = (r.get("action") or "").strip().lower()
            if not obj or not verb:
                continue
            mapping.setdefault(obj, set()).add(verb)
        return mapping

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
