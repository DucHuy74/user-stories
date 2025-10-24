import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.usecases.analyze_story import AnalyzeStoriesUseCase
from src.adapters.phase_adapters import Phase1Adapter, Phase2Adapter, Phase3Adapter
from src.adapters.sqlalchemy_repository import SQLAlchemyRepository
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
        # Wire concrete adapters (IoC) here. We wrap existing implementations.
        # Import concrete phase implementations lazily to avoid circular imports during refactor.
        try:
            from analyzeUserStory.phase1 import Phase1 as Phase1Impl
            from analyzeUserStory.phase2 import Phase2 as Phase2Impl
            from analyzeUserStory.phase3 import Phase3 as Phase3Impl
        except Exception:
            Phase1Impl = Phase2Impl = Phase3Impl = None

        phase1_adapter = Phase1Adapter(Phase1Impl() if Phase1Impl else None)
        phase2_adapter = Phase2Adapter(Phase2Impl() if Phase2Impl else None)
        phase3_adapter = Phase3Adapter(Phase3Impl() if Phase3Impl else None)

        repository = SQLAlchemyRepository()

        usecase = AnalyzeStoriesUseCase(
            phase1=phase1_adapter,
            phase2=phase2_adapter,
            phase3=phase3_adapter,
            repository=repository,
            graph_adapter=graph,
        )

        result = usecase.execute(data.user_stories)
        p1 = result.get('phase1')
        p2 = result.get('phase2')
        p3 = result.get('phase3')

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
        for svo in p3.get("subject_verb_object", []):
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

