from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.advisory import INTELLIGENCE_SNAPSHOT_VERSION
from app.core.config import get_settings
from app.core.exceptions import unprocessable_entity
from app.models.day6_schemas import SimulatorHypothesis, SimulatorRequest, SimulatorResponse, SimulatorSnapshot
from app.models.engine_schemas import ExplanationPayload
from app.services.context_compiler_service import ContextCompilerService
from app.services.explainability_service import build_simulation_explanation


class SimulatorService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.context_compiler = ContextCompilerService(db)
        self.settings = get_settings()

    async def run(self, user_id: str, payload: SimulatorRequest) -> SimulatorResponse:
        if abs(payload.temp_delta) > self.settings.simulator_max_temp_delta:
            raise unprocessable_entity(
                f"temp_delta must be within ±{self.settings.simulator_max_temp_delta}°C"
            )

        hypothesis = SimulatorHypothesis(
            temp_delta=payload.temp_delta,
            irrigation_delta=payload.irrigation_delta,
            nitrogen_delta=payload.nitrogen_delta,
        )
        snapshots = await self.context_compiler.compile_simulator_snapshots(
            user_id,
            payload.farm_id,
            hypothesis,
        )

        explanation_dict = build_simulation_explanation(
            baseline_fsi=snapshots.baseline_fsi,
            projected_fsi=snapshots.projected_fsi,
            inputs=snapshots.explainability_inputs,
        )

        return SimulatorResponse(
            farm_id=payload.farm_id,
            baseline=SimulatorSnapshot(
                fsi=snapshots.baseline_fsi,
                stress_momentum=snapshots.baseline_momentum,
                yield_risk=snapshots.baseline_yield_risk,
                fsi_curve=[snapshots.baseline_fsi],
                yield_factor=round(1.0 - snapshots.baseline_fsi * 0.5, 4),
            ),
            projected=SimulatorSnapshot(
                fsi=snapshots.projected_fsi,
                stress_momentum=snapshots.projected_momentum,
                yield_risk=snapshots.projected_yield_risk,
                fsi_curve=snapshots.fsi_curve,
                yield_factor=snapshots.yield_factor,
            ),
            explanation=ExplanationPayload(**explanation_dict),
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
        )
