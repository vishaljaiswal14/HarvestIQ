"use client";

import { WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useAuthStore } from "@/stores/authStore";
import { useDemoMode } from "@/hooks/useDemoMode";
import { t, useTranslation } from "@/stores/localizationStore";

function formatSyncTime(iso: string | null): string {
  if (!iso) return t("offline.time.unknown", "Unknown");
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);

    if (diffMins < 1) return t("offline.time.justNow", "Just now");
    if (diffMins < 60) {
      const key = diffMins === 1 ? "offline.time.minAgo" : "offline.time.minsAgo";
      return t(key, `${diffMins} min ago`).replace("{minutes}", String(diffMins));
    }
    if (diffHours < 24) {
      return date.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    return date.toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return t("offline.time.unknown", "Unknown");
  }
}

export function OfflineBanner() {
  const online = useOnlineStatus();
  const lastSyncAt = useAuthStore((s) => s.lastSyncAt);
  const { demoMode } = useDemoMode();
  const [syncLabel, setSyncLabel] = useState(() => formatSyncTime(lastSyncAt));
  const { t: tHook } = useTranslation();

  // Refresh the relative time label every minute
  useEffect(() => {
    setSyncLabel(formatSyncTime(lastSyncAt));
    const interval = setInterval(() => {
      setSyncLabel(formatSyncTime(lastSyncAt));
    }, 60_000);
    return () => clearInterval(interval);
  }, [lastSyncAt]);

  if (online) return null;

  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50/90 px-4 py-3.5 text-sm text-amber-900 shadow-sm backdrop-blur-sm">
      <WifiOff className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 animate-pulse" />
      <div className="min-w-0 space-y-1">
        <p className="font-semibold text-base leading-none text-amber-950">
          {tHook("offline.banner.title", "Offline Mode — Showing Last Synced Data")}
        </p>
        <div className="text-xs text-amber-800 space-y-0.5">
          <p className="font-medium">
            {tHook("offline.banner.lastSynced", "Last synced:")}{" "}
            <span className="underline decoration-amber-400 decoration-2">{syncLabel}</span> ·{" "}
            {tHook("offline.banner.connectionOffline", "Connection: Offline")}
          </p>
          <p className="mt-1">
            {demoMode
              ? tHook("offline.banner.demoMode", "Demo mode active. Cached presentation intelligence snapshots are being displayed.")
              : tHook("offline.banner.cachedDesc", "Cached dashboard data is being displayed. Changes will sync automatically when connection returns.")}
          </p>
        </div>
      </div>
    </div>
  );
}

