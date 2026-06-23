"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Wifi, X, Check, AlertTriangle } from "lucide-react";

import { useDemoMode } from "@/hooks/useDemoMode";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { OfflineBanner } from "@/components/OfflineBanner";
import { api } from "@/lib/api";
import { readOutbox } from "@/lib/db";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

export function PwaStatusBar() {
  const online = useOnlineStatus();
  const { demoMode } = useDemoMode();
  const [pendingSync, setPendingSync] = useState(0);
  const [justReconnected, setJustReconnected] = useState(false);
  const [hasPendingSos, setHasPendingSos] = useState(false);
  const [successSos, setSuccessSos] = useState<{
    timestamp: string;
    recipientCount: number;
    status: string;
  } | null>(null);
  
  const { t } = useTranslation();

  const refresh = async () => {
    const entries = await readOutbox();
    setPendingSync(entries.length);
    setHasPendingSos(entries.some((e) => e.operation_type === "TRIGGER_SOS"));
  };

  useEffect(() => {
    void refresh();
    window.addEventListener("outbox-updated", refresh);
    const id = setInterval(() => void refresh(), 5000);
    return () => {
      window.removeEventListener("outbox-updated", refresh);
      clearInterval(id);
    };
  }, [online]);

  useEffect(() => {
    const handleSosSyncSuccess = async (e: Event) => {
      const customEvent = e as CustomEvent<{ server_id: string }>;
      const serverId = customEvent.detail?.server_id;
      if (!serverId) return;
      try {
        const history = await api.getSosHistory();
        const synced = history.find((item: any) => item.action_id === serverId);
        if (synced) {
          setSuccessSos({
            timestamp: new Date(synced.triggered_at).toLocaleString(),
            recipientCount: synced.recipients?.length ?? 0,
            status: synced.delivery_status,
          });
          // Clear after 10 seconds
          setTimeout(() => setSuccessSos(null), 10000);
        }
      } catch (err) {
        console.error("Failed to load synced SOS details", err);
      }
    };

    window.addEventListener("sos-sync-success", handleSosSyncSuccess);
    return () => {
      window.removeEventListener("sos-sync-success", handleSosSyncSuccess);
    };
  }, []);

  useEffect(() => {
    if (!online) return;
    setJustReconnected(true);
    const t = setTimeout(() => setJustReconnected(false), 4000);
    return () => clearTimeout(t);
  }, [online]);

  const showBar = !online || justReconnected || pendingSync > 0 || demoMode || hasPendingSos || !!successSos;

  if (!showBar) return null;

  return (
    <div className="space-y-2">
      {/* SOS Saved Offline Banner */}
      {!online && hasPendingSos && (
        <div className="flex flex-col gap-1 rounded-lg border border-red-200 bg-red-50 p-3.5 text-xs text-red-900 animate-pulse shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-650 shrink-0" />
            <span className="font-bold">{t("sos.banner.savedOffline", "SOS Saved Offline")}</span>
          </div>
          <p className="text-[10px] text-red-750 pl-6 leading-normal font-semibold">
            {t("sos.banner.waitingNetwork", "Waiting for network connection...")}
          </p>
        </div>
      )}

      {/* SOS Replay Successful Banner */}
      {successSos && (
        <div className="flex flex-col gap-1.5 rounded-lg border border-emerald-250 bg-emerald-50 p-4 text-xs text-emerald-950 shadow-md animate-in fade-in duration-300 relative">
          <button 
            onClick={() => setSuccessSos(null)}
            className="absolute top-2 right-2 text-emerald-600 hover:text-emerald-800 p-1 cursor-pointer"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <div className="flex items-center gap-2">
            <Check className="h-4 w-4 text-emerald-600 shrink-0" />
            <span className="font-bold text-sm">{t("sos.banner.delivered", "SOS Delivered Successfully")}</span>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-semibold mt-2 text-emerald-800 border-t border-emerald-100/50 pt-2">
            <div>{t("sos.timestamp", "Timestamp:")}</div>
            <div className="text-right">{successSos.timestamp}</div>
            <div>{t("sos.recipientCount", "Recipient Count:")}</div>
            <div className="text-right">{successSos.recipientCount}</div>
            <div>{t("sos.deliveryStatus", "Delivery Status:")}</div>
            <div className="text-right uppercase font-bold text-emerald-700">{successSos.status}</div>
          </div>
        </div>
      )}

      {!online && !hasPendingSos && <OfflineBanner />}

      {online && justReconnected && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
          <Wifi className="h-4 w-4 shrink-0" />
          <span className="font-medium">{t("pwa.statusBar.backOnline", "Back online")}</span>
          {pendingSync > 0 && (
            <span className="flex items-center gap-1 text-xs text-emerald-700">
              <RefreshCw className="h-3 w-3 animate-spin" />
              {t("pwa.statusBar.syncing", "Syncing {count} queued action(s)…").replace("{count}", String(pendingSync))}
            </span>
          )}
        </div>
      )}

      {online && !justReconnected && pendingSync > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-sky-900">
          <RefreshCw className="h-3.5 w-3.5" />
          {t("pwa.statusBar.waitingToSync", "{count} action(s) waiting to sync").replace("{count}", String(pendingSync))}
        </div>
      )}

      {demoMode && online && (
        <div className={cn("rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-800")}>
          {t("pwa.statusBar.demoMode", "Demo mode — presentation fixtures enabled")}
        </div>
      )}
    </div>
  );
}

