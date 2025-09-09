import json
import spacy
from typing import List, Dict, Tuple, Optional

class Phase1:
    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
            print(f"Loaded spaCy model: {model_name}")
        except OSError:
            print(f"Downloading spaCy model '{model_name}'...")
            from spacy.cli import download
            download(model_name)
            self.nlp = spacy.load(model_name)

        self.user_stories = []
        self.extracted_concepts = {}

    def process_text(self, user_stories: List[str]) -> Dict:
        self.user_stories = user_stories
        results = []

        for i, story in enumerate(self.user_stories):
            if not story.strip():
                continue

            role, action, obj = self._extract_components(story)
            
            role = role.lower().strip() if role else ""
            action = action.lower().strip() if action else ""
            obj = obj.lower().strip() if obj else ""

            concept = {
                "id": f"US_{i+1:03d}",
                "original_text": story.strip(),
                "role": role,
                "action": action,
                "object": obj,
            }
            results.append(concept)

        roles = sorted(list(set([c["role"] for c in results if c["role"]])))
        actions = sorted(list(set([c["action"] for c in results if c["action"]])))
        objects = sorted(list(set([c["object"] for c in results if c["object"]])))

        self.extracted_concepts = {
            "concepts": results,
            "roles": roles,
            "actions": actions,
            "objects": objects,
        }
        return self.extracted_concepts

    def _extract_components(self, story: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Sử dụng spaCy để trích xuất role, action, và object."""
        story_core = story.split("so that", 1)[0]
        doc = self.nlp(story_core.strip())
        role = self._find_role(doc)
        action, obj = self._find_action_and_object(doc)
        return role, action, obj

    def _find_role(self, doc) -> Optional[str]:
        for i, token in enumerate(doc):
            if token.lower_ == "as" and i + 1 < len(doc) and doc[i+1].lower_ in ("a", "an"):
                role_tokens = []
                for j in range(i + 2, len(doc)):
                    if doc[j].pos_ in ("PUNCT", "VERB", "CCONJ"):
                        break
                    role_tokens.append(doc[j].text)
                return " ".join(role_tokens) if role_tokens else None

        for token in doc:
            if token.dep_ in ("nsubj", "nsubjpass") and token.head.dep_ == "ROOT":
                return " ".join([t.text for t in token.subtree if not t.is_punct])

        return None

    def _find_action_and_object(self, doc) -> Tuple[Optional[str], Optional[str]]:
        
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
                    if obj: break
        if not action and not obj:
            first_token = doc[0]
            if first_token.pos_ in ("NOUN", "DET", "PROPN"):
                obj = " ".join([t.text for t in doc if not t.is_punct])

        return action, obj

    def export_json(self, filename: str = "phase1_raw.json") -> str:
        """Xuất kết quả đã trích xuất ra file JSON."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_concepts, f, indent=2, ensure_ascii=False)
            print(f"Exported to {filename}")
            return filename
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return ""