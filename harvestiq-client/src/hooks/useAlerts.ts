"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type AlertListData } from "@/lib/api";

export function useAlerts(farmId?: string | null) {
  return useQuery({
    queryKey: ["alerts", farmId],
    queryFn: () => api.getAlerts(farmId ? { farm_id: farmId } : undefined),
    staleTime: 60 * 1000,
  });
}

export function useTriggerAlerts(farmId?: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.triggerAlertEvaluation(farmId as string),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["alerts", farmId] });
    },
  });
}

export function useAcknowledgeAlert(farmId?: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: string) => api.acknowledgeAlert(alertId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["alerts", farmId] });
    },
  });
}

export type { AlertListData };
