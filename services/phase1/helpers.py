from typing import Dict, Any, Optional, Tuple
import logging
import re
from database import DatabaseSession, get_database_manager
from models import ProcessingSession
from models.user_story import UserStory


def create_processing_session(db_manager, session_name: str, total_stories: int) -> ProcessingSession:
    with DatabaseSession(db_manager) as session:
        processing_session = ProcessingSession(
            session_name=session_name,
            total_stories=total_stories,
            phase_completed=0,
            status="started"
        )
        session.add(processing_session)
        session.flush()
        return processing_session


def save_visual_narrator_result(session, user_story_id: int, visual_result: Dict[str, Any], session_id: str):
    # New schema has no per-concept metadata field; keep for future audit table.
    logging.debug("Visual narrator result received for usid=%s (ignored by current schema)", user_story_id)


def save_to_database(session, story_id: str, original_text: str, role: Optional[str], action: Optional[str], obj: Optional[str]) -> int:
    try:
        user_story = UserStory(
            text=original_text,
            role=role if role else None,
            verb=action if action else None,
            object=obj if obj else None,
        )
        session.add(user_story)
        session.flush()
        return user_story.usid
    except Exception:
        # Ensure any exception doesn't leave transaction open
        try:
            session.rollback()
        except Exception:
            pass
        raise


def update_processing_session(session, session_id: str, phase_completed: int, status: str):
    processing_session = session.query(ProcessingSession).filter_by(id=session_id).first()
    if processing_session:
        processing_session.phase_completed = phase_completed
        processing_session.status = status
        if status == "completed":
            from datetime import datetime
            processing_session.completed_at = datetime.utcnow()


def get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")


from typing import Optional, Tuple, List
# import spacy # Đã có trong context của class Phase1

# Giả định các hàm find_role, find_action_and_object, và visual_narrator_processing đã được định nghĩa

def extract_components(story: str, nlp) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    doc = nlp(story.strip())
    
    story_core_tokens: List[str] = []
    
    tokens_to_exclude = {token.i for token in doc if token.dep_ == "advcl"}

    for token in doc:
        if token.i in tokens_to_exclude:
            for child in token.subtree:
                tokens_to_exclude.add(child.i)


    for token in doc:
        if token.i not in tokens_to_exclude:
            story_core_tokens.append(token.text_with_ws)

    story_core = "".join(story_core_tokens).strip()

    doc_core = nlp(story_core)
    role = find_role(doc_core)
    action, obj = find_action_and_object(doc_core)

    visual_narrator_result = visual_narrator_processing(story, nlp)
    if visual_narrator_result:
        if visual_narrator_result.get('confidence_score', 0) > 0.8:
            role = visual_narrator_result.get('role') or role
            action = visual_narrator_result.get('action') or action
            obj = visual_narrator_result.get('object') or obj

    # 6. Chuẩn hóa chuỗi (Vẫn giữ nguyên)
    role = role.lower().strip() if role else None
    action = action.lower().strip() if action else None
    obj = obj.lower().strip() if obj else None

    return role, action, obj


def find_role(doc) -> Optional[str]:
    for token in doc:
        #prep = giới từ
        if token.lower_ == "as" and token.dep_ == "prep":
            for child in token.children:
                # pobj = tân ngữ giới từ
                if child.dep_ == "pobj":
                    role_tokens = [t.text for t in child.subtree if not t.is_punct]
                    return " ".join(role_tokens).strip()

        if token.i > 5 and token.dep_ not in ("nsubj", "nsubjpass", "ROOT"):
            break


    for token in doc:
        if token.dep_ in ("nsubj", "nsubjpass"):
            if token.pos_ not in ("PRON", "NOUN") or token.head.dep_ != "ROOT":
                continue

            return " ".join([t.text for t in token.subtree if not t.is_punct])

    return None


def find_action_and_object(doc) -> Tuple[Optional[str], Optional[str]]:
    action = None
    obj = None

    main_verb = None
    for token in doc:
        if token.dep_ == "ROOT" and token.pos_ == "VERB":
            main_verb = token
            break

    if main_verb and main_verb.lemma_ in ("want", "like"):
        for child in main_verb.children:
            if child.dep_ == "xcomp" and child.pos_ == "VERB":
                main_verb = child
                break

    if not main_verb:
        for token in doc:
            if token.pos_ == "VERB" and token.dep_ in ("ccomp", "advcl"):
                main_verb = token
                break

    if main_verb:
        action = main_verb.lemma_

        for child in main_verb.children:
            if child.dep_ == "dobj":
                obj = " ".join([t.text for t in child.subtree if not t.is_punct])
                break

        if obj is None:
            for child in main_verb.children:
                if child.dep_ == "prep":
                    for grandchild in child.children:
                        if grandchild.dep_ == "pobj":
                            obj = " ".join([t.text for t in grandchild.subtree if not t.is_punct])
                            break
                if obj:
                    break
    if not action and not obj:
        first_token = doc[0]
        if first_token.pos_ in ("NOUN", "DET", "PROPN"):
            obj = " ".join([t.text for t in doc if not t.is_punct])

    return action, obj


def visual_narrator_processing(story: str, nlp) -> Optional[Dict[str, Any]]:
    try:
        user_story_pattern = r"As an?\s+(.*?),\s*I\s+want\s+to\s+(.*?)\s+(.*?)\s*(?:so that|in order to|because)?"
        match = re.search(user_story_pattern, story, re.IGNORECASE)

        if match:
            role = match.group(1).strip()
            action = match.group(2).strip()
            obj = match.group(3).strip()

            doc = nlp(story)
            entities = []
            relationships = []
            for ent in doc.ents:
                entities.append({'text': ent.text, 'label': ent.label_, 'start': ent.start_char, 'end': ent.end_char})
            for token in doc:
                if token.dep_ in ['nsubj', 'dobj', 'pobj']:
                    relationships.append({'head': token.head.text, 'relation': token.dep_, 'child': token.text})

            return {
                'role': role,
                'action': action,
                'object': obj,
                'entities': entities,
                'relationships': relationships,
                'confidence_score': 0.9,
                'parsed_structure': {
                    'format': 'standard_user_story',
                    'components': {'role': role, 'action': action, 'object': obj}
                }
            }
        else:
            doc = nlp(story)
            entities = [{'text': ent.text, 'label': ent.label_} for ent in doc.ents]
            return {
                'role': None,
                'action': None,
                'object': None,
                'entities': entities,
                'relationships': [],
                'confidence_score': 0.3,
                'parsed_structure': {'format': 'free_text', 'entities': entities}
            }
    except Exception as e:
        logging.error(f"Visual Narrator processing failed: {e}")
        return None