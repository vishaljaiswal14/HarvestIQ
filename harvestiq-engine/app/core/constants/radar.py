from typing import Final

RADAR_GRID_RESOLUTION: Final[float] = 0.05
RADAR_WINDOW_HOURS: Final[int] = 72
RADAR_DEFAULT_RADIUS_KM: Final[float] = 25.0
RADAR_MIN_CASES_MEDIUM: Final[int] = 3
RADAR_MIN_CASES_HIGH: Final[int] = 6

RISK_LEVEL_LOW: Final[str] = "LOW"
RISK_LEVEL_MEDIUM: Final[str] = "MEDIUM"
RISK_LEVEL_HIGH: Final[str] = "HIGH"

MAX_AUDIO_BYTES: Final[int] = 10 * 1024 * 1024
ALLOWED_AUDIO_TYPES: Final[frozenset[str]] = frozenset(
    {"audio/webm", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/ogg"}
)
