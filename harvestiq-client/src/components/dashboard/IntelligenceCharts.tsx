"use client";

import { BarChart } from "@/components/charts/BarChart";
import { HealthScoreRing } from "@/components/charts/HealthScoreRing";
import { RiskGauge } from "@/components/charts/RiskGauge";
import { Sparkline } from "@/components/charts/Sparkline";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useHealthCard } from "@/hooks/useHealthCard";
import { useWeather } from "@/hooks/useWeather";
import { EmptyState } from "@/components/ui/EmptyState";
import { useTranslation } from "@/stores/localizationStore";

type IntelligenceChartsProps = {
  farmId: string;
};

function buildStressTrend(fsi: number, delta: number, insufficient: boolean): number[] {
  if (insufficient) return [fsi];
  const previous = Math.max(0, Math.min(1, fsi - delta));
  const mid = Math.max(0, Math.min(1, fsi - delta / 2));
  return [previous, mid, fsi];
}

export function IntelligenceCharts({ farmId }: IntelligenceChartsProps) {
  const { data: health } = useHealthCard(farmId);
  const { data: weather } = useWeather(farmId);
  const { t } = useTranslation();

  const stressValues = health
    ? buildStressTrend(
        health.fsi,
        health.stress_momentum.fsi_delta,
        health.stress_momentum.insufficient_history,
      )
    : [];

  const stressLabels =
    stressValues.length > 1
      ? [t("analytics.prior", "Prior"), t("analytics.mid", "Mid"), t("analytics.now", "Now")]
      : stressValues.length === 1
      ? [t("analytics.now", "Now")]
      : [];

  const weatherBars =
    weather?.forecast.slice(0, 7).map((day) => ({
      label: new Date(day.date).toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
      value: day.temp_max,
      color: "#0284c7",
    })) ?? [];

  const precipSpark = weather?.forecast.slice(0, 7).map((d) => d.precipitation) ?? [];
  const precipLabels = weather?.forecast.slice(0, 7).map((d) =>
    new Date(d.date).toLocaleDateString(undefined, { day: "numeric" }),
  );

  const stressColor =
    health && health.fsi > 0.6 ? "#dc2626" : health && health.fsi > 0.35 ? "#d97706" : "#059669";

  return (
    <div>
      <p className="dashboard-section-title mb-2">{t("analytics.trendSignals", "Analytics · Trend Signals")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold text-slate-800">{t("analytics.stressTrajectory", "Stress Trajectory")}</CardTitle>
            <CardDescription>
              {health ? t(health.stress_momentum.direction, health.stress_momentum.direction) : "—"} · Δ{" "}
              {health?.stress_momentum.fsi_delta.toFixed(3) ?? "—"}{" "}
              {t("analytics.over", "over")}{" "}
              {health?.stress_momentum.window_days ?? "—"}d
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stressValues.length > 0 ? (
              <Sparkline values={stressValues} color={stressColor} labels={stressLabels} height={76} smooth />
            ) : (
              <EmptyState message={t("analytics.waiting", "Waiting for observations")} />
            )}
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold text-slate-800">{t("analytics.temperatureOutlook", "Temperature Outlook")}</CardTitle>
            <CardDescription>{t("analytics.temperatureDesc", "7-day maximum field temperature")}</CardDescription>
          </CardHeader>
          <CardContent>
            {weatherBars.length > 0 ? (
              <BarChart data={weatherBars} unit="°" title={t("analytics.dailyMax", "Daily max") + " °C"} />
            ) : (
              <EmptyState message={t("analytics.noData", "No data available yet")} />
            )}
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold text-slate-800">{t("analytics.yieldRiskProfile", "Yield Risk Profile")}</CardTitle>
            <CardDescription>{t("analytics.riskEstimate", "Compiled harvest risk estimate")}</CardDescription>
          </CardHeader>
          <CardContent>
            {health ? (
              <RiskGauge percent={health.yield_risk.estimated_risk_percent} band={t(health.yield_risk.risk_band, health.yield_risk.risk_band)} />
            ) : (
              <div className="h-16 animate-pulse rounded-lg bg-slate-100" />
            )}
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-bold text-slate-800">{t("analytics.healthPrecipitation", "Health & Precipitation")}</CardTitle>
            <CardDescription>{t("analytics.scoreRainfallDesc", "Score vs 7-day rainfall outlook")}</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-3">
            {health ? (
              <HealthScoreRing score={health.health_score} band={t(health.health_band, health.health_band)} size={88} strokeWidth={7} />
            ) : (
              <div className="h-[88px] w-[88px] animate-pulse rounded-full bg-slate-100" />
            )}
            <div className="min-w-0 flex-1">
              <Sparkline
                values={precipSpark}
                color="#0284c7"
                height={64}
                fill
                smooth
                labels={precipLabels && precipLabels.length > 1 ? [precipLabels[0], precipLabels[precipLabels.length - 1]] : undefined}
              />
              <p className="mt-1 text-center text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                {t("analytics.precipitation", "Precipitation")} (mm)
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
