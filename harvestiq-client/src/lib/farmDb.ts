import { openDb, enqueueOutbox } from "./db";

export interface LocalFarm {
  key: string; // matches IndexedDB keyPath (maps to id)
  id: string;
  farmer_id: string;
  name: string;
  area: number;
  area_unit: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
}

export interface LocalPlot {
  key: string;
  id: string;
  farm_id: string;
  name: string;
  area: number;
  area_unit: string;
}

export interface LocalCropCycle {
  key: string;
  id: string;
  plot_id: string;
  crop_type: string;
  season: string;
  sowing_date: string;
  expected_harvest_date: string;
  status: "ACTIVE" | "HARVESTED" | "FAILED";
}

export interface LocalExpense {
  key: string;
  id: string;
  crop_cycle_id: string;
  category: string;
  amount: number;
  notes?: string;
  expense_date: string;
}

export interface LocalHarvest {
  key: string;
  id: string;
  crop_cycle_id: string;
  yield_quantity: number;
  yield_unit: string;
  revenue: number;
  harvest_date: string;
}

function isClient(): boolean {
  return typeof window !== "undefined" && typeof indexedDB !== "undefined";
}

export function generateLocalId(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

// ── Generic Object Store Operations ────────────────────────────────────────

export async function getFromStore<T>(storeName: string, key: string): Promise<T | null> {
  if (!isClient()) return null;
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const req = tx.objectStore(storeName).get(key);
    req.onsuccess = () => resolve((req.result as T) ?? null);
    req.onerror = () => reject(req.error);
  });
}

export async function getAllFromStore<T>(storeName: string): Promise<T[]> {
  if (!isClient()) return [];
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = () => resolve(req.result as T[]);
    req.onerror = () => reject(req.error);
  });
}

export async function putToStore<T>(storeName: string, record: T): Promise<void> {
  if (!isClient()) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).put(record);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function deleteFromStore(storeName: string, key: string): Promise<void> {
  if (!isClient()) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

// ── Farm Operations ────────────────────────────────────────────────────────

export async function createFarm(farm: Omit<LocalFarm, "key" | "id" | "created_at"> & { id?: string; created_at?: string }): Promise<LocalFarm> {
  const id = farm.id || generateLocalId("farm");
  const created_at = farm.created_at || new Date().toISOString();
  const record: LocalFarm = {
    ...farm,
    key: id,
    id,
    created_at,
  };
  await putToStore("farms", record);
  return record;
}

export async function getFarmById(id: string): Promise<LocalFarm | null> {
  return getFromStore<LocalFarm>("farms", id);
}

export async function listFarms(): Promise<LocalFarm[]> {
  return getAllFromStore<LocalFarm>("farms");
}

export async function deleteFarm(id: string): Promise<void> {
  await deleteFromStore("farms", id);
  // Cascade delete plots, cycles, etc. from local store
  const plots = await getPlotsByFarm(id);
  for (const plot of plots) {
    await deletePlot(plot.id);
  }
}

// ── Plot Operations ────────────────────────────────────────────────────────

export async function createPlot(plot: Omit<LocalPlot, "key" | "id"> & { id?: string }): Promise<LocalPlot> {
  const id = plot.id || generateLocalId("plot");
  const record: LocalPlot = {
    ...plot,
    key: id,
    id,
  };
  await putToStore("plots", record);
  return record;
}

export async function getPlotById(id: string): Promise<LocalPlot | null> {
  return getFromStore<LocalPlot>("plots", id);
}

export async function getPlotsByFarm(farmId: string): Promise<LocalPlot[]> {
  const all = await getAllFromStore<LocalPlot>("plots");
  return all.filter((p) => p.farm_id === farmId);
}

export async function deletePlot(id: string): Promise<void> {
  await deleteFromStore("plots", id);
  // Cascade delete crop cycles
  const cycles = await getCropCyclesByPlot(id);
  for (const cycle of cycles) {
    await deleteCropCycle(cycle.id);
  }
}

// ── Crop Cycle Operations ──────────────────────────────────────────────────

export async function createCropCycle(cycle: Omit<LocalCropCycle, "key" | "id"> & { id?: string }): Promise<LocalCropCycle> {
  const id = cycle.id || generateLocalId("cycle");
  const record: LocalCropCycle = {
    ...cycle,
    key: id,
    id,
  };
  await putToStore("crop_cycles", record);
  return record;
}

export async function getCropCycleById(id: string): Promise<LocalCropCycle | null> {
  return getFromStore<LocalCropCycle>("crop_cycles", id);
}

export async function getCropCyclesByPlot(plotId: string): Promise<LocalCropCycle[]> {
  const all = await getAllFromStore<LocalCropCycle>("crop_cycles");
  return all.filter((c) => c.plot_id === plotId);
}

export async function getActiveCropCycles(): Promise<LocalCropCycle[]> {
  const all = await getAllFromStore<LocalCropCycle>("crop_cycles");
  return all.filter((c) => c.status === "ACTIVE");
}

export async function deleteCropCycle(id: string): Promise<void> {
  await deleteFromStore("crop_cycles", id);
  // Cascade delete expenses & harvests
  const expenses = await getExpensesByCropCycle(id);
  for (const exp of expenses) {
    await deleteExpense(exp.id);
  }
  const harvests = await getHarvestsByCropCycle(id);
  for (const harv of harvests) {
    await deleteHarvest(harv.id);
  }
}

// ── Expense Operations ─────────────────────────────────────────────────────

export async function createExpense(expense: Omit<LocalExpense, "key" | "id"> & { id?: string }): Promise<LocalExpense> {
  const id = expense.id || generateLocalId("expense");
  const record: LocalExpense = {
    ...expense,
    key: id,
    id,
  };
  await putToStore("expenses", record);
  return record;
}

export async function getExpensesByCropCycle(cycleId: string): Promise<LocalExpense[]> {
  const all = await getAllFromStore<LocalExpense>("expenses");
  return all.filter((e) => e.crop_cycle_id === cycleId);
}

export async function deleteExpense(id: string): Promise<void> {
  await deleteFromStore("expenses", id);
}

// ── Harvest Operations ─────────────────────────────────────────────────────

export async function createHarvest(harvest: Omit<LocalHarvest, "key" | "id"> & { id?: string }): Promise<LocalHarvest> {
  const id = harvest.id || generateLocalId("harvest");
  const record: LocalHarvest = {
    ...harvest,
    key: id,
    id,
  };
  await putToStore("harvests", record);
  // Side-effect: mark the crop cycle as harvested locally
  const cycle = await getCropCycleById(harvest.crop_cycle_id);
  if (cycle) {
    cycle.status = "HARVESTED";
    await putToStore("crop_cycles", cycle);
  }
  return record;
}

export async function getHarvestsByCropCycle(cycleId: string): Promise<LocalHarvest[]> {
  const all = await getAllFromStore<LocalHarvest>("harvests");
  return all.filter((h) => h.crop_cycle_id === cycleId);
}

export async function deleteHarvest(id: string): Promise<void> {
  const harvest = await getFromStore<LocalHarvest>("harvests", id);
  await deleteFromStore("harvests", id);
  if (harvest) {
    // Check if other harvests remain for this cycle; if none, reset cycle status to ACTIVE
    const remaining = await getHarvestsByCropCycle(harvest.crop_cycle_id);
    if (remaining.length === 0) {
      const cycle = await getCropCycleById(harvest.crop_cycle_id);
      if (cycle) {
        cycle.status = "ACTIVE";
        await putToStore("crop_cycles", cycle);
      }
    }
  }
}

export async function reconcileLocalId(storeName: string, clientId: string, serverId: string): Promise<void> {
  const existing = await getFromStore<any>(storeName, clientId);
  if (existing) {
    await deleteFromStore(storeName, clientId);
    const updated = {
      ...existing,
      key: serverId,
      id: serverId
    };
    await putToStore(storeName, updated);
  }
}

export async function reconcileRelationships(operationType: string, clientId: string, serverId: string): Promise<void> {
  if (operationType === "CREATE_FARM") {
    const plots = await getAllFromStore<any>("plots");
    for (const plot of plots) {
      if (plot.farm_id === clientId) {
        plot.farm_id = serverId;
        await putToStore("plots", plot);
      }
    }
  } else if (operationType === "CREATE_PLOT") {
    const cycles = await getAllFromStore<any>("crop_cycles");
    for (const cycle of cycles) {
      if (cycle.plot_id === clientId) {
        cycle.plot_id = serverId;
        await putToStore("crop_cycles", cycle);
      }
    }
  } else if (operationType === "CREATE_CROP_CYCLE") {
    const expenses = await getAllFromStore<any>("expenses");
    for (const exp of expenses) {
      if (exp.crop_cycle_id === clientId) {
        exp.crop_cycle_id = serverId;
        await putToStore("expenses", exp);
      }
    }
    const harvests = await getAllFromStore<any>("harvests");
    for (const harv of harvests) {
      if (harv.crop_cycle_id === clientId) {
        harv.crop_cycle_id = serverId;
        await putToStore("harvests", harv);
      }
    }
  }
}
