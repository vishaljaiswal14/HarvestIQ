from typing import Optional
from pydantic import BaseModel


class ProfitabilityMetrics(BaseModel):
    total_cost: float
    total_revenue: float
    net_profit: float
    roi_percent: float
    cost_per_unit: float
    revenue_per_unit: float
    break_even_yield: float
    break_even_price: float


class CropCycleProfitability(BaseModel):
    crop_cycle_id: str
    crop_type: str
    season: str
    metrics: ProfitabilityMetrics


class FarmProfitabilitySummary(BaseModel):
    total_cost: float
    total_revenue: float
    total_profit: float
    best_performing_crop: str
    worst_performing_crop: str
    roi_percent: float


class SeasonProfitability(BaseModel):
    season: str
    profit: float
    roi: float
