from typing import List, Dict, Any
from collections import Counter
from models.concept import Concept


def count_concept_frequency(concepts: List[Dict[str, Any]]) -> Dict[str, int]:
    # Compute frequency across provided concept records; prefer 'text'
    names = [
        (c.get('text') or c.get('name'))
        for c in concepts
        if (c.get('text') or c.get('name'))
    ]
    return dict(Counter(names))


def attach_frequency_to_concepts(concepts: List[Dict[str, Any]], frequencies: Dict[str, int]) -> List[Dict[str, Any]]:
    for c in concepts:
        # Phase2 may store the text under 'name' or 'text' — use either for lookup
        name = c.get('text') or c.get('name')
        c['frequency'] = frequencies.get(name, 0)
        # normalize type for future persistence
        if 'user_story_db_id' not in c and 'db_id' in c:
            c['user_story_db_id'] = c['db_id']
    return concepts


def save_concepts(session, user_story_id: int, concepts: List[Dict[str, Any]]):
    for c in concepts:
        # Map generic fields into Concept schema
        name = (c.get('text') or c.get('name'))
        if not name:
            # skip malformed entries
            continue
        classification = (c.get('concept_and_domain') or '').lower()
        is_feature = 'feature' in classification
        # derive a simple domain label
        if 'role' in classification:
            domain = 'role'
        elif 'object' in classification:
            domain = 'object'
        elif 'feature' in classification:
            domain = 'feature'
        else:
            domain = None
        frequency = c.get('frequency') or 1

        concept = Concept(
            usid=user_story_id,
            term=name,
            is_feature=is_feature,
            frequency=frequency,
            domain=domain
        )
        session.add(concept)
