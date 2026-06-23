import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, List, Dict, Any

from fastapi import APIRouter, Depends, Request
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_current_user
from app.api.v1.auth import limiter
from app.core.config import get_settings
from app.core.database import get_database
from app.core.exceptions import forbidden
from app.models.day7_schemas import DemoInitializeResponse
from app.models.day7_schemas_timeline import DemoSeedResponse

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_MANIFEST_PATH = Path(__file__).resolve().parents[3] / "data" / "demo_manifest.json"


@router.get("/initialize", response_model=DemoInitializeResponse)
@limiter.limit("10/hour")
async def initialize_demo(request: Request) -> DemoInitializeResponse:
    with DEMO_MANIFEST_PATH.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    return DemoInitializeResponse(**manifest)


@router.post("/seed", response_model=DemoSeedResponse)
@limiter.limit("20/hour")
async def seed_demo_data(
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request,
) -> DemoSeedResponse:
    settings = get_settings()
    if settings.is_production or not settings.demo_enabled:
        raise forbidden("Demo seeding is disabled in this environment")

    db = get_database()
    user_id = ObjectId(current_user["_id"])
    
    # 1. Clean existing demo farms to make this action re-runable
    demo_farm_names = [
        "Demo Farm - Green Valley (Healthy Farm)",
        "Demo Farm - Harvest Crest (Outbreak Farm)",
        "Demo Farm - Dry Plains (High-Risk Farm)"
    ]
    
    cursor = db.farms.find({"user_id": user_id, "name": {"$in": demo_farm_names}})
    existing_farms = []
    async for doc in cursor:
        existing_farms.append(doc)
    existing_ids = [doc["_id"] for doc in existing_farms]
    
    if existing_ids:
        await db.disease_reports.delete_many({"farm_id": {"$in": existing_ids}})
        await db.stress_logs.delete_many({"farm_id": {"$in": existing_ids}})
        await db.alerts.delete_many({"farm_id": {"$in": existing_ids}})
        await db.soil_records.delete_many({"farm_id": {"$in": existing_ids}})
        res_del = db.sos_actions.delete_many({"farm_id": {"$in": existing_ids}})
        if hasattr(res_del, "__await__"):
            await res_del
        
        # Cascade to plots and crop cycles
        plots_cursor = db.plots.find({"farm_id": {"$in": existing_ids}})
        existing_plots = []
        async for p in plots_cursor:
            existing_plots.append(p)
        plot_ids = [p["_id"] for p in existing_plots]
        
        if plot_ids:
            await db.crop_cycles.delete_many({"plot_id": {"$in": plot_ids}})
            await db.plots.delete_many({"_id": {"$in": plot_ids}})
            
        await db.farms.delete_many({"_id": {"$in": existing_ids}})

    now = datetime.now(timezone.utc)
    seeded_farms = []

    # ==========================================
    # 2. SEED HEALTHY FARM
    # ==========================================
    healthy_farm_doc = {
        "user_id": user_id,
        "name": "Demo Farm - Green Valley (Healthy Farm)",
        "area": 5.0,
        "area_unit": "ACRE",
        "latitude": 26.90,
        "longitude": 75.80,
        "state": "Rajasthan",
        "district": "Jaipur",
        "created_at": now
    }
    healthy_res = await db.farms.insert_one(healthy_farm_doc)
    healthy_farm_id = healthy_res.inserted_id

    healthy_plot_doc = {
        "farm_id": healthy_farm_id,
        "name": "Plot Alpha (Wheat)",
        "area": 5.0,
        "area_unit": "ACRE",
        "created_at": now
    }
    healthy_plot_res = await db.plots.insert_one(healthy_plot_doc)
    healthy_plot_id = healthy_plot_res.inserted_id

    healthy_cycle_doc = {
        "plot_id": healthy_plot_id,
        "farm_id": healthy_farm_id,
        "crop_type": "WHEAT",
        "season": "RABI",
        "sowing_date": now - timedelta(days=30),
        "expected_harvest_date": now + timedelta(days=90),
        "status": "ACTIVE",
        "current_gdd": 340.0,
        "created_at": now,
        "updated_at": now
    }
    healthy_cycle_res = await db.crop_cycles.insert_one(healthy_cycle_doc)
    healthy_cycle_id = healthy_cycle_res.inserted_id

    # Seed 5 stress logs with LOW risk values
    healthy_stress_logs = []
    for day in range(5):
        log_time = now - timedelta(days=day)
        fsi_val = 0.10 + (day * 0.012)  # low stress: 0.10 -> 0.16 (0-1 scale)
        healthy_stress_logs.append({
            "farm_id": healthy_farm_id,
            "user_id": user_id,
            "crop_cycle_id": healthy_cycle_id,
            "crop_type": "WHEAT",
            "stage": "VEGETATIVE",
            "fsi_score": fsi_val,
            "classification": "LOW",
            "primary_factor": "NONE",
            "components": {"temp_stress": 0.05, "rainfall_deficit": 0.08, "gdd_scale": 0.1},
            "explanation": {"summary": f"Low stress of {fsi_val:.2f} due to healthy soil and water resources.", "inputs": {}, "primary_factor": "NONE"},
            "calculated_at": log_time
        })
    await db.stress_logs.insert_many(healthy_stress_logs)

    # Seed 2 HEALTHY disease reports
    healthy_disease_reports = [
        {
            "user_id": user_id,
            "farm_id": healthy_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "HEALTHY",
            "confidence": None,
            "deterministic_status": "HEALTHY",
            "location": {"type": "Point", "coordinates": [75.80, 26.90]},
            "created_at": now - timedelta(days=4),
            "disease_name": "Healthy Canopy",
            "severity": "None",
            "what_it_means": "No visual disease symptoms detected in the leaf scan.",
            "immediate_actions": ["Continue standard monitoring and agronomic operations."],
            "recommended_treatment": None,
            "prevention_advice": ["Maintain regular irrigation.", "Apply balanced N-P-K fertilizer as recommended."],
            "risk_level": "Low",
            "crop_confidence": 0.96,
            "validation_result": True,
            "region_validation_result": True
        },
        {
            "user_id": user_id,
            "farm_id": healthy_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "HEALTHY",
            "confidence": None,
            "deterministic_status": "HEALTHY",
            "location": {"type": "Point", "coordinates": [75.80, 26.90]},
            "created_at": now - timedelta(days=1),
            "disease_name": "Healthy Canopy",
            "severity": "None",
            "what_it_means": "No visual disease symptoms detected in the leaf scan.",
            "immediate_actions": ["Continue standard monitoring and agronomic operations."],
            "recommended_treatment": None,
            "prevention_advice": ["Maintain regular irrigation.", "Apply balanced N-P-K fertilizer as recommended."],
            "risk_level": "Low",
            "crop_confidence": 0.98,
            "validation_result": True,
            "region_validation_result": True
        }
    ]
    await db.disease_reports.insert_many(healthy_disease_reports)

    # Seed healthy soil record
    healthy_soil = {
        "farm_id": healthy_farm_id,
        "user_id": user_id,
        "crop_type": "WHEAT",
        "nitrogen": 280.0,
        "phosphorus": 22.0,
        "potassium": 180.0,
        "ph": 6.8,
        "organic_carbon": 0.75,
        "electrical_conductivity": 1.2,
        "soil_health_index": 85.0,
        "deficiency_status": {
            "nitrogen": "OPTIMAL",
            "phosphorus": "OPTIMAL",
            "potassium": "OPTIMAL",
            "ph": "NEUTRAL",
            "organic_carbon": "HIGH",
            "electrical_conductivity": "NORMAL"
        },
        "explanation": {
            "summary": "Soil health index is 85.0 (Optimal) with balanced macro-nutrients and neutral pH.",
            "inputs": {},
            "primary_factor": "NONE"
        },
        "recorded_at": now - timedelta(days=10)
    }
    await db.soil_records.insert_one(healthy_soil)

    seeded_farms.append({
        "farm_id": str(healthy_farm_id),
        "name": "Demo Farm - Green Valley (Healthy Farm)",
        "crop": "WHEAT",
        "status": "Healthy"
    })

    # ==========================================
    # 3. SEED DISEASE OUTBREAK FARM
    # ==========================================
    outbreak_farm_doc = {
        "user_id": user_id,
        "name": "Demo Farm - Harvest Crest (Outbreak Farm)",
        "area": 8.5,
        "area_unit": "ACRE",
        "latitude": 26.91,
        "longitude": 75.81,
        "state": "Rajasthan",
        "district": "Jaipur",
        "created_at": now
    }
    outbreak_res = await db.farms.insert_one(outbreak_farm_doc)
    outbreak_farm_id = outbreak_res.inserted_id

    outbreak_plot_doc = {
        "farm_id": outbreak_farm_id,
        "name": "Plot Beta (Wheat)",
        "area": 8.5,
        "area_unit": "ACRE",
        "created_at": now
    }
    outbreak_plot_res = await db.plots.insert_one(outbreak_plot_doc)
    outbreak_plot_id = outbreak_plot_res.inserted_id

    outbreak_cycle_doc = {
        "plot_id": outbreak_plot_id,
        "farm_id": outbreak_farm_id,
        "crop_type": "WHEAT",
        "season": "RABI",
        "sowing_date": now - timedelta(days=35),
        "expected_harvest_date": now + timedelta(days=85),
        "status": "ACTIVE",
        "current_gdd": 380.0,
        "created_at": now,
        "updated_at": now
    }
    outbreak_cycle_res = await db.crop_cycles.insert_one(outbreak_cycle_doc)
    outbreak_cycle_id = outbreak_cycle_res.inserted_id

    # Seed 5 stress logs with MEDIUM risk values
    outbreak_stress_logs = []
    for day in range(5):
        log_time = now - timedelta(days=day)
        fsi_val = 0.22 + (day * 0.042)  # medium stress: 0.22 -> 0.39 (0-1 scale)
        outbreak_stress_logs.append({
            "farm_id": outbreak_farm_id,
            "user_id": user_id,
            "crop_cycle_id": outbreak_cycle_id,
            "crop_type": "WHEAT",
            "stage": "TILLERING",
            "fsi_score": fsi_val,
            "classification": "MEDIUM",
            "primary_factor": "MOISTURE",
            "components": {"temp_stress": 0.15, "rainfall_deficit": 0.45, "gdd_scale": 0.25},
            "explanation": {"summary": f"Medium stress of {fsi_val:.2f} due to mild moisture deficit and rising humidity.", "inputs": {}, "primary_factor": "MOISTURE"},
            "calculated_at": log_time
        })
    await db.stress_logs.insert_many(outbreak_stress_logs)

    # Seed 3 disease reports (including Wheat Rust and Powdery Mildew)
    outbreak_disease_reports = [
        {
            "user_id": user_id,
            "farm_id": outbreak_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "HEALTHY",
            "confidence": None,
            "deterministic_status": "HEALTHY",
            "location": {"type": "Point", "coordinates": [75.81, 26.91]},
            "created_at": now - timedelta(days=5),
            "disease_name": "Healthy Canopy",
            "severity": "None",
            "what_it_means": "No visual disease symptoms detected in the leaf scan.",
            "immediate_actions": ["Continue standard monitoring."],
            "recommended_treatment": None,
            "prevention_advice": [],
            "risk_level": "Low",
            "crop_confidence": 0.95,
            "validation_result": True,
            "region_validation_result": True
        },
        {
            "user_id": user_id,
            "farm_id": outbreak_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "POWDERY_MILDEW",
            "confidence": 0.78,
            "deterministic_status": "POSSIBLE_DISEASE",
            "location": {"type": "Point", "coordinates": [75.81, 26.91]},
            "created_at": now - timedelta(days=3),
            "disease_name": "Powdery Mildew",
            "severity": "Medium",
            "what_it_means": "White powdery patches on wheat leaves, inhibiting photosynthesis.",
            "immediate_actions": [
                "Apply sulphur dust or propiconazole fungicide.",
                "Reduce irrigation frequency to lower canopy humidity."
            ],
            "recommended_treatment": "Chemical Spray: Propiconazole 25% EC @ 200 ml per acre.",
            "prevention_advice": [
                "Sow disease-resistant wheat varieties.",
                "Avoid excessive nitrogen fertilization."
            ],
            "risk_level": "Medium",
            "crop_confidence": 0.91,
            "validation_result": True,
            "region_validation_result": True
        },
        {
            "user_id": user_id,
            "farm_id": outbreak_farm_id,
            "crop_type": "WHEAT",
            "detected_disease": "WHEAT_RUST",
            "confidence": 0.91,
            "deterministic_status": "CONFIRMED_DISEASE",
            "location": {"type": "Point", "coordinates": [75.81, 26.91]},
            "created_at": now - timedelta(days=2),
            "disease_name": "Wheat Rust",
            "severity": "High",
            "what_it_means": "Orange-brown powdery pustules covering leaf surfaces, threatening yield.",
            "immediate_actions": [
                "Spray tebuconazole or propiconazole fungicide immediately.",
                "Isolate affected plots and restrict movement."
            ],
            "recommended_treatment": "Chemical Spray: Tebuconazole 250 EC @ 200 ml per acre.",
            "prevention_advice": [
                "Monitor regional rust alerts.",
                "Plant rust-resistant cultivars."
            ],
            "risk_level": "High",
            "crop_confidence": 0.93,
            "validation_result": True,
            "region_validation_result": True
        }
    ]
    await db.disease_reports.insert_many(outbreak_disease_reports)

    # Seed 1 active alert for outbreak farm
    outbreak_alert = {
        "user_id": user_id,
        "farm_id": outbreak_farm_id,
        "rule_id": "RULE_FSI_HIGH",
        "severity": "critical",
        "title": "High Disease Outbreak Risk",
        "message": "Wheat Rust confirmed scan has triggered a regional crop safety alert. Please check recommended treatments immediately.",
        "explanation": {
            "summary": "Rule RULE_FSI_HIGH triggered: Wheat Rust disease confirmed visually.",
            "inputs": {"stage": "TILLERING", "disease": "WHEAT_RUST", "status": "CONFIRMED_DISEASE"},
            "primary_factor": "DISEASE"
        },
        "read": False,
        "dedup_key": f"RULE_FSI_HIGH:{outbreak_farm_id}:{now.date().isoformat()}",
        "created_at": now - timedelta(days=2),
        "expires_at": now + timedelta(days=5)
    }
    await db.alerts.insert_one(outbreak_alert)

    seeded_farms.append({
        "farm_id": str(outbreak_farm_id),
        "name": "Demo Farm - Harvest Crest (Outbreak Farm)",
        "crop": "WHEAT",
        "status": "Outbreak"
    })

    # ==========================================
    # 4. SEED HIGH-RISK FARM
    # ==========================================
    high_risk_farm_doc = {
        "user_id": user_id,
        "name": "Demo Farm - Dry Plains (High-Risk Farm)",
        "area": 12.0,
        "area_unit": "ACRE",
        "latitude": 26.92,
        "longitude": 75.82,
        "state": "Rajasthan",
        "district": "Jaipur",
        "created_at": now
    }
    hr_res = await db.farms.insert_one(high_risk_farm_doc)
    hr_farm_id = hr_res.inserted_id

    hr_plot_doc = {
        "farm_id": hr_farm_id,
        "name": "Plot Gamma (Wheat)",
        "area": 12.0,
        "area_unit": "ACRE",
        "created_at": now
    }
    hr_plot_res = await db.plots.insert_one(hr_plot_doc)
    hr_plot_id = hr_plot_res.inserted_id

    hr_cycle_doc = {
        "plot_id": hr_plot_id,
        "farm_id": hr_farm_id,
        "crop_type": "WHEAT",
        "season": "RABI",
        "sowing_date": now - timedelta(days=40),
        "expected_harvest_date": now + timedelta(days=80),
        "status": "ACTIVE",
        "current_gdd": 410.0,
        "created_at": now,
        "updated_at": now
    }
    hr_cycle_res = await db.crop_cycles.insert_one(hr_cycle_doc)
    hr_cycle_id = hr_cycle_res.inserted_id

    # Seed 5 stress logs with HIGH risk values
    hr_stress_logs = []
    for day in range(5):
        log_time = now - timedelta(days=day)
        fsi_val = 0.62 + (day * 0.05)  # high stress: 0.62 -> 0.82 (0-1 scale)
        hr_stress_logs.append({
            "farm_id": hr_farm_id,
            "user_id": user_id,
            "crop_cycle_id": hr_cycle_id,
            "crop_type": "WHEAT",
            "stage": "BOOTING",
            "fsi_score": fsi_val,
            "classification": "HIGH",
            "primary_factor": "THERMAL",
            "components": {"temp_stress": 0.85, "rainfall_deficit": 0.72, "gdd_scale": 0.65},
            "explanation": {"summary": f"High field stress of {fsi_val:.2f} due to extreme temperatures (38°C) and severe rainfall deficit.", "inputs": {}, "primary_factor": "THERMAL"},
            "calculated_at": log_time
        })
    await db.stress_logs.insert_many(hr_stress_logs)

    # Seed 1 Wheat Rust possible report
    hr_disease_report = {
        "user_id": user_id,
        "farm_id": hr_farm_id,
        "crop_type": "WHEAT",
        "detected_disease": "WHEAT_RUST",
        "confidence": 0.82,
        "deterministic_status": "POSSIBLE_DISEASE",
        "location": {"type": "Point", "coordinates": [75.82, 26.92]},
        "created_at": now - timedelta(days=1),
        "disease_name": "Wheat Rust",
        "severity": "High",
        "what_it_means": "Orange-brown powdery pustules covering leaf surfaces, threatening yield.",
        "immediate_actions": [
            "Spray tebuconazole or propiconazole fungicide immediately.",
            "Isolate affected plots and restrict movement."
        ],
        "recommended_treatment": "Chemical Spray: Tebuconazole 250 EC @ 200 ml per acre.",
        "prevention_advice": [
            "Monitor regional rust alerts.",
            "Plant rust-resistant cultivars."
        ],
        "risk_level": "High",
        "crop_confidence": 0.91,
        "validation_result": True,
        "region_validation_result": True
    }
    await db.disease_reports.insert_one(hr_disease_report)

    # Seed 3 active alerts for high-risk farm
    hr_alerts = [
        {
            "user_id": user_id,
            "farm_id": hr_farm_id,
            "rule_id": "RULE_RAINFALL_DEFICIT",
            "severity": "warning",
            "title": "Severe Moisture Deficit Alert",
            "message": "Rainfall deficit exceeds 80% over the last 14 days. Irrigation cycle is highly recommended.",
            "explanation": {
                "summary": "Rule RULE_RAINFALL_DEFICIT triggered: moisture score at critical deficit.",
                "inputs": {"deficit": 0.82, "threshold": 0.60},
                "primary_factor": "MOISTURE"
            },
            "read": False,
            "dedup_key": f"RULE_RAINFALL_DEFICIT:{hr_farm_id}:{now.date().isoformat()}",
            "created_at": now - timedelta(days=4),
            "expires_at": now + timedelta(days=5)
        },
        {
            "user_id": user_id,
            "farm_id": hr_farm_id,
            "rule_id": "RULE_THERMAL_HIGH",
            "severity": "warning",
            "title": "Extreme Thermal Stress Alert",
            "message": "Maximum temperature exceeded 38°C for 3 consecutive days. Heat mitigation sprays required.",
            "explanation": {
                "summary": "Rule RULE_THERMAL_HIGH triggered: temperature exceeded crop threshold.",
                "inputs": {"max_temp": 38.4, "threshold": 35.0},
                "primary_factor": "THERMAL"
            },
            "read": False,
            "dedup_key": f"RULE_THERMAL_HIGH:{hr_farm_id}:{now.date().isoformat()}",
            "created_at": now - timedelta(days=3),
            "expires_at": now + timedelta(days=5)
        },
        {
            "user_id": user_id,
            "farm_id": hr_farm_id,
            "rule_id": "RULE_FSI_HIGH",
            "severity": "critical",
            "title": "Critical Stress Level Alert",
            "message": "Field Stress Index has reached a critical value of 82.1. Immediate crop protection required.",
            "explanation": {
                "summary": "Rule RULE_FSI_HIGH triggered: total FSI exceeds 70% threshold.",
                "inputs": {"fsi": 82.1, "threshold": 70.0},
                "primary_factor": "THERMAL"
            },
            "read": False,
            "dedup_key": f"RULE_FSI_HIGH:{hr_farm_id}:{now.date().isoformat()}",
            "created_at": now - timedelta(days=1),
            "expires_at": now + timedelta(days=5)
        }
    ]
    await db.alerts.insert_many(hr_alerts)

    # Seed deficient soil record
    hr_soil = {
        "farm_id": hr_farm_id,
        "user_id": user_id,
        "crop_type": "WHEAT",
        "nitrogen": 120.0,
        "phosphorus": 8.0,
        "potassium": 110.0,
        "ph": 8.2,
        "organic_carbon": 0.28,
        "electrical_conductivity": 2.5,
        "soil_health_index": 42.0,
        "deficiency_status": {
            "nitrogen": "LOW",
            "phosphorus": "LOW",
            "potassium": "MEDIUM",
            "ph": "ALKALINE",
            "organic_carbon": "LOW",
            "electrical_conductivity": "HIGH"
        },
        "explanation": {
            "summary": "Soil health index is 42.0 (Poor) with severe Nitrogen/Phosphorus deficiencies and alkaline pH.",
            "inputs": {},
            "primary_factor": "NITROGEN"
        },
        "recorded_at": now - timedelta(days=8)
    }
    await db.soil_records.insert_one(hr_soil)

    seeded_farms.append({
        "farm_id": str(hr_farm_id),
        "name": "Demo Farm - Dry Plains (High-Risk Farm)",
        "crop": "WHEAT",
        "status": "High-Risk"
    })

    # Seed 3 mock SOS dispatches: Successful (DELIVERED), Failed (FAILED), Offline (QUEUED)
    successful_sos = {
        "user_id": user_id,
        "farm_id": healthy_farm_id,
        "emergency_type": "FLOOD",
        "coordinates": {"type": "Point", "coordinates": [75.80, 26.90]},
        "checklist": [
            "Current crop stage: Tillering. Field stress: LOW_STRESS (FSI 0.12).",
            "Contact nearest KVK (Krishi Vigyan Kendra) for recovery guidance."
        ],
        "plain_text_message": "HarvestIQ SOS [FLOOD]\nFarmer: Demo Farmer\nFarm: Green Valley\nStatus: Active",
        "delivery_status": "DELIVERED",
        "recipients": [
            {"role": "farmer", "phone": "9999999999", "status": "DELIVERED", "message_sid": "SM1234567890"},
            {"role": "primary", "phone": "9876543210", "status": "DELIVERED", "message_sid": "SM0987654321"}
        ],
        "intelligence_snapshot_version": "v2",
        "triggered_at": now - timedelta(days=2)
    }
    
    failed_sos = {
        "user_id": user_id,
        "farm_id": outbreak_farm_id,
        "emergency_type": "FROST",
        "coordinates": {"type": "Point", "coordinates": [75.81, 26.91]},
        "checklist": [
            "Current crop stage: Flowering. Field stress: HIGH_STRESS (FSI 0.82).",
            "Consult nearest KVK if frost damage becomes widespread."
        ],
        "plain_text_message": "HarvestIQ SOS [FROST]\nFarmer: Demo Farmer\nFarm: Harvest Crest\nStatus: Error",
        "delivery_status": "FAILED",
        "recipients": [
            {"role": "farmer", "phone": "9999999999", "status": "FAILED", "message_sid": None, "error": "Carrier violation / invalid number"},
            {"role": "primary", "phone": "9876543210", "status": "FAILED", "message_sid": None, "error": "Twilio Account Suspended"}
        ],
        "intelligence_snapshot_version": "v2",
        "triggered_at": now - timedelta(days=1)
    }

    queued_sos = {
        "user_id": user_id,
        "farm_id": hr_farm_id,
        "emergency_type": "HEATWAVE",
        "coordinates": {"type": "Point", "coordinates": [75.82, 26.92]},
        "checklist": [
            "Current crop stage: Grain-Filling. Field stress: HIGH_STRESS (FSI 0.82).",
            "Contact local KVK for heat stress mitigation recommendations."
        ],
        "plain_text_message": "HarvestIQ SOS [HEATWAVE]\nFarmer: Demo Farmer\nFarm: Dry Plains\nStatus: Queued",
        "delivery_status": "QUEUED",
        "recipients": [
            {"role": "farmer", "phone": "9999999999", "status": "QUEUED", "message_sid": None},
            {"role": "primary", "phone": "9876543210", "status": "QUEUED", "message_sid": None}
        ],
        "intelligence_snapshot_version": "v2",
        "triggered_at": now - timedelta(hours=3)
    }

    res_ins = db.sos_actions.insert_many([successful_sos, failed_sos, queued_sos])
    if hasattr(res_ins, "__await__"):
        await res_ins

    from app.services.operations_copilot_service import OperationsCopilotService

    copilot = OperationsCopilotService(db)
    for farm_entry in seeded_farms:
        try:
            await copilot.generate_plan(str(user_id), farm_entry["farm_id"], language="en", persist=True)
        except Exception:
            pass

    return DemoSeedResponse(
        success=True,
        message=f"Successfully seeded {len(seeded_farms)} demo farms and SOS dispatches for user.",
        farms=seeded_farms
    )
