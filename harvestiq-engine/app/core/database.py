from typing import Optional

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo() -> None:
    global _client, _db
    settings = get_settings()
    # macOS python.org builds (incl. 3.14) often ship without a CA bundle at
    # etc/openssl/cert.pem. certifi provides Mozilla's CA store without disabling TLS.
    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        tlsCAFile=certifi.where(),
    )
    _db = _client[settings.mongodb_db_name]
    # Fail fast with a clear error if MongoDB is unreachable.
    await _client.admin.command("ping")


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database is not initialized")
    return _db


async def ensure_indexes() -> None:
    db = get_database()

    await db.users.create_index("phone", unique=True)
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.farms.create_index("user_id")
    await db.farms.create_index([("boundary", "2dsphere")], sparse=True)
    await db.farms.create_index([("location", "2dsphere")], sparse=True)
    await db.crop_cycles.create_index("farm_id")
    await db.crop_characteristics.create_index("crop_type", unique=True)
    await db.weather_cache.create_index("farm_id", unique=True)
    await db.weather_cache.create_index([("location", "2dsphere")], sparse=True)
    await db.weather_cache.create_index("expires_at", expireAfterSeconds=0)
    await db.stress_logs.create_index([("farm_id", 1), ("calculated_at", -1)])
    await db.stress_logs.create_index([("user_id", 1), ("calculated_at", -1)])
    await db.alerts.create_index([("user_id", 1), ("read", 1)])
    await db.alerts.create_index([("farm_id", 1), ("created_at", -1)])
    await db.alerts.create_index("dedup_key", unique=True, sparse=True)
    await db.alerts.create_index("expires_at", expireAfterSeconds=0)
    await db.alert_severity_logs.create_index([("user_id", 1), ("farm_id", 1), ("evaluated_at", -1)])
    await db.alert_severity_logs.create_index([("farm_id", 1), ("evaluated_at", -1)])
    await db.alert_escalations.create_index([("alert_id", 1), ("status", 1)])
    await db.alert_escalations.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
    await db.alert_delivery_events.create_index([("alert_id", 1), ("recorded_at", 1)])
    await db.alert_delivery_events.create_index([("user_id", 1), ("recorded_at", -1)])
    await db.push_subscriptions.create_index([("user_id", 1), ("endpoint", 1)], unique=True)
    await db.emergency_contacts.create_index("user_id", unique=True)
    await db.copilot_plans.create_index([("farm_id", 1), ("generated_at", -1)])
    await db.copilot_plans.create_index([("user_id", 1), ("generated_at", -1)])
    await db.copilot_action_completions.create_index([("user_id", 1), ("farm_id", 1), ("completed_at", -1)])
    await db.copilot_action_completions.create_index("action_id", unique=True)
    await db.yield_protection_logs.create_index([("farm_id", 1), ("calculated_at", -1)])
    await db.yield_protection_logs.create_index([("user_id", 1), ("calculated_at", -1)])
    await db.system_rules.create_index("rule_id", unique=True)
    await db.knowledge_metadata.create_index("document_id", unique=True)
    await db.knowledge_metadata.create_index([("crop_type", 1), ("topic", 1)])
    await db.knowledge_metadata.create_index([("state", 1), ("district", 1)])
    await db.soil_records.create_index([("farm_id", 1), ("recorded_at", -1)])
    await db.soil_records.create_index([("user_id", 1), ("recorded_at", -1)])
    await db.disease_reports.create_index([("location", "2dsphere")])
    await db.disease_reports.create_index([("farm_id", 1), ("created_at", -1)])
    await db.disease_reports.create_index([("user_id", 1), ("created_at", -1)])
    await db.disease_reports.create_index(
        [("deterministic_status", 1), ("created_at", -1)]
    )
    await db.advisory_logs.create_index([("user_id", 1), ("created_at", -1)])
    await db.advisory_logs.create_index([("farm_id", 1), ("created_at", -1)])
    await db.disease_radar.create_index([("location_grid", "2dsphere")])
    await db.disease_radar.create_index(
        [("disease_name", 1), ("grid_key", 1), ("crop_type", 1)],
        unique=True,
    )
    await db.localization_dictionary.create_index(
        [("key", 1), ("lang", 1)],
        unique=True,
    )
    await db.briefing_logs.create_index([("user_id", 1), ("generated_at", -1)])
    await db.briefing_logs.create_index([("farm_id", 1), ("generated_at", -1)])
    await db.market_prices.create_index([("crop_type", 1), ("state", 1), ("price_date", -1)])
    await db.market_prices.create_index([("mandi", 1), ("crop_type", 1), ("price_date", -1)])
    await db.schemes.create_index("scheme_id", unique=True)
    await db.schemes.create_index([("active", 1)])
    await db.sos_actions.create_index([("user_id", 1), ("triggered_at", -1)])
    await db.sos_actions.create_index([("farm_id", 1), ("triggered_at", -1)])
    await db.sos_actions.create_index([("delivery_status", 1), ("triggered_at", -1)])
    await db.verification_logs.create_index([("event_type", 1), ("recorded_at", -1)])
    await db.verification_logs.create_index([("environment", 1), ("recorded_at", -1)])
    await db.verification_logs.create_index("recorded_at", expireAfterSeconds=7776000)
    await db.sync_receipts.create_index("client_id", unique=True)
    await db.plots.create_index("farm_id")
    await db.expenses.create_index("crop_cycle_id")
    await db.harvests.create_index("crop_cycle_id")
