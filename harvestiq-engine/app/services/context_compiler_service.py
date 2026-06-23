import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants.advisory import (
    FSI_MITIGATION_LOCK_CLASSIFICATION,
    INTELLIGENCE_SNAPSHOT_VERSION,
    TOPIC_KEYWORDS,
)
from app.core.constants.disease import DISEASE_STATUS_CONFIRMED
from app.core.constants.knowledge import normalize_topic
from app.core.constants.yield_risk import DISEASE_LOOKBACK_DAYS
from app.models.day4_schemas import HybridSearchParams
from app.models.day5_schemas import AdvisoryCitation, CompiledContextResult
from app.models.day6_schemas import (
    CoreIntelligence,
    SimulatorHypothesis,
    StressMomentumResult,
    YieldRiskResult,
)
from app.services.deterministic_engine import compute_health_risk_rating, simulate_scenario
from app.services.disease_radar_service import DiseaseRadarService
from app.services.explainability_service import (
    build_advisory_explanation,
    build_briefing_explanation,
    build_momentum_explanation,
    build_yield_risk_explanation,
)
from app.services.input_window_optimizer_service import InputWindowOptimizerService
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.rag_service import RagService
from app.services.scheme_eligibility_service import SchemeEligibilityService
from app.services.stress_index_service import StressIndexService
from app.services.stress_momentum_service import StressMomentumService
from app.services.yield_risk_service import YieldRiskService


@dataclass
class BriefingCompiledResult:
    context_package: str
    context_hash: str
    sections: dict[str, Any]
    explainability: dict[str, Any]
    mitigation_locked: bool
    intelligence_snapshot_version: str


@dataclass
class HealthCompiledResult:
    core: CoreIntelligence
    health_score: float
    health_band: str
    nearby_radar_high_count: int
    unread_alerts: int
    explainability: dict[str, Any]
    intelligence_snapshot_version: str


@dataclass
class SimulatorCompiledSnapshots:
    baseline_fsi: float
    projected_fsi: float
    baseline_momentum: StressMomentumResult
    projected_momentum: StressMomentumResult
    baseline_yield_risk: YieldRiskResult
    projected_yield_risk: YieldRiskResult
    fsi_curve: list[float]
    yield_factor: float
    explainability_inputs: dict[str, Any]


LOCALIZED_LITERALS = {
    "en": {
        "no_unread_alerts": "No unread alerts.",
        "no_soil_records": "No soil records available.",
        "no_disease_reports": "No disease reports for this farm.",
        "no_nearby_disease": "No nearby disease hotspots in radar.",
        "market_data_unavailable": "Market data unavailable.",
    },
    "hi": {
        "no_unread_alerts": "कोई बिना पढ़ी हुई चेतावनी नहीं।",
        "no_soil_records": "कोई मिट्टी का रिकॉर्ड उपलब्ध नहीं है।",
        "no_disease_reports": "इस खेत के लिए कोई बीमारी की रिपोर्ट नहीं है।",
        "no_nearby_disease": "रडार में आस-पास कोई बीमारी का हॉटस्पॉट नहीं है।",
        "market_data_unavailable": "बाज़ार का डेटा अनुपलब्ध है।",
    }
}


class ContextCompilerService:
    """Single source of truth for advisory and Day 6 intelligence context assembly."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.stress_service = StressIndexService(db)
        self.rag_service = RagService(db)
        self.radar_service = DiseaseRadarService(db)
        self.momentum_service = StressMomentumService(db)
        self.yield_risk_service = YieldRiskService()
        self.optimizer_service = InputWindowOptimizerService(db)
        self.market_service = MarketIntelligenceService(db)
        self.scheme_service = SchemeEligibilityService(db)

    def _localize_core_intelligence(self, core: Any, language: str) -> Any:
        lang = str(language).strip().lower()
        if lang != "hi":
            return core

        CROP_MAP = {"WHEAT": "गेहूं", "PADDY": "धान", "MAIZE": "मक्का"}
        STAGE_MAP = {"Tillering": "टिलरिंग (कल्ले निकलना)", "Flowering": "फूल आने की अवस्था", "V3": "वी3 अवस्था"}
        CLASSIFICATION_MAP = {
            "NO_STRESS": "कोई तनाव नहीं",
            "LOW_STRESS": "कम तनाव",
            "MEDIUM_STRESS": "मध्यम तनाव",
            "HIGH_STRESS": "उच्च तनाव",
        }
        DIRECTION_MAP = {
            "STABLE": "स्थिर",
            "RISING": "बढ़ रहा है",
            "FALLING": "गिर रहा है",
        }
        BAND_MAP = {
            "MINIMAL": "न्यूनतम",
            "LOW": "कम",
            "MEDIUM": "मध्यम",
            "HIGH": "उच्च",
            "CRITICAL": "गंभीर",
            "FAIR": "सामान्य",
        }
        PRIMARY_FACTOR_MAP = {
            "TEMPERATURE": "तापमान",
            "HUMIDITY": "आर्द्रता",
            "SOIL_MOISTURE": "मिट्टी की नमी",
            "PRECIPITATION": "वर्षा",
            "GDD": "जीडीडी (GDD)",
            "NONE": "कोई नहीं",
        }
        CONTRIBUTING_FACTOR_MAP = {
            "fsi": "क्षेत्र तनाव सूचकांक (FSI)",
            "momentum": "तनाव गति",
            "stage_vulnerability": "विकास चरण संवेदनशीलता",
            "soil_health": "मिट्टी का स्वास्थ्य",
            "disease": "रोग की उपस्थिति",
            "radar_hotspot": "निकटवर्ती बीमारी रडार",
        }
        DISEASE_MAP = {
            "Yellow Rust (Stripe Rust)": "पीला रतुआ (Yellow Rust)",
            "Blast": "ब्लास्ट (Blast)",
            "Powdery Mildew": "पाउडरी मिल्ड्यू (Powdery Mildew)",
            "LEAF_RUST": "पत्ती का रतुआ (Leaf Rust)",
            "BLAST": "ब्लास्ट (Blast)",
            "POWDERY_MILDEW": "पाउडरी मिल्ड्यू (Powdery Mildew)",
        }

        localized_core = core.model_copy(deep=True)
        localized_core.crop_type = CROP_MAP.get(localized_core.crop_type, localized_core.crop_type)
        localized_core.stage = STAGE_MAP.get(localized_core.stage, localized_core.stage)
        localized_core.fsi_classification = CLASSIFICATION_MAP.get(localized_core.fsi_classification, localized_core.fsi_classification)
        localized_core.primary_factor = PRIMARY_FACTOR_MAP.get(localized_core.primary_factor, localized_core.primary_factor)
        localized_core.yield_risk.risk_band = BAND_MAP.get(localized_core.yield_risk.risk_band, localized_core.yield_risk.risk_band)
        localized_core.yield_risk.contributing_factors = [
            CONTRIBUTING_FACTOR_MAP.get(f, f) for f in localized_core.yield_risk.contributing_factors
        ]
        localized_core.stress_momentum.direction = DIRECTION_MAP.get(localized_core.stress_momentum.direction, localized_core.stress_momentum.direction)
        
        if hasattr(localized_core, "nearby_outbreaks") and localized_core.nearby_outbreaks:
            outbreaks_mapped = []
            for ob in localized_core.nearby_outbreaks:
                o_map = ob
                for eng, hin in DISEASE_MAP.items():
                    o_map = o_map.replace(eng, hin)
                for eng, hin in BAND_MAP.items():
                    o_map = o_map.replace(eng, hin)
                outbreaks_mapped.append(o_map)
            localized_core.nearby_outbreaks = outbreaks_mapped

        return localized_core

    async def _build_core_intelligence(
        self,
        user_id: str,
        farm_id: str,
        projected_fsi: float | None = None,
    ) -> CoreIntelligence:
        field_context = await self.stress_service.build_field_context(farm_id, user_id)
        fsi_result = self.stress_service.calculate_fsi_from_context(field_context)
        farm = field_context.farm
        crop_type = fsi_result.crop_type
        state = str(farm.get("state", "ALL"))

        soil_section, soil_data = await self._build_soil_section(farm_id)
        _alerts_section, alert_rules = await self._build_alerts_section(user_id, farm_id)
        disease_section, disease_history = await self._build_disease_history_section(farm_id)
        radar_section, nearby_outbreaks = await self._build_radar_section(farm_id, user_id, crop_type)

        soil_health_index = float(soil_data["soil_health_index"]) if soil_data else None
        stage_vulnerability = 0.5
        if field_context.characteristics and field_context.characteristics.stage_vulnerability:
            stage_vulnerability = float(
                field_context.characteristics.stage_vulnerability.get(
                    fsi_result.stage,
                    0.5,
                )
            )

        disease_present = await self._has_confirmed_disease(farm_id)
        radar_high_nearby, radar_high_count = await self._radar_high_nearby(user_id, farm_id, crop_type)

        effective_fsi = projected_fsi if projected_fsi is not None else fsi_result.fsi
        momentum = await self.momentum_service.compute_for_farm(
            farm_id,
            projected_fsi=projected_fsi,
        )
        yield_risk = self.yield_risk_service.compute(
            fsi=effective_fsi,
            momentum=momentum,
            stage=fsi_result.stage,
            soil_health_index=soil_health_index,
            disease_present=disease_present,
            radar_high_nearby=radar_high_nearby,
            stage_vulnerability=stage_vulnerability,
        )

        return CoreIntelligence(
            farm_id=farm_id,
            crop_type=crop_type,
            stage=fsi_result.stage,
            fsi=effective_fsi,
            fsi_classification=fsi_result.classification,
            primary_factor=fsi_result.primary_factor,
            current_gdd=field_context.current_gdd,
            soil_health_index=soil_health_index,
            stress_momentum=momentum,
            yield_risk=yield_risk,
            mitigation_locked=fsi_result.classification == FSI_MITIGATION_LOCK_CLASSIFICATION,
            disease_present=disease_present,
            radar_high_nearby=radar_high_nearby,
            nearby_outbreaks=nearby_outbreaks,
            alert_rules=alert_rules,
            stage_vulnerability=stage_vulnerability,
            cycle_status=field_context.cycle_status,
        )

    def _core_markdown_sections(self, core: CoreIntelligence, field_context: Any | None = None, language: str = "en") -> list[str]:
        lang = language.lower() if language.lower() in LOCALIZED_LITERALS else "en"
        literals = LOCALIZED_LITERALS[lang]
        sections = [
            f"# HarvestIQ Intelligence Context\n\nsnapshot_version: {INTELLIGENCE_SNAPSHOT_VERSION}",
            "## Farm Snapshot",
            f"- Farm ID: {core.farm_id}",
            f"- Crop: {core.crop_type}",
            f"- State crop cycle stage: {core.stage}",
            "## Crop Stage",
            f"- Stage: {core.stage}",
            f"- Current GDD: {core.current_gdd}",
            "## Field Stress Index",
            f"- FSI: {core.fsi}",
            f"- Classification: {core.fsi_classification}",
            f"- Primary factor: {core.primary_factor}",
            "## Soil Health",
            (
                f"- Soil health index: {core.soil_health_index}"
                if core.soil_health_index is not None
                else f"- {literals['no_soil_records']}"
            ),
            "## Stress Momentum",
            f"- direction: {core.stress_momentum.direction}",
            f"- momentum_score: {core.stress_momentum.momentum_score}",
            f"- fsi_delta: {core.stress_momentum.fsi_delta}",
            f"- insufficient_history: {str(core.stress_momentum.insufficient_history).lower()}",
            "## Yield Risk",
            f"- risk_band: {core.yield_risk.risk_band}",
            f"- estimated_risk_percent: {core.yield_risk.estimated_risk_percent}%",
            f"- contributing_factors: {', '.join(core.yield_risk.contributing_factors) or 'none'}",
            "## Nearby Disease Radar",
            (
                "\n".join(f"- {outbreak}" for outbreak in core.nearby_outbreaks)
                if core.nearby_outbreaks
                else f"- {literals['no_nearby_disease']}"
            ),
            "## Mitigation Policy",
            f"- mitigation_locked: {str(core.mitigation_locked).lower()}",
        ]
        if field_context is not None:
            weather = field_context.weather
            farm = field_context.farm
            sections.insert(
                2,
                "\n".join(
                    [
                        f"- Farm: {farm.get('name', core.farm_id)}",
                        f"- State: {farm.get('state', 'ALL')}",
                        f"- District: {farm.get('district', 'ALL')}",
                    ]
                ),
            )
            sections.insert(
                6,
                "\n".join(
                    [
                        "## Weather",
                        f"- Current temperature (C): {weather.current.temp}",
                        f"- Humidity (%): {weather.current.humidity}",
                        f"- Wind speed: {weather.current.wind_speed}",
                        f"- Precipitation (mm): {weather.current.precipitation}",
                    ]
                ),
            )
        return sections

    async def compile_context(
        self,
        user_id: str,
        farm_id: str,
        query: str,
        language: str,
    ) -> CompiledContextResult:
        field_context = await self.stress_service.build_field_context(farm_id, user_id)
        core = await self._build_core_intelligence(user_id, farm_id)
        core = self._localize_core_intelligence(core, language)
        farm = field_context.farm
        weather = field_context.weather
        state = str(farm.get("state", "ALL"))
        district = str(farm.get("district", "ALL"))

        soil_section, soil_data = await self._build_soil_section(farm_id)
        alerts_section, alert_rules = await self._build_alerts_section(user_id, farm_id, language=language)
        disease_section, _disease_history = await self._build_disease_history_section(farm_id, language=language)

        topic = self._infer_topic_from_query(query)
        rag_chunks = await self.rag_service.hybrid_search(
            HybridSearchParams(
                query=query,
                crop_type=core.crop_type,
                state=state,
                district=district,
                topic=topic,
                limit=5,
            )
        )

        citations: list[AdvisoryCitation] = []
        rag_chunk_ids: list[str] = []
        knowledge_lines: list[str] = []
        rag_sources: list[str] = []

        for chunk in rag_chunks:
            metadata = chunk.metadata
            doc_id = str(metadata.get("source_document", "unknown"))
            chunk_index = metadata.get("chunk_index", 0)
            chunk_id = f"{doc_id}:{chunk_index}"
            rag_chunk_ids.append(chunk_id)
            if doc_id not in rag_sources:
                rag_sources.append(doc_id)
            excerpt = chunk.text[:200].replace("\n", " ")
            citations.append(
                AdvisoryCitation(
                    source=str(metadata.get("source", "unknown")),
                    document_id=doc_id,
                    title=str(metadata.get("title", "")),
                    excerpt=excerpt,
                )
            )
            knowledge_lines.append(
                f"- [{metadata.get('source', 'KB')}] {metadata.get('title', doc_id)} "
                f"(score={chunk.score}): {excerpt}"
            )

        sections = self._core_markdown_sections(core, field_context, language=language)
        sections.extend(
            [
                "## Active Alerts",
                alerts_section,
                "## Disease History",
                disease_section,
                "## Knowledge Excerpts",
                "\n".join(knowledge_lines) if knowledge_lines else "- No matching knowledge chunks found.",
                "## User Question",
                query.strip(),
            ]
        )

        context_package = "\n\n".join(sections)
        context_hash = hashlib.sha256(context_package.encode("utf-8")).hexdigest()

        raw_soil = farm.get("soil_type", "UNKNOWN") if farm else "UNKNOWN"
        SOIL_MAP = {"CLAY": "चिकनी मिट्टी (Clay)", "LOAM": "दुमट मिट्टी (Loam)"}
        soil_val = SOIL_MAP.get(raw_soil, raw_soil) if language.lower() == "hi" else raw_soil

        explainability_inputs: dict[str, Any] = {
            "snapshot_version": INTELLIGENCE_SNAPSHOT_VERSION,
            "fsi": core.fsi,
            "classification": core.fsi_classification,
            "crop_stage": core.stage,
            "crop_type": core.crop_type,
            "soil_type": soil_val,
            "current_temp": weather.current.temp,
            "stress_momentum": core.stress_momentum.model_dump(),
            "yield_risk": core.yield_risk.model_dump(),
        }
        if soil_data:
            explainability_inputs["soil_health_index"] = soil_data.get("soil_health_index")

        explainability = build_advisory_explanation(
            primary_factor=core.primary_factor,
            inputs=explainability_inputs,
            triggered_rules=alert_rules,
            rag_sources=rag_sources,
            mitigation_locked=core.mitigation_locked,
            nearby_outbreaks=core.nearby_outbreaks,
        )

        return CompiledContextResult(
            context_package=context_package,
            context_hash=context_hash,
            citations=citations,
            explainability=explainability,
            rag_chunk_ids=rag_chunk_ids,
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
            mitigation_locked=core.mitigation_locked,
            language=language,
        )

    async def compile_briefing_context(
        self,
        user_id: str,
        farm_id: str,
        language: str = "en",
    ) -> BriefingCompiledResult:
        core = await self._build_core_intelligence(user_id, farm_id)
        lang_str = str(language).strip().lower()
        core_localized = self._localize_core_intelligence(core, lang_str)

        try:
            input_windows = await self.optimizer_service.evaluate_all(user_id, farm_id)
        except Exception:
            input_windows = {"SPRAY": False, "IRRIGATE": False, "FERTILIZE": False}

        market_summary = await self.market_service.get_summary_for_farm(user_id, farm_id)
        market_summary_localized = market_summary
        if market_summary and lang_str == "hi":
            CROP_MAP = {"WHEAT": "गेहूं", "PADDY": "धान", "MAIZE": "मक्का"}
            market_summary_localized = dict(market_summary)
            market_summary_localized['crop_type'] = CROP_MAP.get(
                market_summary_localized['crop_type'], market_summary_localized['crop_type']
            )

        try:
            schemes = await self.scheme_service.get_eligible(user_id, farm_id)
            eligible_schemes_count = len(schemes.schemes)
        except Exception:
            eligible_schemes_count = 0

        alerts_section, _alert_rules = await self._build_alerts_section(user_id, farm_id, language=language)

        window_lines = [f"- {action}: {'SAFE' if safe else 'UNSAFE'}" for action, safe in input_windows.items()]
        
        lang = lang_str if lang_str in LOCALIZED_LITERALS else "en"
        literals = LOCALIZED_LITERALS[lang]
        
        market_line = (
            f"- {market_summary_localized['crop_type']} modal {market_summary_localized['modal_price']} "
            f"at {market_summary_localized['mandi']} ({market_summary_localized['trend']})"
            if market_summary_localized
            else f"- {literals['market_data_unavailable']}"
        )

        sections = self._core_markdown_sections(core_localized, language=language)
        sections.extend(
            [
                "## Active Alerts",
                alerts_section,
                "## Input Windows",
                "\n".join(window_lines),
                "## Market Summary",
                market_line,
                "## Eligible Schemes",
                f"- eligible_schemes_count: {eligible_schemes_count}",
            ]
        )

        context_package = "\n\n".join(sections)
        context_hash = hashlib.sha256(context_package.encode("utf-8")).hexdigest()

        structured_sections = {
            "stress_momentum": core_localized.stress_momentum.model_dump(),
            "yield_risk": core_localized.yield_risk.model_dump(),
            "input_windows": input_windows,
            "market_summary": market_summary_localized,
            "eligible_schemes_count": eligible_schemes_count,
        }

        explainability = build_briefing_explanation(structured_sections)

        return BriefingCompiledResult(
            context_package=context_package,
            context_hash=context_hash,
            sections=structured_sections,
            explainability=explainability,
            mitigation_locked=core_localized.mitigation_locked,
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
        )

    async def compile_health_snapshot(self, user_id: str, farm_id: str, language: str = "en") -> HealthCompiledResult:
        core = await self._build_core_intelligence(user_id, farm_id)
        core = self._localize_core_intelligence(core, language)
        unread_alerts = await self._count_unread_alerts(user_id, farm_id)
        radar_high_count = sum(
            1 for outbreak in core.nearby_outbreaks if "HIGH" in outbreak.upper()
        )

        health_score, health_band = compute_health_risk_rating(
            fsi=core.fsi,
            soil_health_index=core.soil_health_index,
            radar_high_nearby=core.radar_high_nearby,
            unread_alerts=unread_alerts,
            yield_risk_percent=core.yield_risk.estimated_risk_percent,
        )

        explainability = {
            **build_momentum_explanation(core.stress_momentum.model_dump()),
            "yield_risk": build_yield_risk_explanation(core.yield_risk.model_dump()),
            "health_score": health_score,
            "health_band": health_band,
        }

        return HealthCompiledResult(
            core=core,
            health_score=health_score,
            health_band=health_band,
            nearby_radar_high_count=radar_high_count,
            unread_alerts=unread_alerts,
            explainability=explainability,
            intelligence_snapshot_version=INTELLIGENCE_SNAPSHOT_VERSION,
        )

    async def compile_simulator_snapshots(
        self,
        user_id: str,
        farm_id: str,
        hypothesis: SimulatorHypothesis,
    ) -> SimulatorCompiledSnapshots:
        baseline_core = await self._build_core_intelligence(user_id, farm_id)
        projected_fsi, fsi_curve, yield_factor = simulate_scenario(
            baseline_fsi=baseline_core.fsi,
            temp_delta=hypothesis.temp_delta,
            irrigation_delta=hypothesis.irrigation_delta,
            nitrogen_delta=hypothesis.nitrogen_delta,
        )

        projected_core = await self._build_core_intelligence(user_id, farm_id, projected_fsi=projected_fsi)

        explainability_inputs = {
            "baseline_fsi": baseline_core.fsi,
            "projected_fsi": projected_fsi,
            "temp_delta": hypothesis.temp_delta,
            "irrigation_delta": hypothesis.irrigation_delta,
            "nitrogen_delta": hypothesis.nitrogen_delta,
            "baseline_yield_risk": baseline_core.yield_risk.model_dump(),
            "projected_yield_risk": projected_core.yield_risk.model_dump(),
            "baseline_momentum": baseline_core.stress_momentum.model_dump(),
            "projected_momentum": projected_core.stress_momentum.model_dump(),
        }

        return SimulatorCompiledSnapshots(
            baseline_fsi=baseline_core.fsi,
            projected_fsi=projected_fsi,
            baseline_momentum=baseline_core.stress_momentum,
            projected_momentum=projected_core.stress_momentum,
            baseline_yield_risk=baseline_core.yield_risk,
            projected_yield_risk=projected_core.yield_risk,
            fsi_curve=fsi_curve,
            yield_factor=yield_factor,
            explainability_inputs=explainability_inputs,
        )

    async def _has_confirmed_disease(self, farm_id: str) -> bool:
        window_start = datetime.now(timezone.utc) - timedelta(days=DISEASE_LOOKBACK_DAYS)
        doc = await self.db.disease_reports.find_one(
            {
                "farm_id": ObjectId(farm_id),
                "deterministic_status": DISEASE_STATUS_CONFIRMED,
                "created_at": {"$gte": window_start},
            }
        )
        return doc is not None

    async def _radar_high_nearby(
        self,
        user_id: str,
        farm_id: str,
        crop_type: str,
    ) -> tuple[bool, int]:
        nearby = await self.radar_service.nearby(
            user_id=user_id,
            farm_id=farm_id,
            radius_km=None,
            crop_type=crop_type,
        )
        high_count = sum(1 for hotspot in nearby.hotspots if hotspot.risk_level.upper() == "HIGH")
        medium_count = sum(1 for hotspot in nearby.hotspots if hotspot.risk_level.upper() == "MEDIUM")
        return (high_count > 0 or medium_count > 0), high_count

    async def _count_unread_alerts(self, user_id: str, farm_id: str) -> int:
        return await self.db.alerts.count_documents(
            {"user_id": ObjectId(user_id), "farm_id": ObjectId(farm_id), "read": False}
        )

    async def _build_soil_section(self, farm_id: str) -> tuple[str, Optional[dict[str, Any]]]:
        doc = await self.db.soil_records.find_one(
            {"farm_id": ObjectId(farm_id)},
            sort=[("recorded_at", -1)],
        )
        if doc is None:
            return "- No soil records available.", None
        return (
            f"- Soil health index: {doc['soil_health_index']}\n"
            f"- Deficiency status: {doc['deficiency_status']}\n"
            f"- Recorded at: {doc['recorded_at']}",
            doc,
        )

    async def _build_alerts_section(self, user_id: str, farm_id: str, language: str = "en") -> tuple[str, list[str]]:
        cursor = self.db.alerts.find(
            {"user_id": ObjectId(user_id), "farm_id": ObjectId(farm_id), "read": False},
        ).sort("created_at", -1).limit(5)
        lines: list[str] = []
        rules: list[str] = []
        async for alert in cursor:
            rule_id = str(alert.get("rule_id", "UNKNOWN"))
            rules.append(rule_id)
            lines.append(
                f"- [{alert.get('severity', 'INFO')}] {alert.get('title')}: {alert.get('message')}"
            )
        if not lines:
            lang = language.lower() if language.lower() in LOCALIZED_LITERALS else "en"
            return f"- {LOCALIZED_LITERALS[lang]['no_unread_alerts']}", []
        return "\n".join(lines), rules

    async def _build_disease_history_section(self, farm_id: str, language: str = "en") -> tuple[str, list[dict[str, Any]]]:
        cursor = self.db.disease_reports.find(
            {"farm_id": ObjectId(farm_id)},
        ).sort("created_at", -1).limit(5)
        lines: list[str] = []
        history: list[dict[str, Any]] = []
        lang_str = str(language).strip().lower()

        async for report in cursor:
            history.append(report)
            disease = report.get('detected_disease')
            status = report.get('deterministic_status')

            if lang_str == "hi":
                DISEASE_MAP = {
                    "Yellow Rust (Stripe Rust)": "पीला रतुआ (Yellow Rust)",
                    "Blast": "ब्लास्ट (Blast)",
                    "Powdery Mildew": "पाउडरी मिल्ड्यू (Powdery Mildew)",
                    "LEAF_RUST": "पत्ती का रतुआ (Leaf Rust)",
                    "BLAST": "ब्लास्ट (Blast)",
                    "POWDERY_MILDEW": "पाउडरी मिल्ड्यू (Powdery Mildew)",
                }
                STATUS_MAP = {
                    "CONFIRMED": "पुष्टि की गई",
                    "SUSPECTED": "संदिग्ध",
                }
                if disease:
                    disease = DISEASE_MAP.get(disease, disease)
                if status:
                    status = STATUS_MAP.get(status, status)

            lines.append(
                f"- {disease} "
                f"(status={status}, "
                f"confidence={report.get('confidence')})"
            )
        if not lines:
            lang = lang_str if lang_str in LOCALIZED_LITERALS else "en"
            return f"- {LOCALIZED_LITERALS[lang]['no_disease_reports']}", []
        return "\n".join(lines), history

    async def _build_radar_section(
        self,
        farm_id: str,
        user_id: str,
        crop_type: str,
    ) -> tuple[str, list[str]]:
        nearby = await self.radar_service.nearby(
            user_id=user_id,
            farm_id=farm_id,
            radius_km=None,
            crop_type=crop_type,
        )
        outbreaks: list[str] = []
        lines: list[str] = []
        for hotspot in nearby.hotspots:
            label = f"{hotspot.disease_name}@{hotspot.distance_km}km ({hotspot.risk_level})"
            outbreaks.append(label)
            lines.append(
                f"- {hotspot.disease_name}: {hotspot.case_count} cases, "
                f"risk={hotspot.risk_level}, distance={hotspot.distance_km} km"
            )
        if not lines:
            return "- No nearby disease hotspots in radar.", []
        return "\n".join(lines), outbreaks

    @staticmethod
    def _infer_topic_from_query(query: str) -> Optional[str]:
        lowered = query.lower()
        tokens = set(re.findall(r"[a-zA-Z0-9]+", lowered))
        best_topic: Optional[str] = None
        best_score = 0
        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in tokens or keyword in lowered)
            if score > best_score:
                best_score = score
                best_topic = topic
        return normalize_topic(best_topic) if best_topic and best_score > 0 else None
