"""High-level usecase that orchestrates Phase1 -> Phase2 -> Phase3.
This is intentionally lightweight: it expects adapters (DB, graph) and phase
implementations to be provided. During migration we'll import the existing
phase packages and pass through.
"""
from typing import List, Dict, Any, Optional
from src.adapters.repositories import get_db_manager

# During migration these imports map to the existing phase packages
try:
    from analyzeUserStory.phase1 import Phase1
    from analyzeUserStory.phase2 import Phase2
    from analyzeUserStory.phase3 import Phase3
except Exception:
    Phase1 = None
    Phase2 = None
    Phase3 = None


class AnalyzeStoriesUseCase:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or get_db_manager()

    def execute(self, user_stories: List[str]) -> Dict[str, Any]:
        if not Phase1 or not Phase2 or not Phase3:
            raise RuntimeError("Phase implementations are not available during migration")

        p1 = Phase1()
        r1 = p1.process_text(user_stories)

        p2 = Phase2()
        r2 = p2.analyze_concepts(r1)

        p3 = Phase3()
        r3 = p3.process_wordnet(r2)

        return {"phase1": r1, "phase2": r2, "phase3": r3}
