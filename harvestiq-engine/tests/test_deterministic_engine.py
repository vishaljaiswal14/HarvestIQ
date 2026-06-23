from datetime import date

from app.models.engine_schemas import CropStageDefinition
from app.services.deterministic_engine import (
    accumulate_gdd,
    calculate_daily_gdd,
    resolve_growth_stage,
)

WHEAT_STAGES = [
    CropStageDefinition(name="Germination", gdd_min=0, gdd_max=100),
    CropStageDefinition(name="Tillering", gdd_min=100, gdd_max=400),
    CropStageDefinition(name="Flowering", gdd_min=400, gdd_max=800),
    CropStageDefinition(name="Maturity", gdd_min=800, gdd_max=1200),
]

RICE_STAGES = [
    CropStageDefinition(name="Germination", gdd_min=0, gdd_max=120),
    CropStageDefinition(name="Vegetative", gdd_min=120, gdd_max=500),
    CropStageDefinition(name="Flowering", gdd_min=500, gdd_max=900),
    CropStageDefinition(name="Maturity", gdd_min=900, gdd_max=1300),
]


def test_gdd_below_base_returns_zero() -> None:
    assert calculate_daily_gdd(t_min=5, t_max=12, base_temp=10) == 0.0


def test_gdd_above_base() -> None:
    assert calculate_daily_gdd(t_min=20, t_max=30, base_temp=10) == 15.0


def test_accumulate_gdd_respects_sowing_date() -> None:
    entries = [
        (date(2026, 5, 1), 5.0),
        (date(2026, 5, 2), 8.0),
        (date(2026, 5, 3), 3.0),
    ]
    total = accumulate_gdd(entries, date(2026, 5, 2))
    assert total == 11.0


def test_different_crop_types_resolve_different_stages() -> None:
    wheat_stage, _, _ = resolve_growth_stage(250, WHEAT_STAGES)
    rice_stage, _, _ = resolve_growth_stage(250, RICE_STAGES)
    assert wheat_stage == "Tillering"
    assert rice_stage == "Vegetative"
