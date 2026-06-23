from typing import Final

NUTRIENT_LOW: Final[str] = "LOW"
NUTRIENT_OPTIMAL: Final[str] = "OPTIMAL"
NUTRIENT_HIGH: Final[str] = "HIGH"

NUTRIENT_KEYS: Final[tuple[str, ...]] = (
    "nitrogen",
    "phosphorus",
    "potassium",
    "ph",
    "organic_carbon",
    "electrical_conductivity",
)

SOIL_HEALTH_WEIGHTS: Final[dict[str, float]] = {
    "nitrogen": 0.25,
    "phosphorus": 0.20,
    "potassium": 0.20,
    "ph": 0.15,
    "organic_carbon": 0.12,
    "electrical_conductivity": 0.08,
}
