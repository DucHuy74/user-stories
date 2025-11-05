import uuid

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from constant import PASSWORD_GRAPH_DB, URL_CONNECTION_GRAPH_DB, USER_GRAPH_DB
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import io
import csv
import uuid as _uuid

from database import DatabaseSession, get_database_manager
from models import UserStory, Concept

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


def _usid_to_uuid(usid: int) -> str:
    """Deterministically map integer usid to a UUID v5 for stable CSV IDs without DB schema changes."""
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"userstory:{usid}"))


@router.get("/export/phase2-index.csv")
async def export_phase2_index_csv():
    """Export CSV: indices, USID(UUID), role, object, domain, flag (adapted to new Concept fields).

    - indices: running number starting at 1
    - USID: UUID (derived deterministically from integer indices)
    - role: Concept.text_userrole
    - object: Concept.text_object_as_concept_domain
    - domain: empty (removed in new model)
    - flag: 0 for feature (feature_flag=1), 1 for value (value_flag=1)
    """
    try:
        dbm = get_database_manager()
        with DatabaseSession(dbm) as session:
            concepts = (
                session.query(Concept)
                .order_by(Concept.indices.asc(), Concept.concept_id.asc())
                .all()
            )

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["indices", "USID", "role", "object", "domain", "flag"])  # header

            idx = 1
            for c in concepts:
                usid_uuid = _usid_to_uuid(c.indices)
                role = c.text_userrole or ""
                obj = c.text_object_as_concept_domain or ""
                domain = ""
                # Map binary flags to single flag column for compatibility
                flag = 0 if int(c.feature_flag or 0) == 1 else 1
                if obj:  # only emit rows with an object term
                    writer.writerow([idx, usid_uuid, role, obj, domain, flag])
                    idx += 1

            buf.seek(0)
            return StreamingResponse(
                iter([buf.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=phase2-index.csv"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

