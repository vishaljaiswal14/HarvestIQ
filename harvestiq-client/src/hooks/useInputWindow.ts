"use client";

import { useMutation } from "@tanstack/react-query";

import { api, type InputWindowData } from "@/lib/api";

export function useInputWindow(farmId?: string | null) {
  return useMutation({
    mutationFn: (actionType: string) =>
      api.evaluateInputWindow({
        farm_id: farmId as string,
        action_type: actionType,
      }),
    mutationKey: ["input-window", farmId],
  });
}

export type { InputWindowData };
