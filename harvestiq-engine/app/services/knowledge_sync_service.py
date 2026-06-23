from datetime import datetime, timezone
from typing import List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.knowledge_schemas import (
    KnowledgeSyncResponse,
    LocalCropSchema,
    LocalCropStageSchema,
    LocalDiseaseSchema,
    LocalCropCalendarSchema,
)

# Reference data for crops
CROP_METADATA: Dict[str, Dict[str, Any]] = {
    "WHEAT": {
        "water_req_mm": 450.0,
        "soil_ph_min": 6.0,
        "soil_ph_max": 7.5,
        "nitrogen_rdf": 120.0,
        "phosphorus_rdf": 60.0,
        "potassium_rdf": 40.0,
    },
    "RICE": {
        "water_req_mm": 1200.0,
        "soil_ph_min": 5.5,
        "soil_ph_max": 7.0,
        "nitrogen_rdf": 120.0,
        "phosphorus_rdf": 60.0,
        "potassium_rdf": 60.0,
    },
    "COTTON": {
        "water_req_mm": 750.0,
        "soil_ph_min": 6.0,
        "soil_ph_max": 8.0,
        "nitrogen_rdf": 100.0,
        "phosphorus_rdf": 50.0,
        "potassium_rdf": 50.0,
    },
    "MAIZE": {
        "water_req_mm": 500.0,
        "soil_ph_min": 5.8,
        "soil_ph_max": 7.2,
        "nitrogen_rdf": 120.0,
        "phosphorus_rdf": 60.0,
        "potassium_rdf": 40.0,
    },
    "SUGARCANE": {
        "water_req_mm": 1500.0,
        "soil_ph_min": 6.0,
        "soil_ph_max": 8.0,
        "nitrogen_rdf": 250.0,
        "phosphorus_rdf": 100.0,
        "potassium_rdf": 125.0,
    },
    "POTATO": {
        "water_req_mm": 500.0,
        "soil_ph_min": 5.2,
        "soil_ph_max": 6.4,
        "nitrogen_rdf": 120.0,
        "phosphorus_rdf": 80.0,
        "potassium_rdf": 120.0,
    },
    "SOYBEAN": {
        "water_req_mm": 600.0,
        "soil_ph_min": 6.0,
        "soil_ph_max": 7.5,
        "nitrogen_rdf": 30.0,
        "phosphorus_rdf": 60.0,
        "potassium_rdf": 40.0,
    },
    "MUSTARD": {
        "water_req_mm": 300.0,
        "soil_ph_min": 6.0,
        "soil_ph_max": 7.5,
        "nitrogen_rdf": 80.0,
        "phosphorus_rdf": 40.0,
        "potassium_rdf": 40.0,
    },
}

# Offline diseases lookup data
DISEASE_METADATA: List[Dict[str, str]] = [
    {
        "disease_tag": "WHEAT_RUST",
        "display_name": "Wheat Leaf Rust",
        "crop_type": "WHEAT",
        "symptoms": "Orange-brown pustules on leaves, disrupt photosynthesis",
        "causes": "Puccinia graminis fungus spread by wind and high moisture",
        "treatment_physical": "Rotate crops with non-cereal options; clear crop residue from fields",
        "treatment_chemical": "Spray Propiconazole or Tebuconazole fungicide",
    },
    {
        "disease_tag": "POWDERY_MILDEW",
        "display_name": "Powdery Mildew",
        "crop_type": "WHEAT",
        "symptoms": "White powdery circular patches on leaf surfaces",
        "causes": "Blumeria graminis fungus under cool, humid, and shaded conditions",
        "treatment_physical": "Improve crop spacing to increase sunlight exposure and air flow",
        "treatment_chemical": "Apply wettable sulphur or Triadimefon fungicide",
    },
    {
        "disease_tag": "BLAST",
        "display_name": "Rice Blast",
        "crop_type": "RICE",
        "symptoms": "Spindle-shaped lesions on leaves with reddish-brown borders and gray centers",
        "causes": "Magnaporthe oryzae fungus favored by high nitrogen fertilizer use",
        "treatment_physical": "Avoid over-fertilizing with nitrogen; plant resistant seed varieties",
        "treatment_chemical": "Apply Tricyclazole or Isoprothiolane fungicide spray",
    },
    {
        "disease_tag": "BROWN_SPOT",
        "display_name": "Brown Spot of Rice",
        "crop_type": "RICE",
        "symptoms": "Oval, brown spots resembling sesame seeds on leaves",
        "causes": "Bipolaris oryzae fungus associated with potassium-deficient soils",
        "treatment_physical": "Ensure balanced soil NPK nutrient application; improve field drainage",
        "treatment_chemical": "Seed treatment or spray with Mancozeb or Edifenphos",
    },
    {
        "disease_tag": "LATE_BLIGHT",
        "display_name": "Potato Late Blight",
        "crop_type": "POTATO",
        "symptoms": "Water-soaked dark lesions on leaves with fine white mold on the underside",
        "causes": "Phytophthora infestans oomycete triggered by cold, humid weather",
        "treatment_physical": "Sow certified disease-free seed tubers; remove infected volunteers immediately",
        "treatment_chemical": "Spray Mancozeb proactively or Metalaxyl-Moxynil when lesions appear",
    },
    {
        "disease_tag": "RED_ROT",
        "display_name": "Red Rot of Sugarcane",
        "crop_type": "SUGARCANE",
        "symptoms": "Reddening of internal stalk tissues with white horizontal bands and acidic smell",
        "causes": "Colletotrichum falcatum fungus spread by infected planting setts",
        "treatment_physical": "Use healthy, treated seed setts; execute crop rotation for at least 2 seasons",
        "treatment_chemical": "Treat seed setts with Carbendazim before planting",
    },
]

# Calendar stage guidelines mapping
CALENDAR_GUIDELINES: Dict[str, Dict[str, Dict[str, str]]] = {
    "GERMINATION": {
        "instructions": "Keep soil moist to support seedling emergence. Monitor surface crusting.",
        "fertilizer_recommendation": "Apply basal dose of NPK (1/3rd Nitrogen, full Phosphorus and Potassium)."
    },
    "SPROUTING": {
        "instructions": "Ensure light watering to promote tuber shoots. Avoid soil logging.",
        "fertilizer_recommendation": "Apply basal NPK dose."
    },
    "TILLERING": {
        "instructions": "Perform first weeding. Keep fields wet but not flooded.",
        "fertilizer_recommendation": "Top-dress with 1/3rd Urea dose after weeding."
    },
    "VEGETATIVE": {
        "instructions": "Perform inter-culture operations. Look out for leaf curl symptoms.",
        "fertilizer_recommendation": "Top-dress with 1/3rd Urea dose."
    },
    "SQUARING": {
        "instructions": "Maintain optimal irrigation. Monitor cotton square retention.",
        "fertilizer_recommendation": "Apply foliar spray of micro-nutrients if deficiency appears."
    },
    "FLOWERING": {
        "instructions": "Ensure steady irrigation. High sensitivity to water deficit stress.",
        "fertilizer_recommendation": "Apply final Urea top-dressing. Avoid heavy spray applications during peak bloom."
    },
    "TASSELING": {
        "instructions": "Maintain moisture. Critical pollen shed phase.",
        "fertilizer_recommendation": "Apply Nitrogen top-dressing."
    },
    "TUBER INITIATION": {
        "instructions": "Ensure soil is loose. Hill the soil around potato plants.",
        "fertilizer_recommendation": "Apply potassium-rich top-dressing for tuber development."
    },
    "GRAND GROWTH": {
        "instructions": "Irrigate crop regularly. Support tall sugarcane stalks by tie-up/earthing up.",
        "fertilizer_recommendation": "Apply final fertilizer top-dress."
    },
    "MATURITY": {
        "instructions": "Withhold irrigation 10-15 days prior to harvest. Allow crop to dry naturally.",
        "fertilizer_recommendation": "No fertilizer application."
    },
    "BOLL OPENING": {
        "instructions": "Avoid watering. Pick mature bolls to prevent fiber degradation.",
        "fertilizer_recommendation": "No fertilizer application."
    }
}


class KnowledgeSyncService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def get_sync_payload(self) -> KnowledgeSyncResponse:
        # Fetch crop characteristics from DB
        cursor = self.db.crop_characteristics.find({})
        crops: List[LocalCropSchema] = []
        stages: List[LocalCropStageSchema] = []
        calendars: List[LocalCropCalendarSchema] = []

        async for char in cursor:
            crop_type = char["crop_type"].upper()
            display_name = char["display_name"]
            gdd_base_temp = char["gdd_base_temp"]

            # Load extended crop parameters
            meta = CROP_METADATA.get(crop_type, {
                "water_req_mm": 500.0,
                "soil_ph_min": 5.5,
                "soil_ph_max": 7.5,
                "nitrogen_rdf": 100.0,
                "phosphorus_rdf": 50.0,
                "potassium_rdf": 50.0,
            })

            crops.append(
                LocalCropSchema(
                    crop_type=crop_type,
                    display_name=display_name,
                    gdd_base_temp=gdd_base_temp,
                    water_req_mm=meta["water_req_mm"],
                    soil_ph_min=meta["soil_ph_min"],
                    soil_ph_max=meta["soil_ph_max"],
                    nitrogen_rdf=meta["nitrogen_rdf"],
                    phosphorus_rdf=meta["phosphorus_rdf"],
                    potassium_rdf=meta["potassium_rdf"],
                )
            )

            # Map stages
            db_stages = char.get("stages", [])
            vulnerabilities = char.get("stage_vulnerability", {})
            for idx, stage in enumerate(db_stages):
                s_name = stage["name"]
                s_name_upper = s_name.upper()
                vuln = vulnerabilities.get(s_name, 0.5)

                # Determine water demand coefficients based on stage
                coef = 1.0
                if "FLOWER" in s_name_upper or "TASSEL" in s_name_upper:
                    coef = 1.5
                elif "MATURITY" in s_name_upper or "OPENING" in s_name_upper:
                    coef = 0.7

                stages.append(
                    LocalCropStageSchema(
                        crop_type=crop_type,
                        stage_name=s_name,
                        gdd_min=stage["gdd_min"],
                        gdd_max=stage["gdd_max"],
                        vulnerability=vuln,
                        water_demand_coefficient=coef,
                    )
                )

                # Map stage to calendar instructions
                stage_guidelines = CALENDAR_GUIDELINES.get(
                    s_name_upper, {
                        "instructions": "Monitor field condition and check local warnings.",
                        "fertilizer_recommendation": None
                    }
                )

                calendars.append(
                    LocalCropCalendarSchema(
                        crop_type=crop_type,
                        stage_name=s_name,
                        instructions=stage_guidelines["instructions"],
                        fertilizer_recommendation=stage_guidelines["fertilizer_recommendation"],
                    )
                )

        # Assemble disease array
        diseases: List[LocalDiseaseSchema] = []
        for dm in DISEASE_METADATA:
            diseases.append(LocalDiseaseSchema(**dm))

        return KnowledgeSyncResponse(
            timestamp=datetime.now(timezone.utc),
            crops=crops,
            stages=stages,
            diseases=diseases,
            calendars=calendars,
        )
