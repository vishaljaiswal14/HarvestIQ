"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SoilHealthForm } from "@/components/SoilHealthForm";
import { useSoilLatest } from "@/hooks/useSoilHealth";
import { useTranslation } from "@/stores/localizationStore";
import { EmptyState } from "@/components/ui/EmptyState";
import { Droplets } from "lucide-react";

type SoilHealthCardProps = {
  farmId?: string | null;
};

export function SoilHealthCard({ farmId }: SoilHealthCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error, refetch } = useSoilLatest(farmId);
  const [showForm, setShowForm] = useState(false);

  if (!farmId) {
    return null;
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("errorBoundary.title.soilHealth", "Soil Health Intelligence")}</CardTitle>
          <CardDescription>{t("soil.loading", "Loading latest soil record...")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const hasRecord = !!data && !error && (data as any).available !== false && (data as any).id !== undefined;

  return (
    <Card className="dashboard-card">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <p className="dashboard-section-title mb-1">{t("soil.analytics", "Soil Analytics")}</p>
          <CardTitle className="text-base font-bold text-slate-800">{t("errorBoundary.title.soilHealth", "Soil Health Intelligence")}</CardTitle>
          <CardDescription>{t("soil.chemistryAssessment", "N-P-K and soil chemistry assessment")}</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={() => setShowForm((value) => !value)}>
          {showForm ? t("soil.closeForm", "Close form") : hasRecord ? t("soil.addSample", "Add sample") : t("soil.recordSample", "Record sample")}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {showForm && (
          <SoilHealthForm
            farmId={farmId}
            onSuccess={() => {
              setShowForm(false);
              void refetch();
            }}
          />
        )}

        {!hasRecord && !showForm && (
          <EmptyState
            message={t("soil.emptyMsg", "No soil health samples recorded for this farm yet. Start by logging your first sample.")}
            title={t("soil.emptyTitle", "No Soil Data")}
            icon={Droplets}
            action={{
              label: t("soil.recordSample", "Record sample"),
              onClick: () => setShowForm(true),
            }}
          />
        )}

        {hasRecord && data && (
          <div className="space-y-3">
            <div className="flex items-end gap-2">
              <span className="text-3xl font-bold text-emerald-900">
                {(data.soil_health_index ?? 0).toFixed(2)}
              </span>
              <span className="pb-1 text-sm text-emerald-700">{t("soil.healthIndex", "soil health index")}</span>
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <NutrientChip label="N" status={data.deficiency_status?.nitrogen ?? "OPTIMAL"} />
              <NutrientChip label="P" status={data.deficiency_status?.phosphorus ?? "OPTIMAL"} />
              <NutrientChip label="K" status={data.deficiency_status?.potassium ?? "OPTIMAL"} />
              <NutrientChip label="pH" status={data.deficiency_status?.ph ?? "OPTIMAL"} />
              <NutrientChip label="OC" status={data.deficiency_status?.organic_carbon ?? "OPTIMAL"} />
              <NutrientChip label="EC" status={data.deficiency_status?.electrical_conductivity ?? "OPTIMAL"} />
            </div>
            <p className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3 text-sm text-emerald-800">
              {data.explanation?.summary}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function NutrientChip({ label, status }: { label: string; status: string }) {
  const { t } = useTranslation();
  const styles =
    status === "LOW"
      ? "bg-red-100 text-red-800"
      : status === "HIGH"
        ? "bg-amber-100 text-amber-800"
        : "bg-emerald-100 text-emerald-800";

  return (
    <div className={`rounded-md px-2 py-1 text-xs font-medium ${styles}`}>
      {label}: {t("soil.status." + status.toLowerCase(), status)}
    </div>
  );
}
