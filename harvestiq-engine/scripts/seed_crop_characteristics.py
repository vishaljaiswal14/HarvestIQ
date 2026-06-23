#!/usr/bin/env python3
"""Seed crop_characteristics collection from data/crop_characteristics_seed.json."""

import asyncio
import json
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402

SEED_PATH = ROOT / "data" / "crop_characteristics_seed.json"


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    with SEED_PATH.open(encoding="utf-8") as handle:
        crops = json.load(handle)

    for crop in crops:
        await db.crop_characteristics.update_one(
            {"crop_type": crop["crop_type"]},
            {"$set": crop},
            upsert=True,
        )
        print(f"Seeded {crop['crop_type']}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
