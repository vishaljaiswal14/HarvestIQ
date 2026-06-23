from app.models.day6_schemas import StressMomentumResult, YieldRiskResult
from app.services.deterministic_engine import compute_yield_risk


class YieldRiskService:
    @staticmethod
    def compute(
        fsi: float,
        momentum: StressMomentumResult,
        stage: str,
        soil_health_index: float | None,
        disease_present: bool,
        radar_high_nearby: bool,
        stage_vulnerability: float = 0.5,
    ) -> YieldRiskResult:
        band, percent, factors = compute_yield_risk(
            fsi=fsi,
            momentum_direction=momentum.direction,
            momentum_score=momentum.momentum_score,
            stage=stage,
            soil_health_index=soil_health_index,
            disease_present=disease_present,
            radar_high_nearby=radar_high_nearby,
            stage_vulnerability=stage_vulnerability,
        )
        return YieldRiskResult(
            risk_band=band,
            estimated_risk_percent=percent,
            contributing_factors=factors,
        )
