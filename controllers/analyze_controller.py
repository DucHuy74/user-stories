import uuid
from typing import Dict, Any

from analyzeUserStory.phase1 import Phase1
from analyzeUserStory.phase2 import Phase2
from analyzeUserStory.phase3 import Phase3
from analyzeUserStory.phase4 import Phase4


def analyze_stories_controller(data, graph) -> Dict[str, Any]:
    """Controller function that orchestrates Phase1 -> Phase2 -> Phase3 -> Phase4.

    Args:
        data: request payload (expects attribute `user_stories` - list of texts)
        graph: GraphDB instance used for persisting results

    Returns:
        dict containing outputs from phase1, phase2 and phase3
    """
    phase1 = Phase1()
    p1 = phase1.process_text(data.user_stories)

    phase2 = Phase2()
    p2 = phase2.analyze_concepts(p1)

    phase3 = Phase3()
    p3 = phase3.process_wordnet(p2)

    # Persist to graph via Phase4
    phase4 = Phase4()
    phase4.persist_graph(p1, p3, graph)

    return {"phase1": p1, "phase2": p2, "phase3": p3}
