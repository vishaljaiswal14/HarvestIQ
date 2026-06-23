"use client";

import { MapPin } from "lucide-react";
import { useCropStage } from "@/hooks/useCropStage";
import { useHealthCard } from "@/hooks/useHealthCard";
import { CropBadge, CropIcon } from "@/lib/agri-identity";
import type { FarmProfile } from "@/lib/api";

type DashboardHeroProps = {
  farm: FarmProfile;
};

export function DashboardHero({ farm }: DashboardHeroProps) {
  const { data: health } = useHealthCard(farm.farm_id);
  const { data: stage } = useCropStage(farm.crop_cycle_id ?? null);

  const stageLabel = health?.stage ?? stage?.stage ?? "—";

  return (
    <section className="relative overflow-hidden rounded-xl border border-slate-150 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <CropIcon cropType={farm.crop_type} size="md" className="border border-slate-100" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
                {farm.farm_name}
              </h2>
              <CropBadge cropType={farm.crop_type} />
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-700 border border-emerald-100/50">
                {stageLabel}
              </span>
            </div>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2.5 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-slate-400" />
                {farm.district}, {farm.state}
              </span>
              <span className="text-slate-355 select-none text-slate-300">•</span>
              {farm.soil_type && (
                <span>
                  Soil: <strong className="font-semibold text-slate-600">{farm.soil_type}</strong>
                </span>
              )}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
