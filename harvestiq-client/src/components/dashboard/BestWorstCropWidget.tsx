"use client";

import React from "react";
import { 
  Trophy, 
  AlertOctagon, 
  TrendingUp, 
  TrendingDown,
  ArrowRight,
  Sprout
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useFarmProfitabilitySummary } from "@/hooks/useProfitability";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

export interface FarmProfitabilitySummaryData {
  total_cost: number;
  total_revenue: number;
  total_profit: number;
  best_performing_crop: string;
  worst_performing_crop: string;
  roi_percent: number;
}

export interface BestWorstCropWidgetProps {
  farmId?: string | null;
  data?: FarmProfitabilitySummaryData;
  className?: string;
}

export function BestWorstCropWidget({ farmId, data: preloadedData, className }: BestWorstCropWidgetProps) {
  const { t } = useTranslation();
  const { data: fetchedData, isLoading, error } = useFarmProfitabilitySummary(preloadedData ? null : farmId);
  const data = preloadedData || (fetchedData as FarmProfitabilitySummaryData);

  if (isLoading) {
    return (
      <Card className={cn("dashboard-card animate-pulse", className)}>
        <CardHeader>
          <div className="h-5 w-1/3 rounded bg-slate-100" />
          <div className="h-4 w-1/2 rounded bg-slate-100 mt-2" />
        </CardHeader>
        <CardContent className="h-28 rounded bg-slate-100" />
      </Card>
    );
  }

  if (error || !data) {
    if (!farmId && !preloadedData) return null;
    return (
      <Card className={cn("dashboard-card border-slate-100", className)}>
        <CardContent className="p-6 text-center text-slate-400">
          {t("financial.leaderboardUnavailable", "Crop leaderboard unavailable. Record harvest transactions to identify crop performances.")}
        </CardContent>
      </Card>
    );
  }

  const { best_performing_crop, worst_performing_crop } = data;

  if (!best_performing_crop && !worst_performing_crop) {
    return (
      <Card className={cn("dashboard-card border-slate-100", className)}>
        <CardHeader>
          <CardTitle className="text-base text-slate-700">{t("financial.cropInsights", "Crop Insights")}</CardTitle>
          <CardDescription>{t("financial.leaderboardSubtitle", "Leaderboard for seasonal crop profitability")}</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-500 py-2">
          {t("financial.noFinancialRecords", "No crop cycle financial records available. Add expenses and harvests to populate analytics.")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("dashboard-card overflow-hidden border border-slate-100 bg-white/90 backdrop-blur-md shadow-sm hover:shadow-md transition-all duration-300", className)}>
      <CardHeader className="pb-3">
        <p className="dashboard-section-title mb-1 flex items-center gap-1.5 text-slate-500 uppercase tracking-wider text-xs font-semibold">
          <Trophy className="h-3.5 w-3.5 text-amber-500" />
          {t("financial.cropLeaderboard", "Crop Leaderboard")}
        </p>
        <CardTitle className="text-base font-bold text-slate-800">{t("financial.performanceInsights", "Performance Insights")}</CardTitle>
        <CardDescription>{t("financial.highestLowestYielding", "Highest and lowest yielding crop cycles based on net profit")}</CardDescription>
      </CardHeader>

      <CardContent className="grid gap-4 sm:grid-cols-2">
        {/* Best Performing Crop */}
        {best_performing_crop ? (
          <div className="relative overflow-hidden rounded-xl border border-emerald-100 bg-emerald-50/20 p-4">
            <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-emerald-500/10" />
            <div className="flex items-start gap-3 relative">
              <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700 border border-emerald-200">
                <Trophy className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800/80 block">
                  {t("financial.bestPerformingCrop", "Best Performing Crop")}
                </span>
                <p className="text-xl font-extrabold text-slate-800">{t("crop." + best_performing_crop.toLowerCase(), best_performing_crop)}</p>
                <p className="text-xs font-medium text-emerald-700 flex items-center gap-1">
                  <TrendingUp className="h-3.5 w-3.5" /> {t("financial.maxNetProfit", "Max Net Profit")}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 p-4 flex items-center justify-center text-slate-400 text-xs font-medium">
            {t("financial.noCropData", "No crop data available")}
          </div>
        )}

        {/* Worst Performing Crop */}
        {worst_performing_crop ? (
          <div className="relative overflow-hidden rounded-xl border border-rose-100 bg-rose-50/20 p-4">
            <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-rose-500/10" />
            <div className="flex items-start gap-3 relative">
              <div className="rounded-lg bg-rose-100 p-2 text-rose-700 border border-rose-200">
                <AlertOctagon className="h-5 w-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800/80 block">
                  {t("financial.lowestPerformingCrop", "Lowest Performing Crop")}
                </span>
                <p className="text-xl font-extrabold text-slate-800">{t("crop." + worst_performing_crop.toLowerCase(), worst_performing_crop)}</p>
                <p className="text-xs font-medium text-rose-700 flex items-center gap-1">
                  <TrendingDown className="h-3.5 w-3.5" /> {t("financial.minNetProfit", "Min Net Profit / High Costs")}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 p-4 flex items-center justify-center text-slate-400 text-xs font-medium">
            {t("financial.noCropData", "No crop data available")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
