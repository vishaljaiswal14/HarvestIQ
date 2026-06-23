from typing import Final, Tuple

FSI_WEIGHTS: Final[Tuple[float, float, float]] = (0.40, 0.35, 0.25)

TEMP_OPTIMAL_C: Final[float] = 32.0
TEMP_CRITICAL_C: Final[float] = 42.0

EXPECTED_DAILY_RAINFALL_MM: Final[float] = 5.0
RAINFALL_WINDOW_DAYS: Final[int] = 3

DEFAULT_STAGE_VULNERABILITY: Final[float] = 0.50

CLASSIFICATION_LOW: Final[str] = "LOW_STRESS"
CLASSIFICATION_MEDIUM: Final[str] = "MEDIUM_STRESS"
CLASSIFICATION_HIGH: Final[str] = "HIGH_STRESS"

LOW_STRESS_MAX: Final[float] = 0.33
MEDIUM_STRESS_MAX: Final[float] = 0.66

STRESS_LOG_FSI_DELTA_THRESHOLD: Final[float] = 0.05
