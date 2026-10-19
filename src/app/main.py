from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from src.app.db import (
    complete_work_item,
    create_work_item,
    database_health,
    delete_work_item,
    list_work_items,
)
from src.app.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.2.0")


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    assigned_role: str = Field(
        default="backend_api_engineer", min_length=1, max_length=100
    )


class WorkItemOut(BaseModel):
    id: int
    title: str
    description: str
    status: Literal["open", "done"]
    assigned_role: str
    created_at: str | None = None
    completed_at: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@app.get("/db/health")
def db_health() -> dict:
    try:
        return database_health()
    except Exception as exc:  # endpoint should report failure without crashing app
        raise HTTPException(
            status_code=503, detail=f"database unavailable: {exc}"
        ) from exc


@app.post(
    "/work-items",
    response_model=WorkItemOut,
    status_code=status.HTTP_201_CREATED,
)
def api_create_work_item(payload: WorkItemCreate) -> WorkItemOut:
    try:
        row = create_work_item(
            title=payload.title,
            description=payload.description,
            assigned_role=payload.assigned_role,
        )
        return WorkItemOut.model_validate(row)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"database unavailable: {exc}"
        ) from exc


@app.get("/work-items", response_model=list[WorkItemOut])
def api_list_work_items(
    item_status: Literal["open", "done"] | None = Query(
        default=None, alias="status"
    ),
) -> list[WorkItemOut]:
    try:
        rows = list_work_items(status=item_status)
        return [WorkItemOut.model_validate(r) for r in rows]
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"database unavailable: {exc}"
        ) from exc


@app.patch("/work-items/{item_id}/complete", response_model=WorkItemOut)
def api_complete_work_item(item_id: int) -> WorkItemOut:
    try:
        row = complete_work_item(item_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"database unavailable: {exc}"
        ) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="work item not found")
    return WorkItemOut.model_validate(row)


@app.delete(
    "/work-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
def api_delete_work_item(item_id: int) -> Response:
    try:
        deleted = delete_work_item(item_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"database unavailable: {exc}"
        ) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="work item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
