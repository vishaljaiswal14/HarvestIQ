"use client";

import { Sprout } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useCropStage } from "@/hooks/useCropStage";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

type CropStageProgressProps = {
  cycleId?: string | null;
};

export function CropStageProgress({ cycleId }: CropStageProgressProps) {
  const { data, isLoading, error } = useCropStage(cycleId);
  const { t } = useTranslation();

  if (!cycleId) {
    return null;
  }

  if (isLoading) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("cropStage.title", "Crop Stage")}</CardTitle>
          <CardDescription>{t("cropStage.calculating", "Calculating growth stage…")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error || !data || typeof data !== "object") {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("cropStage.title", "Crop Stage")}</CardTitle>
          <CardDescription className="text-red-600">
            {error instanceof Error ? error.message : t("cropStage.unableToLoad", "Unable to load crop stage")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Extract ALL values with safe defaults BEFORE JSX to prevent
  // any possibility of crash from undefined field access.
  const cropType = data.crop_type ?? "—";
  const stageName = data.stage ?? "—";
  const currentGdd = typeof data.current_gdd === "number" ? data.current_gdd : 0;
  const progressPct = typeof data.progress_percentage === "number" ? data.progress_percentage : 0;
  const timeline = Array.isArray(data.stages_timeline) ? data.stages_timeline : [];

  return (
    <Card className="dashboard-card">
      <CardHeader>
        <p className="dashboard-section-title mb-1">{t("cropStage.growthTracking", "Growth Tracking")}</p>
        <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
          <Sprout className="h-5 w-5 text-emerald-600" />
          {t("crop." + cropType.toLowerCase(), cropType)} — {t(stageName, stageName)}
        </CardTitle>
        <CardDescription>
          GDD {currentGdd.toFixed(1)} · {progressPct.toFixed(0)}% {t("cropStage.throughStage", "through stage")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 transition-all"
            style={{ width: `${Math.min(progressPct, 100)}%` }}
          />
        </div>
        <ol className="grid gap-2 sm:grid-cols-2">
          {timeline.map((stage) => (
            <li
              key={stage.name}
              className={cn(
                "rounded-lg border p-3 text-sm transition-colors",
                stage.is_current
                  ? "border-emerald-500 bg-emerald-50 shadow-sm"
                  : stage.is_completed
                    ? "border-emerald-200 bg-white text-slate-700"
                    : "border-slate-100 bg-slate-50/50 text-slate-500",
              )}
            >
              <p className="font-medium">{t(stage.name, stage.name)}</p>
              <p className="text-xs text-emerald-700">
                GDD {stage.gdd_min}–{stage.gdd_max}
              </p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

