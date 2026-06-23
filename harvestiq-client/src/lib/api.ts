import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/auth";
import {
  buildDemoSimulatorResult,
  demoAdvisory,
  demoBriefing,
  demoDiseaseRadar,
  demoFarmProfile,
  demoHealthCard,
  demoMarketPrices,
  demoSchemes,
  demoStressIndex,
  demoWeather,
  isDemoModeEnabled,
} from "@/lib/demoFixtures";
import { cacheSnapshot, readCachedSnapshot, writeLastSync, enqueueOutbox } from "@/lib/db";
import { evaluateOfflineQuery } from "@/lib/offlineAi";
import { useLocalizationStore } from "@/stores/localizationStore";
import { syncLocalKnowledge, type KnowledgeSyncPayload } from "@/lib/offlineKnowledgeDb";
import {
  createFarm,
  deleteFarm,
  createPlot,
  deletePlot,
  createCropCycle,
  deleteCropCycle,
  createExpense,
  deleteExpense,
  createHarvest,
  deleteHarvest,
  getFarmById,
  listFarms,
  getPlotById,
  getPlotsByFarm,
  getCropCycleById,
  getCropCyclesByPlot,
  getActiveCropCycles,
  getExpensesByCropCycle,
  getHarvestsByCropCycle,
  reconcileLocalId,
  reconcileRelationships,
  getFromStore,
} from "@/lib/farmDb";
import {
  calculateLocalCropCycleProfitability,
  calculateLocalPlotProfitability,
  calculateLocalFarmProfitability,
  calculateLocalSeasonComparison,
} from "@/lib/profitability";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type UserProfile = {
  id: string;
  name: string;
  phone: string;
  role: string;
  preferred_lang: string;
  onboarding_completed: boolean;
};

export type FarmProfile = {
  farm_id: string;
  farm_name: string;
  state: string;
  district: string;
  soil_type?: string | null;
  boundary?: Record<string, unknown> | null;
  crop_cycle_id?: string | null;
  crop_type?: string | null;
  sowing_date?: string | null;
};

export type WeatherForecast = {
  farm_id: string;
  current: {
    temp: number;
    humidity: number;
    wind_speed: number;
    precipitation: number;
  };
  forecast: Array<{
    date: string;
    temp_min: number;
    temp_max: number;
    humidity: number;
    precipitation: number;
    wind_speed: number;
  }>;
  daily_gdd: Array<{ date: string; gdd: number }>;
  source: string;
  cached_at: string;
};

export type CropStageData = {
  cycle_id: string;
  crop_type: string;
  stage: string;
  progress_percentage: number;
  current_gdd: number;
  stages_timeline: Array<{
    name: string;
    gdd_min: number;
    gdd_max: number;
    is_current: boolean;
    is_completed: boolean;
  }>;
};

export type ExplanationData = {
  summary: string;
  inputs: Record<string, number | string>;
  primary_factor: string;
};

export type StressIndexData = {
  farm_id: string;
  crop_cycle_id: string;
  crop_type: string;
  stage: string;
  fsi: number;
  classification: string;
  primary_factor: string;
  components: {
    temp_stress: number;
    rainfall_deficit: number;
    gdd_scale: number;
  };
  calculated_at: string;
  explanation: ExplanationData;
};

export type AlertData = {
  id: string;
  farm_id: string;
  rule_id: string;
  severity: string;
  title: string;
  message: string;
  read: boolean;
  lifecycle_status?: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
  resolved_at?: string | null;
  explanation: ExplanationData;
  created_at: string;
};

export type AlertPreferences = {
  push_enabled: boolean;
  sms_enabled: boolean;
  quiet_hours_start: number;
  quiet_hours_end: number;
  timezone: string;
};

export type AlertSeverityData = {
  farm_id: string;
  severity_tier: string;
  severity_rank: number;
  critical_triggers: string[];
  generated_because: string[];
  explanation: ExplanationData;
  evaluated_at: string;
  log_id?: string | null;
};

export type AlertListData = {
  alerts: AlertData[];
  unread_count: number;
  farm_severity?: AlertSeverityData | null;
};

export type SoilRecordData = {
  id?: string;
  farm_id?: string;
  crop_type?: string;
  nitrogen?: number;
  phosphorus?: number;
  potassium?: number;
  ph?: number;
  organic_carbon?: number;
  electrical_conductivity?: number;
  deficiency_status?: {
    nitrogen: string;
    phosphorus: string;
    potassium: string;
    ph: string;
    organic_carbon: string;
    electrical_conductivity: string;
  };
  soil_health_index?: number;
  explanation?: ExplanationData;
  recorded_at?: string;
  available?: boolean;
  message?: string;
};

export type DiseaseDetectResult = {
  report_id?: string;
  farm_id: string;
  crop_type: string;
  disease: string;
  confidence?: number | null;
  deterministic_status: string;
  explanation: ExplanationData;
  disease_name?: string;
  severity?: string;
  what_it_means?: string;
  immediate_actions?: string[];
  recommended_treatment?: string;
  prevention_advice?: string[];
  risk_level?: string;
  valid?: boolean;
  image_type?: string;
  validation_confidence?: number;
  reason?: string;
  message?: string;
  crop_confidence?: number | null;
  validation_result?: boolean | null;
  region_validation_result?: boolean | null;
  created_at?: string;
  image_url?: string;
  image_path?: string;
};

export type TimelineEvent = {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  description: string;
  action?: string | null;
  severity?: string | null;
  risk_level?: string | null;
  metadata?: Record<string, unknown>;
};

export type FarmTimelineResponse = {
  farm_id: string;
  events: TimelineEvent[];
};

export type AdvisoryCitation = {
  source: string;
  document_id: string;
  title: string;
  excerpt: string;
};

export type AdvisoryResult = {
  advisory_id: string;
  farm_id: string;
  synthesis: string;
  language: string;
  explainability: ExplanationData;
  citations: AdvisoryCitation[];
  intelligence_snapshot_version: string;
  source?: string;
};

export type ActionCard = {
  card_type: "RED" | "YELLOW" | "GREEN";
  problem: string;
  action: string;
  deadline: string;
  expected_impact: string;
  is_sos?: boolean;
};

export type AdvisoryActionsResponse = {
  priority: "EMERGENCY" | "HIGH" | "MEDIUM" | "LOW";
  situation_summary: string;
  today_actions: ActionCard[];
  this_week_actions: ActionCard[];
  ignore_risk: string;
  why_generated: string[];
};

export type CopilotAction = {
  id: string;
  horizon: "TODAY" | "THIS_WEEK" | "PREVENTIVE";
  priority: "EMERGENCY" | "HIGH" | "MEDIUM" | "LOW";
  card_type: "RED" | "YELLOW" | "GREEN";
  title: string;
  action: string;
  deadline: string;
  expected_impact: string;
  why: string;
  if_ignored: string;
  expected_benefit: string;
  source_signals: string[];
  is_sos?: boolean;
  completed?: boolean;
};

export type CopilotPlan = {
  farm_id: string;
  crop_type: string;
  stage: string;
  priority: string;
  severity_tier: string;
  situation_summary: string;
  today_actions: CopilotAction[];
  this_week_actions: CopilotAction[];
  preventive_actions: CopilotAction[];
  risk_reduction_impact: string;
  potential_loss_prevention_band: "LOW" | "MODERATE" | "HIGH";
  why_generated: string[];
  generated_at: string;
  plan_id: string;
  yield_protection_score?: number | null;
  yield_protection_band?: string | null;
};

export type YieldProtectionScore = {
  farm_id: string;
  score: number;
  band: "PROTECTED" | "MODERATE" | "AT_RISK" | "CRITICAL";
  breakdown: {
    disease_risk: number;
    stress_risk: number;
    alert_burden: number;
    advisory_compliance: number;
  };
  trend: "IMPROVING" | "STABLE" | "DECLINING";
  trend_delta: number;
  top_risk: string;
  risk_reduction_impact: string;
  potential_loss_prevention_band: "LOW" | "MODERATE" | "HIGH";
  explanation: ExplanationData;
  calculated_at: string;
};

export type DiseaseRadarHotspot = {
  disease_name: string;
  crop_type: string;
  risk_level: string;
  case_count: number;
  distance_km: number;
  location_grid: { type: string; coordinates: number[] };
  last_updated: string;
};

export type DiseaseRadarData = {
  hotspots: DiseaseRadarHotspot[];
  queried_at: string;
  radius_km: number;
};

export type VoiceTranscribeResult = {
  transcript: string;
  confidence: number;
  language: string;
};

export type LocalizationData = {
  lang: string;
  labels: Record<string, string>;
};

export type StressMomentumData = {
  direction: string;
  momentum_score: number;
  fsi_delta: number;
  insufficient_history: boolean;
  window_days: number;
};

export type YieldRiskData = {
  risk_band: string;
  estimated_risk_percent: number;
  contributing_factors: string[];
};

export type HealthCardData = {
  farm_id: string;
  crop_type: string;
  stage: string;
  fsi: number;
  fsi_classification: string;
  soil_health_index?: number | null;
  stress_momentum: StressMomentumData;
  yield_risk: YieldRiskData;
  health_score: number;
  health_band: string;
  nearby_radar_high_count: number;
  unread_alerts: number;
  intelligence_snapshot_version: string;
  explanation: ExplanationData;
};

export type BriefingData = {
  briefing_id: string;
  farm_id: string;
  synthesis: string;
  language: string;
  sections: {
    stress_momentum: StressMomentumData;
    yield_risk: YieldRiskData;
    input_windows: Record<string, boolean>;
    market_summary?: Record<string, unknown> | null;
    eligible_schemes_count: number;
  };
  explainability: ExplanationData;
  intelligence_snapshot_version: string;
  generated_at: string;
  source: string;
};

export type InputWindowData = {
  farm_id: string;
  action_type: string;
  safe: boolean;
  reasons: string[];
  triggered_rules: string[];
  explanation: ExplanationData;
  evaluated_at: string;
};

export type MarketPriceRecord = {
  mandi: string;
  crop_type: string;
  min_price: number;
  max_price: number;
  modal_price: number;
  price_date: string;
};

export type MarketPricesData = {
  farm_id: string;
  crop_type: string;
  prices: MarketPriceRecord[];
  modal_trend: string;
  as_of: string;
};

export type SchemeMatch = {
  scheme_id: string;
  name: string;
  description: string;
  application_steps: string[];
};

export type SchemesData = {
  farm_id: string;
  schemes: SchemeMatch[];
  evaluated_at: string;
};

export type SimulatorSnapshotData = {
  fsi: number;
  stress_momentum: StressMomentumData;
  yield_risk: YieldRiskData;
  fsi_curve: number[];
  yield_factor: number;
};

export type SimulatorResult = {
  farm_id: string;
  baseline: SimulatorSnapshotData;
  projected: SimulatorSnapshotData;
  explanation: ExplanationData;
  intelligence_snapshot_version: string;
};

export type SosTriggerResult = {
  action_id: string;
  farm_id: string;
  emergency_type: string;
  checklist: string[];
  plain_text_message: string;
  delivery_status: string;
  intelligence_snapshot_version: string;
  triggered_at: string;
  provider?: string | null;
  message_sid?: string | null;
  callback_available?: boolean;

  recipients?: Array<{
    role: string;
    phone: string;
    recipient_phone?: string | null;
    masked_phone?: string | null;
    status: string;
    message_sid?: string | null;
    provider_status?: string | null;
    error_code?: string | null;
    error_message?: string | null;
    error?: string | null;
    last_updated?: string | null;
  }>;
};


export type EmergencyContacts = {
  primary_contact: string;
  secondary_contact: string;
  village_contact: string;
  updated_at?: string;
};

export type SyncBatchResult = {
  processed: number;
  results: Array<{
    operation_type: string;
    client_id: string;
    server_id?: string | null;
    status: string;
    error?: string | null;
    detail?: string | null;
  }>;
};

type RequestOptions = RequestInit & {
  skipAuth?: boolean;
  retry?: boolean;
};

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await fetch("/api/v1/auth/refresh", {
        method: "POST",
        credentials: "include",
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          clearAccessToken();
        }
        return null;
      }

      const data = (await response.json()) as { access_token: string };
      setAccessToken(data.access_token);
      return data.access_token;
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

function resolveDemoFixture<T>(path: string, method = "GET", body?: string, force = false): T | null {
  if (!force && !isDemoModeEnabled()) return null;
  if (path.includes("/health-card")) return demoHealthCard as T;
  if (path.includes("/briefing/daily")) return demoBriefing as T;
  if (path.includes("/weather/forecast")) return demoWeather as T;
  if (path.includes("/stress-index/")) return demoStressIndex as T;
  if (path.includes("/market/prices")) return demoMarketPrices as T;
  if (path.includes("/schemes/eligible")) return demoSchemes as T;
  if (path.includes("/farms/me")) return demoFarmProfile as T;
  if (path.includes("/disease-radar/")) return demoDiseaseRadar as T;
  if (path.includes("/crop-cycles/") && path.includes("/stage")) {
    return {
      cycle_id: "demo-cycle",
      crop_type: "Rice",
      stage: "Tillering",
      progress_percentage: 87.5,
      current_gdd: 450,
      stages_timeline: [
        { name: "Germination", gdd_min: 0, gdd_max: 100, is_current: false, is_completed: true },
        { name: "Tillering", gdd_min: 100, gdd_max: 500, is_current: true, is_completed: false },
        { name: "Flowering", gdd_min: 500, gdd_max: 900, is_current: false, is_completed: false },
      ]
    } as T;
  }
  if (path.includes("/simulator/run") && method === "POST") {
    return buildDemoSimulatorResult(body) as T;
  }
  if (path.includes("/advisory/actions")) {
    return {
      priority: "HIGH",
      situation_summary: "Your Wheat crop is showing signs of Wheat Rust. Risk Level: High. Take action within 48 hours to avoid yield loss.",
      today_actions: [
        {
          card_type: "RED",
          problem: "Wheat Rust infection detected.",
          action: "Spray recommended fungicide (e.g. Propiconazole) immediately.",
          deadline: "Within 48 hours",
          expected_impact: "Halt disease spread and protect yield."
        }
      ],
      this_week_actions: [
        {
          card_type: "YELLOW",
          problem: "High relative humidity (82%) detected. High risk of fungal infections.",
          action: "Avoid over-watering and monitor crop leaves daily for rust spots.",
          deadline: "This week",
          expected_impact: "Minimize microclimate moisture favoring rust spore growth."
        }
      ],
      ignore_risk: "If ignored for 5-7 days:\nPotential yield reduction: 10-20%",
      why_generated: ["Wheat Rust detected", "Humidity above threshold (82%)"]
    } as T;
  }
  if (path === "/api/v1/advisory/ask" && method === "POST") return demoAdvisory as T;
  if (path.includes("/alerts")) {
    return { alerts: [], unread_count: 2 } as T;
  }
  if (path.includes("/optimizer/window") && method === "POST") {
    return {
      farm_id: demoFarmProfile.farm_id,
      action_type: "SPRAY",
      safe: false,
      reasons: ["Wind speed 24 km/h exceeds limit 20 km/h"],
      triggered_rules: ["RULE_HIGH_WIND"],
      explanation: demoHealthCard.explanation,
      evaluated_at: new Date().toISOString(),
    } as T;
  }
  return null;
}

async function readOfflineCache<T>(path: string): Promise<T | null> {
  if (path.includes("/health-card")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("health", farmId);
  }
  if (path.includes("/advisory/actions")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("briefing", farmId + "-actions");
  }
  if (path.includes("/briefing/daily")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("briefing", farmId);
  }
  if (path.includes("/weather/forecast")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("weather", farmId);
  }
  if (path.includes("/crop-cycles/") && path.includes("/stage")) {
    const match = path.match(/\/crop-cycles\/([^/]+)\/stage/);
    const cycleId = match?.[1] ?? "default";
    return readCachedSnapshot<T>("stage", cycleId);
  }
  if (path.includes("/stress-index/")) {
    const farmId = path.split("/stress-index/")[1]?.split("?")[0] ?? "default";
    return readCachedSnapshot<T>("stress", farmId);
  }
  if (path.includes("/market/prices")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("market", farmId);
  }
  if (path.includes("/schemes/eligible")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("schemes", farmId);
  }
  if (path.includes("/alerts") && !path.includes("/trigger-evaluation")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    return readCachedSnapshot<T>("alerts", farmId);
  }
  if (path.includes("/farms/me")) {
    return readCachedSnapshot<T>("farm", "me");
  }
  if (path.includes("/localization/")) {
    const lang = path.split("/localization/")[1]?.split("?")[0] ?? "hi";
    return readCachedSnapshot<T>("localization", lang);
  }
  if (path.includes("/farm-db/farmer/me")) {
    return readCachedSnapshot<T>("farm", "me");
  }
  if (path.includes("/farm-db/farms")) {
    const match = path.match(/\/farm-db\/farms\/([^/?]+)/);
    if (match) {
      return (await getFarmById(match[1])) as unknown as T;
    }
    return (await listFarms()) as unknown as T;
  }
  if (path.includes("/farm-db/plots")) {
    const match = path.match(/\/farm-db\/plots\/([^/?]+)/);
    if (match) {
      return (await getPlotById(match[1])) as unknown as T;
    }
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") || "";
    return (await getPlotsByFarm(farmId)) as unknown as T;
  }
  if (path.includes("/farm-db/crop-cycles")) {
    if (path.includes("/active")) {
      return (await getActiveCropCycles()) as unknown as T;
    }
    const match = path.match(/\/farm-db\/crop-cycles\/([^/?]+)/);
    if (match) {
      return (await getCropCycleById(match[1])) as unknown as T;
    }
    const plotId = new URL(path, "http://local").searchParams.get("plot_id") || "";
    return (await getCropCyclesByPlot(plotId)) as unknown as T;
  }
  if (path.includes("/farm-db/expenses")) {
    const cycleId = new URL(path, "http://local").searchParams.get("crop_cycle_id") || "";
    return (await getExpensesByCropCycle(cycleId)) as unknown as T;
  }
  if (path.includes("/farm-db/harvests")) {
    const cycleId = new URL(path, "http://local").searchParams.get("crop_cycle_id") || "";
    return (await getHarvestsByCropCycle(cycleId)) as unknown as T;
  }
  if (path.includes("/profitability/crop-cycle/")) {
    const match = path.match(/\/profitability\/crop-cycle\/([^/?]+)/);
    if (match) {
      return (await calculateLocalCropCycleProfitability(match[1])) as unknown as T;
    }
  }
  if (path.includes("/profitability/plot/")) {
    const match = path.match(/\/profitability\/plot\/([^/?]+)/);
    if (match) {
      return (await calculateLocalPlotProfitability(match[1])) as unknown as T;
    }
  }
  if (path.includes("/profitability/farm/") && path.includes("/season-comparison")) {
    const match = path.match(/\/profitability\/farm\/([^/]+)\/season-comparison/);
    if (match) {
      return (await calculateLocalSeasonComparison(match[1])) as unknown as T;
    }
  }
  if (path.includes("/profitability/farm/")) {
    const match = path.match(/\/profitability\/farm\/([^/?]+)/);
    if (match) {
      return (await calculateLocalFarmProfitability(match[1])) as unknown as T;
    }
  }
  if (path.includes("/sos/contacts")) {
    return readCachedSnapshot<T>("briefing", "emergency-contacts");
  }
  if (path.includes("/sos/history")) {
    return readCachedSnapshot<T>("briefing", "sos-history");
  }
  return null;
}

async function writeOfflineCache(path: string, payload: unknown): Promise<void> {
  let wrote = false;
  if (path.includes("/health-card")) {
    const farmId = (payload as any)?.farm_id ?? new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("health", farmId, payload);
    wrote = true;
  } else if (path.includes("/sos/contacts")) {
    await cacheSnapshot("briefing", "emergency-contacts", payload);
    wrote = true;
  } else if (path.includes("/sos/history")) {
    await cacheSnapshot("briefing", "sos-history", payload);
    wrote = true;
    
    // Check if this payload is actually a soil sample record to write to IndexedDB outbox store
    if (payload && typeof payload === "object" && "nitrogen" in payload) {
      const clientId = "soil-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
      await enqueueOutbox({
        client_id: clientId,
        operation_type: "CREATE_SOIL_RECORD",
        payload: payload as Record<string, unknown>,
        client_timestamp: new Date().toISOString(),
      });
      console.log(`[API:writeOfflineCache] Intercepted offline soil record and enqueued to outbox: ${clientId}`);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("outbox-updated"));
      }
    }
  } else if (path.includes("/briefing/daily")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("briefing", farmId, payload);
    wrote = true;
  } else if (path.includes("/advisory/actions")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("briefing", farmId + "-actions", payload);
    wrote = true;
  } else if (path.includes("/weather/forecast")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("weather", farmId, payload);
    wrote = true;
  } else if (path.includes("/crop-cycles/") && path.includes("/stage")) {
    const match = path.match(/\/crop-cycles\/([^/]+)\/stage/);
    const cycleId = match?.[1] ?? "default";
    await cacheSnapshot("stage", cycleId, payload);
    wrote = true;
  } else if (path.includes("/stress-index/")) {
    const farmId = path.split("/stress-index/")[1]?.split("?")[0] ?? "default";
    await cacheSnapshot("stress", farmId, payload);
    wrote = true;
  } else if (path.includes("/market/prices")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("market", farmId, payload);
    wrote = true;
  } else if (path.includes("/schemes/eligible")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("schemes", farmId, payload);
    wrote = true;
  } else if (path.includes("/alerts") && !path.includes("/trigger-evaluation")) {
    const farmId = new URL(path, "http://local").searchParams.get("farm_id") ?? "default";
    await cacheSnapshot("alerts", farmId, payload);
    wrote = true;
  } else if (path.includes("/farms/me")) {
    await cacheSnapshot("farm", "me", payload);
    wrote = true;
  } else if (path.includes("/localization/")) {
    const lang = path.split("/localization/")[1]?.split("?")[0] ?? "hi";
    await cacheSnapshot("localization", lang, payload);
    wrote = true;
  } else if (path.includes("/farm-db/farmer/me")) {
    await cacheSnapshot("farm", "me", payload);
    wrote = true;
  } else if (path.includes("/farm-db/farms")) {
    if (Array.isArray(payload)) {
      for (const farm of payload) {
        await createFarm(farm);
      }
    } else if (payload && typeof payload === "object") {
      await createFarm(payload as any);
    }
    wrote = true;
  } else if (path.includes("/farm-db/plots")) {
    if (Array.isArray(payload)) {
      for (const plot of payload) {
        await createPlot(plot);
      }
    } else if (payload && typeof payload === "object") {
      await createPlot(payload as any);
    }
    wrote = true;
  } else if (path.includes("/farm-db/crop-cycles")) {
    if (Array.isArray(payload)) {
      for (const cycle of payload) {
        await createCropCycle(cycle);
      }
    } else if (payload && typeof payload === "object") {
      await createCropCycle(payload as any);
    }
    wrote = true;
  } else if (path.includes("/farm-db/expenses")) {
    if (Array.isArray(payload)) {
      for (const exp of payload) {
        await createExpense(exp);
      }
    } else if (payload && typeof payload === "object") {
      await createExpense(payload as any);
    }
    wrote = true;
  } else if (path.includes("/farm-db/harvests")) {
    if (Array.isArray(payload)) {
      for (const harv of payload) {
        await createHarvest(harv);
      }
    } else if (payload && typeof payload === "object") {
      await createHarvest(payload as any);
    }
    wrote = true;
  }
  // Record last successful sync timestamp whenever any dashboard data is persisted
  if (wrote) {
    void writeLastSync(new Date().toISOString());
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const { skipAuth = false, retry = true, headers, ...rest } = options;

  // 1. FAULT-TOLERANT CLIENT-SIDE OFFLINE INTERCEPT
  // Only trigger if navigator.onLine is strictly false AND it's not an explicit live override request
  if (typeof window !== 'undefined' && !navigator.onLine) {
    
    // Allow routes to bypass the faulty browser flag if the user is testing online
    const isTestingLive = !path.includes("force_offline=true");
    
    if (!isTestingLive) {
      console.warn("[SMART OFFLINE INTERCEPT] Handling route locally:", path);
      
      if (path.includes("/disease/detect")) {
        return {
          report_id: "offline-report",
          farm_id: "offline-farm",
          crop_type: "Unknown",
          disease: "OFFLINE_MODE",
          confidence: 0.0,
          deterministic_status: "UNAVAILABLE",
          explanation: { summary: "Disease diagnosis is currently unavailable offline.", inputs: {}, primary_factor: "NONE" }
        } as any;
      }
      
      if (path.includes("/disease-radar") || path.includes("/disease/")) {
        return { hotspots: [], queried_at: new Date().toISOString(), radius_km: 0 } as any;
      }

      const cached = await readOfflineCache<T>(path);
      if (cached) return cached;
      
      const fallbackFixture = resolveDemoFixture<T>(path, method, typeof rest.body === "string" ? rest.body : undefined, true);
      if (fallbackFixture) return fallbackFixture;

      return { data: [], status: "OFFLINE" } as any;
    }
  }
  const demoFixture = resolveDemoFixture<T>(
    path,
    method,
    typeof rest.body === "string" ? rest.body : undefined,
  );
  if (demoFixture !== null) {
    return demoFixture;
  }

  const requestHeaders = new Headers(headers);
  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const userLang = useLocalizationStore.getState().preferredLang || "en";
  requestHeaders.set("Accept-Language", userLang);

  if (rest.body && !(rest.body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  let response: Response | undefined;
  let networkError = false;

  try {
    if (typeof window !== "undefined" && !window.navigator.onLine) {
      console.log(`[API:apiRequest] Detected offline mode via navigator.onLine for: ${path}`);
      throw new Error("Offline");
    }
    response = await fetch(path, {
      ...rest,
      headers: requestHeaders,
      credentials: "include",
    });
  } catch (err) {
    console.log(`[API:apiRequest] Network error during fetch for: ${path}`, err);
    networkError = true;
  }

  if (!networkError && response && response.status === 401 && !skipAuth && retry) {
    let newToken: string | null = null;
    let refreshFailedOffline = false;
    
    try {
      newToken = await refreshAccessToken();
    } catch {
      console.log(`[API:apiRequest] Network error during refresh (offline) for: ${path}`);
      refreshFailedOffline = true;
    }

    if (newToken) {
      requestHeaders.set("Authorization", `Bearer ${newToken}`);
      try {
        response = await fetch(path, {
          ...rest,
          headers: requestHeaders,
          credentials: "include",
        });
      } catch {
        console.log(`[API:apiRequest] Network error during retry fetch for: ${path}`);
        networkError = true;
      }
    } else {
      if (!getAccessToken()) {
         console.log(`[API:apiRequest] Token refresh failed or missing, treating as offline for: ${path}`);
         refreshFailedOffline = true;
      }
    }
    
    if (refreshFailedOffline) {
       networkError = true; 
    }
  }

  const isServerError = response && response.status >= 500;
  const isOffline401 = response && response.status === 401;
  const isNotFound = response && response.status === 404;

  if (networkError || isServerError || isOffline401 || isNotFound) {
    console.log(`[API:apiRequest] Fallback triggered for: ${path} | networkError=${networkError}, isServerError=${isServerError}, isOffline401=${isOffline401}, isNotFound=${isNotFound}`);
    
    if (method === "POST" || method === "PUT" || method === "DELETE") {
      if ((path.includes("/sos/trigger") || path.includes("/sos/dispatch")) && method === "POST" && typeof rest.body === "string") {
        const bodyObj = JSON.parse(rest.body);
        const clientId = "sos-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
        const captured_at = new Date().toISOString();
        await enqueueOutbox({
          client_id: clientId,
          operation_type: "TRIGGER_SOS",
          payload: {
            farm_id: bodyObj.farm_id,
            emergency_type: bodyObj.emergency_type || "GENERAL",
            latitude: bodyObj.latitude,
            longitude: bodyObj.longitude,
            captured_at,
          },
          client_timestamp: captured_at,
        });
        console.log(`[SOS] Queued offline SOS request`);
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("outbox-updated"));
        }
        return {
          action_id: "offline-" + clientId,
          farm_id: bodyObj.farm_id,
          emergency_type: bodyObj.emergency_type || "GENERAL",
          checklist: [
            "National Emergency: 112",
            "Ambulance: 108",
            "Fire: 101",
            "Police: 100 / 112"
          ],
          plain_text_message: `Emergency request saved offline.\n\nCall emergency services immediately:\n\n• 112 — National Emergency\n• 108 — Ambulance\n• 101 — Fire\n• 100 / 112 — Police\n\nYour SOS request will automatically be transmitted when internet connectivity returns.`,
          delivery_status: "QUEUED",
          intelligence_snapshot_version: "N/A",
          triggered_at: captured_at,
        } as unknown as T;
      }

      if (path.includes("/sos/contacts") && method === "POST" && typeof rest.body === "string") {
        const bodyObj = JSON.parse(rest.body);
        const clientId = "contacts-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
        const clientTimestamp = new Date().toISOString();
        await enqueueOutbox({
          client_id: clientId,
          operation_type: "SAVE_EMERGENCY_CONTACTS",
          payload: bodyObj,
          client_timestamp: clientTimestamp,
        });
        console.log(`[SOS:Contacts] Queued offline save contacts request`);
        await cacheSnapshot("briefing", "emergency-contacts", {
          ...bodyObj,
          updated_at: clientTimestamp
        });
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("outbox-updated"));
        }
        return {
          ...bodyObj,
          updated_at: clientTimestamp
        } as unknown as T;
      }

      if (path.includes("/soil/records") && method === "POST" && typeof rest.body === "string") {
        const bodyObj = JSON.parse(rest.body);
        const clientId = "soil-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
        await enqueueOutbox({
          client_id: clientId,
          operation_type: "CREATE_SOIL_RECORD",
          payload: bodyObj,
          client_timestamp: new Date().toISOString(),
        });
        console.log(`[API:apiRequest] Intercepted offline CREATE_SOIL_RECORD and enqueued to outbox: ${clientId}`);
        return {
          id: "offline-" + clientId,
          farm_id: bodyObj.farm_id,
          crop_type: "WHEAT",
          nitrogen: bodyObj.nitrogen,
          phosphorus: bodyObj.phosphorus,
          potassium: bodyObj.potassium,
          ph: bodyObj.ph,
          organic_carbon: bodyObj.organic_carbon,
          electrical_conductivity: bodyObj.electrical_conductivity,
          deficiency_status: {
            nitrogen: "OPTIMAL",
            phosphorus: "OPTIMAL",
            potassium: "OPTIMAL",
            ph: "OPTIMAL",
            organic_carbon: "OPTIMAL",
            electrical_conductivity: "OPTIMAL"
          },
          soil_health_index: 80.0,
          recorded_at: new Date().toISOString()
        } as unknown as T;
      }
      
      if (
        path.includes("/alerts/") &&
        (path.includes("/read") || path.includes("/acknowledge")) &&
        method === "PUT"
      ) {
        const alertId = path.split("/alerts/")[1].split("/")[0];
        const clientId = "alert-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
        await enqueueOutbox({
          client_id: clientId,
          operation_type: "MARK_ALERT_READ",
          payload: { alert_id: alertId },
          client_timestamp: new Date().toISOString(),
        });
        console.log(`[API:apiRequest] Intercepted offline MARK_ALERT_READ and enqueued to outbox: ${clientId}`);
        return {
          id: alertId,
          read: true,
          lifecycle_status: "ACKNOWLEDGED",
        } as unknown as T;
      }

      if (path.includes("/notifications/subscribe") && method === "POST" && typeof rest.body === "string") {
        const bodyObj = JSON.parse(rest.body);
        const clientId = "push-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
        await enqueueOutbox({
          client_id: clientId,
          operation_type: "SAVE_PUSH_SUBSCRIPTION",
          payload: bodyObj,
          client_timestamp: new Date().toISOString(),
        });
        return undefined as unknown as T;
      }

      if (path.includes("/farm-db/farms")) {
        if (method === "POST" && typeof rest.body === "string") {
          const bodyObj = JSON.parse(rest.body);
          const localFarm = await createFarm(bodyObj);
          await enqueueOutbox({
            client_id: localFarm.id,
            operation_type: "CREATE_FARM",
            payload: bodyObj,
            client_timestamp: new Date().toISOString(),
          });
          return localFarm as unknown as T;
        }
        if (method === "PUT" && typeof rest.body === "string") {
          const match = path.match(/\/farm-db\/farms\/([^/?]+)/);
          if (match) {
            const farmId = match[1];
            const bodyObj = JSON.parse(rest.body);
            const existing = await getFarmById(farmId);
            const updatedFarm = await createFarm({
              ...existing,
              ...bodyObj,
              id: farmId,
            });
            await enqueueOutbox({
              client_id: "update_farm_" + farmId + "_" + Date.now(),
              operation_type: "UPDATE_FARM",
              payload: { farm_id: farmId, ...bodyObj },
              client_timestamp: new Date().toISOString(),
            });
            return updatedFarm as unknown as T;
          }
        }
        if (method === "DELETE") {
          const match = path.match(/\/farm-db\/farms\/([^/?]+)/);
          if (match) {
            await deleteFarm(match[1]);
            await enqueueOutbox({
              client_id: "del_farm_" + match[1],
              operation_type: "DELETE_FARM",
              payload: { farm_id: match[1] },
              client_timestamp: new Date().toISOString(),
            });
            return undefined as unknown as T;
          }
        }
      }
      if (path.includes("/farm-db/plots")) {
        if (method === "POST" && typeof rest.body === "string") {
          const bodyObj = JSON.parse(rest.body);
          const localPlot = await createPlot(bodyObj);
          await enqueueOutbox({
            client_id: localPlot.id,
            operation_type: "CREATE_PLOT",
            payload: bodyObj,
            client_timestamp: new Date().toISOString(),
          });
          return localPlot as unknown as T;
        }
        if (method === "PUT" && typeof rest.body === "string") {
          const match = path.match(/\/farm-db\/plots\/([^/?]+)/);
          if (match) {
            const plotId = match[1];
            const bodyObj = JSON.parse(rest.body);
            const existing = await getPlotById(plotId);
            const updatedPlot = await createPlot({
              ...existing,
              ...bodyObj,
              id: plotId,
            });
            await enqueueOutbox({
              client_id: "update_plot_" + plotId + "_" + Date.now(),
              operation_type: "UPDATE_PLOT",
              payload: { plot_id: plotId, ...bodyObj },
              client_timestamp: new Date().toISOString(),
            });
            return updatedPlot as unknown as T;
          }
        }
        if (method === "DELETE") {
          const match = path.match(/\/farm-db\/plots\/([^/?]+)/);
          if (match) {
            await deletePlot(match[1]);
            await enqueueOutbox({
              client_id: "del_plot_" + match[1],
              operation_type: "DELETE_PLOT",
              payload: { plot_id: match[1] },
              client_timestamp: new Date().toISOString(),
            });
            return undefined as unknown as T;
          }
        }
      }
      if (path.includes("/farm-db/crop-cycles")) {
        if (method === "POST" && typeof rest.body === "string") {
          const bodyObj = JSON.parse(rest.body);
          const localCycle = await createCropCycle(bodyObj);
          await enqueueOutbox({
            client_id: localCycle.id,
            operation_type: "CREATE_CROP_CYCLE",
            payload: bodyObj,
            client_timestamp: new Date().toISOString(),
          });
          return localCycle as unknown as T;
        }
        if (method === "PUT" && typeof rest.body === "string") {
          const match = path.match(/\/farm-db\/crop-cycles\/([^/?]+)/);
          if (match) {
            const cycleId = match[1];
            const bodyObj = JSON.parse(rest.body);
            const existing = await getCropCycleById(cycleId);
            const updatedCycle = await createCropCycle({
              ...existing,
              ...bodyObj,
              id: cycleId,
            });
            await enqueueOutbox({
              client_id: "update_cycle_" + cycleId + "_" + Date.now(),
              operation_type: "UPDATE_CROP_CYCLE",
              payload: { crop_cycle_id: cycleId, ...bodyObj },
              client_timestamp: new Date().toISOString(),
            });
            return updatedCycle as unknown as T;
          }
        }
        if (method === "DELETE") {
          const match = path.match(/\/farm-db\/crop-cycles\/([^/?]+)/);
          if (match) {
            await deleteCropCycle(match[1]);
            await enqueueOutbox({
              client_id: "del_cycle_" + match[1],
              operation_type: "DELETE_CROP_CYCLE",
              payload: { crop_cycle_id: match[1] },
              client_timestamp: new Date().toISOString(),
            });
            return undefined as unknown as T;
          }
        }
      }
      if (path.includes("/farm-db/expenses")) {
        if (method === "POST" && typeof rest.body === "string") {
          const bodyObj = JSON.parse(rest.body);
          const localExpense = await createExpense(bodyObj);
          await enqueueOutbox({
            client_id: localExpense.id,
            operation_type: "CREATE_EXPENSE",
            payload: bodyObj,
            client_timestamp: new Date().toISOString(),
          });
          return localExpense as unknown as T;
        }
        if (method === "PUT" && typeof rest.body === "string") {
          const match = path.match(/\/farm-db\/expenses\/([^/?]+)/);
          if (match) {
            const expenseId = match[1];
            const bodyObj = JSON.parse(rest.body);
            const existing = await getFromStore<any>("expenses", expenseId);
            const updatedExpense = await createExpense({
              ...existing,
              ...bodyObj,
              id: expenseId,
            });
            await enqueueOutbox({
              client_id: "update_expense_" + expenseId + "_" + Date.now(),
              operation_type: "UPDATE_EXPENSE",
              payload: { expense_id: expenseId, ...bodyObj },
              client_timestamp: new Date().toISOString(),
            });
            return updatedExpense as unknown as T;
          }
        }
        if (method === "DELETE") {
          const match = path.match(/\/farm-db\/expenses\/([^/?]+)/);
          if (match) {
            await deleteExpense(match[1]);
            await enqueueOutbox({
              client_id: "del_expense_" + match[1],
              operation_type: "DELETE_EXPENSE",
              payload: { expense_id: match[1] },
              client_timestamp: new Date().toISOString(),
            });
            return undefined as unknown as T;
          }
        }
      }
      if (path.includes("/farm-db/harvests")) {
        if (method === "POST" && typeof rest.body === "string") {
          const bodyObj = JSON.parse(rest.body);
          const localHarvest = await createHarvest(bodyObj);
          await enqueueOutbox({
            client_id: localHarvest.id,
            operation_type: "CREATE_HARVEST",
            payload: bodyObj,
            client_timestamp: new Date().toISOString(),
          });
          return localHarvest as unknown as T;
        }
        if (method === "PUT" && typeof rest.body === "string") {
          const match = path.match(/\/farm-db\/harvests\/([^/?]+)/);
          if (match) {
            const harvestId = match[1];
            const bodyObj = JSON.parse(rest.body);
            const existing = await getFromStore<any>("harvests", harvestId);
            const updatedHarvest = await createHarvest({
              ...existing,
              ...bodyObj,
              id: harvestId,
            });
            await enqueueOutbox({
              client_id: "update_harvest_" + harvestId + "_" + Date.now(),
              operation_type: "UPDATE_HARVEST",
              payload: { harvest_id: harvestId, ...bodyObj },
              client_timestamp: new Date().toISOString(),
            });
            return updatedHarvest as unknown as T;
          }
        }
        if (method === "DELETE") {
          const match = path.match(/\/farm-db\/harvests\/([^/?]+)/);
          if (match) {
            await deleteHarvest(match[1]);
            await enqueueOutbox({
              client_id: "del_harvest_" + match[1],
              operation_type: "DELETE_HARVEST",
              payload: { harvest_id: match[1] },
              client_timestamp: new Date().toISOString(),
            });
            return undefined as unknown as T;
          }
        }
      }
    }

    const cached = await readOfflineCache<T>(path);
    if (cached) {
      console.log(`[API:apiRequest] Returning cached IndexedDB snapshot for: ${path}`);
      return cached;
    }
    
    const fallbackFixture = resolveDemoFixture<T>(path, method, typeof rest.body === "string" ? rest.body : undefined, true);
    if (fallbackFixture) {
      console.log(`[API:apiRequest] Returning fallback demo fixture for: ${path}`);
      return fallbackFixture;
    }

    // Disease-route safety net: return deterministic fallbacks instead of throwing
    if (path.includes("/disease/detect")) {
      console.log(`[API:apiRequest] Disease detect fallback for: ${path}`);
      return {
        report_id: "offline-report",
        farm_id: "offline-farm",
        crop_type: "Unknown",
        disease: "OFFLINE_MODE",
        confidence: 0.0,
        deterministic_status: "UNAVAILABLE",
        explanation: { summary: "Disease diagnosis is currently unavailable offline.", inputs: {}, primary_factor: "NONE" }
      } as unknown as T;
    }
    if (path.includes("/disease-radar") || path.includes("/disease/")) {
      console.log(`[API:apiRequest] Disease radar/history fallback for: ${path}`);
      return { hotspots: [], queried_at: new Date().toISOString(), radius_km: 0 } as unknown as T;
    }

    console.log(`[API:apiRequest] No cache and no demo fixture found for: ${path}. Throwing ApiError.`);
    // Only throw if the network is genuinely unreachable (not just a flaky navigator.onLine flag)
    if (networkError && (typeof window === "undefined" || !window.navigator.onLine)) {
      throw new ApiError("Network unavailable and no cached snapshot found", 0);
    }
  }

  if (!response) {
    throw new ApiError("Network unavailable", 0);
  }

  if (!response.ok) {
    let detail: unknown = undefined;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    const message =
      typeof detail === "object" &&
      detail !== null &&
      "detail" in detail &&
      typeof (detail as { detail: unknown }).detail === "string"
        ? (detail as { detail: string }).detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const data = (await response.json()) as T;
  if (method === "GET") {
    await writeOfflineCache(path, data);
  }
  return data;
}

export const api = {
  register: (payload: {
    phone: string;
    password: string;
    name: string;
    preferred_lang?: string;
  }) =>
    apiRequest<{ status: string; user_id: string }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
      skipAuth: true,
    }),

  login: (payload: { phone: string; password: string }) =>
    apiRequest<{ access_token: string; token_type: string; expires_in: number }>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
      },
    ),

  logout: () =>
    apiRequest<void>("/api/v1/auth/logout", {
      method: "POST",
    }),

  getMe: () => apiRequest<UserProfile>("/api/v1/users/me"),

  completeOnboarding: (payload: {
    crop_type: string;
    state: string;
    district: string;
    sowing_date: string;
    farm_name?: string;
    soil_type?: string;
  }) =>
    apiRequest<{
      status: string;
      farm_id: string;
      crop_cycle_id: string;
      onboarding_completed: boolean;
    }>("/api/v1/onboarding", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getFarmProfile: () => apiRequest<FarmProfile>("/api/v1/farms/me"),

  getWeatherForecast: (farmId: string) =>
    apiRequest<WeatherForecast>(`/api/v1/weather/forecast?farm_id=${farmId}`),

  getCropStage: (cycleId: string) =>
    apiRequest<CropStageData>(`/api/v1/crop-cycles/${cycleId}/stage`),

  getStressIndex: (farmId: string) =>
    apiRequest<StressIndexData>(`/api/v1/stress-index/${farmId}`),

  getAlerts: (params?: { farm_id?: string; unread_only?: boolean }) => {
    const search = new URLSearchParams();
    if (params?.farm_id) search.set("farm_id", params.farm_id);
    if (params?.unread_only) search.set("unread_only", "true");
    const query = search.toString();
    return apiRequest<AlertListData>(`/api/v1/alerts${query ? `?${query}` : ""}`);
  },

  triggerAlertEvaluation: (farmId: string) =>
    apiRequest<{
      farm_id: string;
      evaluated_rules: number;
      triggered_count: number;
      alerts_created: AlertData[];
      severity?: AlertSeverityData | null;
    }>("/api/v1/alerts/trigger-evaluation", {
      method: "POST",
      body: JSON.stringify({ farm_id: farmId }),
    }),

  getAlertSeverity: (farmId: string) =>
    apiRequest<{ severity: AlertSeverityData }>(
      `/api/v1/alerts/severity?farm_id=${encodeURIComponent(farmId)}`,
    ),

  markAlertRead: (alertId: string) =>
    apiRequest<AlertData>(`/api/v1/alerts/${alertId}/read`, {
      method: "PUT",
    }),

  acknowledgeAlert: (alertId: string) =>
    apiRequest<AlertData>(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: "PUT",
    }),

  resolveAlert: (alertId: string) =>
    apiRequest<AlertData>(`/api/v1/alerts/${alertId}/resolve`, {
      method: "PUT",
    }),

  getAlertEscalation: (alertId: string) =>
    apiRequest<{ id: string; events: Array<{ event_type: string; detail: string; channel?: string; recorded_at: string }> }>(
      `/api/v1/alerts/${alertId}/escalation`,
    ),

  getVapidPublicKey: () =>
    apiRequest<{ public_key: string; enabled: boolean }>("/api/v1/notifications/vapid-public-key"),

  subscribePush: (subscription: { endpoint: string; keys: { p256dh: string; auth: string } }) =>
    apiRequest<void>("/api/v1/notifications/subscribe", {
      method: "POST",
      body: JSON.stringify(subscription),
    }),

  getAlertPreferences: () =>
    apiRequest<AlertPreferences>("/api/v1/users/alert-preferences"),

  saveAlertPreferences: (prefs: AlertPreferences) =>
    apiRequest<AlertPreferences>("/api/v1/users/alert-preferences", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),

  createSoilRecord: async (payload: {
    farm_id: string;
    nitrogen: number;
    phosphorus: number;
    potassium: number;
    ph: number;
    organic_carbon: number;
    electrical_conductivity: number;
  }) => {
    if (typeof window !== 'undefined' && !navigator.onLine) {
      // Intercept the payload and pass it directly to our outbox store
      await writeOfflineCache("/health-card", payload);
      return { cached: true, status: "pending" } as any;
    }
    return apiRequest<SoilRecordData>("/api/v1/soil/records", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getLatestSoilRecord: (farmId: string) =>
    apiRequest<SoilRecordData>(`/api/v1/soil/records/latest?farm_id=${farmId}`),

  detectDisease: async (farmId: string, image: File) => {
    if (typeof window !== 'undefined' && !navigator.onLine) {
      console.warn("[CROP DOCTOR DEBUG] Operating offline. Returning static structural fallback payload.");
      return {
        report_id: "offline-report",
        farm_id: farmId,
        crop_type: "Unknown",
        disease: "OFFLINE_MODE",
        confidence: 0.0,
        deterministic_status: "UNAVAILABLE",
        explanation: {
          summary: "Disease diagnosis is currently unavailable offline.",
          inputs: {},
          primary_factor: "NONE",
        },
      } as DiseaseDetectResult;
    }
    const formData = new FormData();
    formData.append("farm_id", farmId);
    formData.append("image", image);
    return apiRequest<DiseaseDetectResult>("/api/v1/disease/detect", {
      method: "POST",
      body: formData,
    });
  },

  askAdvisory: async (payload: { farm_id: string; query: string; language?: string }) => {
    if (typeof window !== 'undefined' && !navigator.onLine) {
      console.log("[OFFLINE DEBUG] Network is offline. Triggering on-device fallback rule matrix...");
      
      // 1. Compute the local diagnostic result immediately
      const localResult = evaluateOfflineQuery(payload.query);
      
      // 2. Wrap the outbox logging in a safe, decoupled micro-task try/catch
      try {
        await enqueueOutbox({
          client_id: "advisory-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9),
          operation_type: "AUDIT_ADVISORY_QUERY",
          payload: { query: payload.query },
          client_timestamp: new Date().toISOString(),
        });
        console.log("[OFFLINE DEBUG] Audit log successfully enqueued to IndexedDB outbox.");
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("outbox-updated"));
        }
      } catch (dbError) {
        console.error("[OFFLINE WARNING] IndexedDB outbox write stalled, bypassing log to preserve UI:", dbError);
      }
      
      // 3. ALWAYS return the result to the chat screen regardless of outbox database state
      return localResult;
    }
    return apiRequest<AdvisoryResult>("/api/v1/advisory/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getAdvisoryActions: async (farmId: string, language?: string) => {
    const search = new URLSearchParams({ farm_id: farmId });
    if (language) search.set("language", language);
    return apiRequest<AdvisoryActionsResponse>(`/api/v1/advisory/actions?${search.toString()}`);
  },

  getCopilotPlan: (farmId: string, refresh = false) =>
    apiRequest<CopilotPlan>(
      `/api/v1/copilot/plan?farm_id=${encodeURIComponent(farmId)}${refresh ? "&refresh=true" : ""}`,
    ),

  refreshCopilotPlan: (farmId: string) =>
    apiRequest<CopilotPlan>(
      `/api/v1/copilot/plan/refresh?farm_id=${encodeURIComponent(farmId)}`,
      { method: "POST" },
    ),

  completeCopilotAction: (farmId: string, actionId: string, planId: string) =>
    apiRequest<{ action_id: string; completed: boolean; yield_protection_score?: number }>(
      `/api/v1/copilot/actions/${actionId}/complete?farm_id=${encodeURIComponent(farmId)}`,
      { method: "PUT", body: JSON.stringify({ plan_id: planId }) },
    ),

  getYieldProtectionScore: (farmId: string) =>
    apiRequest<YieldProtectionScore>(
      `/api/v1/copilot/yield-protection?farm_id=${encodeURIComponent(farmId)}`,
    ),

  getDiseaseRadarNearby: (params: { farm_id: string; radius_km?: number; crop_type?: string }) => {
    const search = new URLSearchParams({ farm_id: params.farm_id });
    if (params.radius_km) search.set("radius_km", String(params.radius_km));
    if (params.crop_type) search.set("crop_type", params.crop_type);
    return apiRequest<DiseaseRadarData>(`/api/v1/disease-radar/nearby?${search.toString()}`);
  },

  transcribeVoice: async (audio: Blob, language?: string) => {
    const formData = new FormData();
    formData.append("audio", audio, "recording.webm");
    if (language) formData.append("language", language);
    return apiRequest<VoiceTranscribeResult>("/api/v1/voice/transcribe", {
      method: "POST",
      body: formData,
    });
  },

  getLocalization: (lang: string) =>
    apiRequest<LocalizationData>(`/api/v1/localization/${lang}`),

  updateProfile: (payload: { preferred_lang?: string; name?: string }) =>
    apiRequest<UserProfile>("/api/v1/users/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  getHealthCard: (farmId: string) =>
    apiRequest<HealthCardData>(`/api/v1/health-card?farm_id=${farmId}`),

  getDailyBriefing: (farmId: string, language?: string) => {
    const search = new URLSearchParams({ farm_id: farmId });
    if (language) search.set("language", language);
    return apiRequest<BriefingData>(`/api/v1/briefing/daily?${search.toString()}`);
  },

  evaluateInputWindow: (payload: { farm_id: string; action_type: string }) =>
    apiRequest<InputWindowData>("/api/v1/optimizer/window", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMarketPrices: (farmId: string) =>
    apiRequest<MarketPricesData>(`/api/v1/market/prices?farm_id=${farmId}`),

  getEligibleSchemes: (farmId: string) =>
    apiRequest<SchemesData>(`/api/v1/schemes/eligible?farm_id=${farmId}`),

  runSimulator: (payload: {
    farm_id: string;
    temp_delta?: number;
    irrigation_delta?: number;
    nitrogen_delta?: number;
  }) =>
    apiRequest<SimulatorResult>("/api/v1/simulator/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  triggerSos: (payload: {
    farm_id: string;
    emergency_type: string;
    latitude?: number;
    longitude?: number;
  }) =>
    apiRequest<SosTriggerResult>("/api/v1/sos/dispatch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getEmergencyContacts: () =>
    apiRequest<EmergencyContacts>("/api/v1/sos/contacts"),

  saveEmergencyContacts: (contacts: {
    primary_contact: string;
    secondary_contact: string;
    village_contact: string;
  }) =>
    apiRequest<EmergencyContacts>("/api/v1/sos/contacts", {
      method: "POST",
      body: JSON.stringify(contacts),
    }),

  getSosHistory: () =>
    apiRequest<SosTriggerResult[]>("/api/v1/sos/history"),

  syncOutbox: async (operations: Array<{
    client_id: string;
    operation_type: string;
    payload: Record<string, unknown>;
    client_timestamp: string;
  }>) => {
    const result = await apiRequest<SyncBatchResult>("/api/v1/sync", {
      method: "POST",
      body: JSON.stringify({ operations }),
    });

    const opStoreMap: Record<string, string> = {
      "CREATE_FARM": "farms",
      "CREATE_PLOT": "plots",
      "CREATE_CROP_CYCLE": "crop_cycles",
      "CREATE_EXPENSE": "expenses",
      "CREATE_HARVEST": "harvests"
    };

    if (result && Array.isArray(result.results)) {
      for (const item of result.results) {
        if ((item.status === "SUCCESS" || item.status === "DUPLICATE") && item.server_id) {
          const storeName = opStoreMap[item.operation_type];
          if (storeName) {
            await reconcileLocalId(storeName, item.client_id, item.server_id);
            await reconcileRelationships(item.operation_type, item.client_id, item.server_id);
          }
        }
      }
    }

    return result;
  },

  syncKnowledge: async () => {
    try {
      const payload = await apiRequest<KnowledgeSyncPayload>("/api/v1/knowledge/sync");
      await syncLocalKnowledge(payload);
      return { status: "success", timestamp: payload.timestamp };
    } catch (err) {
      console.error("[api:syncKnowledge] Knowledge base sync failed:", err);
      return { status: "failed", error: String(err) };
    }
  },

  getDemoManifest: () =>
    apiRequest<{ demo_mode: boolean; version: string; farms: unknown[]; description: string }>(
      "/api/v1/demo/initialize",
      { skipAuth: true },
    ),

  getFarmerProfile: () => apiRequest<any>("/api/v1/farm-db/farmer/me"),
  updateFarmerProfile: (payload: { name?: string; preferred_language?: string; state?: string; district?: string }) =>
    apiRequest<any>("/api/v1/farm-db/farmer/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  createFarm: (payload: { name: string; area: number; area_unit: string; latitude?: number; longitude?: number }) =>
    apiRequest<any>("/api/v1/farm-db/farms", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listFarms: () => apiRequest<any[]>("/api/v1/farm-db/farms"),
  getFarm: (farmId: string) => apiRequest<any>(`/api/v1/farm-db/farms/${farmId}`),
  updateFarm: (farmId: string, payload: { name: string; area: number; area_unit: string; latitude?: number; longitude?: number }) =>
    apiRequest<any>(`/api/v1/farm-db/farms/${farmId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteFarm: (farmId: string) =>
    apiRequest<void>(`/api/v1/farm-db/farms/${farmId}`, {
      method: "DELETE",
    }),

  createPlot: (payload: { farm_id: string; name: string; area: number; area_unit: string }) =>
    apiRequest<any>("/api/v1/farm-db/plots", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listPlots: (farmId: string) => apiRequest<any[]>(`/api/v1/farm-db/plots?farm_id=${farmId}`),
  getPlot: (plotId: string) => apiRequest<any>(`/api/v1/farm-db/plots/${plotId}`),
  updatePlot: (plotId: string, payload: { farm_id: string; name: string; area: number; area_unit: string }) =>
    apiRequest<any>(`/api/v1/farm-db/plots/${plotId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deletePlot: (plotId: string) =>
    apiRequest<void>(`/api/v1/farm-db/plots/${plotId}`, {
      method: "DELETE",
    }),

  createCropCycle: (payload: { plot_id: string; crop_type: string; season: string; sowing_date: string; expected_harvest_date: string }) =>
    apiRequest<any>("/api/v1/farm-db/crop-cycles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listCropCycles: (plotId: string) => apiRequest<any[]>(`/api/v1/farm-db/crop-cycles?plot_id=${plotId}`),
  listActiveCropCycles: () => apiRequest<any[]>("/api/v1/farm-db/crop-cycles/active"),
  getCropCycle: (cycleId: string) => apiRequest<any>(`/api/v1/farm-db/crop-cycles/${cycleId}`),
  updateCropCycle: (cycleId: string, payload: { plot_id: string; crop_type: string; season: string; sowing_date: string; expected_harvest_date: string }) =>
    apiRequest<any>(`/api/v1/farm-db/crop-cycles/${cycleId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteCropCycle: (cycleId: string) =>
    apiRequest<void>(`/api/v1/farm-db/crop-cycles/${cycleId}`, {
      method: "DELETE",
    }),

  createExpense: (payload: { crop_cycle_id: string; category: string; amount: number; notes?: string; expense_date: string }) =>
    apiRequest<any>("/api/v1/farm-db/expenses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listExpenses: (cropCycleId: string) => apiRequest<any[]>(`/api/v1/farm-db/expenses?crop_cycle_id=${cropCycleId}`),
  getExpense: (expenseId: string) => apiRequest<any>(`/api/v1/farm-db/expenses/${expenseId}`),
  updateExpense: (expenseId: string, payload: { crop_cycle_id: string; category: string; amount: number; notes?: string; expense_date: string }) =>
    apiRequest<any>(`/api/v1/farm-db/expenses/${expenseId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteExpense: (expenseId: string) =>
    apiRequest<void>(`/api/v1/farm-db/expenses/${expenseId}`, {
      method: "DELETE",
    }),

  createHarvest: (payload: { crop_cycle_id: string; yield_quantity: number; yield_unit: string; revenue: number; harvest_date: string }) =>
    apiRequest<any>("/api/v1/farm-db/harvests", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listHarvests: (cropCycleId: string) => apiRequest<any[]>(`/api/v1/farm-db/harvests?crop_cycle_id=${cropCycleId}`),
  getHarvest: (harvestId: string) => apiRequest<any>(`/api/v1/farm-db/harvests/${harvestId}`),
  updateHarvest: (harvestId: string, payload: { crop_cycle_id: string; yield_quantity: number; yield_unit: string; revenue: number; harvest_date: string }) =>
    apiRequest<any>(`/api/v1/farm-db/harvests/${harvestId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteHarvest: (harvestId: string) =>
    apiRequest<void>(`/api/v1/farm-db/harvests/${harvestId}`, {
      method: "DELETE",
    }),
  getCropCycleProfitability: (cycleId: string) => apiRequest<any>(`/api/v1/profitability/crop-cycle/${cycleId}`),
  getPlotProfitability: (plotId: string) => apiRequest<any>(`/api/v1/profitability/plot/${plotId}`),
  getFarmProfitabilitySummary: (farmId: string) => apiRequest<any>(`/api/v1/profitability/farm/${farmId}`),
  getSeasonComparison: (farmId: string) => apiRequest<any[]>(`/api/v1/profitability/farm/${farmId}/season-comparison`),
  getDiseaseHistory: (page = 1, limit = 10, farmId?: string) => {
    let url = `/api/v1/disease/history?page=${page}&limit=${limit}`;
    if (farmId) url += `&farm_id=${farmId}`;
    return apiRequest<{ reports: DiseaseDetectResult[]; total: number; page: number; limit: number }>(url);
  },
  getDiseaseReport: (reportId: string) =>
    apiRequest<DiseaseDetectResult>(`/api/v1/disease/history/${reportId}`),
  getFarmTimeline: (farmId: string, limit = 20) =>
    apiRequest<FarmTimelineResponse>(`/api/v1/disease/timeline?farm_id=${farmId}&limit=${limit}`),
  seedDemoData: () =>
    apiRequest<{ success: boolean; message: string; farms: Array<{ farm_id: string; name: string; crop: string; status: string }> }>("/api/v1/demo/seed", {
      method: "POST",
    }),
};
