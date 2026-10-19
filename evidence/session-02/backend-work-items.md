# Artifact: SESSION-02-DEV-001 (Backend / API Engineer / bae-agent)

- **Role ID:** `backend_api_engineer`
- **Status:** `completed`
- **Accountable Human:** `mirko`
- **Human Approval Required:** `True`

## Summary
Implemented work items Pydantic schemas, database table migration/initialization, and FastAPI CRUD endpoints (create, list, delete/complete) backed by PostgreSQL using psycopg.

## Decisions & Contracts
- Created src/app/models/work_item.py for Pydantic request/response models.
- Created src/app/services/work_item_service.py to handle SQL persistence using psycopg.
- Created src/app/routers/work_items.py for the FastAPI router endpoints (/work-items).
- Updated src/app/main.py to include the work_items router and initialize the work_items table on startup.

## Proposed File Changes
### `src/app/models/work_item.py` (create)
Define Pydantic schemas for WorkItem creation and response.
```
from datetime import datetime
from pydantic import BaseModel, Field

class WorkItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class WorkItemResponse(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime

```
### `src/app/services/work_item_service.py` (create)
Implement database operations for work items using psycopg.
```
from typing import List
import psycopg
from src.app.models.work_item import WorkItemCreate, WorkItemResponse
from src.app.settings import get_settings

def init_work_items_table() -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

def create_work_item(item: WorkItemCreate) -> WorkItemResponse:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO work_items (title, description) VALUES (%s, %s) RETURNING id, title, description, completed, created_at",
                (item.title, item.description),
            )
            row = cur.fetchone()
            conn.commit()
            return WorkItemResponse(
                id=row[0],
                title=row[1],
                description=row[2],
                completed=row[3],
                created_at=row[4],
            )

def list_work_items() -> List[WorkItemResponse]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, description, completed, created_at FROM work_items ORDER BY id DESC")
            rows = cur.fetchall()
            return [
                WorkItemResponse(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    completed=row[3],
                    created_at=row[4],
                )
                for row in rows
            ]

def delete_work_item(item_id: int) -> bool:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM work_items WHERE id = %s RETURNING id", (item_id,))
            row = cur.fetchone()
            conn.commit()
            return row is not None

```
### `src/app/routers/work_items.py` (create)
Implement FastAPI router for work items endpoints.
```
from fastapi import APIRouter, HTTPException, status
from typing import List
from src.app.models.work_item import WorkItemCreate, WorkItemResponse
from src.app.services.work_item_service import (
    create_work_item,
    list_work_items,
    delete_work_item,
)

router = APIRouter(prefix="/work-items", tags=["work-items"])

@router.post("/", response_model=WorkItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: WorkItemCreate) -> WorkItemResponse:
    try:
        return create_work_item(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/", response_model=List[WorkItemResponse])
def get_items() -> List[WorkItemResponse]:
    try:
        return list_work_items()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int) -> None:
    try:
        success = delete_work_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail="Work item not found")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

```
### `src/app/main.py` (modify)
Register work items router and initialize database table on startup.
```
from fastapi import FastAPI, HTTPException

from src.app.db import database_health
from src.app.settings import get_settings
from src.app.routers.work_items import router as work_items_router
from src.app.services.work_item_service import init_work_items_table

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

@app.on_event("startup")
def startup_event() -> None:
    try:
        init_work_items_table()
    except Exception:
        # Allow app to start even if DB is temporarily unavailable
        pass

app.include_router(work_items_router)

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
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc

```
