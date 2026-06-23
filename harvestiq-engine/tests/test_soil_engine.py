from app.core.constants.soil import NUTRIENT_HIGH, NUTRIENT_LOW, NUTRIENT_OPTIMAL
from app.services.deterministic_engine import (
    compute_soil_health_index,
    evaluate_nutrient_status,
)

WHEAT_RANGES = {
    "nitrogen": {"low": 200, "high": 400},
    "phosphorus": {"low": 12, "high": 25},
    "potassium": {"low": 150, "high": 300},
    "ph": {"low": 6.0, "high": 7.5},
    "organic_carbon": {"low": 0.40, "high": 0.75},
    "electrical_conductivity": {"low": 0.2, "high": 1.5},
}


def test_evaluate_nutrient_low() -> None:
    assert evaluate_nutrient_status(100, 200, 400) == NUTRIENT_LOW


def test_evaluate_nutrient_optimal() -> None:
    assert evaluate_nutrient_status(250, 200, 400) == NUTRIENT_OPTIMAL


def test_evaluate_nutrient_high() -> None:
    assert evaluate_nutrient_status(450, 200, 400) == NUTRIENT_HIGH


def test_soil_health_index_optimal_profile() -> None:
    measurements = {
        "nitrogen": 300,
        "phosphorus": 18,
        "potassium": 220,
        "ph": 6.8,
        "organic_carbon": 0.55,
        "electrical_conductivity": 0.8,
    }
    shi, status, _scores = compute_soil_health_index(measurements, WHEAT_RANGES)
    assert shi >= 0.95
    assert all(value == NUTRIENT_OPTIMAL for value in status.values())


def test_soil_health_index_low_nitrogen_reduces_score() -> None:
    measurements = {
        "nitrogen": 80,
        "phosphorus": 18,
        "potassium": 220,
        "ph": 6.8,
        "organic_carbon": 0.55,
        "electrical_conductivity": 0.8,
    }
    shi, status, _scores = compute_soil_health_index(measurements, WHEAT_RANGES)
    assert status["nitrogen"] == NUTRIENT_LOW
    assert shi < 0.9
