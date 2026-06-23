import logging
from typing import Annotated, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.api.deps import get_current_user
from app.api.v1.auth import limiter
from app.core.constants.sos import SOS_RATE_LIMIT
from app.core.database import get_database
from app.core.exceptions import forbidden
from app.models.day7_schemas import (
    SosTriggerRequest,
    SosTriggerResponse,
    EmergencyContactsSchema,
    EmergencyContactsResponse
)
from app.core.config import get_settings
from app.core.twilio_security import build_external_request_url, is_valid_twilio_signature
from app.services.sos_service import SosService

router = APIRouter(prefix="/sos", tags=["sos"])
logger = logging.getLogger(__name__)


def _sos_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"sos:{auth[7:22]}"
    return f"sos-ip:{request.client.host if request.client else 'unknown'}"


@router.post("/status-callback")
async def sos_status_callback(
    request: Request,
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
):
    settings = get_settings()
    form_data = await request.form()
    callback_payload = dict(form_data.multi_items())

    if settings.twilio_enabled and settings.external_callback_url:
        signature = request.headers.get("X-Twilio-Signature")
        expected_url = build_external_request_url(
            settings.external_callback_url,
            request.url.path,
            dict(request.query_params),
        )
        if not is_valid_twilio_signature(
            url=expected_url,
            params=callback_payload,
            signature=signature,
            auth_token=settings.twilio_auth_token,
        ):
            logger.warning("Rejected SOS callback with invalid Twilio signature")
            raise forbidden("Invalid Twilio signature")

    logger.info("Received SOS callback with keys=%s", list(callback_payload.keys()))

    message_sid = callback_payload.get("MessageSid")
    message_status = callback_payload.get("MessageStatus") or callback_payload.get("SmsStatus")
    error_code = callback_payload.get("ErrorCode")
    error_message = callback_payload.get("ErrorMessage")

    if message_sid and message_status:
        logger.info("Processing SOS callback for message_sid=%s status=%s", message_sid, message_status)
        service = SosService(db)
        await service.update_delivery_status(
            message_sid=message_sid,
            provider_status=message_status,
            error_code=error_code,
            error_message=error_message
        )
    else:
        logger.warning("SOS callback missing MessageSid or message status")
    return {"status": "success"}


@router.post("/trigger", response_model=SosTriggerResponse)
@limiter.limit(SOS_RATE_LIMIT, key_func=_sos_rate_limit_key)
async def trigger_sos(
    request: Request,
    payload: SosTriggerRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SosTriggerResponse:
    service = SosService(db)
    settings = get_settings()
    if settings.external_callback_url:
        base_url = settings.external_callback_url.rstrip("/")
        status_callback = f"{base_url}/api/v1/sos/status-callback"
    else:
        status_callback = f"{request.base_url}api/v1/sos/status-callback"
    return await service.trigger(str(current_user["_id"]), payload, status_callback=status_callback)


@router.post("/dispatch", response_model=SosTriggerResponse)
@limiter.limit(SOS_RATE_LIMIT, key_func=_sos_rate_limit_key)
async def dispatch_sos(
    request: Request,
    payload: SosTriggerRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> SosTriggerResponse:
    service = SosService(db)
    settings = get_settings()
    if settings.external_callback_url:
        base_url = settings.external_callback_url.rstrip("/")
        status_callback = f"{base_url}/api/v1/sos/status-callback"
    else:
        status_callback = f"{request.base_url}api/v1/sos/status-callback"
    return await service.trigger(str(current_user["_id"]), payload, status_callback=status_callback)


@router.get("/contacts", response_model=EmergencyContactsResponse)
async def get_emergency_contacts(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict:
    service = SosService(db)
    res = await service.get_contacts(str(current_user["_id"]))
    if "updated_at" not in res or not res["updated_at"]:
        res["updated_at"] = datetime.now(timezone.utc)
    return res


@router.post("/contacts", response_model=EmergencyContactsResponse)
async def save_emergency_contacts(
    payload: EmergencyContactsSchema,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> dict:
    service = SosService(db)
    return await service.save_contacts(str(current_user["_id"]), payload.model_dump())


@router.get("/history", response_model=List[SosTriggerResponse])
async def get_sos_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> List[SosTriggerResponse]:
    service = SosService(db)
    cursor = db.sos_actions.find({"user_id": ObjectId(current_user["_id"])}).sort("triggered_at", -1)
    history = []
    async for doc in cursor:
        doc["action_id"] = str(doc["_id"])
        doc["farm_id"] = str(doc["farm_id"])
        # Ensure triggered_at has timezone
        if doc.get("triggered_at") and doc["triggered_at"].tzinfo is None:
            doc["triggered_at"] = doc["triggered_at"].replace(tzinfo=timezone.utc)
        history.append(SosTriggerResponse(**doc))
    return history
