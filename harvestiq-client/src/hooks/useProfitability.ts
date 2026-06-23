"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useCropCycleProfitability(cycleId?: string | null) {
  return useQuery({
    queryKey: ["profitability", "cycle", cycleId],
    queryFn: () => api.getCropCycleProfitability(cycleId as string),
    enabled: Boolean(cycleId),
  });
}

export function usePlotProfitability(plotId?: string | null) {
  return useQuery({
    queryKey: ["profitability", "plot", plotId],
    queryFn: () => api.getPlotProfitability(plotId as string),
    enabled: Boolean(plotId),
  });
}

export function useFarmProfitabilitySummary(farmId?: string | null) {
  return useQuery({
    queryKey: ["profitability", "farm", farmId],
    queryFn: () => api.getFarmProfitabilitySummary(farmId as string),
    enabled: Boolean(farmId),
  });
}

export function useSeasonComparison(farmId?: string | null) {
  return useQuery({
    queryKey: ["profitability", "season-comparison", farmId],
    queryFn: () => api.getSeasonComparison(farmId as string),
    enabled: Boolean(farmId),
  });
}
