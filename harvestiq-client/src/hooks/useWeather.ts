"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type WeatherForecast } from "@/lib/api";

export function useWeather(farmId?: string | null) {
  const result = useQuery({
    queryKey: ["weather", farmId],
    queryFn: () => api.getWeatherForecast(farmId as string),
    enabled: Boolean(farmId),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
  return result;
}

export type { WeatherForecast };
