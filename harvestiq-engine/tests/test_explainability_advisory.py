from app.services.explainability_service import build_advisory_explanation


def test_build_advisory_explanation_includes_rules_and_sources() -> None:
    result = build_advisory_explanation(
        primary_factor="THERMAL",
        inputs={"fsi": 0.82, "snapshot_version": "v1"},
        triggered_rules=["RULE_THERMAL_HIGH"],
        rag_sources=["icar-wheat-heat-stress-rajasthan"],
        mitigation_locked=True,
        nearby_outbreaks=["WHEAT_RUST@4.2km (HIGH)"],
    )

    assert result["primary_factor"] == "THERMAL"
    assert result["inputs"]["triggered_rules"] == ["RULE_THERMAL_HIGH"]
    assert result["inputs"]["mitigation_locked"] is True
    assert "locked" in result["summary"].lower()
