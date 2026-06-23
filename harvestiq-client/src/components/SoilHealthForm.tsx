"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useSubmitSoilRecord } from "@/hooks/useSoilHealth";
import { useTranslation } from "@/stores/localizationStore";

type SoilHealthFormProps = {
  farmId: string;
  onSuccess?: () => void;
};

export function SoilHealthForm({ farmId, onSuccess }: SoilHealthFormProps) {
  const { t } = useTranslation();
  const mutation = useSubmitSoilRecord(farmId);
  const [form, setForm] = useState({
    nitrogen: "240",
    phosphorus: "18",
    potassium: "180",
    ph: "7.0",
    organic_carbon: "0.45",
    electrical_conductivity: "0.8",
  });

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await mutation.mutateAsync({
      farm_id: farmId,
      nitrogen: Number(form.nitrogen),
      phosphorus: Number(form.phosphorus),
      potassium: Number(form.potassium),
      ph: Number(form.ph),
      organic_carbon: Number(form.organic_carbon),
      electrical_conductivity: Number(form.electrical_conductivity),
    });
    onSuccess?.();
  };

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-3 sm:grid-cols-2">
      <Field label={t("soil_form.nitrogen", "Nitrogen (kg/ha)")} value={form.nitrogen} onChange={(value) => setForm({ ...form, nitrogen: value })} />
      <Field label={t("soil_form.phosphorus", "Phosphorus (kg/ha)")} value={form.phosphorus} onChange={(value) => setForm({ ...form, phosphorus: value })} />
      <Field label={t("soil_form.potassium", "Potassium (kg/ha)")} value={form.potassium} onChange={(value) => setForm({ ...form, potassium: value })} />
      <Field label={t("soil_form.ph", "pH")} value={form.ph} onChange={(value) => setForm({ ...form, ph: value })} />
      <Field label={t("soil_form.organicCarbon", "Organic carbon (%)")} value={form.organic_carbon} onChange={(value) => setForm({ ...form, organic_carbon: value })} />
      <Field label={t("soil_form.ec", "EC (dS/m)")} value={form.electrical_conductivity} onChange={(value) => setForm({ ...form, electrical_conductivity: value })} />
      <div className="sm:col-span-2">
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? t("soil_form.saving", "Saving...") : t("soil_form.saveRecord", "Save soil record")}
        </Button>
        {mutation.error instanceof Error && (
          <p className="mt-2 text-sm text-red-600">{mutation.error.message}</p>
        )}
      </div>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="space-y-1">
      <Label>{label}</Label>
      <Input value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
