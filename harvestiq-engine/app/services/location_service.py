import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.core.constants.weather import LocationSource
from app.core.exceptions import unprocessable_entity

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "india_district_centroids.json"


def _normalize_key(value: str) -> str:
    return " ".join(value.strip().upper().split())


@lru_cache
def _load_centroids() -> dict[str, dict[str, dict[str, float]]]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def lookup_district_centroid(state: str, district: str) -> dict[str, Any]:
    centroids = _load_centroids()
    state_key = _normalize_key(state)
    district_key = _normalize_key(district)

    state_data = centroids.get(state_key)
    if state_data is None:
        raise unprocessable_entity(
            f"Farm location missing: no centroid data for state '{state}'"
        )

    centroid = state_data.get(district_key)
    if centroid is None:
        raise unprocessable_entity(
            f"Farm location missing: no centroid data for district '{district}' in '{state}'"
        )

    return {
        "location": {
            "type": "Point",
            "coordinates": [centroid["longitude"], centroid["latitude"]],
        },
        "location_source": LocationSource.DISTRICT_CENTROID.value,
    }


def build_farm_location(
    state: str,
    district: str,
    existing_location: Optional[dict] = None,
) -> dict[str, Any]:
    if existing_location and existing_location.get("coordinates"):
        return {
            "location": existing_location,
            "location_source": LocationSource.DISTRICT_CENTROID.value,
        }
    return lookup_district_centroid(state, district)
