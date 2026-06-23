import pytest
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_database
from app.main import create_app
from app.services.profitability_service import ProfitabilityService

USER_ID = str(ObjectId())
FARM_ID = str(ObjectId())
PLOT_ID = str(ObjectId())
CYCLE_1_ID = str(ObjectId())
CYCLE_2_ID = str(ObjectId())
CYCLE_3_ID = str(ObjectId())


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    
    # Defaults
    db.users.find_one = AsyncMock(return_value={"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"})
    
    # Farms
    mock_farm = {
        "_id": ObjectId(FARM_ID),
        "user_id": ObjectId(USER_ID),
        "name": "Local Farm",
        "area": 2.5,
        "area_unit": "ACRE",
        "latitude": 22.7,
        "longitude": 75.8,
        "created_at": datetime.now(timezone.utc),
    }
    db.farms.find_one = AsyncMock(return_value=mock_farm)
    
    # Plots
    mock_plot = {
        "_id": ObjectId(PLOT_ID),
        "farm_id": ObjectId(FARM_ID),
        "name": "Plot A",
        "area": 1.25,
        "area_unit": "HECTARE",
    }
    db.plots.find_one = AsyncMock(return_value=mock_plot)
    
    def fake_plot_find(*args, **kwargs):
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            yield mock_plot
        mock_cursor.__aiter__ = fake_iter
        mock_cursor.to_list = AsyncMock(return_value=[mock_plot])
        return mock_cursor
    db.plots.find = MagicMock(side_effect=fake_plot_find)

    # Cycles
    mock_cycles = [
        {
            "_id": ObjectId(CYCLE_1_ID),
            "plot_id": ObjectId(PLOT_ID),
            "crop_type": "WHEAT",
            "season": "RABI",
            "sowing_date": datetime(2025, 11, 15, tzinfo=timezone.utc),
            "expected_harvest_date": datetime(2026, 3, 15, tzinfo=timezone.utc),
            "status": "HARVESTED",
        },
        {
            "_id": ObjectId(CYCLE_2_ID),
            "plot_id": ObjectId(PLOT_ID),
            "crop_type": "RICE",
            "season": "KHARIF",
            "sowing_date": datetime(2025, 6, 15, tzinfo=timezone.utc),
            "expected_harvest_date": datetime(2025, 10, 15, tzinfo=timezone.utc),
            "status": "HARVESTED",
        },
        {
            "_id": ObjectId(CYCLE_3_ID),
            "plot_id": ObjectId(PLOT_ID),
            "crop_type": "COTTON",
            "season": "KHARIF",
            "sowing_date": datetime(2024, 6, 15, tzinfo=timezone.utc),
            "expected_harvest_date": datetime(2024, 11, 15, tzinfo=timezone.utc),
            "status": "FAILED",
        }
    ]

    def fake_cycle_find_one(query):
        q_id = query.get("_id")
        for c in mock_cycles:
            if c["_id"] == q_id:
                return c
        return None
    db.crop_cycles.find_one = AsyncMock(side_effect=fake_cycle_find_one)

    def fake_cycle_find(query):
        plot_id = query.get("plot_id")
        if isinstance(plot_id, dict) and "$in" in plot_id:
            allowed_ids = plot_id["$in"]
            filtered = [c for c in mock_cycles if c["plot_id"] in allowed_ids]
        elif plot_id:
            filtered = [c for c in mock_cycles if c["plot_id"] == plot_id]
        else:
            filtered = mock_cycles

        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            for c in filtered:
                yield c
        mock_cursor.__aiter__ = fake_iter
        mock_cursor.to_list = AsyncMock(return_value=filtered)
        return mock_cursor
    db.crop_cycles.find = MagicMock(side_effect=fake_cycle_find)

    # Expenses & Harvests
    expenses_data = {
        CYCLE_1_ID: [
            {"amount": 10000.0, "category": "SEEDS"},
            {"amount": 15000.0, "category": "FERTILIZER"},
            {"amount": 5000.0, "category": "LABOR"},
        ],
        CYCLE_2_ID: [
            {"amount": 8000.0, "category": "SEEDS"},
            {"amount": 12000.0, "category": "IRRIGATION_FUEL"},
        ],
        CYCLE_3_ID: [
            {"amount": 6000.0, "category": "SEEDS"},
            {"amount": 4000.0, "category": "PESTICIDES"},
        ]
    }
    
    harvests_data = {
        CYCLE_1_ID: [
            {"revenue": 40000.0, "yield_quantity": 20.0, "yield_unit": "QUINTAL"},
            {"revenue": 10000.0, "yield_quantity": 5.0, "yield_unit": "QUINTAL"},
        ],
        CYCLE_2_ID: [
            {"revenue": 15000.0, "yield_quantity": 10.0, "yield_unit": "QUINTAL"},
        ],
        CYCLE_3_ID: [] # Failed crop, no harvest
    }

    def fake_expense_find(query):
        c_id = str(query.get("crop_cycle_id"))
        filtered = expenses_data.get(c_id, [])
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            for e in filtered:
                yield e
        mock_cursor.__aiter__ = fake_iter
        mock_cursor.to_list = AsyncMock(return_value=filtered)
        return mock_cursor
    db.expenses.find = MagicMock(side_effect=fake_expense_find)

    def fake_harvest_find(query):
        c_id = str(query.get("crop_cycle_id"))
        filtered = harvests_data.get(c_id, [])
        mock_cursor = MagicMock()
        async def fake_iter(*args, **kwargs):
            for h in filtered:
                yield h
        mock_cursor.__aiter__ = fake_iter
        mock_cursor.to_list = AsyncMock(return_value=filtered)
        return mock_cursor
    db.harvests.find = MagicMock(side_effect=fake_harvest_find)

    return db


@pytest.fixture
def client(mock_db: MagicMock, monkeypatch) -> TestClient:
    monkeypatch.setattr("app.main.connect_to_mongo", AsyncMock())
    monkeypatch.setattr("app.main.ensure_indexes", AsyncMock())
    monkeypatch.setattr("app.main.close_mongo_connection", AsyncMock())

    app = create_app()

    async def fake_user():
        return {"_id": ObjectId(USER_ID), "preferred_lang": "hi", "role": "FARMER"}

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_database] = lambda: mock_db

    return TestClient(app)


@pytest.mark.asyncio
async def test_profitability_service_cycle_metrics(mock_db: MagicMock) -> None:
    service = ProfitabilityService(mock_db)
    
    # 1. Cycle 1 (Positive Profit, Multiple Harvests and Expenses)
    res_1 = await service.calculate_crop_cycle_metrics(USER_ID, CYCLE_1_ID)
    metrics_1 = res_1.metrics
    assert metrics_1.total_cost == 30000.0 # 10 + 15 + 5
    assert metrics_1.total_revenue == 50000.0 # 40 + 10
    assert metrics_1.net_profit == 20000.0
    assert metrics_1.roi_percent == pytest.approx(66.66666666666666)
    assert metrics_1.cost_per_unit == 1200.0 # 30000 / 25
    assert metrics_1.revenue_per_unit == 2000.0 # 50000 / 25
    assert metrics_1.break_even_yield == 15.0 # 30000 / 2000
    assert metrics_1.break_even_price == 1200.0 # 30000 / 25

    # 2. Cycle 2 (Negative Profit/Loss)
    res_2 = await service.calculate_crop_cycle_metrics(USER_ID, CYCLE_2_ID)
    metrics_2 = res_2.metrics
    assert metrics_2.total_cost == 20000.0 # 8 + 12
    assert metrics_2.total_revenue == 15000.0
    assert metrics_2.net_profit == -5000.0
    assert metrics_2.roi_percent == -25.0

    # 3. Cycle 3 (Zero Harvest/Yield, Negative Profit)
    res_3 = await service.calculate_crop_cycle_metrics(USER_ID, CYCLE_3_ID)
    metrics_3 = res_3.metrics
    assert metrics_3.total_cost == 10000.0
    assert metrics_3.total_revenue == 0.0
    assert metrics_3.net_profit == -10000.0
    assert metrics_3.roi_percent == -100.0
    assert metrics_3.cost_per_unit == 0.0
    assert metrics_3.revenue_per_unit == 0.0
    assert metrics_3.break_even_yield == 0.0
    assert metrics_3.break_even_price == 0.0


@pytest.mark.asyncio
async def test_profitability_service_aggregations(mock_db: MagicMock) -> None:
    service = ProfitabilityService(mock_db)

    # 1. Plot Aggregation
    plot_metrics = await service.calculate_plot_metrics(USER_ID, PLOT_ID)
    assert plot_metrics.total_cost == 60000.0 # 30 + 20 + 10
    assert plot_metrics.total_revenue == 65000.0 # 50 + 15 + 0
    assert plot_metrics.net_profit == 5000.0
    assert plot_metrics.roi_percent == pytest.approx(8.333333333333334)

    # 2. Farm Summary (Crops: Wheat=+20k, Rice=-5k, Cotton=-10k)
    farm_summary = await service.calculate_farm_summary(USER_ID, FARM_ID)
    assert farm_summary.total_cost == 60000.0
    assert farm_summary.total_revenue == 65000.0
    assert farm_summary.total_profit == 5000.0
    assert farm_summary.roi_percent == pytest.approx(8.333333333333334)
    assert farm_summary.best_performing_crop == "WHEAT"
    assert farm_summary.worst_performing_crop == "COTTON"

    # 3. Seasonal Comparison
    seasons = await service.calculate_season_comparison(USER_ID, FARM_ID)
    assert len(seasons) == 3
    # Sorted chronologically: KHARIF_2024, KHARIF_2025, RABI_2025
    assert seasons[0].season == "COTTON_2024" or seasons[0].season == "KHARIF_2024"
    # Detailed values check
    wheat_season = next(s for s in seasons if "2025" in s.season and ("RABI" in s.season or "WHEAT" in s.season))
    assert wheat_season.profit == 20000.0
    assert wheat_season.roi == pytest.approx(66.66666666666666)


def test_endpoints_profitability(client: TestClient) -> None:
    # 1. Crop Cycle endpoint
    res_cycle = client.get(f"/api/v1/profitability/crop-cycle/{CYCLE_1_ID}")
    assert res_cycle.status_code == 200
    assert res_cycle.json()["crop_cycle_id"] == CYCLE_1_ID
    assert res_cycle.json()["metrics"]["net_profit"] == 20000.0

    # 2. Plot endpoint
    res_plot = client.get(f"/api/v1/profitability/plot/{PLOT_ID}")
    assert res_plot.status_code == 200
    assert res_plot.json()["net_profit"] == 5000.0

    # 3. Farm endpoint
    res_farm = client.get(f"/api/v1/profitability/farm/{FARM_ID}")
    assert res_farm.status_code == 200
    assert res_farm.json()["total_profit"] == 5000.0

    # 4. Seasonal comparison endpoint
    res_seasons = client.get(f"/api/v1/profitability/farm/{FARM_ID}/season-comparison")
    assert res_seasons.status_code == 200
    assert len(res_seasons.json()) == 3
