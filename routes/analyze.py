import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from analyzeUserStory.phase1 import Phase1
from analyzeUserStory.phase2 import Phase2
from analyzeUserStory.phase3 import Phase3
from analyzeUserStory.phase4 import Phase4
from constant import PASSWORD_GRAPH_DB, URL_CONNECTION_GRAPH_DB, USER_GRAPH_DB
from fastapi import HTTPException

from graphdb import GraphDB

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
        phase1 = Phase1()
        p1 = phase1.process_text(data.user_stories)

        phase2 = Phase2()
        p2 = phase2.analyze_concepts(p1)

        phase3 = Phase3()
        p3 = phase3.process_wordnet(p2)

        # Persist phase outputs into Neo4j (moved to Phase4)
        phase4 = Phase4()
        phase4.persist_graph(p1, p3, graph)


        return {"phase1": p1, "phase2": p2, "phase3": p3}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

