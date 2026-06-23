from typing import Final

RISK_BAND_LOW: Final[str] = "LOW"
RISK_BAND_MEDIUM: Final[str] = "MEDIUM"
RISK_BAND_HIGH: Final[str] = "HIGH"

LOW_RISK_MAX: Final[float] = 33.0
MEDIUM_RISK_MAX: Final[float] = 66.0

DISEASE_LOOKBACK_DAYS: Final[int] = 30

WEIGHT_FSI: Final[float] = 0.30
WEIGHT_MOMENTUM: Final[float] = 0.15
WEIGHT_STAGE: Final[float] = 0.15
WEIGHT_SOIL: Final[float] = 0.20
WEIGHT_DISEASE: Final[float] = 0.20
