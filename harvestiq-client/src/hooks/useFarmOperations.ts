"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useExpenses(cycleId?: string | null) {
  return useQuery({
    queryKey: ["expenses", cycleId],
    queryFn: () => api.listExpenses(cycleId as string),
    enabled: Boolean(cycleId),
  });
}

export function useHarvests(cycleId?: string | null) {
  return useQuery({
    queryKey: ["harvests", cycleId],
    queryFn: () => api.listHarvests(cycleId as string),
    enabled: Boolean(cycleId),
  });
}

export function useCreateExpense(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { crop_cycle_id: string; category: string; amount: number; notes?: string; expense_date: string }) =>
      api.createExpense(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["expenses", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}

export function useUpdateExpense(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { crop_cycle_id: string; category: string; amount: number; notes?: string; expense_date: string } }) =>
      api.updateExpense(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["expenses", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}

export function useDeleteExpense(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteExpense(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["expenses", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}

export function useCreateHarvest(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { crop_cycle_id: string; yield_quantity: number; yield_unit: string; revenue: number; harvest_date: string }) =>
      api.createHarvest(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["harvests", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}

export function useUpdateHarvest(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { crop_cycle_id: string; yield_quantity: number; yield_unit: string; revenue: number; harvest_date: string } }) =>
      api.updateHarvest(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["harvests", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}

export function useDeleteHarvest(cycleId?: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteHarvest(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["harvests", cycleId] });
      void queryClient.invalidateQueries({ queryKey: ["profitability"] });
    },
  });
}
