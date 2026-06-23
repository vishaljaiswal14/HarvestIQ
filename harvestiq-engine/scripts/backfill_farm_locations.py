#!/usr/bin/env python3
"""Backfill farm location from state/district centroids."""

import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.location_service import build_farm_location  # noqa: E402


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    cursor = db.farms.find(
        {"$or": [{"location": {"$exists": False}}, {"location": None}]}
    )
    updated = 0
    async for farm in cursor:
        try:
            location_fields = build_farm_location(
                farm["state"],
                farm["district"],
                existing_location=farm.get("location"),
            )
            await db.farms.update_one({"_id": farm["_id"]}, {"$set": location_fields})
            updated += 1
            print(f"Updated farm {farm['_id']} -> {farm['district']}, {farm['state']}")
        except Exception as exc:
            print(f"Skipped farm {farm['_id']}: {exc}")

    client.close()
    print(f"Backfill complete. Updated {updated} farms.")


if __name__ == "__main__":
    asyncio.run(main())
