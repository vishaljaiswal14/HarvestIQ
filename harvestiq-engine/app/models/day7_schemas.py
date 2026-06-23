from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SosTriggerRequest(BaseModel):
    farm_id: str
    emergency_type: str = "GENERAL"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    captured_at: Optional[str] = None


class SosRecipientStatus(BaseModel):
    role: str
    phone: str
    recipient_phone: Optional[str] = None
    masked_phone: Optional[str] = None
    status: str
    message_sid: Optional[str] = None
    provider_status: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error: Optional[str] = None
    last_updated: Optional[datetime] = None


class SosTriggerResponse(BaseModel):
    action_id: str
    farm_id: str
    emergency_type: str
    checklist: List[str]
    plain_text_message: str
    delivery_status: str
    intelligence_snapshot_version: str
    triggered_at: datetime
    recipients: Optional[List[SosRecipientStatus]] = None
    provider: Optional[str] = None
    message_sid: Optional[str] = None
    callback_available: Optional[bool] = True



class EmergencyContactsSchema(BaseModel):
    primary_contact: str = Field(default="", description="Primary emergency contact phone number")
    secondary_contact: str = Field(default="", description="Secondary emergency contact phone number")
    village_contact: str = Field(default="", description="Village emergency contact phone number")

    @classmethod
    def _validate_phone_pattern(cls, v: str) -> str:
        import re
        v = v.strip()
        if not v:
            return ""
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError("Phone number must be in E.164 format (e.g. +918441091925)")
        return v

    @field_validator("primary_contact", mode="before")
    @classmethod
    def validate_primary(cls, v: Any) -> str:
        return cls._validate_phone_pattern(str(v) if v is not None else "")

    @field_validator("secondary_contact", mode="before")
    @classmethod
    def validate_secondary(cls, v: Any) -> str:
        return cls._validate_phone_pattern(str(v) if v is not None else "")

    @field_validator("village_contact", mode="before")
    @classmethod
    def validate_village(cls, v: Any) -> str:
        return cls._validate_phone_pattern(str(v) if v is not None else "")

    @model_validator(mode="after")
    def validate_duplicates(self) -> "EmergencyContactsSchema":
        contacts = {}
        for field in ["primary_contact", "secondary_contact", "village_contact"]:
            val = getattr(self, field, "").strip()
            if val:
                if val in contacts.values():
                    raise ValueError(f"Duplicate contact number detected: {val}")
                contacts[field] = val
        return self


class EmergencyContactsResponse(BaseModel):
    primary_contact: str
    secondary_contact: str
    village_contact: str
    updated_at: datetime


class DemoInitializeResponse(BaseModel):
    demo_mode: bool = True
    version: str
    farms: List[Dict[str, Any]]
    description: str


class SyncOperation(BaseModel):
    client_id: str
    operation_type: str
    payload: Dict[str, Any]
    client_timestamp: datetime


class SyncBatchRequest(BaseModel):
    operations: List[SyncOperation] = Field(default_factory=list)


class SyncOperationResult(BaseModel):
    operation_type: str
    client_id: str
    server_id: Optional[str] = None
    status: str
    error: Optional[str] = None
    detail: Optional[str] = None


class SyncBatchResponse(BaseModel):
    processed: int
    results: List[SyncOperationResult]


class VerificationLogRequest(BaseModel):
    event_type: str
    environment: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class VerificationLogResponse(BaseModel):
    log_id: str
    event_type: str
    status: str
    recorded_at: datetime
