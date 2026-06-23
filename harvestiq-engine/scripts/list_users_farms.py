#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.config import get_settings

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    
    print("=== USERS ===")
    async for user in db.users.find():
        print(f"User ID: {user['_id']}, Name: {user.get('name')}, Phone: {user.get('phone')}, Onboarding: {user.get('onboarding_completed')}")
        
    print("\n=== FARMS ===")
    async for farm in db.farms.find():
        print(f"Farm ID: {farm['_id']}, User ID: {farm.get('user_id')}, Name: {farm.get('name')}, State: {farm.get('state')}, District: {farm.get('district')}")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
