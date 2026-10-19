# Artifact: SESSION-02-ARCH-001 (Software Architect / sa-agent)

- **Role ID:** `software_architect`
- **Status:** `completed`
- **Accountable Human:** `minh`
- **Human Approval Required:** `True`

## Summary
Designed the persistent work item feature using PostgreSQL, utilizing psycopg v3 for database interactions, defining table models, repository interfaces, and FastAPI routing contracts.

## Decisions & Contracts
- Use psycopg v3 for synchronous PostgreSQL operations consistent with existing db.py setup.
- Define a `work_items` table with columns: id (UUID PK), title (VARCHAR), description (TEXT), status (VARCHAR), created_at, updated_at.
- Create a dedicated domain model and Pydantic schemas for request/response validation.
- Implement a work item service/repository layer to decouple database operations from FastAPI route handlers.

## Proposed File Changes
### `src/app/models/work_item.py` (create)
Define Pydantic schemas for WorkItem creation, update, and response representation.
```
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class WorkItemCreate(BaseModel):
    title: str = Field(..., min_after_init=1, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="pending")

class WorkItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None

class WorkItemResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

```
### `src/app/services/work_item_service.py` (create)
Implement data access and business logic for persistent work items using psycopg.
```
from typing import List, Optional
from uuid import UUID, uuid4
import psycopg

from src.app.settings import get_settings
from src.app.models.work_item import WorkItemCreate, WorkItemUpdate, WorkItemResponse

def get_connection():
    settings = get_settings()
    return psycopg.connect(settings.database_url)

class WorkItemService:
    @staticmethod
    def create_table() -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS work_items (
                        id UUID PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        description TEXT,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()

    @staticmethod
    def create(item: WorkItemCreate) -> WorkItemResponse:
        item_id = uuid4()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO work_items (id, title, description, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING id, title, description, status, created_at, updated_at
                    """,
                    (item_id, item.title, item.description, item.status)
                ----)
                row = cur.fetchone()
                conn.commit()
        return WorkItemResponse(
            id=row[0], title=row[1], description=row[2], status=row[3], created_at=row[4], updated_at=row[5]
        )

    @staticmethod
    def list_all() -> List[WorkItemResponse]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title, description, status, created_at, updated_at FROM work_items")
                rows = cur.fetchall()
        return [
            WorkItemResponse(id=r[0], title=r[1], description=r[2], status=r[3], created_at=r[4], updated_at=r[5])
            for r in rows
        ]

```
### `src/app/api/work_items.py` (create)
Add FastAPI router endpoints for creating and listing persistent work items.
```
from typing import List
from fastapi import APIRouter, HTTPException

from src.app.models.work_item import WorkItemCreate, WorkItemResponse
from src.app.services.work_item_service import WorkItemService

router = APIRouter(prefix="/work-items", tags=["work-items"])

@router.on_event("startup")
def startup_event():
    try:
        WorkItemService.create_table()
    except Exception:
        pass  # allow application to start even if db is temporarily offline

@router.post("/", response_model=WorkItemResponse, status_code=201)
def create_work_item(item: WorkItemCreate):
    try:
        return WorkItemService.create(item)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/", response_model=List[WorkItemResponse])
def list_work_items():
    try:
        return WorkItemService.list_all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

```
