from typing import List, Dict, Any
from collections import Counter
from models.concept import Concept
from models.user_story import UserStory



CONTROL_VERBS = {"create", "update", "delete", "view", "change", "reset"}


def _classify_domain(name: str, concept_type: str | None, frequency: int, threshold: int = 3) -> str | None:

    if not name:
        return None
    if concept_type and concept_type.lower().startswith("object"):
        return "important" if int(frequency or 0) >= threshold else "general"
    if concept_type and concept_type.lower().startswith("verb"):
        return "action"
    if concept_type and concept_type.lower().startswith("subject"):
        return "role"
    return None


def _compute_flag_and_feature(name: str, concept_type: str | None, object_verbs: set[str] | None = None) -> tuple[int, bool]:
    
    if not name:
        return 0, True
    if concept_type and concept_type == 'Object':
        verbs = object_verbs or set()
        is_feature = any((v in CONTROL_VERBS) for v in verbs)
        return (0 if is_feature else 1), is_feature
    # Subjects/Verbs: keep as feature by default
    return 0, True


def build_object_verbs_map(svo_raw: List[Dict[str, Any]]) -> Dict[str, set[str]]:
 
    mapping: Dict[str, set[str]] = {}
    for r in svo_raw:
        obj = (r.get('object') or '').strip().lower()
        verb = (r.get('verb') or '').strip().lower()
        if not obj or not verb:
            continue
        mapping.setdefault(obj, set()).add(verb)
    return mapping


def count_concept_frequency(concepts: List[Dict[str, Any]]) -> Dict[str, int]:
    names = [
        (c.get('text') or c.get('name'))
        for c in concepts
        if (c.get('text') or c.get('name')) and (c.get('concept_type') == 'Object')
    ]
    return dict(Counter(names))


def attach_frequency_to_concepts(concepts: List[Dict[str, Any]], frequencies: Dict[str, int], object_verbs: Dict[str, set[str]], threshold: int = 3) -> List[Dict[str, Any]]:
    for c in concepts:

        name = c.get('text') or c.get('name')
        ctype = c.get('concept_type')
        
        freq = frequencies.get(name, 0) if ctype == 'Object' else 0
        c['frequency'] = freq
        
        if 'user_story_db_id' not in c and 'db_id' in c:
            c['user_story_db_id'] = c['db_id']
            
        c['domain'] = _classify_domain(name, ctype, freq, threshold)
        
        verbs = object_verbs.get((name or '').lower(), set()) if ctype == 'Object' else set()
        flag, is_feature = _compute_flag_and_feature(name, ctype, verbs)
        c['flag'] = flag  
        
        c['is_feature'] = is_feature  
    return concepts


def save_concepts(session, user_story_id: int, concepts: List[Dict[str, Any]]):
    for c in concepts:
        # Map generic fields into Concept schema
        name = (c.get('text') or c.get('name'))
        if not name:
            # skip malformed entries
            continue
        concept_type = c.get('concept_type')  # Subject | Verb | Object
        is_feature = bool(c.get('is_feature', False))

        # Fetch role from UserStory for pairing
        user_story = session.query(UserStory).filter_by(usid=user_story_id).first()
        role_text = user_story.role if user_story else None

        # Compute binary flags from is_feature
        feature_flag = 1 if is_feature else 0
        value_flag = 0 if is_feature else 1

        # Map new fields based on concept type
        text_userrole = None
        text_object_as_concept_domain = None
        if concept_type == 'Subject':
            text_userrole = name
        elif concept_type == 'Object':
            text_object_as_concept_domain = name
            # also ensure userrole captured for object rows
            if role_text and not text_userrole:
                text_userrole = role_text

        # Persist only Object rows to align with one-row-per-object model
        if concept_type == 'Object':
            concept = Concept(
                indices=user_story_id,
                text_userrole=text_userrole or role_text,
                text_object_as_concept_domain=text_object_as_concept_domain,
                feature_flag=feature_flag,
                value_flag=value_flag,
            )
            session.add(concept)
