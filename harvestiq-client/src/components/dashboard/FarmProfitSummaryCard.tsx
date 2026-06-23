"use client";

import React from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  IndianRupee, 
  TrendingUpIcon, 
  Wallet, 
  PieChart 
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

export interface FarmProfitSummaryCardProps {
  farmId?: string | null;
  data?: FarmProfitabilitySummaryData;
  className?: string;
}

export function FarmProfitSummaryCard({ farmId, data: preloadedData, className }: FarmProfitSummaryCardProps) {
  const { t } = useTranslation();
  const { data: fetchedData, isLoading, error } = useFarmProfitabilitySummary(preloadedData ? null : farmId);
  const data = preloadedData || (fetchedData as FarmProfitabilitySummaryData);

  if (isLoading) {
    return (
      <div className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}>
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="animate-pulse dashboard-card">
            <CardContent className="h-24" />
          </Card>
        ))}
      </div>
    );
  }

  if (error || !data) {
    if (!farmId && !preloadedData) return null;
    return (
      <Card className={cn("dashboard-card border-rose-100 bg-rose-50/20", className)}>
        <CardHeader>
          <CardTitle className="text-rose-800 text-base flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-rose-500" />
            {t("financial.summaryUnavailable", "Farm Financials Unavailable")}
          </CardTitle>
          <CardDescription>
            {t("financial.cannotRetrieveSummary", "Could not retrieve aggregated financial analytics for this farm.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const isProfitable = data.total_profit >= 0;

  return (
    <div className={cn("space-y-4", className)}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Cost Card */}
        <Card className="dashboard-card border border-slate-100 bg-white/95 backdrop-blur shadow-sm hover:shadow-md transition-all duration-300">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                {t("financial.totalExpenses", "Total Expenses")}
              </span>
              <p className="text-2xl font-black text-slate-800 tracking-tight flex items-center">
                <IndianRupee className="h-5 w-5 text-slate-500 stroke-[2.5]" />
                {data.total_cost.toLocaleString("en-IN")}
              </p>
              <span className="text-xs text-slate-400 font-medium">{t("financial.allHistoricalCycles", "All historical cycles")}</span>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-slate-500 border border-slate-100">
              <Wallet className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        {/* Total Revenue Card */}
        <Card className="dashboard-card border border-slate-100 bg-white/95 backdrop-blur shadow-sm hover:shadow-md transition-all duration-300">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                {t("financial.totalRevenue", "Total Revenue")}
              </span>
              <p className="text-2xl font-black text-slate-800 tracking-tight flex items-center">
                <IndianRupee className="h-5 w-5 text-slate-500 stroke-[2.5]" />
                {data.total_revenue.toLocaleString("en-IN")}
              </p>
              <span className="text-xs text-slate-400 font-medium">{t("financial.salesYieldRevenue", "Sales & yield revenue")}</span>
            </div>
            <div className="bg-sky-50 rounded-xl p-3 text-sky-600 border border-sky-100">
              <TrendingUpIcon className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>

        {/* Total Profit Card */}
        <Card className={cn(
          "dashboard-card border shadow-sm hover:shadow-md transition-all duration-300",
          isProfitable ? "border-emerald-100 bg-emerald-50/10" : "border-rose-100 bg-rose-50/10"
        )}>
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                {t("financial.netProfit", "Net Profit")}
              </span>
              <p className={cn(
                "text-2xl font-black tracking-tight flex items-center",
                isProfitable ? "text-emerald-700" : "text-rose-700"
              )}>
                <IndianRupee className="h-5 w-5 stroke-[2.5]" />
                {data.total_profit.toLocaleString("en-IN")}
              </p>
              <span className={cn(
                "text-xs font-semibold",
                isProfitable ? "text-emerald-600" : "text-rose-600"
              )}>
                {isProfitable ? t("financial.netSurplus", "Net Surplus") : t("financial.netLoss", "Net Loss")}
              </span>
            </div>
            <div className={cn(
              "rounded-xl p-3 border",
              isProfitable 
                ? "bg-emerald-50 text-emerald-600 border-emerald-100" 
                : "bg-rose-50 text-rose-600 border-rose-100"
            )}>
              {isProfitable ? (
                <TrendingUp className="h-6 w-6" />
              ) : (
                <TrendingDown className="h-6 w-6" />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Aggregate ROI Card */}
        <Card className="dashboard-card border border-slate-100 bg-white/95 backdrop-blur shadow-sm hover:shadow-md transition-all duration-300">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                {t("financial.farmRoi", "Farm ROI")}
              </span>
              <p className={cn(
                "text-2xl font-black tracking-tight",
                isProfitable ? "text-emerald-700" : "text-rose-700"
              )}>
                {data.roi_percent.toFixed(1)}%
              </p>
              <span className="text-xs text-slate-400 font-medium">{t("financial.returnOnExpenditure", "Return on expenditure")}</span>
            </div>
            <div className="bg-indigo-50 rounded-xl p-3 text-indigo-600 border border-indigo-100">
              <PieChart className="h-6 w-6" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
