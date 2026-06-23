"use client";

import { useEffect } from "react";

import { api } from "@/lib/api";
import { clearOutboxKeys, readOutbox } from "@/lib/db";

export function useSyncOutbox() {
  useEffect(() => {
    let active = true;
    let isReplaying = false;

    const replay = async () => {
      if (!active) return;
      if (isReplaying) return;
      isReplaying = true;
      try {
        const entries = await readOutbox();
        if (entries.length === 0) return;
        
        console.log(`[Sync] replaying ${entries.length} outbox entries`);
        const result = await api.syncOutbox(
          entries.map((entry) => ({
            client_id: entry.client_id,
            operation_type: entry.operation_type,
            payload: entry.payload,
            client_timestamp: entry.client_timestamp,
          })),
        );
        
        const processedIds = result.results
          .filter((item) => item.status === "SUCCESS" || item.status === "DUPLICATE")
          .map((item) => item.client_id);
          
        if (result && Array.isArray(result.results)) {
          for (const item of result.results) {
            if (item.operation_type === "TRIGGER_SOS" && (item.status === "SUCCESS" || item.status === "DUPLICATE")) {
              if (typeof window !== "undefined") {
                window.dispatchEvent(new CustomEvent("sos-sync-success", {
                  detail: {
                    client_id: item.client_id,
                    server_id: item.server_id,
                  }
                }));
              }
            }
          }
        }

        if (processedIds.length > 0) {
          await clearOutboxKeys(processedIds);
          console.log(`[Sync] cleared processed outbox keys:`, processedIds);
        }
      } catch (err) {
        console.error("[Sync] failed to replay outbox:", err);
      } finally {
        isReplaying = false;
      }
    };

    const onOnline = () => {
      void replay();
    };
    window.addEventListener("online", onOnline);
    if (navigator.onLine) void replay();
    
    return () => {
      active = false;
      window.removeEventListener("online", onOnline);
    };
  }, []);
}
