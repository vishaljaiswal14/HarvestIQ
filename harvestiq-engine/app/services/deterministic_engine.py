from datetime import date
from typing import Iterable, List, Sequence

from app.core.constants.disease import (
    DISEASE_STATUS_HEALTHY,
    DISEASE_STATUS_UNKNOWN,
    DISEASE_STATUS_POSSIBLE_DISEASE,
    DISEASE_STATUS_CONFIRMED_DISEASE,
    DISEASE_STATUS_LOW_CONFIDENCE,
)
from app.core.constants.fsi import (
    CLASSIFICATION_HIGH,
    CLASSIFICATION_LOW,
    CLASSIFICATION_MEDIUM,
    FSI_WEIGHTS,
    LOW_STRESS_MAX,
    MEDIUM_STRESS_MAX,
    TEMP_CRITICAL_C,
    TEMP_OPTIMAL_C,
)
from app.core.constants.momentum import (
    FALLING_THRESHOLD,
    MOMENTUM_FALLING,
    MOMENTUM_RISING,
    MOMENTUM_SCALE,
    MOMENTUM_STABLE,
    RISING_THRESHOLD,
)
from app.core.constants.optimizer import (
    ACTION_FERTILIZE,
    ACTION_SPRAY,
    RULE_HIGH_FSI_FERTILIZE,
    RULE_HIGH_WIND,
    RULE_RAIN_FORECAST,
)
from app.core.constants.yield_risk import (
    LOW_RISK_MAX,
    MEDIUM_RISK_MAX,
    RISK_BAND_HIGH,
    RISK_BAND_LOW,
    RISK_BAND_MEDIUM,
    WEIGHT_DISEASE,
    WEIGHT_FSI,
    WEIGHT_MOMENTUM,
    WEIGHT_SOIL,
    WEIGHT_STAGE,
)
from app.core.constants.soil import (
    NUTRIENT_HIGH,
    NUTRIENT_LOW,
    NUTRIENT_OPTIMAL,
    SOIL_HEALTH_WEIGHTS,
)
from app.models.engine_schemas import CropStageDefinition, StageTimelineEntry


def calculate_daily_gdd(t_min: float, t_max: float, base_temp: float) -> float:
    average_temp = (t_max + t_min) / 2
    return max(average_temp - base_temp, 0.0)


def accumulate_gdd(daily_entries: Iterable[tuple[date, float]], sowing_date: date) -> float:
    total = 0.0
    for entry_date, gdd_value in daily_entries:
        if entry_date >= sowing_date:
            total += gdd_value
    return round(total, 2)


def resolve_growth_stage(
    accumulated_gdd: float,
    stages: Sequence[CropStageDefinition],
) -> tuple[str, float, List[StageTimelineEntry]]:
    if not stages:
        return "Unknown", 0.0, []

    ordered = sorted(stages, key=lambda stage: stage.gdd_min)
    current_stage = ordered[-1]
    progress_percentage = 100.0

    for stage in ordered:
        if accumulated_gdd < stage.gdd_max:
            current_stage = stage
            span = max(stage.gdd_max - stage.gdd_min, 1.0)
            progress_percentage = min(
                max(((accumulated_gdd - stage.gdd_min) / span) * 100.0, 0.0),
                100.0,
            )
            break

    timeline: List[StageTimelineEntry] = []
    for stage in ordered:
        is_completed = accumulated_gdd >= stage.gdd_max
        is_current = stage.name == current_stage.name
        timeline.append(
            StageTimelineEntry(
                name=stage.name,
                gdd_min=stage.gdd_min,
                gdd_max=stage.gdd_max,
                is_current=is_current,
                is_completed=is_completed,
            )
        )

    return current_stage.name, round(progress_percentage, 2), timeline


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return min(max(value, lower), upper)


def calculate_temp_stress(
    current_temp: float,
    forecast_temp_max: Sequence[float],
    t_opt: float = TEMP_OPTIMAL_C,
    t_crit: float = TEMP_CRITICAL_C,
) -> float:
    forecast_window = list(forecast_temp_max[:3])
    t_max_3d = max(forecast_window) if forecast_window else current_temp
    t_effective = max(current_temp, t_max_3d)
    if t_effective <= t_opt:
        return 0.0
    span = max(t_crit - t_opt, 1.0)
    return round(_clamp((t_effective - t_opt) / span), 4)


def calculate_rainfall_deficit(
    forecast_precip: Sequence[float],
    expected_daily_mm: float = 5.0,
    days: int = 3,
) -> float:
    window = list(forecast_precip[:days])
    if not window:
        return 1.0
    p_total = sum(window)
    e_total = expected_daily_mm * len(window)
    if e_total <= 0:
        return 0.0
    moisture_ratio = p_total / e_total
    return round(_clamp(1.0 - moisture_ratio), 4)


def calculate_gdd_scale(
    current_gdd: float,
    stage_gdd_max: float,
    stage_vulnerability: float,
) -> float:
    if stage_gdd_max <= 0:
        return 0.0
    gdd_progress = _clamp(current_gdd / stage_gdd_max)
    return round(_clamp(stage_vulnerability * gdd_progress), 4)


def compute_fsi(temp_stress: float, rainfall_deficit: float, gdd_scale: float) -> float:
    w_temp, w_rain, w_gdd = FSI_WEIGHTS
    fsi = (w_temp * temp_stress) + (w_rain * rainfall_deficit) + (w_gdd * gdd_scale)
    return round(_clamp(fsi), 2)


def classify_fsi(fsi: float) -> str:
    if fsi <= LOW_STRESS_MAX:
        return CLASSIFICATION_LOW
    if fsi <= MEDIUM_STRESS_MAX:
        return CLASSIFICATION_MEDIUM
    return CLASSIFICATION_HIGH


def resolve_primary_factor(
    temp_stress: float,
    rainfall_deficit: float,
    gdd_scale: float,
) -> str:
    weighted = {
        "THERMAL": FSI_WEIGHTS[0] * temp_stress,
        "MOISTURE": FSI_WEIGHTS[1] * rainfall_deficit,
        "GDD": FSI_WEIGHTS[2] * gdd_scale,
    }
    return max(weighted, key=weighted.get)  # type: ignore[arg-type]


def normalize_disease_tag(disease_name: str) -> str:
    cleaned = disease_name.strip().upper().replace("-", "_").replace(" ", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
        
    aliases = {
        "YELLOW_RUST": "WHEAT_RUST",
        "STRIPE_RUST": "WHEAT_RUST",
        "WHEAT_YELLOW_RUST": "WHEAT_RUST",
        "WHEAT_STRIPE_RUST": "WHEAT_RUST",
        "RUST_OF_WHEAT": "WHEAT_RUST",
        "YELLOW_RUST_OF_WHEAT": "WHEAT_RUST",
        "STRIPE_RUST_OF_WHEAT": "WHEAT_RUST",
        "WHEAT_RUSTS": "WHEAT_RUST",
        "RICE_BLAST": "BLAST",
        "RICE_BROWN_SPOT": "BROWN_SPOT",
        "EARLY_BLIGHT_POTATO": "EARLY_BLIGHT",
        "LATE_BLIGHT_POTATO": "LATE_BLIGHT",
        "RED_ROT_SUGARCANE": "RED_ROT",
        "RED_ROT_OF_SUGARCANE": "RED_ROT",
    }
    return aliases.get(cleaned, cleaned)


from typing import Optional

def confirm_disease_detection(
    crop_type: str,
    state: str,
    detected_disease: str,
    confidence: Optional[float],
    confidence_threshold: float,
    allowed_by_crop: dict[str, dict[str, list[str]]],
) -> tuple[str, str]:
    if confidence is None:
        return "UNKNOWN", DISEASE_STATUS_UNKNOWN

    disease_tag = normalize_disease_tag(detected_disease)
    
    if disease_tag == "RUST" and crop_type.strip().upper() == "WHEAT":
        disease_tag = "WHEAT_RUST"
    
    # 1. Healthy check
    if disease_tag == "HEALTHY":
        if confidence >= 0.50:
            return "HEALTHY", DISEASE_STATUS_HEALTHY
        else:
            return "UNKNOWN", DISEASE_STATUS_UNKNOWN

    # 2. Unknown or < 50% confidence
    if disease_tag == "UNKNOWN" or confidence < 0.50:
        return "UNKNOWN", DISEASE_STATUS_UNKNOWN

    # 3. Deterministic Regional Allowed check
    crop_key = crop_type.strip().upper()
    state_key = state.strip().upper().replace(" ", "_")
    crop_rules = allowed_by_crop.get(crop_key, {})
    allowed = set(crop_rules.get(state_key, [])) | set(crop_rules.get("ALL", []))

    is_allowed = False
    if disease_tag in allowed:
        is_allowed = True
    else:
        for candidate in allowed:
            if candidate in disease_tag or disease_tag in candidate:
                is_allowed = True
                break

    # If deterministic validation fails, return UNKNOWN
    if not is_allowed:
        return "UNKNOWN", DISEASE_STATUS_UNKNOWN

    # 4. Confidence gating
    if confidence >= 0.85:
        return disease_tag, DISEASE_STATUS_CONFIRMED_DISEASE
    elif confidence >= 0.70:
        return disease_tag, DISEASE_STATUS_POSSIBLE_DISEASE
    elif confidence >= 0.50:
        return disease_tag, DISEASE_STATUS_LOW_CONFIDENCE
    else:
        return "UNKNOWN", DISEASE_STATUS_UNKNOWN


def evaluate_nutrient_status(value: float, low: float, high: float) -> str:
    if value < low:
        return NUTRIENT_LOW
    if value > high:
        return NUTRIENT_HIGH
    return NUTRIENT_OPTIMAL


def _nutrient_health_score(value: float, low: float, high: float) -> float:
    status = evaluate_nutrient_status(value, low, high)
    if status == NUTRIENT_OPTIMAL:
        return 1.0
    if status == NUTRIENT_LOW:
        if low <= 0:
            return 0.0
        return _clamp(value / low)
    excess = value - high
    span = max(high * 0.5, 0.01)
    return _clamp(1.0 - (excess / span))


def compute_soil_health_index(
    measurements: dict[str, float],
    reference_ranges: dict[str, dict[str, float]],
) -> tuple[float, dict[str, str], dict[str, float]]:
    deficiency_status: dict[str, str] = {}
    nutrient_scores: dict[str, float] = {}

    for nutrient, value in measurements.items():
        bounds = reference_ranges.get(nutrient, {"low": 0.0, "high": 1.0})
        low = float(bounds["low"])
        high = float(bounds["high"])
        deficiency_status[nutrient] = evaluate_nutrient_status(value, low, high)
        nutrient_scores[nutrient] = round(_nutrient_health_score(value, low, high), 4)

    weighted_total = 0.0
    weight_sum = 0.0
    for nutrient, score in nutrient_scores.items():
        weight = SOIL_HEALTH_WEIGHTS.get(nutrient, 0.0)
        weighted_total += weight * score
        weight_sum += weight

    soil_health_index = round(weighted_total / weight_sum, 2) if weight_sum > 0 else 0.0
    return soil_health_index, deficiency_status, nutrient_scores


def compute_stress_momentum(
    fsi_scores: list[float],
) -> tuple[str, float, float, bool]:
    if len(fsi_scores) < 2:
        return MOMENTUM_STABLE, 0.0, 0.0, True

    latest = fsi_scores[-1]
    baseline_scores = fsi_scores[:-1]
    baseline = sum(baseline_scores) / len(baseline_scores)
    delta = round(latest - baseline, 4)
    momentum_score = round(_clamp(abs(delta) / MOMENTUM_SCALE, 0.0, 1.0), 4)

    if delta > RISING_THRESHOLD:
        direction = MOMENTUM_RISING
    elif delta < -FALLING_THRESHOLD:
        direction = MOMENTUM_FALLING
    else:
        direction = MOMENTUM_STABLE

    return direction, momentum_score, delta, False


def compute_yield_risk(
    fsi: float,
    momentum_direction: str,
    momentum_score: float,
    stage: str,
    soil_health_index: float | None,
    disease_present: bool,
    radar_high_nearby: bool,
    stage_vulnerability: float = 0.5,
) -> tuple[str, float, list[str]]:
    factors: list[str] = []
    raw = 0.0

    fsi_component = _clamp(fsi) * WEIGHT_FSI
    raw += fsi_component
    if fsi > MEDIUM_STRESS_MAX:
        factors.append("FSI")

    if momentum_direction == MOMENTUM_RISING:
        raw += momentum_score * WEIGHT_MOMENTUM
        factors.append("RISING_MOMENTUM")
    elif momentum_direction == MOMENTUM_FALLING:
        raw -= momentum_score * (WEIGHT_MOMENTUM * 0.5)

    stage_component = _clamp(stage_vulnerability) * WEIGHT_STAGE
    raw += stage_component
    if stage_vulnerability >= 0.6:
        factors.append("STAGE_VULNERABILITY")

    if soil_health_index is not None:
        soil_stress = _clamp(1.0 - soil_health_index)
        raw += soil_stress * WEIGHT_SOIL
        if soil_health_index < 0.6:
            factors.append("LOW_SOIL_HEALTH")

    if disease_present or radar_high_nearby:
        raw += WEIGHT_DISEASE
        if disease_present:
            factors.append("CONFIRMED_DISEASE")
        if radar_high_nearby:
            factors.append("NEARBY_DISEASE")

    estimated_percent = round(_clamp(raw) * 100.0, 1)
    if estimated_percent < LOW_RISK_MAX:
        band = RISK_BAND_LOW
    elif estimated_percent < MEDIUM_RISK_MAX:
        band = RISK_BAND_MEDIUM
    else:
        band = RISK_BAND_HIGH

    return band, estimated_percent, factors


def evaluate_input_window(
    wind_speed_kmh: float,
    forecast_rain_mm_3d: float,
    fsi_classification: str,
    action_type: str,
    wind_limit: float = 20.0,
    rain_limit: float = 5.0,
) -> tuple[bool, list[str], list[str]]:
    reasons: list[str] = []
    rules: list[str] = []
    safe = True

    if action_type == ACTION_SPRAY and wind_speed_kmh > wind_limit:
        safe = False
        reasons.append(f"Wind speed {wind_speed_kmh} km/h exceeds limit {wind_limit} km/h")
        rules.append(RULE_HIGH_WIND)

    if action_type in {ACTION_SPRAY, ACTION_FERTILIZE} and forecast_rain_mm_3d > rain_limit:
        safe = False
        reasons.append(f"Forecast rain {forecast_rain_mm_3d} mm exceeds limit {rain_limit} mm")
        rules.append(RULE_RAIN_FORECAST)

    if action_type == ACTION_FERTILIZE and fsi_classification == CLASSIFICATION_HIGH:
        safe = False
        reasons.append("High field stress — fertilizer application not recommended")
        rules.append(RULE_HIGH_FSI_FERTILIZE)

    if safe and not reasons:
        reasons.append("Current conditions are within safe operating thresholds")

    return safe, reasons, rules


def simulate_scenario(
    baseline_fsi: float,
    temp_delta: float,
    irrigation_delta: float,
    nitrogen_delta: float,
) -> tuple[float, list[float], float]:
    moisture_effect = irrigation_delta * 0.02
    thermal_effect = temp_delta * 0.03
    nutrient_effect = -nitrogen_delta * 0.01

    projected_fsi = round(
        _clamp(baseline_fsi + thermal_effect - moisture_effect + nutrient_effect),
        2,
    )
    curve = [
        round(_clamp(baseline_fsi + step * (projected_fsi - baseline_fsi) / 4), 2)
        for step in range(5)
    ]
    yield_factor = round(_clamp(1.0 - projected_fsi * 0.5), 4)
    return projected_fsi, curve, yield_factor


def compute_health_risk_rating(
    fsi: float,
    soil_health_index: float | None,
    radar_high_nearby: bool,
    unread_alerts: int,
    yield_risk_percent: float,
) -> tuple[float, str]:
    shi_component = (soil_health_index if soil_health_index is not None else 0.5) * 25.0
    fsi_component = (1.0 - _clamp(fsi)) * 25.0
    radar_component = 0.0 if radar_high_nearby else 10.0
    alert_component = max(10.0 - unread_alerts * 2.0, 0.0)
    yield_component = max(10.0 - (yield_risk_percent / 10.0), 0.0)
    score = round(
        _clamp(fsi_component + shi_component + radar_component + alert_component + yield_component, 0.0, 100.0),
        1,
    )
    if score >= 75.0:
        band = "GOOD"
    elif score >= 50.0:
        band = "FAIR"
    else:
        band = "POOR"
    return score, band
