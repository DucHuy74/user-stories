from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from phase1 import Phase1
from phase2 import Phase2
from phase3 import Phase3
from graphdb import GraphDB
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

graph = GraphDB(uri="bolt://localhost:7687", user="neo4j", password="12345678")


# ---- Models ----
class StoryInput(BaseModel):
    text: List[str]

class StoriesInput(BaseModel):
    user_stories: List[str]


@app.get("/")
def root():
    return {"msg": "hello api running"}


@app.get("/stories")
def get_stories():
    return graph.list_nodes("UserStory")


@app.post("/stories")
def add_story(story: StoryInput):
    story_id = str(uuid.uuid4())  # UUID luôn unique
    graph.create_node("UserStory", {"id": story_id, "text": story.text}, key="id")
    return {"id": story_id, "text": story.text}


@app.put("/stories/{story_id}")
def update_story(story_id: str, story: StoryInput):
    updated = graph.update_node("UserStory", "id", story_id, {"text": story.text})
    if not updated:
        raise HTTPException(status_code=404, detail="Story not found")
    return updated


@app.delete("/stories/{story_id}")
def delete_story(story_id: str):
    deleted = graph.delete_node("UserStory", "id", story_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted", "id": story_id}


@app.post("/analyze")
async def analyze_stories(data: StoriesInput):
    try:
        logger.info("Start analysis")

        phase1 = Phase1()
        p1 = phase1.process_text(data.user_stories)
        logger.info(f"Phase1 done: {len(p1['concepts'])} concepts")

        phase2 = Phase2()
        p2 = phase2.analyze_concepts(p1)
        logger.info(f"Phase2 done: {len(p2['final_output'])} records")

        phase3 = Phase3()
        p3 = phase3.process_wordnet(p2)
        logger.info(f"Phase3 done: {len(p3['subject_verb_object'])} SVO relations")

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

        logger.info("Saved UserStory, Role, Object and relationships to Neo4j")

        return {"phase1": p1, "phase2": p2, "phase3": p3}

    except Exception as e:
        logger.error(f" Error in /analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{story_id}")
def analyze_story_by_id(story_id: str):
    try:
        story = graph.get_node("UserStory", "id", story_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        story_text = story["text"]
        if isinstance(story_text, list):
            user_stories = story_text
        else:
            user_stories = [story_text]

        logger.info(f"Start analysis for story {story_id}")

        # Phase1
        phase1 = Phase1()
        p1 = phase1.process_text(user_stories)
        logger.info(f"Phase1 done: {len(p1['concepts'])} concepts")

        # Phase2
        phase2 = Phase2()
        p2 = phase2.analyze_concepts(p1)
        logger.info(f"Phase2 done: {len(p2['final_output'])} records")

        # Phase3
        phase3 = Phase3()
        p3 = phase3.process_wordnet(p2)
        logger.info(f"Phase3 done: {len(p3['subject_verb_object'])} SVO relations")

        return {"id": story_id, "phase1": p1, "phase2": p2, "phase3": p3}

    except Exception as e:
        logger.error(f"Error in /analyze/{story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))