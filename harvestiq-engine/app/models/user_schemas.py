from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import MongoModelConfig, PyObjectId

UserRole = Literal["FARMER", "AGRONOMIST", "ADMIN"]


class UserRegisterSchema(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=2, max_length=50)
    preferred_lang: str = Field(default="hi", min_length=2, max_length=5)


class UserLoginSchema(BaseModel):
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    password: str = Field(..., min_length=8, max_length=128)


class UserProfileUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=50)
    preferred_lang: Optional[str] = Field(default=None, min_length=2, max_length=5)


class UserInDB(BaseModel):
    model_config = MongoModelConfig

    id: PyObjectId = Field(alias="_id")
    phone: str
    password_hash: str
    name: str
    role: UserRole = "FARMER"
    preferred_lang: str = "hi"
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime


class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    role: UserRole
    preferred_lang: str
    onboarding_completed: bool


class RegisterResponse(BaseModel):
    status: str = "success"
    user_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
