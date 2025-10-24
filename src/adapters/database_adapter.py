"""Database adapter shim inside src.adapters.
This module re-exports the existing top-level database helpers so other
src modules can import from `src.adapters.database_adapter` while we
gradually migrate implementations.
"""
try:
    from database import get_database_manager, DatabaseSession, DatabaseManager, init_database
except Exception:
    # Provide fallback stubs if top-level database is not available during tests
    get_database_manager = None
    DatabaseSession = None
    DatabaseManager = None
    def init_database(*args, **kwargs):
        return None

__all__ = ["get_database_manager", "DatabaseSession", "DatabaseManager", "init_database"]
