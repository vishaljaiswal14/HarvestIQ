from app.services.explainability_service import build_alert_explanation, build_fsi_explanation


def test_fsi_explanation_contains_summary_and_inputs() -> None:
    explanation = build_fsi_explanation(
        fsi=0.72,
        classification="HIGH_STRESS",
        primary_factor="THERMAL",
        inputs={"current_temp": 41.2, "temp_stress": 0.85},
    )
    assert "0.72" in explanation["summary"]
    assert explanation["primary_factor"] == "THERMAL"
    assert explanation["inputs"]["current_temp"] == 41.2


def test_alert_explanation_is_deterministic() -> None:
    explanation = build_alert_explanation(
        rule_id="RULE_THERMAL_HIGH",
        primary_factor="THERMAL",
        inputs={"current_temp": 41.2, "threshold": 38.0},
        message="Current temperature 41.2°C exceeds safe limit of 38.0°C.",
    )
    assert "RULE_THERMAL_HIGH" in explanation["summary"]
    assert explanation["inputs"]["threshold"] == 38.0
