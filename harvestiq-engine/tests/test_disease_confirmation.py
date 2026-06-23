from app.core.constants.disease import (
    DISEASE_STATUS_HIGH_CONFIDENCE,
    DISEASE_STATUS_LOW_CONFIDENCE,
    DISEASE_STATUS_REJECTED,
    DISEASE_STATUS_UNKNOWN,
)
from app.services.deterministic_engine import confirm_disease_detection, normalize_disease_tag

ALLOWLIST = {
    "WHEAT": {
        "RAJASTHAN": ["WHEAT_RUST", "POWDERY_MILDEW"],
        "ALL": ["LEAF_BLIGHT"],
    }
}


def test_normalize_disease_tag() -> None:
    assert normalize_disease_tag("Wheat Rust") == "WHEAT_RUST"


def test_low_confidence_status() -> None:
    disease, status = confirm_disease_detection(
        "WHEAT",
        "Rajasthan",
        "Wheat Rust",
        0.55,
        0.70,
        ALLOWLIST,
    )
    assert disease == "WHEAT_RUST"
    assert status == DISEASE_STATUS_LOW_CONFIDENCE


def test_confirmed_for_allowed_region() -> None:
    disease, status = confirm_disease_detection(
        "WHEAT",
        "Rajasthan",
        "WHEAT_RUST",
        0.91,
        0.70,
        ALLOWLIST,
    )
    assert disease == "WHEAT_RUST"
    assert status == DISEASE_STATUS_HIGH_CONFIDENCE


def test_rejected_for_unknown_disease() -> None:
    # Use confidence below the 0.80 high-confidence approval threshold
    # but above the base threshold (0.70) to test regional rejection
    disease, status = confirm_disease_detection(
        "WHEAT",
        "Rajasthan",
        "UNKNOWN_PATHOGEN",
        0.75,
        0.70,
        ALLOWLIST,
    )
    assert disease == "UNKNOWN"
    assert status == DISEASE_STATUS_UNKNOWN


def test_disease_tag_normalization_aliases() -> None:
    aliases = [
        "YELLOW_RUST",
        "STRIPE_RUST",
        "WHEAT_YELLOW_RUST",
        "WHEAT_STRIPE_RUST",
        "RUST_OF_WHEAT",
        "YELLOW_RUST_OF_WHEAT",
        "STRIPE_RUST_OF_WHEAT",
        "WHEAT_RUSTS",
    ]
    for alias in aliases:
        assert normalize_disease_tag(alias) == "WHEAT_RUST"
        assert normalize_disease_tag(alias.lower()) == "WHEAT_RUST"
        assert normalize_disease_tag(alias.replace("_", " ")) == "WHEAT_RUST"


def test_generic_rust_mapping_for_wheat() -> None:
    # If crop is wheat, RUST normalizes to WHEAT_RUST
    disease, status = confirm_disease_detection(
        "WHEAT",
        "Rajasthan",
        "RUST",
        0.91,
        0.70,
        ALLOWLIST,
    )
    assert disease == "WHEAT_RUST"
    assert status == DISEASE_STATUS_HIGH_CONFIDENCE

    # If crop is soybean, generic RUST is kept as RUST (so it does not mismatch allowed checks for soybean)
    soybean_allowlist = {
        "SOYBEAN": {
            "RAJASTHAN": ["RUST", "YELLOW_MOSAIC"],
            "ALL": ["RUST"]
        }
    }
    disease, status = confirm_disease_detection(
        "SOYBEAN",
        "Rajasthan",
        "RUST",
        0.91,
        0.70,
        soybean_allowlist,
    )
    assert disease == "RUST"
    assert status == DISEASE_STATUS_HIGH_CONFIDENCE

