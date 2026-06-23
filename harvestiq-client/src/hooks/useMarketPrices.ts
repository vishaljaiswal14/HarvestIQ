"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type MarketPricesData } from "@/lib/api";

export function useMarketPrices(farmId?: string | null) {
  const result = useQuery({
    queryKey: ["market-prices", farmId],
    queryFn: () => api.getMarketPrices(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 30 * 60 * 1000,
  });
  return result;
}

export type { MarketPricesData };
