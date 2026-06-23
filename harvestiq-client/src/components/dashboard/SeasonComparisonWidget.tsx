"use client";

import React from "react";
import { 
  Calendar, 
  IndianRupee, 
  TrendingUp, 
  TrendingDown, 
  ArrowUpRight,
  TrendingUpIcon
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSeasonComparison } from "@/hooks/useProfitability";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

export interface SeasonProfitability {
  season: string;
  profit: number;
  roi: number;
}

export interface SeasonComparisonWidgetProps {
  farmId?: string | null;
  data?: SeasonProfitability[];
  className?: string;
}

export function SeasonComparisonWidget({ farmId, data: preloadedData, className }: SeasonComparisonWidgetProps) {
  const { t } = useTranslation();
  const { data: fetchedData, isLoading, error } = useSeasonComparison(preloadedData ? null : farmId);
  const data = preloadedData || fetchedData;

  if (isLoading) {
    return (
      <Card className={cn("dashboard-card animate-pulse", className)}>
        <CardHeader>
          <div className="h-5 w-1/3 rounded bg-slate-100" />
          <div className="h-4 w-1/2 rounded bg-slate-100 mt-2" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 rounded bg-slate-100" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.length === 0) {
    if (!farmId && !preloadedData) return null;
    return (
      <Card className={cn("dashboard-card border-slate-100", className)}>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">{t("financial.seasonalComparison", "Seasonal Comparison")}</CardTitle>
          <CardDescription>{t("financial.seasonalComparisonSubtitle", "Performance comparison across seasons")}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-500 py-4 text-center">
          {t("financial.noComparisonData", "No historical crop cycle finances available for comparison.")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("dashboard-card overflow-hidden border border-slate-100 bg-white/90 backdrop-blur-md shadow-sm hover:shadow-md transition-all duration-300", className)}>
      <CardHeader className="pb-3">
        <p className="dashboard-section-title mb-1 flex items-center gap-1.5 text-slate-500 uppercase tracking-wider text-xs font-semibold">
          <Calendar className="h-3.5 w-3.5 text-indigo-500" />
          {t("financial.seasonalAnalysis", "Seasonal Analysis")}
        </p>
        <CardTitle className="text-base font-bold text-slate-800">{t("financial.seasonalPerformance", "Seasonal Performance")}</CardTitle>
        <CardDescription>{t("financial.seasonalPerformanceSubtitle", "Financial growth comparison across Rabi and Kharif crop cycles")}</CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        <div className="divide-y divide-slate-100">
          {data.map((seasonData, index) => {
            const isProfitable = seasonData.profit >= 0;
            
            // Clean up the season display label (e.g. "KHARIF_2024" to "Kharif 2024")
            const parts = seasonData.season.split("_");
            const seasonKey = parts[0]?.toLowerCase();
            const year = parts[1] ? ` ${parts[1]}` : "";
            const formattedSeason = t(`season.${seasonKey}`, parts[0]) + year;

            return (
              <div 
                key={seasonData.season}
                className={cn(
                  "flex items-center justify-between p-4 transition-colors hover:bg-slate-50/40",
                  index === 0 && "pt-2"
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "rounded-xl p-2.5 border",
                    isProfitable 
                      ? "bg-emerald-50 text-emerald-600 border-emerald-100/60" 
                      : "bg-rose-50 text-rose-600 border-rose-100/60"
                  )}>
                    <Calendar className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-800">{formattedSeason}</h4>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      {t("financial.seasonCycle", "Season Cycle")}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  {/* Profit Amount */}
                  <div className="text-right">
                    <p className={cn(
                      "text-sm font-bold flex items-center justify-end",
                      isProfitable ? "text-emerald-600" : "text-rose-600"
                    )}>
                      {isProfitable ? "+" : ""}
                      <IndianRupee className="h-3 w-3 stroke-[2.5] mt-0.5" />
                      {seasonData.profit.toLocaleString("en-IN")}
                    </p>
                    <span className="text-[10px] text-slate-400 font-semibold block">{t("financial.netReturn", "Net Return")}</span>
                  </div>

                  {/* ROI Badge */}
                  <div className={cn(
                    "px-2.5 py-1 rounded-full text-xs font-bold border min-w-[70px] text-center",
                    isProfitable 
                      ? "bg-emerald-50/60 border-emerald-100/80 text-emerald-700" 
                      : "bg-rose-50/60 border-rose-100/80 text-rose-700"
                  )}>
                    {isProfitable ? "+" : ""}
                    {seasonData.roi.toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
