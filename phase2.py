import json
from typing import Dict, List, Any
from collections import Counter

class Phase2:
    def __init__(self):
        self.input_data = {}
        self.object_frequency = {}
        self.final_output = []

    def analyze_concepts(self, phase1_data: Dict) -> Dict:
        self.input_data = phase1_data
        self._calculate_object_frequency()
        self._generate_final_output()

        results = {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output
        }
        return results

    def _calculate_object_frequency(self):
        all_concepts = []
        for concept_item in self.input_data.get("concepts", []):
            if concept_item.get("role"):
                role = concept_item["role"].split(' ', 1)[-1] if concept_item["role"].split(' ', 1)[0] in ('a', 'an', 'the') else concept_item["role"]
                all_concepts.append(role)
            if concept_item.get("object"):
                obj = concept_item["object"].split(' ', 1)[-1] if concept_item["object"].split(' ', 1)[0] in ('a', 'an', 'the') else concept_item["object"]
                all_concepts.append(obj)
        self.object_frequency = dict(Counter(all_concepts))
        print(f"📊 Tần suất khái niệm: {self.object_frequency}")

    def _generate_final_output(self):
        
        for concept_item in self.input_data.get("concepts", []):
            usid = concept_item.get("id")
            original_text = concept_item.get("original_text")
            role = concept_item.get("role")
            action = concept_item.get("action")
            obj = concept_item.get("object")

            if action:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": action,
                    "concept_and_domain": "feature",
                    "0 - feature flag": 0,
                    "1 - value flag": None
                })
            
            if role:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": role,
                    "concept_and_domain": "role (general)",
                    "0 - feature flag": None,
                    "1 - value flag": 1
                })
            
            if obj:
                self.final_output.append({
                    "usid_text": f"{usid}: {original_text}",
                    "text": obj,
                    "concept_and_domain": "object (general)",
                    "0 - feature flag": None,
                    "1 - value flag": 1
                })

        for i, record in enumerate(self.final_output):
            record["indices"] = i + 1


    def export_json(self, filename: str = "phase2_output.json") -> str:
        results = {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            return filename
        except Exception as e:
            return ""

    def get_results(self):
        return {
            "object_frequency": self.object_frequency,
            "final_output": self.final_output
        }