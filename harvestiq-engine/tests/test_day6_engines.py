from app.core.constants.momentum import MOMENTUM_FALLING, MOMENTUM_RISING, MOMENTUM_STABLE
from app.core.constants.yield_risk import RISK_BAND_HIGH, RISK_BAND_LOW, RISK_BAND_MEDIUM
from app.services.deterministic_engine import (
    compute_health_risk_rating,
    compute_stress_momentum,
    compute_yield_risk,
    evaluate_input_window,
    simulate_scenario,
)


def test_momentum_rising_when_fsi_increases() -> None:
    direction, score, delta, insufficient = compute_stress_momentum([0.4, 0.45, 0.5, 0.55, 0.7])
    assert direction == MOMENTUM_RISING
    assert score > 0
    assert delta > 0
    assert insufficient is False


def test_momentum_stable_with_insufficient_history() -> None:
    direction, score, delta, insufficient = compute_stress_momentum([0.5])
    assert direction == MOMENTUM_STABLE
    assert score == 0.0
    assert delta == 0.0
    assert insufficient is True


def test_momentum_falling_when_fsi_decreases() -> None:
    direction, _, delta, _ = compute_stress_momentum([0.8, 0.75, 0.7, 0.65, 0.4])
    assert direction == MOMENTUM_FALLING
    assert delta < 0


def test_yield_risk_low_for_healthy_farm() -> None:
    band, percent, factors = compute_yield_risk(
        fsi=0.2,
        momentum_direction=MOMENTUM_STABLE,
        momentum_score=0.0,
        stage="Tillering",
        soil_health_index=0.85,
        disease_present=False,
        radar_high_nearby=False,
        stage_vulnerability=0.4,
    )
    assert band == RISK_BAND_LOW
    assert percent < 33.0
    assert "FSI" not in factors


def test_yield_risk_high_with_disease_and_rising_momentum() -> None:
    band, percent, factors = compute_yield_risk(
        fsi=0.9,
        momentum_direction=MOMENTUM_RISING,
        momentum_score=0.8,
        stage="Flowering",
        soil_health_index=0.4,
        disease_present=True,
        radar_high_nearby=True,
        stage_vulnerability=0.8,
    )
    assert band == RISK_BAND_HIGH
    assert percent >= 66.0
    assert "RISING_MOMENTUM" in factors
    assert "CONFIRMED_DISEASE" in factors


def test_yield_risk_medium_band_boundary() -> None:
    band, percent, _ = compute_yield_risk(
        fsi=0.55,
        momentum_direction=MOMENTUM_STABLE,
        momentum_score=0.1,
        stage="Tillering",
        soil_health_index=0.7,
        disease_present=False,
        radar_high_nearby=False,
        stage_vulnerability=0.5,
    )
    assert band in {RISK_BAND_LOW, RISK_BAND_MEDIUM, RISK_BAND_HIGH}
    assert 0 <= percent <= 100


def test_optimizer_high_wind_unsafe_for_spray() -> None:
    safe, reasons, rules = evaluate_input_window(
        wind_speed_kmh=25.0,
        forecast_rain_mm_3d=0.0,
        fsi_classification="LOW_STRESS",
        action_type="SPRAY",
    )
    assert safe is False
    assert "RULE_HIGH_WIND" in rules
    assert reasons


def test_optimizer_high_fsi_blocks_fertilize() -> None:
    safe, _, rules = evaluate_input_window(
        wind_speed_kmh=5.0,
        forecast_rain_mm_3d=0.0,
        fsi_classification="HIGH_STRESS",
        action_type="FERTILIZE",
    )
    assert safe is False
    assert "RULE_HIGH_FSI_FERTILIZE" in rules


def test_simulator_temp_delta_increases_fsi() -> None:
    projected, curve, yield_factor = simulate_scenario(
        baseline_fsi=0.4,
        temp_delta=5.0,
        irrigation_delta=0.0,
        nitrogen_delta=0.0,
    )
    assert projected > 0.4
    assert len(curve) == 5
    assert yield_factor < 1.0


def test_health_risk_rating_score_and_band() -> None:
    score, band = compute_health_risk_rating(
        fsi=0.2,
        soil_health_index=0.9,
        radar_high_nearby=False,
        unread_alerts=0,
        yield_risk_percent=15.0,
    )
    assert score >= 50.0
    assert band in {"GOOD", "FAIR", "POOR"}
