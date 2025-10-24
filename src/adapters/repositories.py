"""Repository / adapter layer helpers.
This file provides small wrapper functions that delegate to the existing top-level
`database.py` and `graphdb.py` implementations. The goal is to centralize access
and provide a stable import path for usecases.
"""
from typing import Any

# Import existing implementations (keeps backward compatibility while we migrate)
try:
    from database import get_database_manager, DatabaseSession
except Exception:
    # Fall back to local null implementations if imports fail during incremental refactor
    def get_database_manager() -> Any:
        return None

    class DatabaseSession:
        def __init__(self, db_manager):
            pass
        def __enter__(self):
            return None
        def __exit__(self, exc_type, exc, tb):
            return False

try:
    from graphdb import GraphDB
except Exception:
    class GraphDB:
        def __init__(self, *args, **kwargs):
            pass
        def create_node(self, *a, **k):
            return None
        def create_relationship(self, *a, **k):
            return None


def get_db_manager():
    """Return the existing database manager (wrapper)."""
    return get_database_manager()


def get_graph_adapter(uri=None, user=None, password=None):
    """Return a GraphDB adapter instance (wrapper)."""
    try:
        return GraphDB(uri=uri, user=user, password=password)
    except Exception:
        return GraphDB()
