import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.disease_radar_aggregator import DiseaseRadarAggregator

async def main():
    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    
    # 1. Find the test farm
    farm = await db.farms.find_one()
    if not farm:
        print("Error: No farm found in the database. Please onboard a farm first.")
        client.close()
        return
    
    farm_name = farm.get("name", "Unnamed Farm")
    location = farm.get("location", {})
    if not location or "coordinates" not in location:
        print("Error: Farm location or coordinates missing.")
        client.close()
        return
        
    lng, lat = location["coordinates"]
    print(f"Found farm '{farm_name}' at coordinates: Lng={lng}, Lat={lat}")
    
    # 2. Define 3 mock disease reports near the farm coordinates
    # 0.01 degree is roughly 1.1 km
    offsets = [
        (0.015, -0.01),   # North-East
        (-0.01, 0.012),   # South-West
        (0.005, 0.018),   # North-West
    ]
    
    now = datetime.now(timezone.utc)
    mock_reports = []
    
    # Use a dummy user/farm ID to represent other regional farmers reporting cases
    dummy_user_id = ObjectId()
    dummy_farm_id = ObjectId()
    
    for i, (d_lng, d_lat) in enumerate(offsets):
        rep_lng = lng + d_lng
        rep_lat = lat + d_lat
        report = {
            "user_id": dummy_user_id,
            "farm_id": dummy_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "LEAF_RUST",
            "confidence": 0.95,
            "deterministic_status": "CONFIRMED",
            "location": {
                "type": "Point",
                "coordinates": [rep_lng, rep_lat]
            },
            "explanation": {
                "summary": f"Mock regional disease report #{i+1}",
                "recommendation": "Monitor fields and apply fungicide if symptoms appear",
                "confidence": 0.95,
                "status": "CONFIRMED",
                "primary_factor": "DISEASE",
                "inputs": {
                    "crop_type": "WHEAT",
                    "state": farm.get("state", "Rajasthan"),
                    "district": farm.get("district", "Bharatpur"),
                    "detected_disease": "LEAF_RUST",
                    "confidence": 0.95,
                    "deterministic_status": "CONFIRMED"
                }
            },
            "created_at": now
        }
        mock_reports.append(report)
        
    # 3. Clean existing mock reports/radar entries first to prevent accumulation
    # and ensure fresh run
    await db.disease_reports.delete_many({"detected_disease": "LEAF_RUST"})
    await db.disease_radar.delete_many({"disease_name": "LEAF_RUST"})
    
    # 4. Insert reports
    result = await db.disease_reports.insert_many(mock_reports)
    print(f"Inserted {len(result.inserted_ids)} mock disease reports into 'disease_reports' collection.")
    
    # 5. Run the Aggregator to compile reports into the radar hotspots
    print("Running DiseaseRadarAggregator...")
    aggregator = DiseaseRadarAggregator(db)
    upserted = await aggregator.run()
    print(f"DiseaseRadarAggregator completed. Upserted {upserted} hotspots.")
    
    # 6. Verify hotspots were successfully created
    cursor = db.disease_radar.find({"disease_name": "LEAF_RUST"})
    async for doc in cursor:
        coords = doc["location_grid"]["coordinates"]
        print(f"Hotspot verified: Disease={doc['disease_name']}, Crop={doc['crop_type']}, Cases={doc['case_count']}, Risk={doc['risk_level']}, GridCoords={coords}")
        
    client.close()
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
