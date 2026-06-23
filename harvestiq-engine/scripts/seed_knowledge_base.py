#!/usr/bin/env python3
"""Ingest agronomic knowledge documents into ChromaDB and knowledge_metadata."""

import asyncio
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.services.knowledge_ingest_service import KnowledgeIngestService  # noqa: E402


async def main() -> None:
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]

    service = KnowledgeIngestService(db)
    count = await service.ingest_all()
    print(f"Ingested {count} knowledge documents.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
