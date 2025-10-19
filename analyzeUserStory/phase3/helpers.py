from typing import List, Dict, Any
from models import Concept


def generate_synonym_records(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # placeholder: real synonym generation is more complex
    records = []
    for c in concepts:
        name = c.get('name')
        records.append({
            'concept': name,
            'synonyms': [name]
        })
    return records


def save_synonyms(session, user_story_id: str, synonym_records: List[Dict[str, Any]]):
    for rec in synonym_records:
        concept = session.query(Concept).filter_by(user_story_id=user_story_id, name=rec['concept']).first()
        if concept:
            meta = concept.metadata_json or {}
            meta['synonyms'] = rec.get('synonyms', [])
            concept.metadata_json = meta
            session.add(concept)
