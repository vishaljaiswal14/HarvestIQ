from typing import Final

INTELLIGENCE_SNAPSHOT_VERSION: Final[str] = "v3"

ADVISORY_RATE_LIMIT: Final[str] = "60/hour"

FSI_MITIGATION_LOCK_CLASSIFICATION: Final[str] = "HIGH_STRESS"

TOPIC_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "HEAT_STRESS": ("heat", "temperature", "thermal", "stress", "hot", "drought"),
    "FERTILIZER": ("fertilizer", "fertiliser", "npk", "nitrogen", "phosphorus", "potassium", "nutrient"),
    "DISEASE_MANAGEMENT": ("disease", "pathogen", "fungus", "blight", "rust", "mildew", "infection"),
    "PEST_CONTROL": ("pest", "insect", "aphid", "borer", "spray", "pesticide"),
}
