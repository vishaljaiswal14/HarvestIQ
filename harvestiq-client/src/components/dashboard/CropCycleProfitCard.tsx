"use client";

import React, { useState } from "react";
import { 
  Sprout, 
  IndianRupee, 
  TrendingUp, 
  TrendingDown, 
  Percent, 
  ChevronDown, 
  ChevronUp, 
  Scale, 
  Tag 
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useCropCycleProfitability } from "@/hooks/useProfitability";
import { useTranslation } from "@/stores/localizationStore";
import { cn } from "@/lib/utils";

export interface CropCycleProfitabilityData {
  crop_cycle_id: string;
  crop_type: string;
  season: string;
  metrics: {
    total_cost: number;
    total_revenue: number;
    net_profit: number;
    roi_percent: number;
    cost_per_unit: number;
    revenue_per_unit: number;
    break_even_yield: number;
    break_even_price: number;
  };
}

export interface CropCycleProfitCardProps {
  cycleId?: string | null;
  data?: CropCycleProfitabilityData;
  className?: string;
}

export function CropCycleProfitCard({ cycleId, data: preloadedData, className }: CropCycleProfitCardProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);

  const { data: fetchedData, isLoading, error } = useCropCycleProfitability(preloadedData ? null : cycleId);
  const data = preloadedData || (fetchedData as CropCycleProfitabilityData);

  if (isLoading) {
    return (
      <Card className={cn("dashboard-card animate-pulse", className)}>
        <CardHeader>
          <div className="h-5 w-1/3 rounded bg-slate-100" />
          <div className="h-4 w-1/2 rounded bg-slate-100 mt-2" />
        </CardHeader>
        <CardContent>
          <div className="h-24 rounded bg-slate-100" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    if (!cycleId && !preloadedData) return null;
    return (
      <Card className={cn("dashboard-card border-red-100 bg-red-50/20", className)}>
        <CardHeader>
          <CardTitle className="text-red-800 text-base flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-500" />
            {t("financial.unavailable", "Financial Analysis Unavailable")}
          </CardTitle>
          <CardDescription>
            {t("financial.cannotCompute", "Could not compute profitability for this crop cycle.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const { metrics } = data;
  const isProfitable = metrics.net_profit >= 0;

  return (
    <Card className={cn("dashboard-card overflow-hidden transition-all duration-300 hover:shadow-md border border-slate-100/80 bg-white/90 backdrop-blur-md", className)}>
      {/* Decorative top border colored by profitability */}
      <div className={cn("h-1.5 w-full", isProfitable ? "bg-emerald-500" : "bg-rose-500")} />
      
      <CardHeader className="pb-3 flex flex-row items-start justify-between gap-4">
        <div>
          <p className="dashboard-section-title mb-1 flex items-center gap-1.5 text-slate-500 uppercase tracking-wider text-xs font-semibold">
            <Sprout className="h-3.5 w-3.5 text-emerald-600" />
            {t("financial.cropPerformance", "Crop Performance")}
          </p>
          <CardTitle className="text-base font-bold text-slate-800 flex items-center gap-2">
            {t("crop." + data.crop_type.toLowerCase(), data.crop_type)}
            <span className="text-xs font-normal text-slate-400 border border-slate-100 px-2 py-0.5 rounded-full bg-slate-50/50">
              {t("season." + data.season.toLowerCase(), data.season)}
            </span>
          </CardTitle>
          <CardDescription>{t("financial.analysisSummary", "Cycle Financial Analysis Summary")}</CardDescription>
        </div>

        <div className={cn(
          "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold shadow-sm border",
          isProfitable 
            ? "bg-emerald-50 border-emerald-100 text-emerald-800" 
            : "bg-rose-50 border-rose-100 text-rose-800"
        )}>
          {isProfitable ? (
            <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5 text-rose-600" />
          )}
          ROI: {metrics.roi_percent.toFixed(1)}%
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Main Financial KPI Grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              {t("financial.totalRevenue", "Total Revenue")}
            </span>
            <span className="text-base font-bold text-slate-900 flex items-center">
              <IndianRupee className="h-3.5 w-3.5 text-slate-500 stroke-[2.5]" />
              {metrics.total_revenue.toLocaleString("en-IN")}
            </span>
          </div>

          <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              {t("financial.totalCost", "Total Cost")}
            </span>
            <span className="text-base font-bold text-slate-900 flex items-center">
              <IndianRupee className="h-3.5 w-3.5 text-slate-500 stroke-[2.5]" />
              {metrics.total_cost.toLocaleString("en-IN")}
            </span>
          </div>

          <div className={cn(
            "rounded-xl border p-3",
            isProfitable 
              ? "bg-emerald-50/30 border-emerald-100/50" 
              : "bg-rose-50/30 border-rose-100/50"
          )}>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-1">
              {t("financial.netProfit", "Net Profit")}
            </span>
            <span className={cn(
              "text-base font-bold flex items-center",
              isProfitable ? "text-emerald-700" : "text-rose-700"
            )}>
              <IndianRupee className="h-3.5 w-3.5 stroke-[2.5]" />
              {metrics.net_profit.toLocaleString("en-IN")}
            </span>
          </div>
        </div>

        {/* Expandable detailed parameters */}
        <div className="border-t border-slate-100 pt-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex w-full items-center justify-between py-1 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
          >
            <span>{isExpanded ? t("financial.hideDetails", "Hide detailed diagnostics") : t("financial.showDetails", "Show break-even & unit diagnostics")}</span>
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </button>

          {isExpanded && (
            <div className="mt-3 grid grid-cols-2 gap-3 animate-fadeIn">
              <div className="rounded-lg border border-slate-100 p-3 space-y-1 bg-white">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Scale className="h-3.5 w-3.5 text-sky-500" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">{t("financial.breakEvenYield", "Break-Even Yield")}</span>
                </div>
                <p className="text-sm font-bold text-slate-800">
                  {metrics.break_even_yield > 0 
                    ? `${metrics.break_even_yield.toFixed(2)} ${t("financial.units", "units")}` 
                    : "—"}
                </p>
                <p className="text-[9px] text-slate-400 font-medium">{t("financial.yieldRequiredDesc", "Yield required to cover total costs")}</p>
              </div>

              <div className="rounded-lg border border-slate-100 p-3 space-y-1 bg-white">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Tag className="h-3.5 w-3.5 text-indigo-500" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">{t("financial.breakEvenPrice", "Break-Even Price")}</span>
                </div>
                <p className="text-sm font-bold text-slate-800 flex items-center">
                  {metrics.break_even_price > 0 ? (
                    <>
                      <IndianRupee className="h-3 w-3 stroke-[2]" />
                      {metrics.break_even_price.toFixed(2)} {t("financial.perUnit", "/ unit")}
                    </>
                  ) : "—"}
                </p>
                <p className="text-[9px] text-slate-400 font-medium">{t("financial.priceRequiredDesc", "Selling price required to cover costs")}</p>
              </div>

              <div className="rounded-lg border border-slate-100 p-3 space-y-1 bg-white">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Percent className="h-3.5 w-3.5 text-amber-500" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">{t("financial.costPerUnit", "Cost / Unit")}</span>
                </div>
                <p className="text-sm font-bold text-slate-800 flex items-center">
                  <IndianRupee className="h-3 w-3 stroke-[2]" />
                  {metrics.cost_per_unit.toFixed(2)} {t("financial.perUnit", "/ unit")}
                </p>
              </div>

              <div className="rounded-lg border border-slate-100 p-3 space-y-1 bg-white">
                <div className="flex items-center gap-1.5 text-slate-500">
                  <Percent className="h-3.5 w-3.5 text-teal-500" />
                  <span className="text-[10px] font-semibold uppercase tracking-wider">{t("financial.revenuePerUnit", "Revenue / Unit")}</span>
                </div>
                <p className="text-sm font-bold text-slate-800 flex items-center">
                  <IndianRupee className="h-3 w-3 stroke-[2]" />
                  {metrics.revenue_per_unit.toFixed(2)} {t("financial.perUnit", "/ unit")}
                </p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
