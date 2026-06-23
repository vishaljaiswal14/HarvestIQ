import type {
  AdvisoryResult,
  BriefingData,
  DiseaseRadarData,
  FarmProfile,
  HealthCardData,
  MarketPricesData,
  SchemesData,
  SimulatorResult,
  StressIndexData,
  WeatherForecast,
} from "@/lib/api";

export const DEMO_FARM_ID = "demo-farm-rajasthan-wheat";

export const demoFarmProfile: FarmProfile = {
  farm_id: DEMO_FARM_ID,
  farm_name: "Demo Farm — Bharatpur Wheat",
  state: "Rajasthan",
  district: "Bharatpur",
  soil_type: "Loamy",
  crop_cycle_id: "demo-cycle-001",
  crop_type: "WHEAT",
  sowing_date: "2025-11-15",
};

export const demoHealthCard: HealthCardData = {
  farm_id: DEMO_FARM_ID,
  crop_type: "WHEAT",
  stage: "Tillering",
  fsi: 0.78,
  fsi_classification: "HIGH_STRESS",
  soil_health_index: 0.62,
  stress_momentum: {
    direction: "RISING",
    momentum_score: 0.55,
    fsi_delta: 0.09,
    insufficient_history: false,
    window_days: 7,
  },
  yield_risk: {
    risk_band: "HIGH",
    estimated_risk_percent: 72.5,
    contributing_factors: ["FSI", "RISING_MOMENTUM", "LOW_SOIL_HEALTH"],
  },
  health_score: 48.0,
  health_band: "POOR",
  nearby_radar_high_count: 1,
  unread_alerts: 2,
  intelligence_snapshot_version: "v3",
  explanation: {
    summary: "Demo farm health snapshot with rising stress momentum.",
    inputs: { fsi: 0.78, health_band: "POOR" },
    primary_factor: "THERMAL",
  },
};

export const demoBriefing: BriefingData = {
  briefing_id: "demo-briefing-001",
  farm_id: DEMO_FARM_ID,
  synthesis:
    "सुप्रभात। आपके गेहूं के खेत में तापीय तनाव बढ़ रहा है। आज छिड़काव असुरक्षित है। निकटवर्ती मंडी में गेहूं का मॉडल भाव ₹2250 है।",
  language: "hi",
  sections: {
    stress_momentum: demoHealthCard.stress_momentum,
    yield_risk: demoHealthCard.yield_risk,
    input_windows: { SPRAY: false, IRRIGATE: true, FERTILIZE: false },
    market_summary: {
      mandi: "Bharatpur APMC",
      modal_price: 2250,
      trend: "RISING",
      crop_type: "WHEAT",
    },
    eligible_schemes_count: 2,
  },
  explainability: demoHealthCard.explanation,
  intelligence_snapshot_version: "v3",
  generated_at: new Date().toISOString(),
  source: "DEMO",
};

function forecastDay(offset: number, tempMax: number, precip: number) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return {
    date: d.toISOString().slice(0, 10),
    temp_min: tempMax - 12,
    temp_max: tempMax,
    humidity: 30 + offset * 3,
    precipitation: precip,
    wind_speed: 18 + offset,
  };
}

export const demoWeather: WeatherForecast = {
  farm_id: DEMO_FARM_ID,
  current: { temp: 39.0, humidity: 35.0, wind_speed: 24.0, precipitation: 0.0 },
  forecast: [
    forecastDay(0, 41.0, 0),
    forecastDay(1, 40.5, 0),
    forecastDay(2, 39.0, 2.5),
    forecastDay(3, 38.0, 4.0),
    forecastDay(4, 37.5, 1.0),
    forecastDay(5, 36.0, 0),
    forecastDay(6, 35.5, 0),
  ],
  daily_gdd: [],
  source: "demo",
  cached_at: new Date().toISOString(),
};

export const demoDiseaseRadar: DiseaseRadarData = {
  hotspots: [
    {
      disease_name: "Yellow Rust (Stripe Rust)",
      crop_type: "WHEAT",
      risk_level: "HIGH",
      case_count: 14,
      distance_km: 8.2,
      location_grid: { type: "Point", coordinates: [77.49, 27.22] },
      last_updated: new Date().toISOString(),
    },
    {
      disease_name: "Powdery Mildew",
      crop_type: "WHEAT",
      risk_level: "MEDIUM",
      case_count: 6,
      distance_km: 18.5,
      location_grid: { type: "Point", coordinates: [77.38, 27.15] },
      last_updated: new Date().toISOString(),
    },
    {
      disease_name: "Karnal Bunt",
      crop_type: "WHEAT",
      risk_level: "LOW",
      case_count: 2,
      distance_km: 32.0,
      location_grid: { type: "Point", coordinates: [77.62, 27.05] },
      last_updated: new Date().toISOString(),
    },
  ],
  queried_at: new Date().toISOString(),
  radius_km: 50,
};

const demoSimulatorBaseline = {
  fsi: demoHealthCard.fsi,
  stress_momentum: demoHealthCard.stress_momentum,
  yield_risk: demoHealthCard.yield_risk,
  fsi_curve: [0.62, 0.68, 0.74, 0.78],
  yield_factor: 0.72,
};

export function buildDemoSimulatorResult(body?: string): SimulatorResult {
  let tempDelta = 0;
  let irrigationDelta = 0;
  let nitrogenDelta = 0;
  if (body) {
    try {
      const parsed = JSON.parse(body) as {
        temp_delta?: number;
        irrigation_delta?: number;
        nitrogen_delta?: number;
      };
      tempDelta = parsed.temp_delta ?? 0;
      irrigationDelta = parsed.irrigation_delta ?? 0;
      nitrogenDelta = parsed.nitrogen_delta ?? 0;
    } catch {
      // use defaults
    }
  }

  const fsiShift = tempDelta * 0.04 - irrigationDelta * 0.12 - nitrogenDelta * 0.001;
  const projectedFsi = Math.max(0.05, Math.min(1, demoSimulatorBaseline.fsi + fsiShift));
  const riskShift = tempDelta * 3 - irrigationDelta * 8 - nitrogenDelta * 0.05;
  const projectedRisk = Math.max(
    5,
    Math.min(95, demoHealthCard.yield_risk.estimated_risk_percent + riskShift),
  );

  return {
    farm_id: DEMO_FARM_ID,
    baseline: demoSimulatorBaseline,
    projected: {
      fsi: projectedFsi,
      stress_momentum: {
        ...demoHealthCard.stress_momentum,
        direction: projectedFsi > demoSimulatorBaseline.fsi ? "RISING" : projectedFsi < demoSimulatorBaseline.fsi ? "FALLING" : "STABLE",
        fsi_delta: projectedFsi - demoSimulatorBaseline.fsi,
      },
      yield_risk: {
        ...demoHealthCard.yield_risk,
        estimated_risk_percent: Math.round(projectedRisk * 10) / 10,
        risk_band: projectedRisk >= 60 ? "HIGH" : projectedRisk >= 35 ? "MEDIUM" : "LOW",
      },
      fsi_curve: demoSimulatorBaseline.fsi_curve.map((v) =>
        Math.max(0.05, Math.min(1, v + fsiShift * 0.5)),
      ),
      yield_factor: Math.max(0.4, Math.min(1, demoSimulatorBaseline.yield_factor - fsiShift * 0.3)),
    },
    explanation: {
      summary: `Demo projection: temp ${tempDelta >= 0 ? "+" : ""}${tempDelta}°C, irrigation ${irrigationDelta >= 0 ? "+" : ""}${irrigationDelta}, nitrogen ${nitrogenDelta >= 0 ? "+" : ""}${nitrogenDelta} kg/ha.`,
      inputs: { temp_delta: tempDelta, irrigation_delta: irrigationDelta, nitrogen_delta: nitrogenDelta },
      primary_factor: tempDelta > 2 ? "THERMAL" : irrigationDelta < -0.3 ? "MOISTURE" : "COMPOSITE",
    },
    intelligence_snapshot_version: "v3",
  };
}

export const demoStressIndex: StressIndexData = {
  farm_id: DEMO_FARM_ID,
  crop_cycle_id: "demo-cycle-001",
  crop_type: "WHEAT",
  stage: "Tillering",
  fsi: 0.78,
  classification: "HIGH_STRESS",
  primary_factor: "THERMAL",
  components: { temp_stress: 0.88, rainfall_deficit: 0.45, gdd_scale: 0.5 },
  calculated_at: new Date().toISOString(),
  explanation: demoHealthCard.explanation,
};

export const demoMarketPrices: MarketPricesData = {
  farm_id: DEMO_FARM_ID,
  crop_type: "WHEAT",
  prices: [
    {
      mandi: "Bharatpur APMC",
      crop_type: "WHEAT",
      min_price: 2100,
      max_price: 2350,
      modal_price: 2250,
      price_date: new Date().toISOString(),
    },
  ],
  modal_trend: "RISING",
  as_of: new Date().toISOString(),
};

export const demoSchemes: SchemesData = {
  farm_id: DEMO_FARM_ID,
  schemes: [
    {
      scheme_id: "PM-KISAN",
      name: "PM-KISAN",
      description: "Income support for eligible farmers.",
      application_steps: ["Visit agriculture office", "Submit land records"],
    },
    {
      scheme_id: "RJ-WHEAT-INSURANCE",
      name: "Rajasthan Wheat Crop Insurance",
      description: "Weather-based crop insurance for wheat.",
      application_steps: ["Enroll before sowing window", "Pay premium share"],
    },
  ],
  evaluated_at: new Date().toISOString(),
};

export const demoAdvisory: AdvisoryResult = {
  advisory_id: "demo-advisory-001",
  farm_id: DEMO_FARM_ID,
  synthesis:
    "Your wheat field shows high thermal stress. Avoid spray and fertilizer until wind drops below 20 km/h and temperatures moderate.",
  language: "en",
  explainability: demoHealthCard.explanation,
  citations: [],
  intelligence_snapshot_version: "v3",
};

export const DEMO_MODE_KEY = "harvestiq_demo_mode";

export function isDemoModeEnabled(): boolean {
  if (typeof window === "undefined") return false;
  const val = localStorage.getItem(DEMO_MODE_KEY);
  if (val === null) {
    return true;
  }
  return val === "true";
}
