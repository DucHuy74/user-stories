from typing import List, Dict, Any
from models import Concept
from sqlalchemy import or_


def generate_synonym_records(concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Accept either dicts with 'name'/'text' or plain strings
    records = []
    for c in concepts:
        if isinstance(c, dict):
            name = c.get('name') or c.get('text')
        else:
            name = str(c)
        if not name:
            continue
        records.append({
            'concept': name,
            'synonyms': [name]
        })
    return records


def save_synonyms(session, user_story_id: str, synonym_records: List[Dict[str, Any]]):
    for rec in synonym_records:
        concept_text = rec.get('concept')
        if not concept_text:
            continue
        # Find concept row where any of role/action/object matches the concept text
        concept = session.query(Concept).filter(
            Concept.user_story_id == user_story_id,
            or_(
                Concept.action == concept_text,
                Concept.role == concept_text,
                Concept.object == concept_text,
            )
        ).first()
        if concept:
            meta = concept.metadata_json or {}
            meta['synonyms'] = rec.get('synonyms', [])
            concept.metadata_json = meta
            session.add(concept)
