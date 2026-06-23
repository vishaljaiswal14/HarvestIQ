"use client";

import { useEffect } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import { AuthGuard } from "@/components/AuthGuard";
import { AlertsPanel } from "@/components/AlertsPanel";
import { BriefingCard } from "@/components/BriefingCard";
import { BRAND } from "@/components/branding/HarvestIQLogo";
import { CropStageProgress } from "@/components/CropStageProgress";
import { IntelligenceCharts } from "@/components/dashboard/IntelligenceCharts";
import { FarmerHealthCard } from "@/components/FarmerHealthCard";
import { InputWindowCard } from "@/components/InputWindowCard";
import { AppShell } from "@/components/layout/AppShell";
import { MarketPriceCard } from "@/components/MarketPriceCard";
import { RadarMap } from "@/components/RadarMap";
import { SchemesCard } from "@/components/SchemesCard";
import { SoilHealthCard } from "@/components/SoilHealthCard";
import { StressIndexCard } from "@/components/StressIndexCard";
import { WeatherCard } from "@/components/WeatherCard";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { CropCycleProfitCard } from "@/components/dashboard/CropCycleProfitCard";
import { FarmProfitSummaryCard } from "@/components/dashboard/FarmProfitSummaryCard";
import { BestWorstCropWidget } from "@/components/dashboard/BestWorstCropWidget";
import { SeasonComparisonWidget } from "@/components/dashboard/SeasonComparisonWidget";
import { FarmHealthWidget } from "@/components/dashboard/FarmHealthWidget";
import { CopilotStrip } from "@/components/dashboard/CopilotStrip";
import { ClipboardList, MessageSquare, Microscope, SlidersHorizontal, BellOff, Clock, Droplets } from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import { useLocalizationStore, useTranslation } from "@/stores/localizationStore";
import { useHealthCard } from "@/hooks/useHealthCard";
import { useWeather } from "@/hooks/useWeather";
import { useAlerts } from "@/hooks/useAlerts";
import { EmptyState } from "@/components/ui/EmptyState";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import Link from "next/link";
import { SosButton } from "@/components/SosButton";
import { cn } from "@/lib/utils";

function getFarmStatusLabel(health?: { health_band: string; yield_risk: { risk_band: string }; unread_alerts: number } | null) {
  if (!health) return "Needs Attention";
  if (health.yield_risk.risk_band === "HIGH" || health.yield_risk.risk_band === "CRITICAL" || health.health_band === "POOR") {
    return "High Risk";
  }
  if (health.yield_risk.risk_band === "MEDIUM" || health.health_band === "FAIR" || health.unread_alerts > 0) {
    return "Needs Attention";
  }
  return "Healthy";
}

function getFarmStatusClasses(status: string) {
  if (status === "Healthy") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (status === "High Risk" || status === "Critical") return "bg-red-50 text-red-700 border-red-200";
  return "bg-amber-50 text-amber-700 border-amber-200";
}

function getCropStressLabel(classification?: string | null) {
  if (classification === "HIGH_STRESS") return "High Risk";
  if (classification === "MEDIUM_STRESS") return "Moderate Risk";
  if (classification === "LOW_STRESS") return "Needs Attention";
  return "Healthy";
}

function getMainRisk(health?: { fsi_classification: string; yield_risk: { risk_band: string }; unread_alerts: number } | null) {
  if (!health) return "Recent monitoring unavailable";
  if (health.fsi_classification === "HIGH_STRESS" || health.fsi_classification === "MEDIUM_STRESS") {
    return "Moisture Stress";
  }
  if (health.yield_risk.risk_band === "HIGH" || health.yield_risk.risk_band === "CRITICAL") {
    return "Yield Protection";
  }
  if (health.unread_alerts > 0) return "New Field Alert";
  return "No major risk detected";
}

function getRecommendedAction(health?: { fsi_classification: string; unread_alerts: number } | null) {
  if (!health) return "Review the latest field update when connectivity returns.";
  if (health.fsi_classification === "HIGH_STRESS") return "Irrigate within 24 hours.";
  if (health.fsi_classification === "MEDIUM_STRESS") return "Check soil moisture and plan irrigation.";
  if (health.unread_alerts > 0) return "Review active alerts and complete the recommended action.";
  return "Continue routine monitoring.";
}

function DashboardContent() {
  const router = useRouter();
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const farm = useAuthStore((state) => state.farm);

  // Load metrics data for Row 1
  const { data: health } = useHealthCard(farm?.farm_id);
  const { data: weather } = useWeather(farm?.farm_id);
  const { data: alerts } = useAlerts(farm?.farm_id);

  const preferredLang = useLocalizationStore((state) => state.preferredLang);
  const setLanguage = useLocalizationStore((state) => state.setLanguage);

  // Sync user profile preference with localization store preference
  useEffect(() => {
    if (user?.preferred_lang && user.preferred_lang !== preferredLang) {
      void setLanguage(user.preferred_lang);
    }
  }, [user?.preferred_lang, preferredLang, setLanguage]);

  return (
    <AppShell userName={user?.name}>
      {farm ? (
        <div className="space-y-6">
          {/* TOP SECTION (above the fold) */}
          <section className="rounded-2xl border border-emerald-100 bg-gradient-to-br from-white via-emerald-50/35 to-sky-50/35 p-4 shadow-sm">
            <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <div className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-700">{t("dashboard.farmStatus", "Farm Status")}</p>
                    <h2 className="mt-1 text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl">
                      {getFarmStatusLabel(health)}
                    </h2>
                  </div>
                  <span className={cn("rounded-full border px-3 py-1 text-xs font-extrabold", getFarmStatusClasses(getFarmStatusLabel(health)))}>
                    {getFarmStatusLabel(health)}
                  </span>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/70 bg-white/80 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{t("dashboard.cropAndStage", "Crop & Stage")}</p>
                    <p className="mt-1 text-sm font-extrabold text-slate-900">
                      {farm.crop_type} <span className="font-semibold text-slate-400">·</span> {health?.stage ?? "Current stage"}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/70 bg-white/80 p-3">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{t("dashboard.mainRisk", "Main Risk")}</p>
                    <p className="mt-1 text-sm font-extrabold text-slate-900">{getMainRisk(health)}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/80 bg-white/85 p-4 shadow-sm">
                <div className="flex items-start gap-3">
                  <div className="rounded-lg bg-emerald-50 p-2 text-emerald-700">
                    <Droplets className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{t("dashboard.recommendedAction", "Recommended Action")}</p>
                    <p className="mt-1 text-base font-extrabold text-slate-900">{getRecommendedAction(health)}</p>
                    <p className="mt-2 flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
                      <Clock className="h-3.5 w-3.5 text-slate-400" />
                      {t("dashboard.lastUpdated", "Last updated")}: {new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
          
          {/* Row 1: Health Score, Yield Risk, Active Alerts, Weather */}
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {/* Health Score */}
            <Card className="dashboard-card flex flex-col justify-between border-emerald-100/50 bg-white h-full">
              <CardHeader className="compact-card-header pb-1">
                <CardDescription className="text-slate-400 uppercase font-bold text-[9px] tracking-wider">{t("dashboard.primaryHealth", "Primary Health")}</CardDescription>
                <CardTitle className="text-sm font-bold text-slate-800">{t("dashboard.cropCondition", "Crop Condition")}</CardTitle>
              </CardHeader>
              <CardContent className="flex items-center justify-between px-4 py-3 flex-grow gap-2">
                {health ? (
                  <>
                    <div className="flex flex-col justify-center">
                      <div className="flex items-baseline">
                        <span className="text-2xl font-extrabold text-slate-900 leading-none">{getFarmStatusLabel(health)}</span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-1.5 leading-none">
                        <span className={cn(
                          "text-xs font-bold",
                          health.health_band.toUpperCase() === "GOOD" || health.health_band === "अच्छा" ? "text-emerald-600" :
                          health.health_band.toUpperCase() === "MODERATE" || health.health_band === "सामान्य" ? "text-amber-600" : "text-red-600"
                        )}>
                          {t(health.health_band, health.health_band)}
                        </span>
                        <span className="text-slate-300 select-none text-xs">·</span>
                        <span className="text-[10px] font-bold text-slate-600 bg-slate-100 px-1 py-0.5 rounded leading-none select-none">
                          {getCropStressLabel(health.fsi_classification)}
                        </span>
                      </div>
                      <span className="text-[9px] mt-1.5 text-slate-500 font-medium flex items-center gap-0.5 leading-none">
                        {health.stress_momentum.direction === "FALLING" ? (
                          <span className="text-emerald-600 font-bold">{t("dashboard.improving", "▲ Improving")}</span>
                        ) : health.stress_momentum.direction === "RISING" ? (
                          <span className="text-red-500 font-bold">{t("dashboard.worsening", "▼ Worsening")}</span>
                        ) : (
                          <span className="text-slate-400">{t("dashboard.stable", "Stable")}</span>
                        )}
                      </span>
                    </div>
                    <div className={cn("shrink-0 rounded-full border px-3 py-1 text-[10px] font-extrabold", getFarmStatusClasses(getFarmStatusLabel(health)))}>
                      {getCropStressLabel(health.fsi_classification)}
                    </div>
                  </>
                ) : (
                  <EmptyState message={t("dashboard.noHealthData", "Crop condition will appear after the next field update")} />
                )}
              </CardContent>
            </Card>

            {/* Yield Risk */}
            <Card className="dashboard-card flex flex-col justify-between border-emerald-100/50 bg-white h-full">
              <CardHeader className="compact-card-header pb-1">
                <CardDescription className="text-slate-400 uppercase font-bold text-[9px] tracking-wider">{t("dashboard.harvestEstimate", "Harvest Estimate")}</CardDescription>
                <CardTitle className="text-sm font-bold text-slate-800">{t("kpi.farmConditionLabel", "Farm Condition")}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col justify-center px-4 py-3 flex-grow">
                {health ? (
                  <div className="flex flex-col justify-center h-full">
                    <span className="text-xl font-extrabold text-slate-900 leading-none">
                      {["CRITICAL", "HIGH"].includes(health.yield_risk.risk_band)
                        ? t("farmCondition.highRisk", "High Risk")
                        : health.yield_risk.risk_band === "MEDIUM"
                          ? t("farmCondition.attention", "Needs Attention")
                          : t("farmCondition.stable", "Stable")}
                    </span>
                  </div>
                ) : (
                  <EmptyState message={t("dashboard.noYieldRiskData", "Yield outlook will appear after the next field update")} />
                )}
              </CardContent>
            </Card>

            {/* Active Alerts */}
            <Card className="dashboard-card flex flex-col justify-between border-emerald-100/50 bg-white h-full">
              <CardHeader className="compact-card-header pb-1">
                <CardDescription className="text-slate-400 uppercase font-bold text-[9px] tracking-wider">{t("dashboard.thresholdMonitoring", "Threshold Monitoring")}</CardDescription>
                <CardTitle className="text-sm font-bold text-slate-800">{t("dashboard.activeAlerts", "Active Alerts")}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col justify-center px-4 py-3 flex-grow">
                {alerts ? (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-3xl font-extrabold text-slate-900 leading-none">{alerts.alerts.length}</span>
                      {alerts.unread_count > 0 && (
                        <span className="rounded-full bg-red-500 px-2 py-0.5 text-[9px] font-bold text-white leading-none">
                          {t("alerts.newAlerts", "{count} new").replace("{count}", String(alerts.unread_count))}
                        </span>
                      )}
                    </div>
                    <p className={cn(
                      "text-xs mt-1.5 font-semibold truncate leading-none",
                      alerts.alerts.length > 0 ? "text-amber-600" : "text-emerald-600"
                    )}>
                      {alerts.alerts.length > 0 ? t(alerts.alerts[0].title, alerts.alerts[0].title) : t("dashboard.allSystemsClear", "All monitoring systems clear")}
                    </p>
                  </div>
                ) : (
                  <EmptyState message={t("dashboard.noAlertsData", "No active alerts right now")} icon={BellOff} />
                )}
              </CardContent>
            </Card>

            {/* Weather */}
            <Card className="dashboard-card flex flex-col justify-between border-emerald-100/50 bg-white h-full">
              <CardHeader className="compact-card-header pb-1">
                <CardDescription className="text-slate-400 uppercase font-bold text-[9px] tracking-wider">{t("dashboard.fieldConditions", "Field Conditions")}</CardDescription>
                <CardTitle className="text-sm font-bold text-slate-800">{t("dashboard.weather", "Weather")}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col justify-center px-4 py-3 flex-grow">
                {weather ? (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-3xl font-extrabold text-slate-900 leading-none">{weather.current.temp.toFixed(1)}°C</span>
                      <span className="text-[9px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-bold uppercase tracking-wider leading-none">
                        {weather.source === "CACHE_HIT" ? t("dashboard.cached", "Cached") : t("dashboard.live", "Live")}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 font-medium mt-1.5 leading-none">
                      {weather.current.humidity.toFixed(0)}% RH <span className="text-slate-300 select-none">·</span> {weather.current.wind_speed.toFixed(0)} km/h
                    </p>
                  </div>
                ) : (
                  <EmptyState message={t("dashboard.noWeatherData", "Weather guidance will appear when field data syncs")} />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Operations Copilot Strip */}
          <div className="w-full">
            <ErrorBoundary fallbackTitle={t("copilot.title", "Farm Operations Copilot")}>
              <CopilotStrip farmId={farm.farm_id} />
            </ErrorBoundary>
          </div>

          {/* Row 2: Daily Briefing (full-width prominent card) */}
          <div className="w-full">
            <ErrorBoundary fallbackTitle={t("errorBoundary.title.healthIntelligence", "Farmer Health Intelligence")}>
              <BriefingCard farmId={farm.farm_id} language={preferredLang} />
            </ErrorBoundary>
          </div>

          {/* Row 3: Quick Actions (Advisory, Disease Detection, Simulator, Operations, SOS) */}
          <div>
            <p className="dashboard-section-title mb-2">{t("dashboard.quickActions", "Quick Actions")}</p>
            <div className="grid grid-cols-2 gap-3">
              {/* 1. Advisory */}
              <Link
                href="/advisory"
                className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-100 bg-white shadow-sm hover:shadow-md hover:border-[#10b981]/35 transition-all duration-200 group w-full"
              >
                <div className="rounded-lg bg-emerald-50 p-1.5 text-emerald-600 shrink-0">
                  <MessageSquare className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-slate-800 leading-tight">{t("dashboard.advisoryLabel", "Advisory")}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5 leading-none truncate">{t("dashboard.advisoryDesc", "Get AI advice")}</p>
                </div>
              </Link>

              {/* 2. Disease Detection */}
              <Link
                href="/disease"
                className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-100 bg-white shadow-sm hover:shadow-md hover:border-blue-200 transition-all duration-200 group w-full"
              >
                <div className="rounded-lg bg-blue-50 p-1.5 text-blue-600 shrink-0">
                  <Microscope className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-slate-800 leading-tight">{t("dashboard.diseaseLabel", "Disease Detection")}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5 leading-none truncate">{t("dashboard.diseaseDesc", "Scan crop health")}</p>
                </div>
              </Link>

              {/* 3. Simulator */}
              <Link
                href="/simulator"
                className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-100 bg-white shadow-sm hover:shadow-md hover:border-purple-200 transition-all duration-200 group w-full"
              >
                <div className="rounded-lg bg-purple-50 p-1.5 text-purple-600 shrink-0">
                  <SlidersHorizontal className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-slate-800 leading-tight">{t("dashboard.simulatorLabel", "Simulator")}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5 leading-none truncate">{t("dashboard.simulatorDesc", "Run what-if tests")}</p>
                </div>
              </Link>

              {/* 4. Operations */}
              <Link
                href="/operations"
                className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-100 bg-white shadow-sm hover:shadow-md hover:border-amber-200 transition-all duration-200 group w-full"
              >
                <div className="rounded-lg bg-amber-50 p-1.5 text-amber-600 shrink-0">
                  <ClipboardList className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-bold text-slate-800 leading-tight">{t("dashboard.operationsLabel", "Operations")}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5 leading-none truncate">{t("dashboard.operationsDesc", "Track farm records")}</p>
                </div>
              </Link>

              {/* 5. SOS (Spans both columns) */}
              <SosButton farmId={farm.farm_id} variant="quickaction" />
            </div>
          </div>

          {/* BELOW THE FOLD - ADVANCED INTELLIGENCE */}
          <div className="border-t border-slate-100 pt-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4">{t("dashboard.advancedIntelligence", "Advanced Intelligence")}</h3>
            
            <div className="space-y-6">
              {/* Row 1: Charts & Map */}
              <div className="grid gap-4 xl:grid-cols-12">
                <div className="xl:col-span-8 space-y-4">
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.healthIntelligence", "Farmer Health Intelligence")}>
                    <FarmerHealthCard farmId={farm.farm_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.intelligenceCharts", "Intelligence Charts")}>
                    <IntelligenceCharts farmId={farm.farm_id} />
                  </ErrorBoundary>
                </div>
                <div className="xl:col-span-4 space-y-4">
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.farmHealth", "Farm Health Monitoring")}>
                    <FarmHealthWidget farmId={farm.farm_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.alerts", "Alerts & Notifications")}>
                    <AlertsPanel farmId={farm.farm_id} />
                  </ErrorBoundary>
                </div>
              </div>

              {/* Map */}
              <ErrorBoundary fallbackTitle={t("errorBoundary.title.radarMap", "Satellite & Radar Map")}>
                <RadarMap farmId={farm.farm_id} cropType={farm.crop_type ?? undefined} />
              </ErrorBoundary>

              {/* Forecast & Soil */}
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <ErrorBoundary fallbackTitle={t("stress.cropStressTitle", "Crop Stress Outlook")}>
                  <StressIndexCard farmId={farm.farm_id} />
                </ErrorBoundary>
                <ErrorBoundary fallbackTitle={t("errorBoundary.title.weatherForecast", "Weather Forecast")}>
                  <WeatherCard farmId={farm.farm_id} />
                </ErrorBoundary>
                <ErrorBoundary fallbackTitle={t("errorBoundary.title.cropStage", "Crop Stage Progress")}>
                  <CropStageProgress cycleId={farm.crop_cycle_id} />
                </ErrorBoundary>
                <ErrorBoundary fallbackTitle={t("errorBoundary.title.soilHealth", "Soil Health Intelligence")}>
                  <SoilHealthCard farmId={farm.farm_id} />
                </ErrorBoundary>
              </div>

              {/* Financials */}
              <div>
                <p className="dashboard-section-title mb-2">{t("dashboard.financialPerformance", "Financial Performance & Analytics")}</p>
                <ErrorBoundary fallbackTitle={t("errorBoundary.title.profitSummary", "Farm Profitability Summary")}>
                  <FarmProfitSummaryCard farmId={farm.farm_id} className="mb-4" />
                </ErrorBoundary>
                <div className="grid gap-4 md:grid-cols-3">
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.cycleProfit", "Crop Cycle Profitability")}>
                    <CropCycleProfitCard cycleId={farm.crop_cycle_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.cropLeaderboard", "Crop Performance Leaderboard")}>
                    <BestWorstCropWidget farmId={farm.farm_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.seasonalComparison", "Seasonal Performance Comparison")}>
                    <SeasonComparisonWidget farmId={farm.farm_id} />
                  </ErrorBoundary>
                </div>
              </div>

              {/* Recommendations & Market */}
              <div>
                <p className="dashboard-section-title mb-2">{t("dashboard.operationsAndMarket", "Operations & Market")}</p>
                <div className="grid gap-4 md:grid-cols-3">
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.inputRecommendations", "Input Recommendations")}>
                    <InputWindowCard farmId={farm.farm_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.marketPrices", "Market Prices")}>
                    <MarketPriceCard farmId={farm.farm_id} />
                  </ErrorBoundary>
                  <ErrorBoundary fallbackTitle={t("errorBoundary.title.govSchemes", "Government Schemes")}>
                    <SchemesCard farmId={farm.farm_id} />
                  </ErrorBoundary>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-emerald-200 bg-white py-16 text-center p-6">
          <Image src={BRAND.icon} alt="HarvestIQ" width={64} height={64} className="mb-3 rounded-full" />
          <p className="font-semibold text-slate-800">{t("dashboard.noFarmProfile", "No farm profile loaded")}</p>
          <p className="mt-1 text-sm text-slate-500 max-w-sm">{t("dashboard.noFarmProfileDesc", "Complete onboarding or set up your farm database to view your dashboard.")}</p>
          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <Button onClick={() => router.push("/onboarding")} className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl px-6 py-2">
              {t("dashboard.onboardingForm", "Onboarding Form")}
            </Button>
            <Button onClick={() => router.push("/farm-setup")} variant="outline" className="border-emerald-200 text-emerald-800 rounded-xl px-6 py-2">
              {t("dashboard.farmDbWizard", "Farm DB Wizard")}
            </Button>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function HomePage() {
  return (
    <AuthGuard requireOnboarding>
      <DashboardContent />
    </AuthGuard>
  );
}
