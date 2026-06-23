"use client";

import { CloudRain, Droplets, Thermometer, Wind } from "lucide-react";

import { BarChart } from "@/components/charts/BarChart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useWeather } from "@/hooks/useWeather";
import { useTranslation } from "@/stores/localizationStore";

type WeatherCardProps = {
  farmId?: string | null;
};

export function WeatherCard({ farmId }: WeatherCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useWeather(farmId);

  if (!farmId) {
    return null;
  }

  if (isLoading) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("dashboard.weather", "Weather")}</CardTitle>
          <CardDescription>{t("weather.loading", "Loading forecast…")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-32 animate-pulse rounded-xl bg-slate-100" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("dashboard.weather", "Weather")}</CardTitle>
          <CardDescription className="text-amber-700">
            {t("weather.unavailable", "Weather data unavailable — check your connection.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isCached = data.source === "CACHE_HIT";
  const forecastBars = data.forecast.slice(0, 5).map((day) => ({
    label: new Date(day.date).toLocaleDateString(undefined, { weekday: "short", day: "numeric" }),
    value: day.precipitation,
    color: "#0ea5e9",
  }));

  return (
    <Card className="dashboard-card">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <p className="dashboard-section-title mb-1">{t("weather.fieldConditions", "Field Conditions")}</p>
          <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
            <CloudRain className="h-5 w-5 text-sky-500" />
            {t("dashboard.weather", "Weather")}
          </CardTitle>
          <CardDescription>{t("weather.sevenDayConditions", "7-day field conditions")}</CardDescription>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
            isCached ? "bg-emerald-100 text-emerald-800" : "bg-sky-100 text-sky-800"
          }`}
        >
          {isCached ? t("weather.cached", "Cached") : t("weather.live", "Live")}
        </span>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric icon={Thermometer} label={t("weather.temp", "Temperature")} value={`${data.current.temp.toFixed(1)}°C`} accent="#f59e0b" />
          <Metric icon={Droplets} label={t("weather.humidity", "Humidity")} value={`${data.current.humidity.toFixed(0)}%`} accent="#0ea5e9" />
          <Metric icon={Wind} label={t("weather.wind", "Wind")} value={`${data.current.wind_speed.toFixed(1)} km/h`} accent="#64748b" />
          <Metric icon={CloudRain} label={t("weather.precipitation", "Precipitation")} value={`${data.current.precipitation.toFixed(1)} mm`} accent="#10b981" />
        </div>

        {forecastBars.length > 0 && (
          <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t("weather.outlook", "5-day precipitation outlook")}
            </p>
            <BarChart data={forecastBars} unit="mm" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-slate-100 bg-white p-3">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5" style={{ color: accent }} />
        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      </div>
      <p className="mt-1 text-lg font-bold text-slate-900">{value}</p>
    </div>
  );
}
