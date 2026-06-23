from app.core.constants.fsi import (
    CLASSIFICATION_HIGH,
    CLASSIFICATION_LOW,
    CLASSIFICATION_MEDIUM,
)
from app.services.deterministic_engine import (
    calculate_gdd_scale,
    calculate_rainfall_deficit,
    calculate_temp_stress,
    classify_fsi,
    compute_fsi,
    resolve_primary_factor,
)


def test_temp_stress_below_optimal_is_zero() -> None:
    assert calculate_temp_stress(30.0, [28.0, 29.0, 31.0]) == 0.0


def test_temp_stress_at_critical_is_one() -> None:
    assert calculate_temp_stress(42.0, [42.0, 41.0, 40.0]) == 1.0


def test_temp_stress_uses_forecast_max() -> None:
    stress = calculate_temp_stress(30.0, [45.0, 32.0, 31.0])
    assert stress > 0.9


def test_rainfall_deficit_no_rain_is_one() -> None:
    assert calculate_rainfall_deficit([0.0, 0.0, 0.0]) == 1.0


def test_rainfall_deficit_meets_expected_is_zero() -> None:
    assert calculate_rainfall_deficit([5.0, 5.0, 5.0]) == 0.0


def test_gdd_scale_clamped() -> None:
    assert calculate_gdd_scale(200.0, 400.0, 0.60) == 0.3


def test_compute_fsi_weighted_sum() -> None:
    fsi = compute_fsi(1.0, 0.0, 0.0)
    assert fsi == 0.4


def test_classify_fsi_boundaries() -> None:
    assert classify_fsi(0.33) == CLASSIFICATION_LOW
    assert classify_fsi(0.34) == CLASSIFICATION_MEDIUM
    assert classify_fsi(0.66) == CLASSIFICATION_MEDIUM
    assert classify_fsi(0.67) == CLASSIFICATION_HIGH


def test_resolve_primary_factor_thermal() -> None:
    assert resolve_primary_factor(1.0, 0.0, 0.0) == "THERMAL"


def test_resolve_primary_factor_moisture() -> None:
    assert resolve_primary_factor(0.0, 1.0, 0.0) == "MOISTURE"


def test_high_temp_produces_high_fsi() -> None:
    temp_stress = calculate_temp_stress(41.0, [41.0, 40.0, 39.0])
    rainfall_deficit = calculate_rainfall_deficit([0.0, 0.0, 0.0])
    gdd_scale = calculate_gdd_scale(200.0, 400.0, 0.60)
    fsi = compute_fsi(temp_stress, rainfall_deficit, gdd_scale)
    assert fsi >= 0.67
    assert classify_fsi(fsi) == CLASSIFICATION_HIGH
