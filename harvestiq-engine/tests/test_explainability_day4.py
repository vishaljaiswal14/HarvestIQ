from app.services.explainability_service import build_disease_explanation, build_soil_explanation


def test_soil_explanation_is_deterministic() -> None:
    explanation = build_soil_explanation(
        soil_health_index=0.72,
        primary_factor="NITROGEN",
        inputs={"nitrogen": 120, "crop_type": "WHEAT"},
        deficiency_status={"nitrogen": "LOW", "phosphorus": "OPTIMAL"},
    )
    assert "0.72" in explanation["summary"]
    assert explanation["primary_factor"] == "NITROGEN"
    assert explanation["inputs"]["nitrogen"] == 120


def test_disease_explanation_is_deterministic() -> None:
    explanation = build_disease_explanation(
        disease="WHEAT_RUST",
        confidence=0.92,
        deterministic_status="CONFIRMED",
        primary_factor="DISEASE",
        inputs={"crop_type": "WHEAT", "state": "Rajasthan"},
    )
    assert "WHEAT_RUST" in explanation["summary"]
    assert explanation["primary_factor"] == "DISEASE"
