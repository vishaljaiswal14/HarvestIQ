from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str
    mongodb_db_name: str = "harvestiq"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    refresh_token_cookie_name: str = "harvestiq_refresh_token"

    environment: str = "development"

    open_meteo_base_url: str = "https://api.open-meteo.com/v1/forecast"
    openweather_api_key: str = ""
    weather_cache_ttl_minutes: int = 30

    chroma_persist_dir: str = "data/chroma"
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    gemini_vision_model: str = "gemini-2.0-flash"
    gemini_text_model: str = "gemini-2.0-flash"
    disease_confidence_threshold: float = 0.70
    disease_upload_dir: str = "data/uploads/disease"
    radar_grid_resolution: float = 0.05
    radar_window_hours: int = 72
    radar_min_cases_medium: int = 3
    radar_min_cases_high: int = 6
    optimizer_wind_limit_kmh: float = 20.0
    optimizer_rain_limit_mm: float = 5.0
    briefing_cron_hour: int = 6
    simulator_max_temp_delta: float = 10.0

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    demo_enabled: bool = True
    external_callback_url: str = ""

    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:alerts@harvestiq.app"

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
