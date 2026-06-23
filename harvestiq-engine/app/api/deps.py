from typing import Annotated, Optional

from bson import ObjectId
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.database import get_database
from app.core.exceptions import forbidden, unauthorized
from app.core.security import decode_token
from app.models.user_schemas import UserRole

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security_scheme)],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise unauthorized("Invalid or expired access token")

    if payload.get("type") != "access":
        raise unauthorized("Invalid access token type")

    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized("Invalid token subject")

    db = get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise unauthorized("User not found")

    return user


def require_roles(*roles: UserRole):
    async def role_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if current_user.get("role") not in roles:
            raise forbidden("Insufficient permissions")
        return current_user

    return role_checker


def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
    from app.core.config import get_settings

    settings = get_settings()
    return request.cookies.get(settings.refresh_token_cookie_name)
