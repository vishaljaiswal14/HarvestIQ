import { cacheSnapshot, readCachedSnapshot } from "./db";

export type LocalCrop = {
  crop_type: string;
  display_name: string;
  gdd_base_temp: number;
  water_req_mm: number;
  soil_ph_min: number;
  soil_ph_max: number;
  nitrogen_rdf: number;
  phosphorus_rdf: number;
  potassium_rdf: number;
};

export type LocalCropStage = {
  crop_type: string;
  stage_name: string;
  gdd_min: number;
  gdd_max: number;
  vulnerability: number;
  water_demand_coefficient: number;
};

export type LocalDisease = {
  disease_tag: string;
  display_name: string;
  crop_type: string;
  symptoms: string;
  causes: string;
  treatment_physical: string;
  treatment_chemical: string;
};

export type LocalCropCalendar = {
  crop_type: string;
  stage_name: string;
  instructions: string;
  fertilizer_recommendation?: string | null;
};

export type KnowledgeSyncPayload = {
  timestamp: string;
  crops: LocalCrop[];
  stages: LocalCropStage[];
  diseases: LocalDisease[];
  calendars: LocalCropCalendar[];
};

/**
 * Persists the incoming knowledge synchronization payload to the local offline IndexedDB database.
 */
export async function syncLocalKnowledge(payload: KnowledgeSyncPayload): Promise<void> {
  if (typeof window === "undefined") return;

  console.log("[OfflineDB] Committing sync local knowledge packet dated:", payload.timestamp);

  // 1. Group stages, diseases, and calendars by crop type
  const stagesByCrop: Record<string, LocalCropStage[]> = {};
  const diseasesByCrop: Record<string, LocalDisease[]> = {};
  const calendarsByCrop: Record<string, LocalCropCalendar[]> = {};

  for (const c of payload.crops) {
    stagesByCrop[c.crop_type] = [];
    diseasesByCrop[c.crop_type] = [];
    calendarsByCrop[c.crop_type] = [];
  }

  for (const s of payload.stages) {
    if (stagesByCrop[s.crop_type]) {
      stagesByCrop[s.crop_type].push(s);
    }
  }

  for (const d of payload.diseases) {
    if (diseasesByCrop[d.crop_type]) {
      diseasesByCrop[d.crop_type].push(d);
    }
  }

  for (const cal of payload.calendars) {
    if (calendarsByCrop[cal.crop_type]) {
      calendarsByCrop[cal.crop_type].push(cal);
    }
  }

  // 2. Cache individual elements transactionally
  await cacheSnapshot("knowledge", "crops_list", payload.crops);

  for (const c of payload.crops) {
    await cacheSnapshot("knowledge", `crop:${c.crop_type}`, c);
    await cacheSnapshot("knowledge", `stages:${c.crop_type}`, stagesByCrop[c.crop_type] || []);
    await cacheSnapshot("knowledge", `diseases:${c.crop_type}`, diseasesByCrop[c.crop_type] || []);
    await cacheSnapshot("knowledge", `calendar:${c.crop_type}`, calendarsByCrop[c.crop_type] || []);
  }

  await cacheSnapshot("knowledge", "sync_meta", {
    last_synced_at: payload.timestamp,
    status: "SUCCESS",
  });
}

/**
 * Retrieves the full list of supported crops offline.
 */
export async function getLocalCrops(): Promise<LocalCrop[]> {
  return (await readCachedSnapshot<LocalCrop[]>("knowledge", "crops_list")) ?? [];
}

/**
 * Retrieves target details for a specific crop type.
 */
export async function getLocalCropDetails(cropType: string): Promise<LocalCrop | null> {
  return await readCachedSnapshot<LocalCrop>("knowledge", `crop:${cropType.toUpperCase()}`);
}

/**
 * Retrieves growth stage GDD triggers for a crop type.
 */
export async function getLocalCropStages(cropType: string): Promise<LocalCropStage[]> {
  return (await readCachedSnapshot<LocalCropStage[]>("knowledge", `stages:${cropType.toUpperCase()}`)) ?? [];
}

/**
 * Retrieves crop diseases catalog entries offline.
 */
export async function getLocalCropDiseases(cropType: string): Promise<LocalDisease[]> {
  return (await readCachedSnapshot<LocalDisease[]>("knowledge", `diseases:${cropType.toUpperCase()}`)) ?? [];
}

/**
 * Retrieves stage calendar operational guidance instructions.
 */
export async function getLocalCropCalendar(cropType: string, stageName: string): Promise<LocalCropCalendar | null> {
  const list = await readCachedSnapshot<LocalCropCalendar[]>("knowledge", `calendar:${cropType.toUpperCase()}`);
  if (!list) return null;
  const match = list.find((item) => item.stage_name.toLowerCase() === stageName.toLowerCase());
  return match ?? null;
}
