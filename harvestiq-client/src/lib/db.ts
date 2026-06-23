const DB_NAME = "harvestiq-pwa";
const DB_VERSION = 6;

export type CacheStore =
  | "health"
  | "briefing"
  | "weather"
  | "stage"
  | "stress"
  | "market"
  | "schemes"
  | "alerts"
  | "farm"
  | "localization"
  | "knowledge"
  | "farms"
  | "plots"
  | "crop_cycles"
  | "expenses"
  | "harvests";

type CacheRecord = {
  key: string;
  payload: unknown;
  cached_at: string;
};

const ALL_STORES = [
  "health",
  "briefing",
  "weather",
  "stage",
  "stress",
  "market",
  "schemes",
  "alerts",
  "farm",
  "localization",
  "knowledge",
  "outbox",
  "lastSync",
  "farms",
  "plots",
  "crop_cycles",
  "expenses",
  "harvests",
] as const;

export function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      for (const store of ALL_STORES) {
        if (!db.objectStoreNames.contains(store)) {
          db.createObjectStore(store, { keyPath: "key" });
        }
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function cacheSnapshot(store: CacheStore, key: string, payload: unknown): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put({
      key,
      payload,
      cached_at: new Date().toISOString(),
    } satisfies CacheRecord);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function readCachedSnapshot<T>(store: CacheStore, key: string): Promise<T | null> {
  if (typeof indexedDB === "undefined") return null;
  const db = await openDb();
  const record = await new Promise<CacheRecord | undefined>((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const request = tx.objectStore(store).get(key);
    request.onsuccess = () => resolve(request.result as CacheRecord | undefined);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return (record?.payload as T) ?? null;
}

// ── Last sync timestamp ────────────────────────────────────────────────────

export async function writeLastSync(isoTimestamp: string): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  try {
    const db = await openDb();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("lastSync", "readwrite");
      tx.objectStore("lastSync").put({ key: "global", payload: isoTimestamp, cached_at: isoTimestamp });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  } catch {
    // non-fatal
  }
}

export async function readLastSync(): Promise<string | null> {
  if (typeof indexedDB === "undefined") return null;
  try {
    const db = await openDb();
    const record = await new Promise<CacheRecord | undefined>((resolve, reject) => {
      const tx = db.transaction("lastSync", "readonly");
      const req = tx.objectStore("lastSync").get("global");
      req.onsuccess = () => resolve(req.result as CacheRecord | undefined);
      req.onerror = () => reject(req.error);
    });
    db.close();
    return (record?.payload as string) ?? null;
  } catch {
    return null;
  }
}

// ── Outbox ────────────────────────────────────────────────────────────────

export type OutboxEntry = {
  key: string;
  client_id: string;
  operation_type: string;
  payload: Record<string, unknown>;
  client_timestamp: string;
};

export async function enqueueOutbox(entry: Omit<OutboxEntry, "key">): Promise<void> {
  if (typeof indexedDB === "undefined") return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction("outbox", "readwrite");
    tx.objectStore("outbox").put({ ...entry, key: entry.client_id });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function readOutbox(): Promise<OutboxEntry[]> {
  if (typeof indexedDB === "undefined") return [];
  const db = await openDb();
  const entries = await new Promise<OutboxEntry[]>((resolve, reject) => {
    const tx = db.transaction("outbox", "readonly");
    const request = tx.objectStore("outbox").getAll();
    request.onsuccess = () => resolve(request.result as OutboxEntry[]);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return entries;
}

export async function clearOutboxKeys(keys: string[]): Promise<void> {
  if (typeof indexedDB === "undefined" || keys.length === 0) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction("outbox", "readwrite");
    const store = tx.objectStore("outbox");
    for (const key of keys) store.delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("outbox-updated"));
  }
}
