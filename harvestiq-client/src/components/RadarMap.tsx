"use client";

import { MapPin, Radar as RadarIcon, ShieldAlert } from "lucide-react";

import { AlertSeverityBadge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useDiseaseRadar } from "@/hooks/useDiseaseRadar";
import { alertSeverity, SEVERITY_STYLES } from "@/lib/dashboard-theme";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

type RadarMapProps = {
  farmId: string;
  cropType?: string | null;
};

export function RadarMap({ farmId, cropType }: RadarMapProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useDiseaseRadar(farmId, cropType ?? undefined);
  const highCount = data?.hotspots.filter((h) => h.risk_level === "HIGH").length ?? 0;

  return (
    <Card className="dashboard-card overflow-hidden">
      <div className="h-1.5 bg-gradient-to-r from-orange-500 via-red-500 to-orange-600" />
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="dashboard-section-title mb-1 text-orange-700/80">{t("radar.outbreakSurveillance", "Outbreak Surveillance")}</p>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
              <RadarIcon className="h-5 w-5 text-orange-500" />
              {t("errorBoundary.title.radarMap", "Satellite & Radar Map")}
            </CardTitle>
            <CardDescription>{t("radar.nearbyClusters", "Nearby confirmed outbreak clusters (72h window)")}</CardDescription>
          </div>
          {highCount > 0 && (
            <span className="flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800">
              <ShieldAlert className="h-3.5 w-3.5" />
              {t("radar.highRiskCount", "{count} HIGH").replace("{count}", String(highCount))}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-100" />
            ))}
          </div>
        )}
        {error && (
          <p className="text-sm text-red-700">
            {error instanceof Error ? error.message : t("radar.failed", "Failed to load radar")}
          </p>
        )}
        {data && data.hotspots.length === 0 && (
          <div className="flex flex-col items-center rounded-xl border border-dashed border-emerald-200 bg-emerald-50/50 py-10 text-center">
            <RadarIcon className="mb-3 h-10 w-10 text-emerald-400" />
            <p className="font-semibold text-emerald-800">{t("radar.noHotspots", "No hotspots detected")}</p>
            <p className="text-sm text-emerald-600">{t("radar.noOutbreaks", "Your field region shows no nearby outbreaks.")}</p>
          </div>
        )}
        {data?.hotspots.map((hotspot, index) => {
          const severity = alertSeverity(hotspot.risk_level);
          const styles = SEVERITY_STYLES[severity];
          return (
            <div
              key={`${hotspot.disease_name}-${index}`}
              className={cn(
                "relative overflow-hidden rounded-xl border p-4 transition-shadow hover:shadow-md",
                styles.border,
                "bg-white",
              )}
            >
              <div
                className="absolute inset-y-0 left-0 w-1.5"
                style={{ backgroundColor: styles.accent }}
              />
              <div className="flex items-start justify-between gap-3 pl-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-base font-bold text-slate-900">{hotspot.disease_name}</span>
                    <AlertSeverityBadge severity={hotspot.risk_level} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
                    <span className="font-medium">{hotspot.case_count} {t("radar.cases", "cases")}</span>
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {hotspot.distance_km} {t("radar.kmAway", "km away")}
                    </span>
                    <span>{t("crop." + hotspot.crop_type.toLowerCase(), hotspot.crop_type)}</span>
                  </div>
                </div>
                <div
                  className={cn("hidden shrink-0 rounded-full p-3 sm:block", styles.bg)}
                  style={{ color: styles.accent }}
                >
                  <RadarIcon className="h-5 w-5" />
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function RadarSummaryChip({ farmId, cropType }: RadarMapProps) {
  const { t } = useTranslation();
  const { data } = useDiseaseRadar(farmId, cropType ?? undefined);
  const highRisk = data?.hotspots.filter((h) => h.risk_level === "HIGH").length ?? 0;
  if (!highRisk) return null;
  return (
    <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-800">
      {t("radar.summaryHotspots", "{count} high-risk radar hotspot(s) nearby").replace("{count}", String(highRisk))}
    </span>
  );
}
