import uuid
from typing import Dict, Any


class Phase4:
    """Phase4: persist phase outputs into Neo4j using provided GraphDB instance."""

    def persist_graph(self, phase1_output: Dict[str, Any], phase3_output: Dict[str, Any], graph):
        """Persist phase1 user stories and phase3 SVO relationships into graph DB.

        Args:
            phase1_output: result from Phase1.process_text (expects key 'concepts')
            phase3_output: result from Phase3.process_wordnet (expects key 'subject_verb_object')
            graph: GraphDB instance with create_node / create_relationship methods
        """
        # 1. Persist user stories (from phase1 output)
        for us in phase1_output.get("concepts", []):
            story_uuid = str(uuid.uuid4())
            story_text = us.get("original_text")
            # phase1 may provide an id for the phase1 concept; preserve as phase1_id
            phase1_id = us.get("id")
            graph.create_node(
                "UserStory",
                {"id": story_uuid, "phase1_id": phase1_id, "text": story_text},
                key="id"
            )

        # 2. Persist Role - Action - Object relationships (prefer normalized_svo)
        svo_source = phase3_output.get("normalized_svo") or phase3_output.get("subject_verb_object", [])
        for svo in svo_source:
            subj = svo.get("subject")
            verb = svo.get("verb")
            obj = svo.get("object")

            if subj and obj and verb:
                # Create role and object nodes (merge by name)
                graph.create_node("Role", {"name": subj}, key="name")
                graph.create_node("Object", {"name": obj}, key="name")

                # Create relationship with verb stored in relationship properties
                graph.create_relationship(
                    start_label="Role", start_key="name", start_val=subj,
                    rel_type="ACTION",
                    end_label="Object", end_key="name", end_val=obj,
                    props={"verb": verb}
                )
