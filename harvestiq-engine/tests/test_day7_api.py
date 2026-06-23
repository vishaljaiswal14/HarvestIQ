from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.models.day7_schemas import DemoInitializeResponse, SosTriggerResponse, SyncBatchResponse

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: MagicMock()

    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        "app.api.v1.sos.SosService.trigger",
        AsyncMock(
            return_value=SosTriggerResponse(
                action_id=str(ObjectId()),
                farm_id=FARM_ID,
                emergency_type="GENERAL",
                checklist=["Step 1", "Step 2"],
                plain_text_message="SOS message",
                delivery_status="LOGGED",
                intelligence_snapshot_version="v3",
                triggered_at=now,
            )
        ),
    )
    monkeypatch.setattr(
        "app.api.v1.sync.SyncService.replay_batch",
        AsyncMock(
            return_value=SyncBatchResponse(processed=0, results=[]),
        ),
    )

    return TestClient(app)


def test_sos_trigger_endpoint(client: TestClient) -> None:
    response = client.post(
        "/api/v1/sos/trigger",
        json={"farm_id": FARM_ID, "emergency_type": "GENERAL"},
    )
    assert response.status_code == 200
    assert response.json()["intelligence_snapshot_version"] == "v3"


def test_demo_initialize_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/demo/initialize")
    assert response.status_code == 200
    body = response.json()
    assert body["demo_mode"] is True
    assert len(body["farms"]) >= 1


def test_sync_endpoint(client: TestClient) -> None:
    response = client.post("/api/v1/sync", json={"operations": []})
    assert response.status_code == 200


def test_health_includes_db_status(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.main.get_database",
        MagicMock(return_value=MagicMock(command=AsyncMock(return_value={"ok": 1}))),
    )
    response = client.get("/health")
    assert response.status_code == 200
    assert "db" in response.json()
