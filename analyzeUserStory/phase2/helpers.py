from typing import List, Dict, Any
from collections import Counter
from models import Concept


def count_concept_frequency(concepts: List[Dict[str, Any]]) -> Dict[str, int]:
    # Phase2 concepts may use 'name' or 'text' as the value holder
    names = [c.get('name') or c.get('text') for c in concepts if (c.get('name') or c.get('text'))]
    return dict(Counter(names))


def attach_frequency_to_concepts(concepts: List[Dict[str, Any]], frequencies: Dict[str, int]) -> List[Dict[str, Any]]:
    for c in concepts:
        # Phase2 may store the text under 'name' or 'text' — use either for lookup
        name = c.get('name') or c.get('text')
        c['frequency'] = frequencies.get(name, 0)
    return concepts


def save_concepts(session, user_story_id: str, concepts: List[Dict[str, Any]]):
    for c in concepts:
        # Map the generic 'name' or 'text' field from Phase2 final_output into the
        # appropriate Concept columns (action/role/object) based on classification
        name = c.get('name') or c.get('text')
        classification = c.get('concept_and_domain', '') or ''
        role = None
        action = None
        obj = None
        if 'feature' in classification:
            action = name
        elif 'role' in classification:
            role = name
        elif 'object' in classification:
            obj = name
        else:
            # fallback to action
            action = name

        concept = Concept(
            user_story_id=user_story_id,
            role=role,
            action=action,
            object=obj,
            metadata_json=c
        )
        session.add(concept)
