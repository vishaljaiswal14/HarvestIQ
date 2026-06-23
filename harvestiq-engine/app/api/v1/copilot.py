from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.operations_copilot_schemas import (
    CopilotActionCompleteRequest,
    CopilotActionCompleteResponse,
    OperationsCopilotResponse,
)
from app.models.yield_protection_schemas import (
    YieldProtectionHistoryResponse,
    YieldProtectionScoreResponse,
)
from app.services.operations_copilot_service import OperationsCopilotService
from app.services.yield_protection_score_service import YieldProtectionScoreService

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.get("/plan", response_model=OperationsCopilotResponse)
async def get_copilot_plan(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
    refresh: Annotated[bool, Query()] = False,
) -> OperationsCopilotResponse:
    db = get_database()
    service = OperationsCopilotService(db)
    language = str(current_user.get("preferred_lang", "en"))
    if refresh:
        return await service.generate_plan(
            str(current_user["_id"]), farm_id, language=language, persist=True
        )
    return await service.get_latest_plan(str(current_user["_id"]), farm_id)


@router.post("/plan/refresh", response_model=OperationsCopilotResponse)
async def refresh_copilot_plan(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
) -> OperationsCopilotResponse:
    db = get_database()
    service = OperationsCopilotService(db)
    return await service.generate_plan(
        str(current_user["_id"]),
        farm_id,
        language=str(current_user.get("preferred_lang", "en")),
        persist=True,
    )


@router.put("/actions/{action_id}/complete", response_model=CopilotActionCompleteResponse)
async def complete_copilot_action(
    action_id: str,
    payload: CopilotActionCompleteRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
) -> CopilotActionCompleteResponse:
    db = get_database()
    service = OperationsCopilotService(db)
    return await service.complete_action(
        str(current_user["_id"]), farm_id, action_id, payload.plan_id
    )


@router.get("/yield-protection", response_model=YieldProtectionScoreResponse)
async def get_yield_protection_score(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
) -> YieldProtectionScoreResponse:
    db = get_database()
    service = YieldProtectionScoreService(db)
    return await service.compute(
        str(current_user["_id"]),
        farm_id,
        language=str(current_user.get("preferred_lang", "en")),
        persist=True,
    )


@router.get("/yield-protection/history", response_model=YieldProtectionHistoryResponse)
async def get_yield_protection_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    farm_id: Annotated[str, Query()],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> YieldProtectionHistoryResponse:
    db = get_database()
    service = YieldProtectionScoreService(db)
    return await service.get_history(str(current_user["_id"]), farm_id, days=days)
