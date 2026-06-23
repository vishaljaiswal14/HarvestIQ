"use client";

import { useMutation } from "@tanstack/react-query";

import { api, type SimulatorResult } from "@/lib/api";

export type SimulatorParams = {
  temp_delta: number;
  irrigation_delta: number;
  nitrogen_delta: number;
};

export function useSimulator(farmId?: string | null) {
  return useMutation({
    mutationFn: (params: SimulatorParams) =>
      api.runSimulator({
        farm_id: farmId as string,
        ...params,
      }),
    mutationKey: ["simulator", farmId],
  });
}

export type { SimulatorResult };
