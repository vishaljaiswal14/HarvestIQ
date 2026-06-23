from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.day6_schemas import HealthCardResponse
from app.models.engine_schemas import ExplanationPayload
from app.services.context_compiler_service import ContextCompilerService


LOCALIZED_BANDS = {
    "en": {
        "FAIR": "FAIR",
        "POOR": "POOR",
        "EXCELLENT": "EXCELLENT",
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
    },
    "hi": {
        "FAIR": "सामान्य",
        "POOR": "खराब",
        "EXCELLENT": "उत्कृष्ट",
        "LOW": "कम",
        "MEDIUM": "मध्यम",
        "HIGH": "उच्च",
    }
}


class HealthCardService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.context_compiler = ContextCompilerService(db)

    async def get_health_card(self, user_id: str, farm_id: str, language: str = "en") -> HealthCardResponse:
        snapshot = await self.context_compiler.compile_health_snapshot(user_id, farm_id, language=language)
        core = snapshot.core
        
        lang = language.lower() if language.lower() in LOCALIZED_BANDS else "en"
        band_dict = LOCALIZED_BANDS[lang]
        
        hb = band_dict.get(snapshot.health_band, snapshot.health_band)
        rb = band_dict.get(core.yield_risk.risk_band, core.yield_risk.risk_band)
        
        if lang == "hi":
            summary = (
                f"खेत का स्वास्थ्य {hb} (अंक={snapshot.health_score}) है। "
                f"उत्पादन जोखिम {rb} पर {core.yield_risk.estimated_risk_percent}% है।"
            )
        else:
            summary = (
                f"Farm health is {hb} "
                f"(score={snapshot.health_score}). "
                f"Yield risk {rb} "
                f"at {core.yield_risk.estimated_risk_percent}%."
            )

        return HealthCardResponse(
            farm_id=farm_id,
            crop_type=core.crop_type,
            stage=core.stage,
            fsi=core.fsi,
            fsi_classification=core.fsi_classification,
            soil_health_index=core.soil_health_index,
            stress_momentum=core.stress_momentum,
            yield_risk=core.yield_risk,
            health_score=snapshot.health_score,
            health_band=hb,
            nearby_radar_high_count=snapshot.nearby_radar_high_count,
            unread_alerts=snapshot.unread_alerts,
            intelligence_snapshot_version=snapshot.intelligence_snapshot_version,
            explanation=ExplanationPayload(
                summary=summary,
                inputs={
                    "health_score": snapshot.health_score,
                    "health_band": snapshot.health_band,
                    "fsi": core.fsi,
                    "stress_momentum": core.stress_momentum.model_dump(),
                    "yield_risk": core.yield_risk.model_dump(),
                },
                primary_factor=core.primary_factor,
            ),
            cycle_status=core.cycle_status,
        )
