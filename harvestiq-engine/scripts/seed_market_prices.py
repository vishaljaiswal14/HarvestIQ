#!/usr/bin/env python3
"""Seed market_prices collection from data/market_prices.json."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402

SEED_PATH = ROOT / "data" / "market_prices.json"


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    now = datetime.now(timezone.utc)

    with SEED_PATH.open(encoding="utf-8") as handle:
        prices = json.load(handle)

    for record in prices:
        price_date = datetime.fromisoformat(record["price_date"].replace("Z", "+00:00"))
        doc = {
            **record,
            "price_date": price_date,
            "updated_at": now,
        }
        await db.market_prices.update_one(
            {
                "mandi": doc["mandi"],
                "crop_type": doc["crop_type"],
                "price_date": doc["price_date"],
            },
            {"$set": doc},
            upsert=True,
        )
        print(f"Seeded {doc['mandi']} {doc['crop_type']} {doc['price_date'].date()}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
