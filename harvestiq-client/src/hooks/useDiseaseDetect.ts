"use client";

import { useMutation } from "@tanstack/react-query";

import { api, type DiseaseDetectResult } from "@/lib/api";

export function useDiseaseDetect() {
  return useMutation({
    mutationFn: ({ farmId, image }: { farmId: string; image: File }) =>
      api.detectDisease(farmId, image),
  });
}

export type { DiseaseDetectResult };
