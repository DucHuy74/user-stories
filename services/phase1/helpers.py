from typing import Dict, Any, Optional, Tuple, List
import logging
import re
from database import DatabaseSession
from models import ProcessingSession
from models.user_story import UserStory
from models.svo_raw import SvoRaw


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


# Visual Narrator is no longer used


def extract_svos(doc) -> List[Tuple[Optional[str], Optional[str], Optional[str]]]:
    """Extract all SVO triples from a spaCy doc (simple heuristic)."""
    svos: List[Tuple[Optional[str], Optional[str], Optional[str]]] = []
    for token in doc:
        if token.pos_ == 'VERB':
            subj = None
            obj = None
            # subject
            for child in token.children:
                if child.dep_ in ('nsubj', 'nsubjpass'):
                    subj = " ".join([t.text for t in child.subtree if not t.is_punct])
                    break
            # direct object or pobj
            for child in token.children:
                if child.dep_ == 'dobj':
                    obj = " ".join([t.text for t in child.subtree if not t.is_punct])
                    break
                if child.dep_ == 'prep':
                    for gc in child.children:
                        if gc.dep_ == 'pobj':
                            obj = " ".join([t.text for t in gc.subtree if not t.is_punct])
                            break
            verb = token.lemma_.lower()
            svos.append(((subj or '') or None, verb or None, (obj or '') or None))
    # deduplicate
    uniq = []
    seen = set()
    for s, v, o in svos:
        key = (s or '', v or '', o or '')
        if key not in seen and (s or v or o):
            seen.add(key)
            uniq.append((s, v, o))
    return uniq


def save_to_database(session, story_id: str, original_text: str, role: Optional[str], action: Optional[str], obj: Optional[str], nlp=None) -> int:
    try:
        user_story = UserStory(
            text=original_text,
            role=role if role else None,
            verb=action if action else None,
            object=obj if obj else None,
        )
        session.add(user_story)
        session.flush()
        usid = user_story.usid
        # Extract and persist SVO_raw
        if nlp is not None:
            doc = nlp(original_text)
            for s, v, o in extract_svos(doc):
                session.add(SvoRaw(usid=usid, subject=(s or None), verb=(v or None), object=(o or None)))
        return usid
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

