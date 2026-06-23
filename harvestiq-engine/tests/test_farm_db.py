from datetime import datetime, date, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())
PLOT_ID = str(ObjectId())
CYCLE_ID = str(ObjectId())
EXPENSE_ID = str(ObjectId())
HARVEST_ID = str(ObjectId())


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    mock_db = MagicMock()
    
    # 1. Mock users endpoints
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": ObjectId(USER_ID),
        "name": "Rajesh Kumar",
        "phone": "+919876543210",
        "role": "FARMER",
        "preferred_lang": "hi",
        "state": "Madhya Pradesh",
        "district": "Indore",
        "created_at": datetime.now(timezone.utc),
    })
    mock_db.users.update_one = AsyncMock()

    # 2. Mock farms endpoints
    mock_farm = {
        "_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "name": "North Plot",
        "area": 2.5,
        "area_unit": "ACRE",
        "latitude": 22.7,
        "longitude": 75.8,
        "created_at": datetime.now(timezone.utc),
    }
    mock_db.farms.find_one = AsyncMock(return_value=mock_farm)
    
    def fake_farm_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_farm
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    mock_db.farms.find = MagicMock(side_effect=fake_farm_find)
    mock_db.farms.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(FARM_ID)))
    mock_db.farms.update_one = AsyncMock()
    mock_db.farms.delete_one = AsyncMock()
    mock_db.farms.delete_many = AsyncMock()

    # 3. Mock plots endpoints
    mock_plot = {
        "_id": ObjectId(PLOT_ID),
        "farm_id": ObjectId(FARM_ID),
        "name": "Plot A",
        "area": 1.25,
        "area_unit": "HECTARE",
    }
    mock_db.plots.find_one = AsyncMock(return_value=mock_plot)
    
    def fake_plot_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_plot
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    mock_db.plots.find = MagicMock(side_effect=fake_plot_find)
    mock_db.plots.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(PLOT_ID)))
    mock_db.plots.update_one = AsyncMock()
    mock_db.plots.delete_one = AsyncMock()
    mock_db.plots.delete_many = AsyncMock()

    # 4. Mock crop cycles endpoints
    mock_cycle = {
        "_id": ObjectId(CYCLE_ID),
        "plot_id": ObjectId(PLOT_ID),
        "crop_type": "WHEAT",
        "season": "RABI",
        "sowing_date": datetime.now(timezone.utc),
        "expected_harvest_date": datetime.now(timezone.utc),
        "status": "ACTIVE",
    }
    mock_db.crop_cycles.find_one = AsyncMock(return_value=mock_cycle)
    
    def fake_cycle_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_cycle
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    mock_db.crop_cycles.find = MagicMock(side_effect=fake_cycle_find)
    mock_db.crop_cycles.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(CYCLE_ID)))
    mock_db.crop_cycles.update_one = AsyncMock()
    mock_db.crop_cycles.delete_one = AsyncMock()
    mock_db.crop_cycles.delete_many = AsyncMock()

    # 5. Mock expenses endpoints
    mock_expense = {
        "_id": ObjectId(EXPENSE_ID),
        "crop_cycle_id": ObjectId(CYCLE_ID),
        "category": "FERTILIZER",
        "amount": 2500.0,
        "notes": "Purchased Urea",
        "expense_date": datetime.now(timezone.utc),
    }
    mock_db.expenses.find_one = AsyncMock(return_value=mock_expense)
    
    def fake_expense_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_expense
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    mock_db.expenses.find = MagicMock(side_effect=fake_expense_find)
    mock_db.expenses.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(EXPENSE_ID)))
    mock_db.expenses.update_one = AsyncMock()
    mock_db.expenses.delete_one = AsyncMock()
    mock_db.expenses.delete_many = AsyncMock()

    # 6. Mock harvests endpoints
    mock_harvest = {
        "_id": ObjectId(HARVEST_ID),
        "crop_cycle_id": ObjectId(CYCLE_ID),
        "yield_quantity": 30.0,
        "yield_unit": "QUINTAL",
        "revenue": 65000.0,
        "harvest_date": datetime.now(timezone.utc),
    }
    mock_db.harvests.find_one = AsyncMock(return_value=mock_harvest)
    
    def fake_harvest_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_harvest
        mock_cursor.__aiter__ = fake_iter
        return mock_cursor
    mock_db.harvests.find = MagicMock(side_effect=fake_harvest_find)
    mock_db.harvests.insert_one = AsyncMock(return_value=MagicMock(inserted_id=ObjectId(HARVEST_ID)))
    mock_db.harvests.update_one = AsyncMock()
    mock_db.harvests.delete_one = AsyncMock()
    mock_db.harvests.delete_many = AsyncMock()

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: mock_db

    return TestClient(app)


def test_get_farmer_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/farm-db/farmer/me")
    assert response.status_code == 200
    assert response.json()["name"] == "Rajesh Kumar"


def test_update_farmer_endpoint(client: TestClient) -> None:
    response = client.put(
        "/api/v1/farm-db/farmer/me",
        json={"name": "Rajesh Singh", "state": "Punjab", "district": "Ludhiana"},
    )
    assert response.status_code == 200


def test_farms_crud_endpoints(client: TestClient) -> None:
    # Test Create Farm
    res_create = client.post(
        "/api/v1/farm-db/farms",
        json={"name": "West Plot", "area": 3.0, "area_unit": "ACRE", "latitude": 22.0, "longitude": 75.0},
    )
    assert res_create.status_code == 201

    # Test List Farms
    res_list = client.get("/api/v1/farm-db/farms")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # Test Get Farm
    res_get = client.get(f"/api/v1/farm-db/farms/{FARM_ID}")
    assert res_get.status_code == 200

    # Test Update Farm
    res_update = client.put(
        f"/api/v1/farm-db/farms/{FARM_ID}",
        json={"name": "West Plot Updated", "area": 3.5, "area_unit": "ACRE", "latitude": 22.1, "longitude": 75.1},
    )
    assert res_update.status_code == 200

    # Test Delete Farm
    res_delete = client.delete(f"/api/v1/farm-db/farms/{FARM_ID}")
    assert res_delete.status_code == 204


def test_plots_crud_endpoints(client: TestClient) -> None:
    # Test Create Plot
    res_create = client.post(
        "/api/v1/farm-db/plots",
        json={"farm_id": FARM_ID, "name": "Plot B", "area": 1.0, "area_unit": "HECTARE"},
    )
    assert res_create.status_code == 201

    # Test List Plots
    res_list = client.get(f"/api/v1/farm-db/plots?farm_id={FARM_ID}")
    assert res_list.status_code == 200

    # Test Get Plot
    res_get = client.get(f"/api/v1/farm-db/plots/{PLOT_ID}")
    assert res_get.status_code == 200


def test_crop_cycles_crud_endpoints(client: TestClient) -> None:
    # Test Create Crop Cycle
    res_create = client.post(
        "/api/v1/farm-db/crop-cycles",
        json={
            "plot_id": PLOT_ID,
            "crop_type": "WHEAT",
            "season": "RABI",
            "sowing_date": "2026-06-15",
            "expected_harvest_date": "2026-10-15",
        },
    )
    assert res_create.status_code == 201

    # Test List Crop Cycles
    res_list = client.get(f"/api/v1/farm-db/crop-cycles?plot_id={PLOT_ID}")
    assert res_list.status_code == 200

    # Test List Active Crop Cycles
    res_active = client.get("/api/v1/farm-db/crop-cycles/active")
    assert res_active.status_code == 200


def test_expenses_crud_endpoints(client: TestClient) -> None:
    # Test Create Expense
    res_create = client.post(
        "/api/v1/farm-db/expenses",
        json={
            "crop_cycle_id": CYCLE_ID,
            "category": "FERTILIZER",
            "amount": 2500,
            "notes": "Bought Urea",
            "expense_date": "2026-06-16",
        },
    )
    assert res_create.status_code == 201

    # Test List Expenses
    res_list = client.get(f"/api/v1/farm-db/expenses?crop_cycle_id={CYCLE_ID}")
    assert res_list.status_code == 200


def test_harvests_crud_endpoints(client: TestClient) -> None:
    # Test Create Harvest
    res_create = client.post(
        "/api/v1/farm-db/harvests",
        json={
            "crop_cycle_id": CYCLE_ID,
            "yield_quantity": 30.0,
            "yield_unit": "QUINTAL",
            "revenue": 65000,
            "harvest_date": "2026-06-16",
        },
    )
    assert res_create.status_code == 201

    # Test List Harvests
    res_list = client.get(f"/api/v1/farm-db/harvests?crop_cycle_id={CYCLE_ID}")
    assert res_list.status_code == 200
