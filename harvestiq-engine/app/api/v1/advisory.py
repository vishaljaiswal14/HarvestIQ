from typing import Annotated, Optional
from app.models.day8_schemas_actions import AdvisoryActionsResponse

from fastapi import APIRouter, Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.api.v1.auth import limiter
from app.core.constants.advisory import ADVISORY_RATE_LIMIT
from app.core.database import get_database
from app.models.day5_schemas import AdvisoryAskRequest, AdvisoryAskResponse
from app.models.engine_schemas import ExplanationPayload
from app.services.advisory_service import AdvisoryService

router = APIRouter(prefix="/advisory", tags=["advisory"])


def _advisory_rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return f"advisory:{auth[7:22]}"
    return f"advisory-ip:{request.client.host if request.client else 'unknown'}"


@router.post("/ask", response_model=AdvisoryAskResponse)
@limiter.limit(ADVISORY_RATE_LIMIT, key_func=_advisory_rate_limit_key)
async def ask_advisory(
    request: Request,
    payload: AdvisoryAskRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
) -> AdvisoryAskResponse:
    service = AdvisoryService(db)
    accept_lang = request.headers.get("accept-language")
    header_lang = accept_lang.split(",")[0].split(";")[0].strip().lower() if accept_lang else None
    language = payload.language or header_lang or str(current_user.get("preferred_lang", "hi"))
    if language not in ["hi", "en", "mr"]:
        language = "hi"
    try:
        res = await service.ask(str(current_user["_id"]), payload, language)
        res.advisory_text = res.synthesis
        res.explanation = res.explainability.model_dump() if res.explainability else {}
        return res
    except HTTPException:
        raise
    except Exception as exc:
        fallback_msg = "I am currently experiencing high demand. Please try again in a few moments."
        if language.lower() == "hi":
            fallback_msg = "मैं वर्तमान में उच्च मांग का अनुभव कर रहा हूँ। कृपया कुछ क्षणों में पुनः प्रयास करें।"
        return AdvisoryAskResponse(
            advisory_id="fallback-id",
            farm_id=payload.farm_id,
            synthesis=fallback_msg,
            advisory_text=fallback_msg,
            language=language,
            explainability=ExplanationPayload(
                summary="Local router fallback triggered",
                inputs={},
                primary_factor="ROUTER_FALLBACK"
            ),
            explanation={},
            citations=[],
            intelligence_snapshot_version="v3"
        )

@router.get("/actions", response_model=AdvisoryActionsResponse)
async def get_advisory_actions(
    request: Request,
    farm_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncIOMotorDatabase, Depends(get_database)],
    language: Optional[str] = None,
) -> AdvisoryActionsResponse:
    service = AdvisoryService(db)
    accept_lang = request.headers.get("accept-language")
    header_lang = accept_lang.split(",")[0].split(";")[0].strip().lower() if accept_lang else None
    resolved_lang = language or header_lang or str(current_user.get("preferred_lang", "hi"))
    if resolved_lang not in ["hi", "en", "mr"]:
        resolved_lang = "hi"
    
    return await service.get_actions(str(current_user["_id"]), farm_id, resolved_lang)
