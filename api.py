from fastapi import FastAPI
from routes.analyze import router


app = FastAPI()

app.include_router(router, prefix="/api")

@app.get("/")
def root():
    return {"msg": "hello api running"}



# @app.get("/stories")
# def get_stories():
#     return graph.list_nodes("UserStory")


# @app.post("/stories")
# def add_story(story: StoryInput):
#     story_id = str(uuid.uuid4())  # UUID luôn unique
#     graph.create_node("UserStory", {"id": story_id, "text": story.text}, key="id")
#     return {"id": story_id, "text": story.text}


# @app.put("/stories/{story_id}")
# def update_story(story_id: str, story: StoryInput):
#     updated = graph.update_node("UserStory", "id", story_id, {"text": story.text})
#     if not updated:
#         raise HTTPException(status_code=404, detail="Story not found")
#     return updated


# @app.delete("/stories/{story_id}")
# def delete_story(story_id: str):
#     deleted = graph.delete_node("UserStory", "id", story_id)
#     if deleted == 0:
#         raise HTTPException(status_code=404, detail="Story not found")
#     return {"message": "Story deleted", "id": story_id}

# @app.get("/analyze/{story_id}")
# def analyze_story_by_id(story_id: str):
#     try:
#         story = graph.get_node("UserStory", "id", story_id)
#         if not story:
#             raise HTTPException(status_code=404, detail="Story not found")

#         story_text = story["text"]
#         if isinstance(story_text, list):
#             user_stories = story_text
#         else:
#             user_stories = [story_text]


#         # Phase1
#         phase1 = Phase1()
#         p1 = phase1.process_text(user_stories)

#         # Phase2
#         phase2 = Phase2()
#         p2 = phase2.analyze_concepts(p1)

#         # Phase3
#         phase3 = Phase3()
#         p3 = phase3.process_wordnet(p2)

#         return {"id": story_id, "phase1": p1, "phase2": p2, "phase3": p3}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))