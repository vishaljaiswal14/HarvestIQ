from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.day7_schemas import VerificationLogResponse


class VerificationLogService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def record(
        self,
        event_type: str,
        environment: str,
        status: str,
        details: dict | None = None,
    ) -> VerificationLogResponse:
        now = datetime.now(timezone.utc)
        doc = {
            "event_type": event_type,
            "environment": environment,
            "status": status,
            "details": details or {},
            "recorded_at": now,
        }
        result = await self.db.verification_logs.insert_one(doc)
        return VerificationLogResponse(
            log_id=str(result.inserted_id),
            event_type=event_type,
            status=status,
            recorded_at=now,
        )
