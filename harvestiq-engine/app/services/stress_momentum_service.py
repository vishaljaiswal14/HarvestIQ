from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.momentum import MOMENTUM_MAX_LOGS, MOMENTUM_WINDOW_DAYS
from app.models.day6_schemas import StressMomentumResult
from app.services.deterministic_engine import compute_stress_momentum


class StressMomentumService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def compute_for_farm(
        self,
        farm_id: str,
        projected_fsi: float | None = None,
    ) -> StressMomentumResult:
        window_start = datetime.now(timezone.utc) - timedelta(days=MOMENTUM_WINDOW_DAYS)
        cursor = self.db.stress_logs.find(
            {"farm_id": ObjectId(farm_id), "calculated_at": {"$gte": window_start}},
        ).sort("calculated_at", 1).limit(MOMENTUM_MAX_LOGS)

        scores: list[float] = []
        async for log in cursor:
            scores.append(float(log.get("fsi_score", 0.0)))

        if len(scores) < MOMENTUM_MAX_LOGS:
            cursor_all = self.db.stress_logs.find(
                {"farm_id": ObjectId(farm_id)},
            ).sort("calculated_at", 1).limit(MOMENTUM_MAX_LOGS)
            scores = [float(log["fsi_score"]) async for log in cursor_all]

        if projected_fsi is not None:
            scores = (scores + [projected_fsi])[-(MOMENTUM_MAX_LOGS + 1) :]

        direction, momentum_score, delta, insufficient = compute_stress_momentum(scores)
        return StressMomentumResult(
            direction=direction,
            momentum_score=momentum_score,
            fsi_delta=delta,
            insufficient_history=insufficient,
            window_days=MOMENTUM_WINDOW_DAYS,
        )
