from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_refresh_token_from_cookie
from app.core.config import get_settings
from app.core.database import get_database
from app.core.exceptions import unauthorized
from app.models.user_schemas import (
    RegisterResponse,
    TokenResponse,
    UserLoginSchema,
    UserRegisterSchema,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=max_age,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_token_cookie_name,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit("20/15minutes")
async def register(request: Request, payload: UserRegisterSchema) -> RegisterResponse:
    db = get_database()
    service = AuthService(db)
    return await service.register(payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/15minutes")
async def login(
    request: Request,
    response: Response,
    payload: UserLoginSchema,
) -> TokenResponse:
    db = get_database()
    service = AuthService(db)
    token_response, refresh_token = await service.login(payload)
    _set_refresh_cookie(response, refresh_token)
    return token_response


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/15minutes")
async def refresh_token(
    request: Request,
    response: Response,
    cookie_token: Annotated[Optional[str], Depends(get_refresh_token_from_cookie)],
) -> TokenResponse:
    if not cookie_token:
        raise unauthorized("Refresh token cookie missing")

    db = get_database()
    service = AuthService(db)
    token_response, new_refresh_token = await service.refresh_access_token(cookie_token)
    _set_refresh_cookie(response, new_refresh_token)
    return token_response


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    cookie_token: Annotated[Optional[str], Depends(get_refresh_token_from_cookie)],
) -> None:
    if cookie_token:
        db = get_database()
        service = AuthService(db)
        await service.revoke_refresh_token(cookie_token)
    _clear_refresh_cookie(response)
