from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.auth import limiter
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo, ensure_indexes, get_database
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.localization import LocalizationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await connect_to_mongo()
        await ensure_indexes()
    except Exception as exc:
        message = str(exc)
        hint = (
            "Check MONGODB_URI in harvestiq-engine/.env. "
            "Use a MongoDB Atlas connection string with correct username/password."
        )
        if "CERTIFICATE_VERIFY_FAILED" in message or "unable to get local issuer certificate" in message:
            hint = (
                "SSL certificate bundle missing for this Python install. "
                "Run: /Applications/Python\\ 3.14/Install\\ Certificates.command "
                "OR reinstall deps: ./scripts/setup.sh (certifi is used automatically)."
            )
        elif "bad auth" in message or "Authentication failed" in message:
            hint = (
                "Atlas authentication failed. Verify database username/password in Atlas "
                "→ Database Access. URL-encode special characters in the password within MONGODB_URI."
            )
        raise RuntimeError(f"Failed to connect to MongoDB. {hint} Original error: {exc}") from exc
    yield
    await close_mongo_connection()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HarvestIQ Engine",
        description="Deterministic agricultural intelligence API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LocalizationMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check() -> dict:
        db_status = "ok"
        try:
            db = get_database()
            await db.command("ping")
        except Exception:
            db_status = "unavailable"
        return {
            "status": "ok" if db_status == "ok" else "degraded",
            "environment": settings.environment,
            "db": db_status,
        }

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
