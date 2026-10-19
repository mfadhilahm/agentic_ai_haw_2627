from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from src.app.settings import get_settings

WORK_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS work_items (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'done')),
    assigned_role TEXT NOT NULL DEFAULT 'backend_api_engineer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
"""


def database_health() -> dict[str, Any]:
    """Return a small database/pgvector health report.

    A connection is opened only when this function is called, so the FastAPI
    service can start even when PostgreSQL is temporarily unavailable.
    """
    settings = get_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            postgres_version = cur.fetchone()[0]
            cur.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
            row = cur.fetchone()

    return {
        "database": "ok",
        "postgres": postgres_version,
        "pgvector": row[0] if row else None,
    }


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("created_at", "completed_at"):
        val = out.get(key)
        if isinstance(val, datetime):
            out[key] = val.isoformat()
    return out


def init_work_items_schema() -> None:
    """Ensure the persistent work_items table exists in PostgreSQL."""
    settings = get_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_ITEMS_DDL)
        conn.commit()


def create_work_item(
    title: str,
    description: str = "",
    assigned_role: str = "backend_api_engineer",
) -> dict[str, Any]:
    """Insert a new work item into PostgreSQL and return the persisted row."""
    settings = get_settings()
    with psycopg.connect(
        settings.database_url, connect_timeout=3, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_ITEMS_DDL)
            cur.execute(
                """
                INSERT INTO work_items (title, description, status, assigned_role)
                VALUES (%s, %s, 'open', %s)
                RETURNING id, title, description, status, assigned_role, created_at, completed_at
                """,
                (title, description, assigned_role),
            )
            row = cur.fetchone()
        conn.commit()
    assert row is not None
    return _normalize_row(row)


def list_work_items(status: str | None = None) -> list[dict[str, Any]]:
    """List work items from PostgreSQL ordered by id."""
    settings = get_settings()
    with psycopg.connect(
        settings.database_url, connect_timeout=3, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_ITEMS_DDL)
            if status:
                cur.execute(
                    """
                    SELECT id, title, description, status, assigned_role, created_at, completed_at
                    FROM work_items
                    WHERE status = %s
                    ORDER BY id ASC
                    """,
                    (status,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, title, description, status, assigned_role, created_at, completed_at
                    FROM work_items
                    ORDER BY id ASC
                    """
                )
            rows = cur.fetchall()
        conn.commit()
    return [_normalize_row(r) for r in rows]


def complete_work_item(item_id: int) -> dict[str, Any] | None:
    """Mark a work item as done in PostgreSQL."""
    settings = get_settings()
    with psycopg.connect(
        settings.database_url, connect_timeout=3, row_factory=dict_row
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_ITEMS_DDL)
            cur.execute(
                """
                UPDATE work_items
                SET status = 'done', completed_at = NOW()
                WHERE id = %s
                RETURNING id, title, description, status, assigned_role, created_at, completed_at
                """,
                (item_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return _normalize_row(row) if row else None


def delete_work_item(item_id: int) -> bool:
    """Delete a work item from PostgreSQL."""
    settings = get_settings()
    with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(WORK_ITEMS_DDL)
            cur.execute("DELETE FROM work_items WHERE id = %s", (item_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted
