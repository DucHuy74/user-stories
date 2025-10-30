import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from constant import PASSWORD_GRAPH_DB, URL_CONNECTION_GRAPH_DB, USER_GRAPH_DB
from fastapi import HTTPException

from graphdb import GraphDB
from controllers.analyze_controller import analyze_stories_controller

router = APIRouter()
# ---- Models ----
class StoryInput(BaseModel):
    text: List[str]

class StoriesInput(BaseModel):
    user_stories: List[str]

graph = GraphDB(uri=URL_CONNECTION_GRAPH_DB , user=USER_GRAPH_DB, password=PASSWORD_GRAPH_DB)

@router.post("/analyze")
async def analyze_stories(data: StoriesInput):
    try:
        result = analyze_stories_controller(data, graph)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

