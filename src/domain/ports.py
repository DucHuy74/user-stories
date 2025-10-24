from typing import Protocol, List, Dict, Any, Optional


class Phase1Port(Protocol):
    def process_text(self, user_stories: List[str]) -> Dict[str, Any]:
        ...


class Phase2Port(Protocol):
    def analyze_concepts(self, phase1_data: Dict[str, Any]) -> Dict[str, Any]:
        ...


class Phase3Port(Protocol):
    def process_wordnet(self, phase2_data: Dict[str, Any]) -> Dict[str, Any]:
        ...


class RepositoryPort(Protocol):
    def create_processing_session(self, session_name: str, total_stories: int) -> Any:
        ...

    def save_user_story(self, *args, **kwargs) -> Any:
        ...

    def update_processing_session(self, session_id: str, phase_completed: int, status: str) -> None:
        ...


class GraphAdapterPort(Protocol):
    def create_node(self, label: str, properties: Dict[str, Any], key: Optional[str] = None) -> Any:
        ...

    def create_relationship(self, *args, **kwargs) -> Any:
        ...
