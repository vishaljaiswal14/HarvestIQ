"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type StressIndexData } from "@/lib/api";

export function useStressIndex(farmId?: string | null) {
  return useQuery({
    queryKey: ["stress-index", farmId],
    queryFn: () => api.getStressIndex(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 5 * 60 * 1000,
  });
}

export type { StressIndexData };
