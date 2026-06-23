import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, Header, Query
from fastapi.responses import FileResponse
from bson import ObjectId

from app.api.deps import get_current_user
from app.core.database import get_database
from app.core.exceptions import not_found
from app.models.day4_schemas import DiseaseDetectResponse
from app.models.day7_schemas_timeline import DiseaseHistoryListResponse, FarmTimelineResponse, TimelineEvent
from app.services.disease_detection_service import DiseaseDetectionService

router = APIRouter(prefix="/disease", tags=["disease"])

TIMELINE_MERGE_WINDOW_SECONDS = 30 * 60
TIMELINE_SOURCE_PRIORITY = {
    "DISEASE": 100,
    "STRESS_LOG": 80,
    "ALERT": 70,
    "COPILOT_PLAN": 40,
    "YIELD_PROTECTION": 30,
}
TIMELINE_SEVERITY_RANK = {
    "LOW": 1,
    "MODERATE": 2,
    "MEDIUM": 2,
    "WARNING": 2,
    "HIGH": 3,
    "AT_RISK": 3,
    "CRITICAL": 4,
    "EMERGENCY": 5,
}


def _normalize_timestamp(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _severity_rank(value: Optional[str]) -> int:
    if not value:
        return 0
    return TIMELINE_SEVERITY_RANK.get(str(value).upper(), 0)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _strip_technical_text(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"\bFSI\b[:\s]*\d+(\.\d+)?%?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"field stress index[:\s]*\d+(\.\d+)?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"rainfall deficit index[:\s]*\d+(\.\d+)?", "insufficient rainfall", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bHIGH_STRESS\b|\bMEDIUM_STRESS\b|\bLOW_STRESS\b", "crop stress", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _map_primary_factor_root(primary_factor: Optional[str]) -> str:
    factor = (primary_factor or "").upper()
    if factor == "MOISTURE":
        return "stress:moisture"
    if factor in {"THERMAL", "TEMPERATURE", "HEAT"}:
        return "stress:thermal"
    return "stress:general"


def _infer_root_from_text(*values: Optional[str]) -> str:
    text = " ".join(_normalize_token(value or "") for value in values)
    if any(token in text for token in ("rust", "blight", "disease", "infection", "fungal", "spot")):
        return "disease:general"
    if any(token in text for token in ("rainfall", "moisture", "irrigation", "water", "dry", "drought")):
        return "stress:moisture"
    if any(token in text for token in ("thermal", "heat", "temperature", "hot", "wilting")):
        return "stress:thermal"
    if "stress" in text:
        return "stress:general"
    return "general:timeline"


def _stress_title_from_root(root_key: str) -> str:
    if root_key == "stress:moisture":
        return "Moisture Stress Detected"
    if root_key == "stress:thermal":
        return "Heat Stress Detected"
    return "Crop Stress Alert"


def _stress_description_from_root(root_key: str) -> str:
    if root_key == "stress:moisture":
        return "The crop is showing signs of moisture stress that may affect growth and yield."
    if root_key == "stress:thermal":
        return "High temperatures may be putting the crop under stress and slowing healthy growth."
    return "The crop is showing signs of stress that may affect growth, plant health, and yield."


def _stress_action_from_root(root_key: str) -> str:
    if root_key == "stress:moisture":
        return "Irrigate within 24 hours and check soil moisture across the field."
    if root_key == "stress:thermal":
        return "Inspect the field during the hottest hours and provide light irrigation if needed."
    return "Inspect field conditions today and follow the latest advisory to reduce crop stress."


def _weather_card_for_rule(rule_id: Optional[str]) -> tuple[str, str, str, str]:
    if rule_id == "RULE_RAINFALL_DEFICIT":
        return (
            "stress:moisture",
            "Weather Alert",
            "Low Rainfall Alert",
            "Insufficient rainfall may reduce soil moisture and affect crop growth.",
        )
    if rule_id == "RULE_THERMAL_HIGH":
        return (
            "stress:thermal",
            "Weather Alert",
            "Heat Stress Alert",
            "High temperatures may strain the crop and reduce healthy growth.",
        )
    return (
        "stress:general",
        "Crop Stress Alert",
        "Crop Stress Alert",
        "Field conditions may be putting the crop under stress.",
    )


def _weather_action_for_rule(rule_id: Optional[str]) -> str:
    if rule_id == "RULE_RAINFALL_DEFICIT":
        return "Plan irrigation or moisture-conservation measures this week."
    if rule_id == "RULE_THERMAL_HIGH":
        return "Check for wilting during the afternoon and irrigate if conditions remain hot."
    return "Inspect the field and follow the latest recommended action."


def _build_raw_timeline_event(
    *,
    event_id: str,
    source: str,
    root_key: str,
    event_type: str,
    timestamp: datetime,
    title: str,
    description: str,
    action: Optional[str],
    severity: Optional[str],
    risk_level: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "source": source,
        "root_key": root_key,
        "type": event_type,
        "timestamp": _normalize_timestamp(timestamp),
        "title": _strip_technical_text(title),
        "description": _strip_technical_text(description),
        "action": _strip_technical_text(action) if action else None,
        "severity": severity,
        "risk_level": risk_level,
        "metadata": metadata or {},
        "source_priority": TIMELINE_SOURCE_PRIORITY[source],
    }


def _select_group_action(group: list[dict[str, Any]], fallback: Optional[str]) -> Optional[str]:
    for source in ("COPILOT_PLAN", "DISEASE", "ALERT", "STRESS_LOG", "YIELD_PROTECTION"):
        for item in group:
            if item["source"] == source and item.get("action"):
                return item["action"]
    return fallback


def _root_keys_match(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.startswith("stress:") and right.startswith("stress:"):
        return left.endswith("general") or right.endswith("general")
    return False


def _build_final_timeline_event(group: list[dict[str, Any]]) -> TimelineEvent:
    group = sorted(
        group,
        key=lambda item: (_severity_rank(item.get("severity")), item["source_priority"]),
        reverse=True,
    )
    primary = group[0]
    root_key = primary["root_key"]
    event_type = primary["type"]
    title = primary["title"]
    description = primary["description"]
    severity = primary.get("severity")
    risk_level = primary.get("risk_level")
    metadata = dict(primary.get("metadata") or {})
    action = primary.get("action")

    if event_type == "Crop Stress Alert":
        title = _stress_title_from_root(root_key)
        description = _stress_description_from_root(root_key)
        action = _select_group_action(group, _stress_action_from_root(root_key))
    elif event_type == "Weather Alert":
        action = _select_group_action(group, action or _stress_action_from_root(root_key))
    elif event_type == "Disease Alert":
        action = _select_group_action(group, action or "Inspect affected plants and begin treatment as soon as possible.")
    elif event_type == "Scan Result":
        action = action or "Continue routine crop monitoring and repeat the scan if symptoms appear."
    elif event_type == "Advisory Generated":
        title = "Recommended Action"
        description = description or "A field advisory has been prepared based on current crop conditions."
        action = _select_group_action(group, action or "Review the latest advisory and complete the top-priority field action.")
    elif event_type == "Yield Protection Alert":
        title = "Yield Protection Alert"
        description = description or "Current field conditions may reduce yield if no action is taken."
        action = _select_group_action(group, action or "Act on the latest advisory to protect crop performance.")

    timestamp = max(item["timestamp"] for item in group)
    merged_id = "|".join(item["id"] for item in group)
    metadata["merged_sources"] = [item["source"] for item in group]

    return TimelineEvent(
        id=merged_id,
        type=event_type,
        timestamp=timestamp,
        title=title,
        description=description,
        action=action,
        severity=severity,
        risk_level=risk_level,
        metadata=metadata,
    )


def _merge_timeline_events(raw_events: list[dict[str, Any]]) -> list[TimelineEvent]:
    grouped: list[list[dict[str, Any]]] = []
    for event in sorted(raw_events, key=lambda item: item["timestamp"], reverse=True):
        placed = False
        for group in grouped:
            same_root = _root_keys_match(group[0]["root_key"], event["root_key"])
            close_in_time = abs((group[0]["timestamp"] - event["timestamp"]).total_seconds()) <= TIMELINE_MERGE_WINDOW_SECONDS
            if same_root and close_in_time:
                group.append(event)
                placed = True
                break
        if not placed:
            grouped.append([event])

    merged = [_build_final_timeline_event(group) for group in grouped]

    deduped: list[TimelineEvent] = []
    seen: set[tuple[str, str, str, datetime]] = set()
    for event in sorted(merged, key=lambda item: item.timestamp, reverse=True):
        ts_key = event.timestamp.replace(microsecond=0)
        key = (event.type, event.title, event.description, ts_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def to_disease_detect_response(doc: dict) -> DiseaseDetectResponse:
    from app.models.engine_schemas import ExplanationPayload
    
    exp_data = doc.get("explanation", {})
    explanation = ExplanationPayload(
        summary=exp_data.get("summary", ""),
        inputs=exp_data.get("inputs", {}),
        primary_factor=exp_data.get("primary_factor", "NONE"),
    )
    
    disease = doc.get("detected_disease", "UNKNOWN")
    
    created_at = doc.get("created_at")
    if created_at and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
        
    return DiseaseDetectResponse(
        report_id=str(doc["_id"]),
        farm_id=str(doc["farm_id"]),
        crop_type=doc.get("crop_type", "WHEAT"),
        disease=disease,
        confidence=doc.get("confidence"),
        deterministic_status=doc.get("deterministic_status", "UNKNOWN"),
        explanation=explanation,
        disease_name=doc.get("disease_name"),
        severity=doc.get("severity"),
        what_it_means=doc.get("what_it_means"),
        immediate_actions=doc.get("immediate_actions"),
        recommended_treatment=doc.get("recommended_treatment"),
        prevention_advice=doc.get("prevention_advice"),
        risk_level=doc.get("risk_level"),
        valid=doc.get("validation_result", True),
        crop_confidence=doc.get("crop_confidence"),
        validation_result=doc.get("validation_result"),
        region_validation_result=doc.get("region_validation_result"),
        created_at=created_at,
        image_url=doc.get("image_url") or f"/api/v1/disease/history/{str(doc['_id'])}/image",
        image_path=doc.get("image_storage_key"),
    )


@router.post("/detect", response_model=DiseaseDetectResponse)
async def detect_disease(
    farm_id: Annotated[str, Form(...)],
    image: Annotated[UploadFile, File(...)],
    current_user: Annotated[dict, Depends(get_current_user)],
    accept_language: Annotated[Optional[str], Header(alias="Accept-Language")] = "en",
) -> DiseaseDetectResponse:
    content_type = image.content_type or "application/octet-stream"
    image_bytes = await image.read()
    db = get_database()

    lang = "en"
    if accept_language:
        primary = accept_language.split(",")[0].split(";")[0].strip().lower()
        if primary in ["hi", "hindi"]:
            lang = "hi"

    service = DiseaseDetectionService(db)
    return await service.detect(
        user_id=str(current_user["_id"]),
        farm_id=farm_id,
        image_bytes=image_bytes,
        content_type=content_type,
        lang=lang,
    )


@router.get("/history", response_model=DiseaseHistoryListResponse)
async def get_disease_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
) -> DiseaseHistoryListResponse:
    db = get_database()
    query = {"user_id": ObjectId(current_user["_id"])}
    if farm_id:
        if ObjectId.is_valid(farm_id):
            query["farm_id"] = ObjectId(farm_id)
        else:
            raise not_found("Farm not found")

    skip = (page - 1) * limit
    total = await db.disease_reports.count_documents(query)

    cursor = db.disease_reports.find(query).sort("created_at", -1).skip(skip).limit(limit)
    reports = []
    async for doc in cursor:
        reports.append(to_disease_detect_response(doc))

    return DiseaseHistoryListResponse(
        reports=reports,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/history/{report_id}", response_model=DiseaseDetectResponse)
async def get_disease_report(
    report_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> DiseaseDetectResponse:
    db = get_database()
    if not ObjectId.is_valid(report_id):
        raise not_found("Report not found")
        
    doc = await db.disease_reports.find_one({
        "_id": ObjectId(report_id),
        "user_id": ObjectId(current_user["_id"])
    })
    if not doc:
        raise not_found("Report not found")
        
    return to_disease_detect_response(doc)


@router.get("/history/{report_id}/image")
async def get_disease_image(
    report_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    db = get_database()
    if not ObjectId.is_valid(report_id):
        raise not_found("Image not found")
        
    doc = await db.disease_reports.find_one({
        "_id": ObjectId(report_id),
        "user_id": ObjectId(current_user["_id"])
    })
    if not doc:
        raise not_found("Image not found")
        
    image_path_str = doc.get("image_storage_key")
    if not image_path_str:
        raise not_found("Image not found")
        
    image_path = Path(image_path_str)
    if not image_path.exists():
        raise not_found("Image file not found")
        
    return FileResponse(str(image_path))


@router.get("/timeline", response_model=FarmTimelineResponse)
async def get_farm_timeline(
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = Query(20, ge=1, le=100),
) -> FarmTimelineResponse:
    db = get_database()
    if not ObjectId.is_valid(farm_id):
        raise not_found("Farm not found")
        
    # Verify farm ownership
    farm = await db.farms.find_one({
        "_id": ObjectId(farm_id),
        "user_id": ObjectId(current_user["_id"])
    })
    if not farm:
        raise not_found("Farm not found")
        
    raw_events: list[dict[str, Any]] = []
    
    # 1. Fetch disease reports
    reports_cursor = db.disease_reports.find({"farm_id": ObjectId(farm_id)}).sort("created_at", -1).limit(limit)
    async for doc in reports_cursor:
        created_at = doc["created_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        disease_name = doc.get("disease_name") or doc.get("detected_disease", "Unknown Anomaly")
        if disease_name == "HEALTHY":
            disease_name = "Healthy Canopy"
        elif disease_name == "UNKNOWN":
            disease_name = "Unknown Plant Anomaly"
            
        deterministic_status = doc.get("deterministic_status")
        metadata = {
            "report_id": str(doc["_id"]),
            "image_url": doc.get("image_url") or f"/api/v1/disease/history/{str(doc['_id'])}/image",
        }
        if deterministic_status in {"HEALTHY", "UNKNOWN"}:
            description = "The latest crop scan did not detect a confirmed disease issue."
            action = "Continue routine monitoring and repeat the scan if symptoms appear."
            if deterministic_status == "UNKNOWN":
                description = "The crop scan found a visual issue that needs closer inspection."
                action = "Inspect the affected area and repeat the scan if symptoms continue."
            raw_events.append(_build_raw_timeline_event(
                event_id=str(doc["_id"]),
                source="DISEASE",
                root_key=f"scan:{str(doc['_id'])}",
                event_type="Scan Result",
                timestamp=created_at,
                title="Crop Scan Completed",
                description=description,
                action=action,
                severity=doc.get("severity"),
                risk_level=doc.get("risk_level"),
                metadata=metadata,
            ))
        else:
            action = None
            immediate_actions = doc.get("immediate_actions") or []
            if immediate_actions:
                action = immediate_actions[0]
            elif doc.get("recommended_treatment"):
                action = str(doc["recommended_treatment"])
            raw_events.append(_build_raw_timeline_event(
                event_id=str(doc["_id"]),
                source="DISEASE",
                root_key=f"disease:{_normalize_token(doc.get('detected_disease') or disease_name)}",
                event_type="Disease Alert",
                timestamp=created_at,
                title=f"{disease_name} Detected" if disease_name not in {"Healthy Canopy", "Unknown Plant Anomaly"} else "Disease Alert",
                description=doc.get("what_it_means") or f"Signs of {disease_name.lower()} were detected in the crop scan.",
                action=action or "Inspect affected plants and begin the recommended treatment promptly.",
                severity=doc.get("severity"),
                risk_level=doc.get("risk_level"),
                metadata=metadata,
            ))
        
    # 2. Fetch FSI logs (stress_logs)
    stress_cursor = db.stress_logs.find({"farm_id": ObjectId(farm_id)}).sort("calculated_at", -1).limit(limit)
    async for doc in stress_cursor:
        calc_at = doc["calculated_at"]
        if calc_at.tzinfo is None:
            calc_at = calc_at.replace(tzinfo=timezone.utc)
        root_key = _map_primary_factor_root(doc.get("primary_factor"))
        raw_events.append(_build_raw_timeline_event(
            event_id=str(doc["_id"]),
            source="STRESS_LOG",
            root_key=root_key,
            event_type="Crop Stress Alert",
            timestamp=calc_at,
            title=_stress_title_from_root(root_key),
            description=_stress_description_from_root(root_key),
            action=_stress_action_from_root(root_key),
            severity=doc.get("classification"),
            risk_level=doc.get("classification"),
            metadata={},
        ))
        
    # 3. Fetch alerts
    alerts_cursor = db.alerts.find({"farm_id": ObjectId(farm_id)}).sort("created_at", -1).limit(limit)
    async for doc in alerts_cursor:
        created_at = doc["created_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        root_key, event_type, title, description = _weather_card_for_rule(doc.get("rule_id"))
        raw_events.append(_build_raw_timeline_event(
            event_id=str(doc["_id"]),
            source="ALERT",
            root_key=root_key,
            event_type=event_type,
            timestamp=created_at,
            title=title,
            description=description,
            action=_weather_action_for_rule(doc.get("rule_id")),
            severity=doc.get("severity"),
            risk_level=None,
            metadata={
                "rule_id": doc.get("rule_id"),
                "alert_id": str(doc["_id"]),
            },
        ))
        
    # 4. Copilot plans
    plans_cursor = db.copilot_plans.find({"farm_id": ObjectId(farm_id)}).sort("generated_at", -1).limit(limit)
    async for doc in plans_cursor:
        gen_at = doc["generated_at"]
        if gen_at.tzinfo is None:
            gen_at = gen_at.replace(tzinfo=timezone.utc)
        actions = doc.get("actions") or []
        first_action = None
        if actions:
            first_action = actions[0].get("action") or actions[0].get("title")
        raw_events.append(_build_raw_timeline_event(
            event_id=str(doc["_id"]),
            source="COPILOT_PLAN",
            root_key=_infer_root_from_text(doc.get("situation_summary"), first_action),
            event_type="Advisory Generated",
            timestamp=gen_at,
            title="Recommended Action",
            description=doc.get("situation_summary", "")[:220] or "A field advisory has been generated from the latest crop conditions.",
            action=first_action or "Review the latest advisory and complete the top-priority field action.",
            severity=doc.get("severity_tier") or doc.get("priority"),
            risk_level=doc.get("potential_loss_prevention_band"),
            metadata={
                "plan_id": str(doc["_id"]),
                "priority": doc.get("priority"),
                "action_count": len(actions),
            },
        ))

    # 5. Yield protection score logs
    yp_cursor = db.yield_protection_logs.find({"farm_id": ObjectId(farm_id)}).sort("calculated_at", -1).limit(limit)
    async for doc in yp_cursor:
        calc_at = doc["calculated_at"]
        if calc_at.tzinfo is None:
            calc_at = calc_at.replace(tzinfo=timezone.utc)
        top_risk = _strip_technical_text(doc.get("top_risk", ""))
        raw_events.append(_build_raw_timeline_event(
            event_id=str(doc["_id"]),
            source="YIELD_PROTECTION",
            root_key=_infer_root_from_text(top_risk, str(doc.get("band", ""))),
            event_type="Yield Protection Alert",
            timestamp=calc_at,
            title="Yield Protection Alert",
            description=top_risk or "Current field conditions may reduce yield if no action is taken.",
            action="Act on the latest farm advisory to reduce crop risk and protect yield.",
            severity=doc.get("band"),
            risk_level=None,
            metadata={},
        ))

    events = _merge_timeline_events(raw_events)
    
    return FarmTimelineResponse(
        farm_id=farm_id,
        events=events[:limit]
    )
