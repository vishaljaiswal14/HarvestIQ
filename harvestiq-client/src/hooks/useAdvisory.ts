"use client";

import { useMutation } from "@tanstack/react-query";

import { api, type AdvisoryResult } from "@/lib/api";

export function useAdvisory() {
  return useMutation({
    mutationFn: (payload: { farm_id: string; query: string; language?: string }) =>
      api.askAdvisory(payload),
  });
}

export type { AdvisoryResult };
