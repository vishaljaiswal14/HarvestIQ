"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useCopilotPlan(farmId?: string | null) {
  return useQuery({
    queryKey: ["copilot-plan", farmId],
    queryFn: () => api.getCopilotPlan(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 60 * 1000,
  });
}

export function useYieldProtection(farmId?: string | null) {
  return useQuery({
    queryKey: ["yield-protection", farmId],
    queryFn: () => api.getYieldProtectionScore(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 60 * 1000,
  });
}
