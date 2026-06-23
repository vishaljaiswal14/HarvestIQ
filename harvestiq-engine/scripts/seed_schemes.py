#!/usr/bin/env python3
"""Seed schemes collection from data/schemes.json."""

import asyncio
import json
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402

SEED_PATH = ROOT / "data" / "schemes.json"


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    with SEED_PATH.open(encoding="utf-8") as handle:
        schemes = json.load(handle)

    for scheme in schemes:
        await db.schemes.update_one(
            {"scheme_id": scheme["scheme_id"]},
            {"$set": scheme},
            upsert=True,
        )
        print(f"Seeded {scheme['scheme_id']}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
