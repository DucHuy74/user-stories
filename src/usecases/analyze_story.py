"""High-level usecase that orchestrates Phase1 -> Phase2 -> Phase3.
This is intentionally lightweight: it expects adapters (DB, graph) and phase
implementations to be provided. During migration we'll import the existing
phase packages and pass through.
"""
from typing import List, Dict, Any, Optional
from src.domain.ports import (
    Phase1Port,
    Phase2Port,
    Phase3Port,
    RepositoryPort,
    GraphAdapterPort,
)


class AnalyzeStoriesUseCase:
    """Usecase that orchestrates the three phases.

    This class depends only on abstract ports (interfaces). Concrete adapters
    should be provided by the application wiring (IoC).
    """
    def __init__(
        self,
        phase1: Phase1Port,
        phase2: Phase2Port,
        phase3: Phase3Port,
        repository: RepositoryPort,
        graph_adapter: GraphAdapterPort,
    ):
        self.phase1 = phase1
        self.phase2 = phase2
        self.phase3 = phase3
        self.repository = repository
        self.graph_adapter = graph_adapter

    def execute(self, user_stories: List[str]) -> Dict[str, Any]:
        # Delegate to phase ports — usecase does not import concrete implementations
        r1 = self.phase1.process_text(user_stories)
        r2 = self.phase2.analyze_concepts(r1)
        r3 = self.phase3.process_wordnet(r2)

        return {"phase1": r1, "phase2": r2, "phase3": r3}
