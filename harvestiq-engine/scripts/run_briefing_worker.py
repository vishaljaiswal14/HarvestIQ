#!/usr/bin/env python3
"""Generate daily briefings for all farms with active crop cycles."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.services.briefing_service import BriefingService  # noqa: E402


async def run_one_pass(service, db) -> None:
    farms_cursor = db.farms.find({})
    processed = 0
    failures = 0

    async for farm in farms_cursor:
        farm_id = str(farm["_id"])
        user_id = str(farm["user_id"])
        cycle = await db.crop_cycles.find_one({"farm_id": farm["_id"], "status": "ACTIVE"})
        if cycle is None:
            continue
        try:
            user = await db.users.find_one({"_id": farm["user_id"]})
            language = str((user or {}).get("preferred_lang", "hi"))
            # In the worker, we force_regenerate to compile the latest data
            await service.get_daily_briefing(
                user_id=user_id,
                farm_id=farm_id,
                language=language,
                source="WORKER",
                force_regenerate=True,
            )
            processed += 1
            print(f"Briefing generated for farm {farm_id}")
        except Exception as exc:
            failures += 1
            print(f"Failed farm {farm_id}: {exc}")

    print(f"Pass completed. processed={processed} failures={failures}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Briefing Automation Worker Loop")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Interval between runs in seconds")
    args = parser.parse_args()

    await connect_to_mongo()
    db = get_database()
    service = BriefingService(db)

    print(f"Starting Briefing Worker loop (interval={args.interval}s, once={args.once})...")

    try:
        while True:
            print("Executing briefing pass...")
            await run_one_pass(service, db)
            if args.once:
                break
            await asyncio.sleep(args.interval)
    finally:
        await close_mongo_connection()
        print("Briefing Worker stopped.")


if __name__ == "__main__":
    asyncio.run(main())
