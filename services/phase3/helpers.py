from typing import List, Dict, Any
from models.concept import Concept
from models.synonym import Synonym
from models.concept_map import ConceptMap


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


def save_synonyms(session, user_story_id: int, synonym_records: List[Dict[str, Any]]):
    for rec in synonym_records:
        concept_text = rec.get('concept')
        if not concept_text:
            continue
        concepts = session.query(Concept).filter(
            Concept.usid == user_story_id,
            Concept.term == concept_text,
        ).all()
        for c in concepts:
            for syn in rec.get('synonyms', [concept_text]):
                session.add(Synonym(concept_id=c.concept_id, synonym_term=syn, source='WordNet'))


def save_svo_relationships(session, svo_list: List[Dict[str, Any]]):
    """Persist SVO as entries in concept_map.
    Each item should contain keys: subject, verb, object, and user_story_db_id.
    """
    for svo in svo_list:
        usid = svo.get('user_story_db_id')
        subj = (svo.get('subject') or '').strip()
        verb = (svo.get('verb') or '').strip()
        obj = (svo.get('object') or '').strip()
        if not (usid and subj and obj):
            continue
        subj_concept = session.query(Concept).filter(Concept.usid == usid, Concept.term == subj).first()
        obj_concept = session.query(Concept).filter(Concept.usid == usid, Concept.term == obj).first()
        if subj_concept and obj_concept:
            session.add(ConceptMap(
                subject_concept_id=subj_concept.concept_id,
                verb=verb or None,
                object_concept_id=obj_concept.concept_id,
                relation_type='SVO',
                source='phase3'
            ))
