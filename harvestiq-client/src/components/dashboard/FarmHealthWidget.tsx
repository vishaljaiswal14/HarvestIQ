"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type DiseaseDetectResult } from "@/lib/api";
import { useHealthCard } from "@/hooks/useHealthCard";
import { useTranslation } from "@/stores/localizationStore";
import { useAuthStore } from "@/stores/authStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Activity, Microscope, ArrowRight, ShieldAlert, CheckCircle2, AlertTriangle, Database } from "lucide-react";
import { cn } from "@/lib/utils";

type FarmHealthWidgetProps = {
  farmId: string;
};

export function FarmHealthWidget({ farmId }: FarmHealthWidgetProps) {
  const { t } = useTranslation();
  const refreshUser = useAuthStore((state) => state.refreshUser);
  const { data: health } = useHealthCard(farmId);
  const [reports, setReports] = useState<DiseaseDetectResult[]>([]);
  const [totalReports, setTotalReports] = useState(0);
  const [lastDisease, setLastDisease] = useState("None");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState("");

  const fetchHistorySummary = async () => {
    setLoadingHistory(true);
    try {
      const res = await api.getDiseaseHistory(1, 3, farmId);
      setReports(res.reports);
      setTotalReports(res.total);
      
      // Find the most recent non-HEALTHY disease scan
      const activeOutbreakRes = await api.getDiseaseHistory(1, 20, farmId);
      const lastDiseaseScan = activeOutbreakRes.reports.find(
        (r) => r.deterministic_status !== "HEALTHY" && r.deterministic_status !== "UNKNOWN"
      );
      if (lastDiseaseScan) {
        setLastDisease(lastDiseaseScan.disease_name || lastDiseaseScan.disease);
      } else {
        setLastDisease("None");
      }
    } catch (err) {
      console.error("Failed to load dashboard disease summary", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistorySummary();
  }, [farmId]);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setSeedMessage("");
    try {
      const res = await api.seedDemoData();
      if (res.success) {
        setSeedMessage(t("dashboard.seedingSuccess", "Seeding successful! Refreshing..."));
        // Reload Zustand farm profile state
        if (refreshUser) {
          await refreshUser();
        }
        // Force refresh page content after 1s
        setTimeout(() => {
          window.location.reload();
        }, 1200);
      }
    } catch (err) {
      console.error("Failed to seed demo data", err);
      setSeedMessage(t("dashboard.seedingFailed", "Seeding failed. Try again."));
    } finally {
      setSeeding(false);
    }
  };

  const getCropRisk = () => {
    if (!health) return "Low";
    const classification = health.fsi_classification.toUpperCase();
    if (classification.includes("HIGH")) return "High";
    if (classification.includes("MEDIUM")) return "Medium";
    return "Low";
  };

  const riskLevel = getCropRisk();

  return (
    <Card className="dashboard-card border border-slate-100 bg-white/95 shadow-sm overflow-hidden flex flex-col justify-between">
      <div className="h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-blue-600" />
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-600" />
            <div>
              <CardTitle className="text-sm font-bold text-slate-800">{t("dashboard.farmHealthTitle", "Farm Health Monitoring")}</CardTitle>
              <CardDescription className="text-[10px] text-slate-400 mt-0.5">{t("dashboard.farmHealthDesc", "Crop scans and field risk trends")}</CardDescription>
            </div>
          </div>
          <Link href="/disease">
            <Button variant="ghost" className="h-6 text-[10px] font-bold text-blue-600 hover:bg-blue-50 gap-1 px-1.5 py-0.5 rounded-lg border border-blue-100">
              {t("common.details", "Monitor")}
              <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Core Farm Health summary indicators */}
        <div className="grid grid-cols-3 gap-2 bg-slate-50/50 p-2.5 rounded-xl border border-slate-100 text-[10px]">
          <div className="flex flex-col gap-0.5">
            <span className="text-[9px] uppercase font-bold text-slate-400 leading-none">{t("dashboard.fh.risk", "Current Risk")}</span>
            <span className={cn(
              "font-extrabold text-xs mt-1 leading-none",
              riskLevel === "High" ? "text-red-650" : riskLevel === "Medium" ? "text-amber-600" : "text-emerald-600"
            )}>
              {riskLevel === "High" ? t("status.highRisk", "High Risk") : riskLevel === "Medium" ? t("status.moderateRisk", "Moderate Risk") : t("status.healthy", "Healthy")}
            </span>
          </div>

          {/* Last Disease */}
          <div className="flex flex-col gap-0.5 border-l border-slate-150 pl-2">
            <span className="text-[9px] uppercase font-bold text-slate-400 leading-none">{t("dashboard.fh.lastDisease", "Last Disease")}</span>
            <span className="font-extrabold text-xs text-slate-800 mt-1 leading-none truncate max-w-[120px]">
              {lastDisease === "None" ? t("cropStress.none", "None") : lastDisease}
            </span>
          </div>

          {/* Total reports */}
          <div className="flex flex-col gap-0.5 border-l border-slate-150 pl-2">
            <span className="text-[9px] uppercase font-bold text-slate-400 leading-none">{t("dashboard.fh.reports", "Reports")}</span>
            <span className="font-extrabold text-xs text-slate-800 mt-1 leading-none">
              {totalReports}
            </span>
          </div>
        </div>

        {/* Small list of recent disease reports */}
        <div className="space-y-1.5">
          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{t("dashboard.fh.recentScans", "Recent Scans")}</p>
          {loadingHistory ? (
            <div className="h-10 bg-slate-50 rounded-xl animate-pulse" />
          ) : reports.length === 0 ? (
            <p className="text-[10px] text-slate-600 bg-emerald-50/40 p-2 rounded-lg text-center border border-dashed border-emerald-100">{t("dashboard.fh.noScansYet", "No disease incidents detected. Recent monitoring looks clear.")}</p>
          ) : (
            <div className="space-y-1.5">
              {reports.map((report) => {
                const dateStr = report.created_at
                  ? new Date(report.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                  : "";
                const isHealthy = report.deterministic_status === "HEALTHY";
                const isUnknown = report.deterministic_status === "UNKNOWN";
                return (
                  <div key={report.report_id} className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-100/80 shadow-sm text-[10px] hover:border-slate-200 transition-colors">
                    <div className="flex items-center gap-2">
                      <div className="rounded p-1 bg-slate-50 border border-slate-100 text-slate-600">
                        <Microscope className="h-3 w-3" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-slate-850 truncate max-w-[120px]">
                          {t(report.disease_name || report.disease, report.disease_name || report.disease)}
                        </p>
                        <p className="text-[8px] text-slate-400 leading-none mt-0.5">{dateStr}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {isHealthy ? (
                        <span className="text-[9px] font-bold text-emerald-600 flex items-center gap-0.5 leading-none">
                          <CheckCircle2 className="h-3 w-3" />
                          Healthy
                        </span>
                      ) : isUnknown ? (
                        <span className="text-[9px] font-bold text-slate-500 flex items-center gap-0.5 leading-none">
                          <AlertTriangle className="h-3 w-3" />
                          Needs Review
                        </span>
                      ) : (
                        <span className="text-[9px] font-extrabold text-red-600 flex items-center gap-0.5 leading-none">
                          <ShieldAlert className="h-3 w-3" />
                          {report.risk_level === "High" ? t("status.highRisk", "High Risk") : t("status.moderateRisk", "Moderate Risk")}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Demo seeding block */}
        <div className="border-t border-slate-100 pt-3">
          <Button
            onClick={handleSeedDemo}
            disabled={seeding}
            variant="outline"
            className="w-full h-8 text-[10px] font-bold text-indigo-600 hover:text-indigo-750 hover:bg-indigo-50/50 border-indigo-200 border rounded-xl gap-1.5 flex items-center justify-center shadow-sm select-none"
          >
            <Database className="h-3.5 w-3.5" />
            {seeding ? t("dashboard.seeding", "Seeding mock data...") : t("dashboard.seedDemo", "Seed Demo Farm Scenarios")}
          </Button>
          {seedMessage && (
            <p className={cn(
              "text-[9px] text-center mt-1.5 font-bold leading-none animate-pulse",
              seedMessage.includes("success") ? "text-emerald-600" : "text-slate-650"
            )}>
              {seedMessage}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
