from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.exceptions import conflict, unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user_schemas import (
    RegisterResponse,
    TokenResponse,
    UserLoginSchema,
    UserRegisterSchema,
)


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.settings = get_settings()

    async def register(self, payload: UserRegisterSchema) -> RegisterResponse:
        now = datetime.now(timezone.utc)
        user_doc = {
            "phone": payload.phone,
            "password_hash": hash_password(payload.password),
            "name": payload.name,
            "role": "FARMER",
            "preferred_lang": payload.preferred_lang,
            "onboarding_completed": False,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self.db.users.insert_one(user_doc)
        except DuplicateKeyError:
            raise conflict("Phone number already registered")

        return RegisterResponse(user_id=str(result.inserted_id))

    async def login(self, payload: UserLoginSchema) -> tuple[TokenResponse, str]:
        user = await self.db.users.find_one({"phone": payload.phone})
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise unauthorized("Invalid phone or password")

        access_token = create_access_token(
            subject=str(user["_id"]),
            role=user["role"],
        )
        refresh_token = create_refresh_token(subject=str(user["_id"]))
        await self._persist_refresh_session(str(user["_id"]), refresh_token)

        return (
            TokenResponse(
                access_token=access_token,
                expires_in=self.settings.access_token_expire_minutes * 60,
            ),
            refresh_token,
        )

    async def refresh_access_token(self, refresh_token: str) -> tuple[TokenResponse, str]:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise unauthorized("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise unauthorized("Invalid refresh token type")

        user_id = payload.get("sub")
        if not user_id:
            raise unauthorized("Invalid refresh token subject")

        token_hash = hash_refresh_token(refresh_token)
        session = await self.db.sessions.find_one(
            {
                "user_id": ObjectId(user_id),
                "refresh_token_hash": token_hash,
                "revoked": False,
            }
        )
        if session is None:
            raise unauthorized("Refresh session not found or revoked")

        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise unauthorized("User not found")

        await self.db.sessions.update_one(
            {"_id": session["_id"]},
            {"$set": {"revoked": True}},
        )

        new_access_token = create_access_token(
            subject=user_id,
            role=user["role"],
        )
        new_refresh_token = create_refresh_token(subject=user_id)
        await self._persist_refresh_session(user_id, new_refresh_token)

        return (
            TokenResponse(
                access_token=new_access_token,
                expires_in=self.settings.access_token_expire_minutes * 60,
            ),
            new_refresh_token,
        )

    async def revoke_refresh_token(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            return

        user_id = payload.get("sub")
        if not user_id:
            return

        await self.db.sessions.update_one(
            {
                "user_id": ObjectId(user_id),
                "refresh_token_hash": hash_refresh_token(refresh_token),
            },
            {"$set": {"revoked": True}},
        )

    async def _persist_refresh_session(self, user_id: str, refresh_token: str) -> None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self.settings.refresh_token_expire_days)
        await self.db.sessions.insert_one(
            {
                "user_id": ObjectId(user_id),
                "refresh_token_hash": hash_refresh_token(refresh_token),
                "expires_at": expires_at,
                "created_at": now,
                "revoked": False,
            }
        )
