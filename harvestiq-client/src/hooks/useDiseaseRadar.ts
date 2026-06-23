"use client";

import { useQuery } from "@tanstack/react-query";

import { api, type DiseaseRadarData } from "@/lib/api";

export function useDiseaseRadar(
  farmId?: string,
  cropType?: string,
  radiusKm?: number,
) {
  return useQuery<DiseaseRadarData, Error>({
    queryKey: ["disease-radar", farmId, cropType, radiusKm],
    queryFn: async () => {
      if (typeof window !== "undefined" && !navigator.onLine) {
        return { hotspots: [], queried_at: new Date().toISOString(), radius_km: 0 };
      }
      try {
        return await api.getDiseaseRadarNearby({
          farm_id: farmId!,
          crop_type: cropType,
          radius_km: radiusKm,
        });
      } catch (err) {
        console.warn("[useDiseaseRadar] Fetch failed, returning empty fallback:", err);
        return { hotspots: [], queried_at: new Date().toISOString(), radius_km: 0 };
      }
    },
    enabled: Boolean(farmId) && (typeof window !== "undefined" && navigator.onLine),
    staleTime: 5 * 60 * 1000,
  });
}

export type { DiseaseRadarData };
