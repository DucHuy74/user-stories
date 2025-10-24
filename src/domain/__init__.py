# Domain layer: entities and business models
# This package will host pure domain models (data classes / DTOs) used across the app.

from typing import TypedDict, Optional

class UserStoryDTO(TypedDict):
    id: str
    original_text: str
    role: Optional[str]
    action: Optional[str]
    object: Optional[str]


__all__ = ["UserStoryDTO"]
