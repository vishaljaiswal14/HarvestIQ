#!/usr/bin/env python3
"""Seed system_rules collection from data/system_rules_seed.json."""

import asyncio
import json
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402

SEED_PATH = ROOT / "data" / "system_rules_seed.json"


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    with SEED_PATH.open(encoding="utf-8") as handle:
        rules = json.load(handle)

    for rule in rules:
        await db.system_rules.update_one(
            {"rule_id": rule["rule_id"]},
            {"$set": rule},
            upsert=True,
        )
        print(f"Seeded {rule['rule_id']}")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
