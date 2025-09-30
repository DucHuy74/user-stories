import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from analyzeUserStory.phase1 import Phase1
from analyzeUserStory.phase2 import Phase2
from analyzeUserStory.phase3 import Phase3
from typing import List
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

        # ---- Lưu vào Neo4j ----
        for us in p1["concepts"]:
            story_uuid = str(uuid.uuid4())
            story_text = us["original_text"]
            graph.create_node(
                "UserStory",
                {"id": story_uuid, "phase1_id": us["id"], "text": story_text},
                key="id"
            )

        # 2. Lưu Role - Action - Object
        for svo in p3["subject_verb_object"]:
            subj = svo.get("subject")
            verb = svo.get("verb")
            obj = svo.get("object")

            if subj and obj and verb:
                graph.create_node("Role", {"name": subj}, key="name")
                
                graph.create_node("Object", {"name": obj}, key="name")
                
                graph.create_relationship(
                    start_label="Role", start_key="name", start_val=subj,
                    rel_type="ACTION",
                    end_label="Object", end_key="name", end_val=obj,
                    props={"verb": verb}
                )


        return {"phase1": p1, "phase2": p2, "phase3": p3}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

