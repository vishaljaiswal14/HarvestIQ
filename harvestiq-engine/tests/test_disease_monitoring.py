import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient
from pathlib import Path

import app.core.database as db_module
from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())
REPORT_ID = str(ObjectId())


class MockAsyncCursor:
    def __init__(self, items: list) -> None:
        self._items = items

    def sort(self, *_args, **_kwargs):
        return self

    def skip(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._index]
        self._index += 1
        return item


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: mock_db
    monkeypatch.setattr(db_module, "_db", mock_db)
    
    app.state.db = mock_db

    return TestClient(app)


def test_disease_history_endpoint(client: TestClient) -> None:
    db = client.app.state.db
    db.disease_reports.count_documents = AsyncMock(return_value=1)
    
    mock_doc = {
        "_id": ObjectId(REPORT_ID),
        "farm_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "crop_type": "WHEAT",
        "detected_disease": "WHEAT_RUST",
        "confidence": 0.88,
        "deterministic_status": "POSSIBLE_DISEASE",
        "created_at": datetime.now(timezone.utc),
        "disease_name": "Wheat Rust",
        "severity": "Medium",
        "risk_level": "Medium",
        "validation_result": True,
        "crop_confidence": 0.94,
        "region_validation_result": True,
        "image_storage_key": "data/uploads/disease/some-file.jpg"
    }
    
    db.disease_reports.find = MagicMock(return_value=MockAsyncCursor([mock_doc]))
    
    response = client.get(f"/api/v1/disease/history?farm_id={FARM_ID}&page=1&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["reports"]) == 1
    report = body["reports"][0]
    assert report["report_id"] == REPORT_ID
    assert report["disease"] == "WHEAT_RUST"
    assert report["confidence"] == 0.88
    assert report["crop_confidence"] == 0.94


def test_disease_detail_endpoint(client: TestClient) -> None:
    db = client.app.state.db
    
    mock_doc = {
        "_id": ObjectId(REPORT_ID),
        "farm_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "crop_type": "WHEAT",
        "detected_disease": "WHEAT_RUST",
        "confidence": 0.88,
        "deterministic_status": "POSSIBLE_DISEASE",
        "created_at": datetime.now(timezone.utc),
        "disease_name": "Wheat Rust",
        "severity": "Medium",
        "risk_level": "Medium",
        "validation_result": True,
        "crop_confidence": 0.94,
        "region_validation_result": True,
        "image_storage_key": "data/uploads/disease/some-file.jpg"
    }
    
    db.disease_reports.find_one = AsyncMock(return_value=mock_doc)
    
    response = client.get(f"/api/v1/disease/history/{REPORT_ID}")
    assert response.status_code == 200
    report = response.json()
    assert report["report_id"] == REPORT_ID
    assert report["disease_name"] == "Wheat Rust"
    assert report["crop_confidence"] == 0.94


def test_disease_image_serving_endpoint(client: TestClient) -> None:
    db = client.app.state.db
    
    mock_doc = {
        "_id": ObjectId(REPORT_ID),
        "user_id": ObjectId(USER_ID),
        "image_storage_key": "/fake/path/to/image.jpg"
    }
    
    db.disease_reports.find_one = AsyncMock(return_value=mock_doc)
    
    from fastapi.responses import Response
    with patch("app.api.v1.disease.Path.exists", return_value=True), \
         patch("app.api.v1.disease.FileResponse", return_value=Response(content=b"fake-image-bytes", media_type="image/jpeg")):
        response = client.get(f"/api/v1/disease/history/{REPORT_ID}/image")
        assert response.status_code == 200
        assert response.content == b"fake-image-bytes"


def test_farm_timeline_aggregation(client: TestClient) -> None:
    db = client.app.state.db
    now = datetime.now(timezone.utc)
    
    db.farms.find_one = AsyncMock(return_value={
        "_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "name": "Wheat Field",
        "state": "Rajasthan"
    })
    
    # Mock Disease scan
    disease_doc = {
        "_id": ObjectId(),
        "farm_id": ObjectId(FARM_ID),
        "created_at": now,
        "detected_disease": "WHEAT_RUST",
        "deterministic_status": "POSSIBLE_DISEASE",
        "disease_name": "Wheat Rust",
        "severity": "Medium",
        "risk_level": "Medium",
        "what_it_means": "Leaf symptoms suggest an active rust infection.",
        "immediate_actions": ["Spray the recommended fungicide within 48 hours."],
    }
    db.disease_reports.find = MagicMock(return_value=MockAsyncCursor([disease_doc]))
    
    # Mock FSI Stress Log
    stress_doc = {
        "_id": ObjectId(),
        "farm_id": ObjectId(FARM_ID),
        "calculated_at": now - timedelta(seconds=10),
        "fsi_score": 45.0,
        "classification": "HIGH",
        "primary_factor": "MOISTURE"
    }
    db.stress_logs.find = MagicMock(return_value=MockAsyncCursor([stress_doc]))
    
    # Mock Alert
    alert_doc = {
        "_id": ObjectId(),
        "farm_id": ObjectId(FARM_ID),
        "created_at": now - timedelta(seconds=20),
        "title": "Moisture stress alert",
        "message": "FSI medium risk detected",
        "severity": "warning",
        "rule_id": "RULE_FSI_HIGH"
    }
    db.alerts.find = MagicMock(return_value=MockAsyncCursor([alert_doc]))

    plan_doc = {
        "_id": ObjectId(),
        "farm_id": ObjectId(FARM_ID),
        "generated_at": now - timedelta(seconds=15),
        "priority": "HIGH",
        "severity_tier": "HIGH",
        "potential_loss_prevention_band": "HIGH",
        "situation_summary": "Your Wheat crop is undergoing high stress due to MOISTURE deficit/excess (FSI: 82%). Act now to save your yield.",
        "actions": [
            {
                "id": "action-1",
                "title": "Irrigate now",
                "action": "Irrigate within 24 hours.",
                "horizon": "TODAY",
            }
        ],
    }
    db.copilot_plans.find = MagicMock(return_value=MockAsyncCursor([plan_doc]))

    yield_doc = {
        "_id": ObjectId(),
        "farm_id": ObjectId(FARM_ID),
        "calculated_at": now - timedelta(seconds=12),
        "score": 61.2,
        "band": "AT_RISK",
        "top_risk": "High_Stress Stress Risk",
        "breakdown": {"stress_risk": 20.0},
    }
    db.yield_protection_logs.find = MagicMock(return_value=MockAsyncCursor([yield_doc]))
    
    response = client.get(f"/api/v1/disease/timeline?farm_id={FARM_ID}")
    assert response.status_code == 200
    body = response.json()
    assert body["farm_id"] == FARM_ID
    assert len(body["events"]) == 2
    
    events = body["events"]
    assert events[0]["type"] == "Disease Alert"
    assert events[0]["title"] == "Wheat Rust Detected"
    assert events[0]["action"] == "Spray the recommended fungicide within 48 hours."

    assert events[1]["type"] == "Crop Stress Alert"
    assert events[1]["title"] == "Moisture Stress Detected"
    assert "FSI" not in events[1]["description"]
    assert "High_Stress" not in events[1]["description"]
    assert events[1]["action"] == "Irrigate within 24 hours."


def test_demo_seed_endpoint(client: TestClient) -> None:
    db = client.app.state.db
    
    # Mocking cleanup queries
    db.farms.find = MagicMock(return_value=MockAsyncCursor([]))
    db.farms.delete_many = AsyncMock()
    db.plots.find = MagicMock(return_value=MockAsyncCursor([]))
    
    # Mocking insertions
    db.farms.insert_one = AsyncMock(side_effect=lambda doc: MagicMock(inserted_id=ObjectId()))
    db.plots.insert_one = AsyncMock(side_effect=lambda doc: MagicMock(inserted_id=ObjectId()))
    db.crop_cycles.insert_one = AsyncMock(side_effect=lambda doc: MagicMock(inserted_id=ObjectId()))
    db.stress_logs.insert_many = AsyncMock()
    db.disease_reports.insert_many = AsyncMock()
    db.disease_reports.insert_one = AsyncMock()
    db.alerts.insert_one = AsyncMock()
    db.alerts.insert_many = AsyncMock()
    db.soil_records.insert_one = AsyncMock()
    
    response = client.post("/api/v1/demo/seed")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["farms"]) == 3
    assert body["farms"][0]["status"] == "Healthy"
    assert body["farms"][1]["status"] == "Outbreak"
    assert body["farms"][2]["status"] == "High-Risk"
