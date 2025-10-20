from typing import List, Dict, Any
from collections import Counter
from models import Concept


def count_concept_frequency(concepts: List[Dict[str, Any]]) -> Dict[str, int]:
    names = [c.get('name') for c in concepts if c.get('name')]
    return dict(Counter(names))


def attach_frequency_to_concepts(concepts: List[Dict[str, Any]], frequencies: Dict[str, int]) -> List[Dict[str, Any]]:
    for c in concepts:
        name = c.get('name')
        c['frequency'] = frequencies.get(name, 0)
    return concepts


def save_concepts(session, user_story_id: str, concepts: List[Dict[str, Any]]):
    for c in concepts:
        concept = Concept(
            user_story_id=user_story_id,
            name=c.get('name'),
            metadata_json=c
        )
        session.add(concept)
