from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class AlertPreferencesSchema(BaseModel):
    push_enabled: bool = True
    sms_enabled: bool = True
    quiet_hours_start: int = Field(default=22, ge=0, le=23)
    quiet_hours_end: int = Field(default=6, ge=0, le=23)
    timezone: str = "Asia/Kolkata"


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    expiration_time: Optional[int] = None


class VapidPublicKeyResponse(BaseModel):
    public_key: str
    enabled: bool


class DeliveryEventResponse(BaseModel):
    id: str
    alert_id: str
    escalation_id: Optional[str] = None
    event_type: str
    channel: Optional[str] = None
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime


class EscalationStateResponse(BaseModel):
    id: str
    alert_id: str
    farm_id: str
    severity_tier: str
    status: Literal["ACTIVE", "STOPPED"]
    stop_reason: Optional[str] = None
    push_sent: bool = False
    push_sent_at: Optional[datetime] = None
    sms_farmer_sent: bool = False
    contacts_sent: bool = False
    created_at: datetime
    events: List[DeliveryEventResponse] = Field(default_factory=list)


class EscalationHistoryResponse(BaseModel):
    events: List[DeliveryEventResponse]
    total: int


class EscalationTickResponse(BaseModel):
    processed: int
    push_sent: int
    sms_sent: int
    contacts_sent: int
    stopped: int
    deferred: int
