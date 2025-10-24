from typing import List, Dict, Any
from src.domain.ports import Phase1Port, Phase2Port, Phase3Port


class Phase1Adapter(Phase1Port):
    def __init__(self, impl):
        # impl is the existing analyzeUserStory.phase1.Phase1 (or compatible)
        self.impl = impl

    def process_text(self, user_stories: List[str]) -> Dict[str, Any]:
        return self.impl.process_text(user_stories)


class Phase2Adapter(Phase2Port):
    def __init__(self, impl):
        self.impl = impl

    def analyze_concepts(self, phase1_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.impl.analyze_concepts(phase1_data)


class Phase3Adapter(Phase3Port):
    def __init__(self, impl):
        self.impl = impl

    def process_wordnet(self, phase2_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.impl.process_wordnet(phase2_data)
