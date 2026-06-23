from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class LocalCropSchema(BaseModel):
    crop_type: str
    display_name: str
    gdd_base_temp: float
    water_req_mm: float = 0.0
    soil_ph_min: float = 5.0
    soil_ph_max: float = 8.5
    nitrogen_rdf: float = 0.0
    phosphorus_rdf: float = 0.0
    potassium_rdf: float = 0.0

class LocalCropStageSchema(BaseModel):
    crop_type: str
    stage_name: str
    gdd_min: float
    gdd_max: float
    vulnerability: float
    water_demand_coefficient: float = 1.0

class LocalDiseaseSchema(BaseModel):
    disease_tag: str
    display_name: str
    crop_type: str
    symptoms: str
    causes: str
    treatment_physical: str
    treatment_chemical: str

class LocalCropCalendarSchema(BaseModel):
    crop_type: str
    stage_name: str
    instructions: str
    fertilizer_recommendation: Optional[str] = None

class KnowledgeSyncResponse(BaseModel):
    timestamp: datetime
    crops: List[LocalCropSchema]
    stages: List[LocalCropStageSchema]
    diseases: List[LocalDiseaseSchema]
    calendars: List[LocalCropCalendarSchema]
