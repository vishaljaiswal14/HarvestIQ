"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type CropStageData } from "@/lib/api";

export function useCropStage(cycleId?: string | null) {
  return useQuery({
    queryKey: ["crop-stage", cycleId],
    queryFn: () => api.getCropStage(cycleId as string),
    enabled: Boolean(cycleId),
    staleTime: 5 * 60 * 1000,
  });
}

export type { CropStageData };
