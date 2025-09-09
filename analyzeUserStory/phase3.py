import json
from typing import Dict, List, Any
from collections import defaultdict
import nltk
from nltk.corpus import wordnet as wn

class Phase3:
    def __init__(self):
        self.input_data = {}
        self.synonyms = defaultdict(list)
        self.similarities = []
        self.final_output = {}

        try:
            wn.synsets('test')
        except LookupError:
            nltk.download('wordnet')

    def process_wordnet(self, phase2_data: Dict) -> Dict:
        self.input_data = phase2_data
        self._generate_synonyms()
        self._calculate_similarity()
        self._create_final_output()
        return self.final_output
    
    def _get_concepts_from_phase2_output(self) -> List[str]:
        all_concepts = []
        for record in self.input_data.get("final_output", []):
            text_value = record.get("text")
            if text_value:
                all_concepts.append(text_value)
        return list(set(all_concepts))

    def _generate_synonyms(self):
        all_concepts = self._get_concepts_from_phase2_output()
        for concept in all_concepts:
            concept_synsets = wn.synsets(concept.lower().replace(" ", "_"), pos=wn.NOUN)
            
            if not concept_synsets:
                concept_synsets = wn.synsets(concept.lower().replace(" ", "_"), pos=wn.VERB)
            
            if concept_synsets:
                for synset in concept_synsets:
                    for lemma in synset.lemmas():
                        lemma_name = lemma.name().replace('_', ' ')
                        if lemma_name.lower() not in [s.lower() for s in self.synonyms[concept]] and lemma_name.lower() != concept.lower():
                            self.synonyms[concept].append(lemma_name)

    def _calculate_similarity(self):
        all_concepts = self._get_concepts_from_phase2_output()
        for i, concept1 in enumerate(all_concepts):
            for j, concept2 in enumerate(all_concepts):
                if i < j:
                    score = self._compute_similarity(concept1, concept2)
                    if score is not None and score > 0.5:
                        self.similarities.append({
                            "concept1": concept1,
                            "concept2": concept2,
                            "similarity": score,
                            "type": "Wu-Palmer"
                        })

    def _compute_similarity(self, concept1: str, concept2: str) -> float:
        synsets1 = wn.synsets(concept1.lower().replace(" ", "_"))
        synsets2 = wn.synsets(concept2.lower().replace(" ", "_"))
        if not synsets1 or not synsets2:
            return None
        max_score = 0.0
        for s1 in synsets1:
            for s2 in synsets2:
                similarity = s1.wup_similarity(s2)
                if similarity is not None and similarity > max_score:
                    max_score = similarity
        return max_score

    def _create_final_output(self):
        all_records = self.input_data.get("final_output", [])
        
        roles = list(set([r.get("text") for r in all_records if "role" in r.get("concept_and_domain", "") and r.get("text")]))
        objects = list(set([r.get("text") for r in all_records if "object" in r.get("concept_and_domain", "") and r.get("text")]))
        verbs = list(set([r.get("text") for r in all_records if r.get("concept_and_domain") == "feature" and r.get("text")]))
        
        svo_relationships = []
        story_map = defaultdict(lambda: {"subject": "", "verb": "", "object": "", "usid": ""})

        for record in all_records:
            usid = record.get("usid_text", "").split(":")[0].strip()
            
            if "role" in record.get("concept_and_domain", ""):
                story_map[usid]["subject"] = record.get("text", "")
                story_map[usid]["usid"] = usid
            elif "object" in record.get("concept_and_domain", ""):
                story_map[usid]["object"] = record.get("text", "")
                story_map[usid]["usid"] = usid
            elif record.get("concept_and_domain") == "feature":
                story_map[usid]["verb"] = record.get("text", "")
                story_map[usid]["usid"] = usid

        svo_relationships = [v for v in story_map.values() if v.get("subject") or v.get("verb") or v.get("object")]

        pairwise_relationships = []
        for sim in self.similarities:
            pairwise_relationships.append({
                "concept1": sim["concept1"],
                "concept2": sim["concept2"],
                "relationship_type": sim["type"],
                "strength": sim["similarity"]
            })
        
        self.final_output = {
            "user_roles": [r for r in roles if r],
            "objects": [o for o in objects if o],
            "verbs": [v for v in verbs if v],
            "subject_verb_object": svo_relationships,
            "pairwise_relationships": pairwise_relationships,
            "synonyms": dict(self.synonyms)
        }

    def export_json(self, filename: str = "phase3_wordnet.json") -> str:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.final_output, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            return ""

    def get_results(self):
        return self.final_output