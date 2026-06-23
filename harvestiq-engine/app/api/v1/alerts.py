from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.alert_escalation_schemas import (
    EscalationHistoryResponse,
    EscalationStateResponse,
    EscalationTickResponse,
    PushSubscriptionRequest,
    VapidPublicKeyResponse,
)
from app.models.engine_schemas import (
    AlertListResponse,
    AlertResponse,
    TriggerEvaluationRequest,
    TriggerEvaluationResponse,
)
from app.models.alert_severity_schemas import AlertSeverityResponse
from app.integrations.web_push_client import WebPushClient
from app.services.alert_escalation_service import AlertEscalationService
from app.services.alert_severity_service import AlertSeverityService
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    current_user: Annotated[dict, Depends(get_current_user)],
    unread_only: Annotated[bool, Query()] = False,
    farm_id: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AlertListResponse:
    db = get_database()
    service = AlertService(db)
    return await service.list_for_user(
        str(current_user["_id"]),
        unread_only=unread_only,
        farm_id=farm_id,
        limit=limit,
    )


@router.post("/trigger-evaluation", response_model=TriggerEvaluationResponse)
async def trigger_alert_evaluation(
    payload: TriggerEvaluationRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> TriggerEvaluationResponse:
    db = get_database()
    service = AlertService(db)
    return await service.trigger_evaluation(
        str(current_user["_id"]),
        payload,
        language=str(current_user.get("preferred_lang", "en")),
    )


@router.get("/severity", response_model=AlertSeverityResponse)
async def get_farm_alert_severity(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
) -> AlertSeverityResponse:
    db = get_database()
    service = AlertSeverityService(db)
    result = await service.evaluate(
        str(current_user["_id"]),
        farm_id,
        language=str(current_user.get("preferred_lang", "en")),
        persist=True,
    )
    return AlertSeverityResponse(severity=result)


@router.get("/escalation/history", response_model=EscalationHistoryResponse)
async def get_escalation_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> EscalationHistoryResponse:
    db = get_database()
    service = AlertEscalationService(db)
    return await service.get_delivery_history(str(current_user["_id"]), limit=limit)


@router.post("/escalation/tick", response_model=EscalationTickResponse)
async def run_escalation_tick(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> EscalationTickResponse:
    db = get_database()
    service = AlertEscalationService(db)
    return await service.process_tick()


@router.put("/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AlertResponse:
    db = get_database()
    service = AlertService(db)
    return await service.mark_read(alert_id, str(current_user["_id"]))


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AlertResponse:
    db = get_database()
    service = AlertService(db)
    return await service.acknowledge(alert_id, str(current_user["_id"]))


@router.put("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> AlertResponse:
    db = get_database()
    service = AlertService(db)
    return await service.resolve(alert_id, str(current_user["_id"]))


@router.get("/{alert_id}/escalation", response_model=EscalationStateResponse)
async def get_alert_escalation(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> EscalationStateResponse:
    db = get_database()
    service = AlertEscalationService(db)
    return await service.get_escalation_timeline(alert_id, str(current_user["_id"]))


notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key() -> VapidPublicKeyResponse:
    client = WebPushClient()
    return VapidPublicKeyResponse(
        public_key=client.get_public_key(),
        enabled=client.enabled,
    )


@notifications_router.post("/subscribe", status_code=204)
async def subscribe_push(
    payload: PushSubscriptionRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> None:
    db = get_database()
    service = AlertEscalationService(db)
    await service.save_push_subscription(
        str(current_user["_id"]),
        payload.model_dump(),
    )


@notifications_router.delete("/subscribe", status_code=204)
async def unsubscribe_push(
    current_user: Annotated[dict, Depends(get_current_user)],
    endpoint: Annotated[str, Query()],
) -> None:
    db = get_database()
    service = AlertEscalationService(db)
    await service.remove_push_subscription(str(current_user["_id"]), endpoint)
