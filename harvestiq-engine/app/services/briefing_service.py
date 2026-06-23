from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.constants.advisory import INTELLIGENCE_SNAPSHOT_VERSION
from app.core.exceptions import bad_gateway
from app.integrations.gemini_client import OpenRouterClient
from app.models.day6_schemas import BriefingResponse, BriefingSections
from app.models.engine_schemas import ExplanationPayload
from app.services.context_compiler_service import ContextCompilerService


class BriefingService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        gemini_client: Optional[OpenRouterClient] = None,
    ) -> None:
        self.db = db
        self.gemini_client = gemini_client or OpenRouterClient()
        self.context_compiler = ContextCompilerService(db)
        self.settings = get_settings()

    async def get_daily_briefing(
        self,
        user_id: str,
        farm_id: str,
        language: str,
        source: str = "ON_DEMAND",
        force_regenerate: bool = False,
    ) -> BriefingResponse:
        if not force_regenerate:
            cached = await self._get_todays_briefing(user_id, farm_id, language=language)
            if cached is not None:
                return cached

        compiled = await self.context_compiler.compile_briefing_context(user_id, farm_id, language=language)
        synthesis = await self._synthesize(compiled.context_package, language, compiled.mitigation_locked)

        now = datetime.now(timezone.utc)
        doc = {
            "user_id": ObjectId(user_id),
            "farm_id": ObjectId(farm_id),
            "language": language,
            "context_package": compiled.context_package,
            "context_hash": compiled.context_hash,
            "synthesis": synthesis,
            "structured_sections": compiled.sections,
            "intelligence_snapshot_version": compiled.intelligence_snapshot_version,
            "generated_at": now,
            "source": source,
        }
        result = await self.db.briefing_logs.insert_one(doc)

        return BriefingResponse(
            briefing_id=str(result.inserted_id),
            farm_id=farm_id,
            synthesis=synthesis,
            language=language,
            sections=BriefingSections(**compiled.sections),
            explainability=ExplanationPayload(**compiled.explainability),
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
            generated_at=now,
            source=source,
        )

    async def _get_todays_briefing(self, user_id: str, farm_id: str, language: str) -> BriefingResponse | None:
        start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        doc = await self.db.briefing_logs.find_one(
            {
                "user_id": ObjectId(user_id),
                "farm_id": ObjectId(farm_id),
                "language": language,
                "generated_at": {"$gte": start_of_day},
            },
            sort=[("generated_at", -1)],
        )
        if doc is None:
            return None
        return BriefingResponse(
            briefing_id=str(doc["_id"]),
            farm_id=farm_id,
            synthesis=doc["synthesis"],
            language=doc.get("language", "hi"),
            sections=BriefingSections(**doc.get("structured_sections", {})),
            explainability=ExplanationPayload(
                summary="Daily briefing from cached log.",
                inputs=doc.get("structured_sections", {}),
                primary_factor="BRIEFING",
            ),
            intelligence_snapshot_version=doc.get(
                "intelligence_snapshot_version",
                INTELLIGENCE_SNAPSHOT_VERSION,
            ),
            generated_at=doc["generated_at"],
            source=doc.get("source", "ON_DEMAND"),
        )

    async def _synthesize(
        self,
        context_package: str,
        language: str,
        mitigation_locked: bool,
    ) -> str:
        if not self.gemini_client.api_key:
            return self._template_fallback(context_package, language)

        try:
            return await self.gemini_client.synthesize_advisory(
                context_package=context_package,
                language=language,
                mitigation_locked=mitigation_locked,
                briefing_mode=True,
            )
        except Exception as exc:
            if self.settings.environment == "development":
                return self._template_fallback(context_package, language)
            raise bad_gateway(f"Briefing synthesis unavailable: {exc}") from exc

    @staticmethod
    def _template_fallback(context_package: str, language: str = "en") -> str:
        lines = [line.strip() for line in context_package.splitlines() if line.strip().startswith("-")]
        preview = " ".join(lines[:6])
        if language == "hi":
            return f"सुबह की ब्रीफिंग (Morning briefing - deterministic): {preview}"
        return f"Morning briefing (deterministic): {preview}"

    async def get_latest_precompiled_briefing(
        self,
        user_id: str,
        farm_id: str,
    ) -> BriefingResponse:
        from app.services.farm_access_service import get_owned_farm
        await get_owned_farm(self.db, farm_id, user_id)

        doc = await self.db.briefing_logs.find_one(
            {
                "user_id": ObjectId(user_id),
                "farm_id": ObjectId(farm_id),
            },
            sort=[("generated_at", -1)],
        )
        if doc is None:
            from app.core.exceptions import unprocessable_entity
            raise unprocessable_entity("No pre-compiled briefing log found for this farm. Run the briefing worker first.")

        return BriefingResponse(
            briefing_id=str(doc["_id"]),
            farm_id=farm_id,
            synthesis=doc["synthesis"],
            language=doc.get("language", "hi"),
            sections=BriefingSections(**doc.get("structured_sections", {})),
            explainability=ExplanationPayload(
                summary="Daily briefing from pre-compiled log.",
                inputs=doc.get("structured_sections", {}),
                primary_factor="BRIEFING",
            ),
            intelligence_snapshot_version=doc.get(
                "intelligence_snapshot_version",
                INTELLIGENCE_SNAPSHOT_VERSION,
            ),
            generated_at=doc["generated_at"],
            source=doc.get("source", "WORKER"),
        )

