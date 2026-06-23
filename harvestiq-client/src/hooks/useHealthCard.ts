"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type HealthCardData } from "@/lib/api";

export function useHealthCard(farmId?: string | null) {
  const result = useQuery({
    queryKey: ["health-card", farmId],
    queryFn: () => api.getHealthCard(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 5 * 60 * 1000,
  });
  return result;
}

export type { HealthCardData };
