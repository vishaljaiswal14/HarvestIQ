"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { onboardingSchema, type OnboardingFormValues } from "@/lib/validations";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";

const CROP_OPTIONS = [
  "Wheat",
  "Rice",
  "Maize",
  "Cotton",
  "Sugarcane",
  "Soybean",
  "Mustard",
  "Potato",
];

export function OnboardingForm() {
  const router = useRouter();
  const { t } = useTranslation();
  const refreshUser = useAuthStore((state) => state.refreshUser);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OnboardingFormValues>({
    resolver: zodResolver(onboardingSchema),
    defaultValues: {
      crop_type: "",
      state: "",
      district: "",
      sowing_date: "",
      farm_name: "",
      soil_type: undefined,
    },
  });

  const onSubmit = async (values: OnboardingFormValues) => {
    setError(null);
    try {
      await api.completeOnboarding({
        crop_type: values.crop_type,
        state: values.state,
        district: values.district,
        sowing_date: values.sowing_date,
        farm_name: values.farm_name || undefined,
        soil_type: values.soil_type,
      });
      await refreshUser();
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("onboarding.failed", "Onboarding failed"));
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="farm-name">{t("onboarding.farmNameLabel", "Farm name (optional)")}</Label>
        <Input id="farm-name" placeholder={t("onboarding.farmNamePlaceholder", "My Farm")} {...register("farm_name")} />
      </div>

      <div className="space-y-2">
        <Label htmlFor="crop-type">{t("onboarding.cropTypeLabel", "Crop type")}</Label>
        <Input id="crop-type" list="crop-options" {...register("crop_type")} />
        <datalist id="crop-options">
          {CROP_OPTIONS.map((crop) => (
            <option key={crop} value={crop}>
              {t("crop." + crop.toLowerCase(), crop)}
            </option>
          ))}
        </datalist>
        {errors.crop_type && (
          <p className="text-sm text-red-600">{t(errors.crop_type.message || "", errors.crop_type.message)}</p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="state">{t("onboarding.stateLabel", "State")}</Label>
          <Input id="state" placeholder={t("onboarding.statePlaceholder", "Punjab")} {...register("state")} />
          {errors.state && (
            <p className="text-sm text-red-600">{t(errors.state.message || "", errors.state.message)}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="district">{t("onboarding.districtLabel", "District")}</Label>
          <Input id="district" placeholder={t("onboarding.districtPlaceholder", "Ludhiana")} {...register("district")} />
          {errors.district && (
            <p className="text-sm text-red-600">{t(errors.district.message || "", errors.district.message)}</p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="sowing-date">{t("onboarding.sowingDateLabel", "Sowing date")}</Label>
        <Input id="sowing-date" type="date" {...register("sowing_date")} />
        {errors.sowing_date && (
          <p className="text-sm text-red-600">{t(errors.sowing_date.message || "", errors.sowing_date.message)}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="soil-type">{t("onboarding.soilTypeLabel", "Soil type (optional)")}</Label>
        <select
          id="soil-type"
          className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm"
          {...register("soil_type")}
        >
          <option value="">{t("onboarding.selectSoilType", "Select soil type")}</option>
          <option value="CLAY">{t("onboarding.soilType.clay", "Clay")}</option>
          <option value="SANDY">{t("onboarding.soilType.sandy", "Sandy")}</option>
          <option value="LOAM">{t("onboarding.soilType.loam", "Loam")}</option>
          <option value="SILT">{t("onboarding.soilType.silt", "Silt")}</option>
        </select>
      </div>

      {error && <p className="text-sm text-red-600">{t(error, error)}</p>}

      <Button type="submit" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? t("onboarding.saving", "Saving...") : t("onboarding.completeOnboarding", "Complete onboarding")}
      </Button>
    </form>
  );
}
