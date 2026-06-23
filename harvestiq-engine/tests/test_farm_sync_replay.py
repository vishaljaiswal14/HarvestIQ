import pytest
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId

from app.models.day7_schemas import SyncBatchRequest, SyncOperation
from app.services.sync_service import SyncService

USER_ID = str(ObjectId())
CLIENT_FARM_ID = "farm_local_123"
SERVER_FARM_ID = str(ObjectId())
CLIENT_PLOT_ID = "plot_local_456"
SERVER_PLOT_ID = str(ObjectId())
CLIENT_CYCLE_ID = "cycle_local_789"
SERVER_CYCLE_ID = str(ObjectId())
CLIENT_EXPENSE_ID = "expense_local_999"
SERVER_EXPENSE_ID = str(ObjectId())
CLIENT_HARVEST_ID = "harvest_local_888"
SERVER_HARVEST_ID = str(ObjectId())


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    
    # Defaults
    db.sync_receipts.find_one = AsyncMock(return_value=None)
    db.sync_receipts.insert_one = AsyncMock()

    # User Profile
    db.users.find_one = AsyncMock(return_value={
        "_id": ObjectId(USER_ID),
        "name": "Rajesh Kumar",
        "phone": "+919876543210",
        "role": "FARMER",
        "preferred_lang": "hi",
        "state": "Madhya Pradesh",
        "district": "Indore",
        "created_at": datetime.now(timezone.utc),
    })

    # Farms
    mock_farm = {
        "_id": ObjectId(SERVER_FARM_ID),
        "user_id": ObjectId(USER_ID),
        "name": "Local Farm",
        "area": 2.5,
        "area_unit": "ACRE",
        "latitude": 22.7,
        "longitude": 75.8,
        "created_at": datetime.now(timezone.utc),
    }
    db.farms.find_one = AsyncMock(return_value=mock_farm)
    db.farms.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(SERVER_FARM_ID)))
    db.farms.update_one = AsyncMock()
    db.farms.delete_one = AsyncMock()
    db.farms.delete_many = AsyncMock()

    def fake_farm_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_farm
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    db.farms.find = MagicMock(side_effect=fake_farm_find)

    # Plots
    mock_plot = {
        "_id": ObjectId(SERVER_PLOT_ID),
        "farm_id": ObjectId(SERVER_FARM_ID),
        "name": "Plot A",
        "area": 1.25,
        "area_unit": "HECTARE",
    }
    db.plots.find_one = AsyncMock(return_value=mock_plot)
    db.plots.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(SERVER_PLOT_ID)))
    db.plots.update_one = AsyncMock()
    db.plots.delete_one = AsyncMock()
    db.plots.delete_many = AsyncMock()

    def fake_plot_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_plot
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    db.plots.find = MagicMock(side_effect=fake_plot_find)

    # Crop Cycles
    mock_cycle = {
        "_id": ObjectId(SERVER_CYCLE_ID),
        "plot_id": ObjectId(SERVER_PLOT_ID),
        "crop_type": "WHEAT",
        "season": "RABI",
        "sowing_date": datetime.now(timezone.utc),
        "expected_harvest_date": datetime.now(timezone.utc),
        "status": "ACTIVE",
    }
    db.crop_cycles.find_one = AsyncMock(return_value=mock_cycle)
    db.crop_cycles.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(SERVER_CYCLE_ID)))
    db.crop_cycles.update_one = AsyncMock()
    db.crop_cycles.delete_one = AsyncMock()
    db.crop_cycles.delete_many = AsyncMock()

    def fake_cycle_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_cycle
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    db.crop_cycles.find = MagicMock(side_effect=fake_cycle_find)

    # Expenses
    mock_expense = {
        "_id": ObjectId(SERVER_EXPENSE_ID),
        "crop_cycle_id": ObjectId(SERVER_CYCLE_ID),
        "category": "FERTILIZER",
        "amount": 2500.0,
        "notes": "Bought Urea",
        "expense_date": datetime.now(timezone.utc),
    }
    db.expenses.find_one = AsyncMock(return_value=mock_expense)
    db.expenses.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(SERVER_EXPENSE_ID)))
    db.expenses.update_one = AsyncMock()
    db.expenses.delete_one = AsyncMock()
    db.expenses.delete_many = AsyncMock()

    def fake_expense_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_expense
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    db.expenses.find = MagicMock(side_effect=fake_expense_find)

    # Harvests
    mock_harvest = {
        "_id": ObjectId(SERVER_HARVEST_ID),
        "crop_cycle_id": ObjectId(SERVER_CYCLE_ID),
        "yield_quantity": 30.0,
        "yield_unit": "QUINTAL",
        "revenue": 65000.0,
        "harvest_date": datetime.now(timezone.utc),
    }
    db.harvests.find_one = AsyncMock(return_value=mock_harvest)
    db.harvests.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(SERVER_HARVEST_ID)))
    db.harvests.update_one = AsyncMock()
    db.harvests.delete_one = AsyncMock()
    db.harvests.delete_many = AsyncMock()
    db.harvests.count_documents = AsyncMock(return_value=1)

    def fake_harvest_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_harvest
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    db.harvests.find = MagicMock(side_effect=fake_harvest_find)

    return db


@pytest.mark.asyncio
async def test_farm_crud_sync_replay(mock_db: MagicMock) -> None:
    service = SyncService(mock_db)

    # 1. CREATE_FARM Replay
    req_create = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_FARM_ID,
                operation_type="CREATE_FARM",
                payload={"name": "North Field", "area": 3.0, "area_unit": "ACRE", "latitude": 22.0, "longitude": 75.0},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_create = await service.replay_batch(USER_ID, req_create)
    assert len(res_create.results) == 1
    assert res_create.results[0].status == "SUCCESS"
    assert res_create.results[0].server_id == SERVER_FARM_ID

    # 2. UPDATE_FARM Replay
    req_update = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id="upd-farm-1",
                operation_type="UPDATE_FARM",
                payload={"farm_id": SERVER_FARM_ID, "name": "North Field Updated", "area": 3.5, "area_unit": "ACRE", "latitude": 22.1, "longitude": 75.1},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_update = await service.replay_batch(USER_ID, req_update)
    assert res_update.results[0].status == "SUCCESS"
    assert res_update.results[0].server_id == SERVER_FARM_ID

    # 3. DELETE_FARM Replay
    req_delete = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id="del-farm-1",
                operation_type="DELETE_FARM",
                payload={"farm_id": SERVER_FARM_ID},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_delete = await service.replay_batch(USER_ID, req_delete)
    assert res_delete.results[0].status == "SUCCESS"


@pytest.mark.asyncio
async def test_plot_crud_sync_replay(mock_db: MagicMock) -> None:
    service = SyncService(mock_db)

    # 1. CREATE_PLOT Replay
    req_create = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_PLOT_ID,
                operation_type="CREATE_PLOT",
                payload={"farm_id": SERVER_FARM_ID, "name": "Plot B", "area": 1.0, "area_unit": "HECTARE"},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_create = await service.replay_batch(USER_ID, req_create)
    assert res_create.results[0].status == "SUCCESS"
    assert res_create.results[0].server_id == SERVER_PLOT_ID

    # 2. UPDATE_PLOT Replay
    req_update = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id="upd-plot-1",
                operation_type="UPDATE_PLOT",
                payload={"plot_id": SERVER_PLOT_ID, "farm_id": SERVER_FARM_ID, "name": "Plot B Updated", "area": 1.5, "area_unit": "HECTARE"},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_update = await service.replay_batch(USER_ID, req_update)
    assert res_update.results[0].status == "SUCCESS"

    # 3. DELETE_PLOT Replay
    req_delete = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id="del-plot-1",
                operation_type="DELETE_PLOT",
                payload={"plot_id": SERVER_PLOT_ID},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_delete = await service.replay_batch(USER_ID, req_delete)
    assert res_delete.results[0].status == "SUCCESS"


@pytest.mark.asyncio
async def test_dependent_entity_replays(mock_db: MagicMock) -> None:
    service = SyncService(mock_db)

    # CREATE_CROP_CYCLE Replay
    req_cycle = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_CYCLE_ID,
                operation_type="CREATE_CROP_CYCLE",
                payload={
                    "plot_id": SERVER_PLOT_ID,
                    "crop_type": "WHEAT",
                    "season": "RABI",
                    "sowing_date": "2026-06-15",
                    "expected_harvest_date": "2026-10-15",
                },
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_cycle = await service.replay_batch(USER_ID, req_cycle)
    assert res_cycle.results[0].status == "SUCCESS"
    assert res_cycle.results[0].server_id == SERVER_CYCLE_ID

    # CREATE_EXPENSE Replay
    req_expense = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_EXPENSE_ID,
                operation_type="CREATE_EXPENSE",
                payload={
                    "crop_cycle_id": SERVER_CYCLE_ID,
                    "category": "FERTILIZER",
                    "amount": 2500.0,
                    "notes": "Bought Urea",
                    "expense_date": "2026-06-16",
                },
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_expense = await service.replay_batch(USER_ID, req_expense)
    assert res_expense.results[0].status == "SUCCESS"
    assert res_expense.results[0].server_id == SERVER_EXPENSE_ID

    # CREATE_HARVEST Replay
    req_harvest = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_HARVEST_ID,
                operation_type="CREATE_HARVEST",
                payload={
                    "crop_cycle_id": SERVER_CYCLE_ID,
                    "yield_quantity": 30.0,
                    "yield_unit": "QUINTAL",
                    "revenue": 65000.0,
                    "harvest_date": "2026-06-16",
                },
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )
    res_harvest = await service.replay_batch(USER_ID, req_harvest)
    assert res_harvest.results[0].status == "SUCCESS"
    assert res_harvest.results[0].server_id == SERVER_HARVEST_ID


@pytest.mark.asyncio
async def test_parent_child_relationship_reconciliation_batch(mock_db: MagicMock) -> None:
    service = SyncService(mock_db)

    # In this test, we create Farm -> Plot -> Crop Cycle all offline.
    # The plot references the farm's local ID.
    # The cycle references the plot's local ID.
    # The service must reconcile them in order.
    
    batch = SyncBatchRequest(
        operations=[
            # 1. Create Farm
            SyncOperation(
                client_id=CLIENT_FARM_ID,
                operation_type="CREATE_FARM",
                payload={"name": "Golden Acre", "area": 5.0, "area_unit": "ACRE", "latitude": 22.0, "longitude": 75.0},
                client_timestamp=datetime.now(timezone.utc)
            ),
            # 2. Create Plot (references CLIENT_FARM_ID)
            SyncOperation(
                client_id=CLIENT_PLOT_ID,
                operation_type="CREATE_PLOT",
                payload={"farm_id": CLIENT_FARM_ID, "name": "Plot C", "area": 2.0, "area_unit": "ACRE"},
                client_timestamp=datetime.now(timezone.utc)
            ),
            # 3. Create Crop Cycle (references CLIENT_PLOT_ID)
            SyncOperation(
                client_id=CLIENT_CYCLE_ID,
                operation_type="CREATE_CROP_CYCLE",
                payload={
                    "plot_id": CLIENT_PLOT_ID,
                    "crop_type": "RICE",
                    "season": "KHARIF",
                    "sowing_date": "2026-06-15",
                    "expected_harvest_date": "2026-10-15",
                },
                client_timestamp=datetime.now(timezone.utc)
            ),
        ]
    )

    res = await service.replay_batch(USER_ID, batch)
    assert len(res.results) == 3
    for op_res in res.results:
        assert op_res.status == "SUCCESS"
    
    # Check that Plot insert was called with the reconciled SERVER_FARM_ID, NOT the client temporary ID
    mock_db.plots.insert_one.assert_called()
    called_plot_doc = mock_db.plots.insert_one.call_args[0][0]
    assert called_plot_doc["farm_id"] == ObjectId(SERVER_FARM_ID)

    # Check that Crop Cycle insert was called with the reconciled SERVER_PLOT_ID
    mock_db.crop_cycles.insert_one.assert_called()
    called_cycle_doc = mock_db.crop_cycles.insert_one.call_args[0][0]
    assert called_cycle_doc["plot_id"] == ObjectId(SERVER_PLOT_ID)


@pytest.mark.asyncio
async def test_duplicate_replay_protection_idempotency(mock_db: MagicMock) -> None:
    # First call will record success.
    # Second call with same client_id should return duplicate check bypass.
    mock_db.sync_receipts.find_one = AsyncMock(side_effect=[
        None, # First check
        {"client_id": CLIENT_FARM_ID, "server_id": SERVER_FARM_ID} # Second check
    ])
    
    service = SyncService(mock_db)

    req = SyncBatchRequest(
        operations=[
            SyncOperation(
                client_id=CLIENT_FARM_ID,
                operation_type="CREATE_FARM",
                payload={"name": "North Field", "area": 3.0, "area_unit": "ACRE", "latitude": 22.0, "longitude": 75.0},
                client_timestamp=datetime.now(timezone.utc)
            )
        ]
    )

    # Attempt 1
    res1 = await service.replay_batch(USER_ID, req)
    assert res1.results[0].status == "SUCCESS"
    assert res1.results[0].server_id == SERVER_FARM_ID

    # Attempt 2 (Idempotency trigger)
    res2 = await service.replay_batch(USER_ID, req)
    assert res2.results[0].status == "DUPLICATE"
    assert res2.results[0].server_id == SERVER_FARM_ID
    assert "Duplicate" in res2.results[0].detail


@pytest.mark.asyncio
async def test_partial_failure_handling(mock_db: MagicMock) -> None:
    service = SyncService(mock_db)

    # Force create plot to throw exception (e.g. invalid farm ID or validation error)
    mock_db.plots.insert_one = AsyncMock(side_effect=ValueError("Plot insert crashed"))

    batch = SyncBatchRequest(
        operations=[
            # 1. Create Farm (should succeed)
            SyncOperation(
                client_id=CLIENT_FARM_ID,
                operation_type="CREATE_FARM",
                payload={"name": "Golden Acre", "area": 5.0, "area_unit": "ACRE", "latitude": 22.0, "longitude": 75.0},
                client_timestamp=datetime.now(timezone.utc)
            ),
            # 2. Create Plot (fails)
            SyncOperation(
                client_id=CLIENT_PLOT_ID,
                operation_type="CREATE_PLOT",
                payload={"farm_id": CLIENT_FARM_ID, "name": "Plot C", "area": 2.0, "area_unit": "ACRE"},
                client_timestamp=datetime.now(timezone.utc)
            ),
            # 3. Create Crop Cycle (succeeds, referencing hardcoded cycle ID)
            SyncOperation(
                client_id=CLIENT_CYCLE_ID,
                operation_type="CREATE_CROP_CYCLE",
                payload={
                    "plot_id": SERVER_PLOT_ID,
                    "crop_type": "RICE",
                    "season": "KHARIF",
                    "sowing_date": "2026-06-15",
                    "expected_harvest_date": "2026-10-15",
                },
                client_timestamp=datetime.now(timezone.utc)
            ),
        ]
    )

    res = await service.replay_batch(USER_ID, batch)
    assert len(res.results) == 3
    assert res.results[0].status == "SUCCESS"
    assert res.results[1].status == "FAILED"
    assert "Plot insert crashed" in res.results[1].error
    assert res.results[2].status == "SUCCESS"
