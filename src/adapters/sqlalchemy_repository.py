from typing import Any, Optional
from src.domain.ports import RepositoryPort

try:
    from src.adapters.database_adapter import get_database_manager, DatabaseSession
    # Try to import domain models from src first, fall back to top-level models
    try:
        from src.domain.models import UserStory, Concept, ProcessingSession
    except Exception:
        from models import UserStory, Concept, ProcessingSession
except Exception:
    # If imports fail during early migration, provide placeholders (will raise at runtime on use)
    get_database_manager = None
    DatabaseSession = None
    UserStory = None
    Concept = None
    ProcessingSession = None


class SQLAlchemyRepository(RepositoryPort):
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or (get_database_manager() if get_database_manager else None)

    def create_processing_session(self, session_name: str, total_stories: int) -> Any:
        with DatabaseSession(self.db_manager) as session:
            processing_session = ProcessingSession(
                session_name=session_name,
                total_stories=total_stories,
                phase_completed=0,
                status="started",
            )
            session.add(processing_session)
            session.flush()
            return processing_session

    def save_user_story(self, *args, **kwargs) -> Any:
        # wrapper for existing save logic used by phase helpers
        with DatabaseSession(self.db_manager) as session:
            user_story = UserStory(story_id=kwargs.get('story_id'), original_text=kwargs.get('original_text'))
            session.add(user_story)
            session.flush()
            concept = Concept(user_story_id=user_story.id, role=kwargs.get('role'), action=kwargs.get('action'), object=kwargs.get('object'))
            session.add(concept)
            return user_story.id

    def update_processing_session(self, session_id: str, phase_completed: int, status: str) -> None:
        with DatabaseSession(self.db_manager) as session:
            ps = session.query(ProcessingSession).filter_by(id=session_id).first()
            if ps:
                ps.phase_completed = phase_completed
                ps.status = status
                if status == 'completed':
                    from datetime import datetime
                    ps.completed_at = datetime.utcnow()
                session.add(ps)
