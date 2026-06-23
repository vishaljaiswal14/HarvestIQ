"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type SoilRecordData } from "@/lib/api";

export function useSoilLatest(farmId?: string | null) {
  return useQuery({
    queryKey: ["soil-latest", farmId],
    queryFn: () => api.getLatestSoilRecord(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useSubmitSoilRecord(farmId?: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: Omit<SoilRecordData, "id" | "crop_type" | "deficiency_status" | "soil_health_index" | "explanation" | "recorded_at">) =>
      api.createSoilRecord(payload as any),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["soil-latest", farmId] });
    },
  });
}

export type { SoilRecordData };
