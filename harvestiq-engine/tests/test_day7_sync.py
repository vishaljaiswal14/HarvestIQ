from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.models.day7_schemas import SyncBatchRequest, SyncOperation
from app.services.sync_service import SyncService


@pytest.mark.asyncio
async def test_sync_duplicate_client_id_skipped() -> None:
    db = MagicMock()
    db.sync_receipts.find_one = AsyncMock(return_value={"client_id": "abc-123"})
    service = SyncService(db)

    result = await service.replay_batch(
        str(ObjectId()),
        SyncBatchRequest(
            operations=[
                SyncOperation(
                    client_id="abc-123",
                    operation_type="MARK_ALERT_READ",
                    payload={"alert_id": str(ObjectId())},
                    client_timestamp=datetime.now(timezone.utc),
                )
            ]
        ),
    )

    assert result.results[0].status == "DUPLICATE"


@pytest.mark.asyncio
async def test_sync_unsupported_operation_fails() -> None:
    db = MagicMock()
    db.sync_receipts.find_one = AsyncMock(return_value=None)
    service = SyncService(db)

    result = await service.replay_batch(
        str(ObjectId()),
        SyncBatchRequest(
            operations=[
                SyncOperation(
                    client_id="new-op-1",
                    operation_type="UNKNOWN",
                    payload={},
                    client_timestamp=datetime.now(timezone.utc),
                )
            ]
        ),
    )

    assert result.results[0].status == "FAILED"


@pytest.mark.asyncio
async def test_sync_trigger_sos_replay(monkeypatch) -> None:
    db = MagicMock()
    db.sync_receipts.find_one = AsyncMock(return_value=None)
    db.sync_receipts.insert_one = AsyncMock()
    
    db.users.find_one = AsyncMock(return_value={
        "_id": ObjectId(),
        "name": "Rajesh Kumar",
        "phone": "+919876543210"
    })
    db.farms.find_one = AsyncMock(return_value={
        "_id": ObjectId(),
        "name": "Test Farm",
        "state": "Madhya Pradesh",
        "district": "Indore"
    })
    
    from app.services.context_compiler_service import HealthCompiledResult, ContextCompilerService
    core = MagicMock()
    core.stage = "Tillering"
    core.fsi = 0.82
    core.fsi_classification = "HIGH_STRESS"
    core.yield_risk.risk_band = "HIGH"
    snapshot = HealthCompiledResult(
        core=core,
        health_score=42.0,
        health_band="POOR",
        nearby_radar_high_count=1,
        unread_alerts=2,
        explainability={},
        intelligence_snapshot_version="v3",
    )
    
    monkeypatch.setattr(ContextCompilerService, "compile_health_snapshot", AsyncMock(return_value=snapshot))
    
    db.sos_actions.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId()))
    
    service = SyncService(db)
    
    farm_id = str(ObjectId())
    result = await service.replay_batch(
        str(ObjectId()),
        SyncBatchRequest(
            operations=[
                SyncOperation(
                    client_id="sos-local-1",
                    operation_type="TRIGGER_SOS",
                    payload={
                        "farm_id": farm_id,
                        "emergency_type": "FLOOD",
                        "latitude": 22.7,
                        "longitude": 75.8,
                        "captured_at": "2026-06-16T19:27:39Z"
                    },
                    client_timestamp=datetime.now(timezone.utc),
                )
            ]
        ),
    )
    
    assert len(result.results) == 1
    assert result.results[0].status == "SUCCESS"
    assert "triggered" in result.results[0].detail
    db.sos_actions.insert_one.assert_called_once()
    inserted_doc = db.sos_actions.insert_one.call_args[0][0]
    assert inserted_doc["emergency_type"] == "FLOOD"
    assert inserted_doc["triggered_at"] == datetime.fromisoformat("2026-06-16T19:27:39+00:00")
