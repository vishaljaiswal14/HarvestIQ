#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.services.localization_service import LocalizationService  # noqa: E402


async def main() -> None:
    await connect_to_mongo()
    db = get_database()
    service = LocalizationService(db)
    count = await service.seed_defaults()
    print(f"Seeded {count} localization entries")
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
