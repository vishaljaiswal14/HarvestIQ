"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type SchemesData } from "@/lib/api";

export function useSchemes(farmId?: string | null) {
  return useQuery({
    queryKey: ["schemes", farmId],
    queryFn: () => api.getEligibleSchemes(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 60 * 60 * 1000,
  });
}

export type { SchemesData };
