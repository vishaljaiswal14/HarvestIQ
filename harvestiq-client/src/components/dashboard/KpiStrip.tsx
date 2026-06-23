"use client";

import { Activity, AlertTriangle, HeartPulse, TrendingUp } from "lucide-react";

import { useAlerts } from "@/hooks/useAlerts";
import { useHealthCard } from "@/hooks/useHealthCard";
import {
  fsiSeverity,
  healthBandSeverity,
  riskBandSeverity,
  SEVERITY_STYLES,
} from "@/lib/dashboard-theme";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

type KpiStripProps = {
  farmId: string;
};

type KpiCardProps = {
  label: string;
  value: string;
  sublabel: string;
  severity: keyof typeof SEVERITY_STYLES;
  icon: React.ReactNode;
};

type SeverityStyleKey = keyof typeof SEVERITY_STYLES;

function KpiCard({ label, value, sublabel, severity, icon }: KpiCardProps) {
  const styles = SEVERITY_STYLES[severity];

  return (
    <div
      className={cn(
        "dashboard-kpi relative overflow-hidden rounded-xl border p-4 shadow-sm transition-shadow hover:shadow-md",
        styles.border,
        "bg-white",
      )}
    >
      <div
        className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full opacity-20"
        style={{ backgroundColor: styles.accent }}
      />
      <div className="relative flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
          <p className="text-2xl font-bold tracking-tight text-slate-900">{value}</p>
          {sublabel && <p className={cn("text-sm font-medium", styles.text)}>{sublabel}</p>}
        </div>
        <div
          className={cn("rounded-lg p-2.5", styles.bg)}
          style={{ color: styles.accent }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

export function KpiStrip({ farmId }: KpiStripProps) {
  const { t } = useTranslation();
  const { data: health, isLoading: healthLoading } = useHealthCard(farmId);
  const { data: alerts, isLoading: alertsLoading } = useAlerts(farmId);

  if (healthLoading || alertsLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-100" />
        ))}
      </div>
    );
  }

  const unread = alerts?.unread_count ?? 0;
  const alertList = alerts?.alerts ?? [];
  const highAlerts = alertList.filter((a) => a.severity === "HIGH").length;
  const alertSeverityLevel =
    highAlerts > 0 ? "critical" : unread > 0 ? "moderate" : "healthy";

  const fsiLabel = t("kpi.cropStressLabel", "Crop Stress");
  let fsiValue = "—";
  let fsiSublabel = "";
  if (health) {
    const cls = health.fsi_classification;
    if (cls === "HIGH_STRESS") fsiValue = t("status.highRisk", "High Risk");
    else if (cls === "MEDIUM_STRESS") fsiValue = t("status.moderateRisk", "Moderate Risk");
    else if (cls === "LOW_STRESS") fsiValue = t("status.needsAttention", "Needs Attention");
    else fsiValue = t("status.healthy", "Healthy");
  }

  const yieldLabel = t("kpi.farmConditionLabel", "Farm Condition");
  let yieldValue = "—";
  let yieldSublabel = "";
  if (health) {
    const band = health.yield_risk.risk_band;
    if (["CRITICAL", "HIGH"].includes(band)) {
      yieldValue = t("status.highRisk", "High Risk");
    } else if (band === "MEDIUM") {
      yieldValue = t("farmCondition.attention", "Needs Attention");
    } else {
      yieldValue = t("farmCondition.stable", "Stable");
    }
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        label={t("kpi.farmerHealth", "Farm Health")}
        value={health ? health.health_band === "GOOD" ? t("status.healthy", "Healthy") : health.health_band === "FAIR" ? t("status.needsAttention", "Needs Attention") : t("status.highRisk", "High Risk") : "—"}
        sublabel=""
        severity={health ? healthBandSeverity(health.health_band) as SeverityStyleKey : "neutral" as SeverityStyleKey}
        icon={<HeartPulse className="h-5 w-5" />}
      />
      <KpiCard
        label={fsiLabel}
        value={fsiValue}
        sublabel={fsiSublabel}
        severity={health ? fsiSeverity(health.fsi_classification) as SeverityStyleKey : "neutral" as SeverityStyleKey}
        icon={<Activity className="h-5 w-5" />}
      />
      <KpiCard
        label={yieldLabel}
        value={yieldValue}
        sublabel={yieldSublabel}
        severity={health ? riskBandSeverity(health.yield_risk.risk_band) as SeverityStyleKey : "neutral" as SeverityStyleKey}
        icon={<TrendingUp className="h-5 w-5" />}
      />
      <KpiCard
        label={t("kpi.activeAlerts", "Active Alerts")}
        value={String(alertList.length)}
        sublabel={unread > 0 ? t("kpi.unreadAlerts", "{count} unread").replace("{count}", String(unread)) : t("kpi.allClear", "All clear")}
        severity={alertList.length === 0 ? "healthy" as SeverityStyleKey : alertSeverityLevel as SeverityStyleKey}
        icon={<AlertTriangle className="h-5 w-5" />}
      />
    </div>
  );
}
