from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from src.app import db as app_db
from src.app.main import app
from src.app.settings import get_settings


def _postgres_reachable() -> bool:
    try:
        app_db.init_work_items_schema()
        return True
    except Exception:
        return False


@pytest.fixture()
def work_items_backend(monkeypatch: pytest.MonkeyPatch):
    """Use real PostgreSQL when reachable (e.g. CI or local Docker), otherwise an in-memory DB adapter for offline unit runs."""
    if _postgres_reachable():
        yield "postgres"
        return

    store: dict[int, dict[str, Any]] = {}
    seq = {"id": 0}

    def fake_create(
        title: str,
        description: str = "",
        assigned_role: str = "backend_api_engineer",
    ) -> dict[str, Any]:
        seq["id"] += 1
        item = {
            "id": seq["id"],
            "title": title,
            "description": description,
            "status": "open",
            "assigned_role": assigned_role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        store[item["id"]] = item
        return dict(item)

    def fake_list(status: str | None = None) -> list[dict[str, Any]]:
        items = [dict(v) for v in store.values()]
        if status:
            items = [i for i in items if i["status"] == status]
        return sorted(items, key=lambda x: x["id"])

    def fake_complete(item_id: int) -> dict[str, Any] | None:
        if item_id not in store:
            return None
        store[item_id]["status"] = "done"
        store[item_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        return dict(store[item_id])

    def fake_delete(item_id: int) -> bool:
        return store.pop(item_id, None) is not None

    monkeypatch.setattr("src.app.main.create_work_item", fake_create)
    monkeypatch.setattr("src.app.main.list_work_items", fake_list)
    monkeypatch.setattr("src.app.main.complete_work_item", fake_complete)
    monkeypatch.setattr("src.app.main.delete_work_item", fake_delete)
    yield "memory"


def test_work_items_crud_lifecycle(work_items_backend: str) -> None:
    client = TestClient(app)

    create_resp = client.post(
        "/work-items",
        json={
            "title": "Implement persistent work items",
            "description": "Dry run task for Session 2",
            "assigned_role": "backend_api_engineer",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    item_id = created["id"]
    assert created["title"] == "Implement persistent work items"
    assert created["status"] == "open"
    assert created["assigned_role"] == "backend_api_engineer"

    list_resp = client.get("/work-items")
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(i["id"] == item_id for i in items)

    complete_resp = client.patch(f"/work-items/{item_id}/complete")
    assert complete_resp.status_code == 200
    completed = complete_resp.json()
    assert completed["id"] == item_id
    assert completed["status"] == "done"
    assert completed["completed_at"] is not None

    done_resp = client.get("/work-items", params={"status": "done"})
    assert done_resp.status_code == 200
    assert any(i["id"] == item_id for i in done_resp.json())

    delete_resp = client.delete(f"/work-items/{item_id}")
    assert delete_resp.status_code == 204

    missing_resp = client.patch(f"/work-items/{item_id}/complete")
    assert missing_resp.status_code == 404


def test_work_items_validation_rejects_empty_title() -> None:
    client = TestClient(app)
    resp = client.post("/work-items", json={"title": ""})
    assert resp.status_code == 422


@pytest.mark.skipif(
    os.environ.get("STARTER_DATABASE_TEST") != "1" and not _postgres_reachable(),
    reason="PostgreSQL container not running locally",
)
def test_work_items_postgresql_persistence() -> None:
    app_db.init_work_items_schema()
    client = TestClient(app)

    create_resp = client.post(
        "/work-items",
        json={
            "title": "PostgreSQL API persistence check",
            "description": "Verify HTTP POST /work-items commits to real PostgreSQL table",
            "assigned_role": "data_rag_engineer",
        },
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    try:
        # Verify committed row across an independent PostgreSQL connection
        with psycopg.connect(get_settings().database_url) as verify_conn:
            row = verify_conn.execute(
                "SELECT title, status, assigned_role FROM work_items WHERE id = %s",
                (item_id,),
            ).fetchone()
            assert row == ("PostgreSQL API persistence check", "open", "data_rag_engineer")

        complete_resp = client.patch(f"/work-items/{item_id}/complete")
        assert complete_resp.status_code == 200
        assert complete_resp.json()["status"] == "done"

        with psycopg.connect(get_settings().database_url) as verify_conn:
            row_done = verify_conn.execute(
                "SELECT status, completed_at IS NOT NULL FROM work_items WHERE id = %s",
                (item_id,),
            ).fetchone()
            assert row_done == ("done", True)
    finally:
        del_resp = client.delete(f"/work-items/{item_id}")
        assert del_resp.status_code == 204
