"use client";

import { Activity } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useStressIndex } from "@/hooks/useStressIndex";
import { fsiSeverity, SEVERITY_STYLES } from "@/lib/dashboard-theme";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

type StressIndexCardProps = {
  farmId?: string | null;
};

export function StressIndexCard({ farmId }: StressIndexCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useStressIndex(farmId);

  if (!farmId) {
    return null;
  }

  if (isLoading) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("stress.cropStressTitle", "Crop Stress Outlook")}</CardTitle>
          <CardDescription>{t("stress.calculating", "Checking field conditions...")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-24 animate-pulse rounded-xl bg-slate-100" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("stress.cropStressTitle", "Crop Stress Outlook")}</CardTitle>
          <CardDescription className="text-amber-700">
            {t("stress.unavailable", "Crop stress outlook is unavailable right now. Cached guidance will appear when available.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const severity = fsiSeverity(data.classification);
  const styles = SEVERITY_STYLES[severity];
  const components = [
    { label: t("stress.thermal", "Heat pressure"), value: data.components.temp_stress, color: "#f59e0b" },
    { label: t("stress.moisture", "Moisture level"), value: data.components.rainfall_deficit, color: "#0ea5e9" },
    { label: t("stress.growthStage", "Growth stage"), value: data.components.gdd_scale, color: "#10b981" },
  ];
  const stressLabel =
    data.classification === "HIGH_STRESS" ? t("cropStress.highRisk", "High Risk") :
    data.classification === "MEDIUM_STRESS" ? t("cropStress.moderateRisk", "Moderate Risk") :
    data.classification === "LOW_STRESS" ? t("cropStress.needsAttention", "Needs Attention") :
    t("cropStress.healthy", "Healthy");
  const cleanExplanation = data.explanation.summary
    .replace(/\bFSI\b/gi, "crop stress")
    .replace(/Field Stress Index/gi, "crop stress")
    .replace(/Rainfall Deficit Index/gi, "rainfall shortage")
    .replace(/\bGDD\b/g, "crop growth stage")
    .replace(/\b(?:HIGH|MEDIUM|LOW)_STRESS\b/g, stressLabel.toLowerCase());

  return (
    <Card className="dashboard-card">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <p className="dashboard-section-title mb-1">{t("stress.analytics", "Crop Stress")}</p>
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
            <Activity className="h-5 w-5" style={{ color: styles.accent }} />
            {t("stress.cropStressTitle", "Crop Stress Outlook")}
          </CardTitle>
          <CardDescription>
            {t("crop." + data.crop_type.toLowerCase(), data.crop_type)} · {data.stage}
          </CardDescription>
        </div>
        <Badge severity={severity}>{stressLabel}</Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{stressLabel}</span>
          <div className="mb-2 ml-auto h-3 flex-1 max-w-[200px] overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${data.fsi * 100}%`, backgroundColor: styles.accent }}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {components.map((comp) => (
            <div key={comp.label} className="rounded-xl border border-slate-100 bg-white p-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{comp.label}</p>
                <span className="text-sm font-bold text-slate-900">
                  {comp.value >= 0.66 ? t("risk.high", "High") : comp.value >= 0.33 ? t("risk.moderate", "Moderate") : t("risk.low", "Low")}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${comp.value * 100}%`, backgroundColor: comp.color }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className={cn("rounded-xl border p-4 text-sm", styles.border, styles.bg)}>
          <p className="font-semibold text-slate-900">{t("stress.whyThisMatters", "Why this matters")}</p>
          <p className="mt-1 text-slate-700">{cleanExplanation}</p>
        </div>
      </CardContent>
    </Card>
  );
}
