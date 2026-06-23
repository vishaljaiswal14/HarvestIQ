"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type BriefingData } from "@/lib/api";

export function useBriefing(farmId?: string | null, language?: string) {
  const result = useQuery({
    queryKey: ["briefing", farmId, language],
    queryFn: () => api.getDailyBriefing(farmId as string, language),
    enabled: Boolean(farmId),
    staleTime: 30 * 60 * 1000,
  });
  return result;
}

export type { BriefingData };
