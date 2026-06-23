"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTranslation } from "@/stores/localizationStore";
import { useAuthStore } from "@/stores/authStore";
import { cacheSnapshot } from "@/lib/db";

const CROP_OPTIONS = [
  "WHEAT",
  "RICE",
  "MAIZE",
  "COTTON",
  "SUGARCANE",
  "SOYBEAN",
  "MUSTARD",
  "POTATO",
];

const SEASON_OPTIONS = [
  { value: "KHARIF", label: "Kharif (Monsoon)" },
  { value: "RABI", label: "Rabi (Winter)" },
  { value: "ZAID", label: "Zaid (Summer)" },
  { value: "WHOLE_YEAR", label: "Whole Year" },
];

const getSeasonKey = (val: string) => {
  if (val === "WHOLE_YEAR" || val === "WHOLE_YEAR") return "farmSetup.season.wholeYear";
  return `farmSetup.season.${val.toLowerCase()}`;
};

export function FarmSetupFlow() {
  const router = useRouter();
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);

  // Form State
  const [farmData, setFarmData] = useState({
    name: "",
    area: "",
    area_unit: "ACRE",
    latitude: "",
    longitude: "",
  });

  const [plotData, setPlotData] = useState({
    name: "",
    area: "",
    area_unit: "ACRE",
  });

  const [cropData, setCropData] = useState({
    crop_type: "WHEAT",
    season: "RABI",
    sowing_date: "",
    expected_harvest_date: "",
  });

  // Fetch existing farm on mount if it exists, to reuse it and bypass Step 1
  useEffect(() => {
    const ef = useAuthStore.getState().farm;
    if (ef?.farm_id) {
      setStep(2);
      setFarmData((prev) => ({
        ...prev,
        name: ef.farm_name,
      }));
      api.getFarm(ef.farm_id)
        .then((farm) => {
          if (farm) {
            setFarmData({
              name: farm.name || ef.farm_name,
              area: farm.area ? String(farm.area) : "",
              area_unit: farm.area_unit || "ACRE",
              latitude: farm.latitude ? String(farm.latitude) : "",
              longitude: farm.longitude ? String(farm.longitude) : "",
            });
          }
        })
        .catch((err) => {
          console.warn("[FarmSetupFlow] Failed to fetch full farm details on mount:", err);
        });
    }
  }, []);

  // Geolocation Handler
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setError(t("farmSetup.error.geoNotSupported", "Geolocation is not supported by your browser"));
      return;
    }
    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFarmData((prev) => ({
          ...prev,
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6),
        }));
        setLocating(false);
      },
      (err) => {
        setError(`${t("farmSetup.error.geoFailed", "Failed to get location:")} ${err.message}`);
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Step Validation
  const validateStep = () => {
    setError(null);
    if (step === 1) {
      if (!farmData.name.trim()) return t("farmSetup.error.farmNameRequired", "Farm name is required");
      if (!farmData.area || parseFloat(farmData.area) <= 0) return t("farmSetup.error.farmAreaRequired", "Valid farm area is required");
    } else if (step === 2) {
      if (!plotData.name.trim()) return t("farmSetup.error.plotNameRequired", "Plot name is required");
      if (!plotData.area || parseFloat(plotData.area) <= 0) return t("farmSetup.error.plotAreaRequired", "Valid plot area is required");
      if (parseFloat(plotData.area) > parseFloat(farmData.area)) {
        return t("farmSetup.error.plotAreaExceeds", "Plot area cannot exceed total farm area");
      }
    } else if (step === 3) {
      if (!cropData.sowing_date) return t("farmSetup.error.sowingDateRequired", "Sowing date is required");
      if (!cropData.expected_harvest_date) return t("farmSetup.error.harvestDateRequired", "Expected harvest date is required");
      if (new Date(cropData.expected_harvest_date) <= new Date(cropData.sowing_date)) {
        return t("farmSetup.error.harvestAfterSowing", "Harvest date must be after sowing date");
      }
    }
    return null;
  };

  const handleNext = () => {
    const err = validateStep();
    if (err) {
      setError(err);
    } else {
      setStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setError(null);
    setStep((prev) => prev - 1);
  };

  const handleSubmit = async () => {
    const err = validateStep();
    if (err) {
      setError(err);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const existingFarm = useAuthStore.getState().farm;
      let farmId = existingFarm?.farm_id || "";
      let farmName = farmData.name || existingFarm?.farm_name || "";

      if (existingFarm?.farm_id) {
        // Update existing farm
        await api.updateFarm(existingFarm.farm_id, {
          name: farmData.name || existingFarm.farm_name,
          area: farmData.area ? parseFloat(farmData.area) : 0,
          area_unit: farmData.area_unit,
          latitude: farmData.latitude ? parseFloat(farmData.latitude) : undefined,
          longitude: farmData.longitude ? parseFloat(farmData.longitude) : undefined,
        });
      } else {
        // 1. Create Farm
        const farm = await api.createFarm({
          name: farmData.name,
          area: parseFloat(farmData.area),
          area_unit: farmData.area_unit,
          latitude: farmData.latitude ? parseFloat(farmData.latitude) : undefined,
          longitude: farmData.longitude ? parseFloat(farmData.longitude) : undefined,
        });
        farmId = farm.id;
        farmName = farm.name;
      }

      // 2. Create Plot
      const plot = await api.createPlot({
        farm_id: farmId,
        name: plotData.name,
        area: parseFloat(plotData.area),
        area_unit: plotData.area_unit,
      });

      // 3. Create Crop Cycle
      const cropCycle = await api.createCropCycle({
        plot_id: plot.id,
        crop_type: cropData.crop_type,
        season: cropData.season,
        sowing_date: cropData.sowing_date,
        expected_harvest_date: cropData.expected_harvest_date,
      });

      // Hydrate local Zustand and offline IndexedDB cache to allow instant loading offline
      const updatedFarmProfile = {
        farm_id: farmId,
        farm_name: farmName,
        state: existingFarm?.state || "Punjab",
        district: existingFarm?.district || "Amritsar",
        soil_type: existingFarm?.soil_type || "Clay",
        crop_cycle_id: cropCycle.id,
        crop_type: cropData.crop_type,
        sowing_date: cropData.sowing_date,
      };

      useAuthStore.getState().setFarm(updatedFarmProfile);
      try {
        await cacheSnapshot("farm", "me", updatedFarmProfile);
      } catch (cacheErr) {
        console.warn("[FarmSetupFlow] Failed to write offline farm cache:", cacheErr);
      }

      // Refresh user to get latest state from server (if online)
      try {
        await useAuthStore.getState().refreshUser();
      } catch (refreshErr) {
        console.warn("[FarmSetupFlow] refreshUser failed, proceeding offline:", refreshErr);
      }

      router.push("/operations");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("farmSetup.error.creationFailed", "An error occurred during creation"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto bg-white/80 backdrop-blur-md border border-emerald-100 shadow-2xl rounded-3xl p-6 sm:p-8 space-y-6">
      {/* Step Progress Header */}
      {step <= 3 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center text-xs font-semibold text-emerald-800 uppercase tracking-wider">
            <span>{t("farmSetup.stepOf", "Step {step} of 3").replace("{step}", String(step))}</span>
            <span>{step === 1 ? t("farmSetup.step.farmDetails", "Farm Details") : step === 2 ? t("farmSetup.step.addPlot", "Add Plot") : t("farmSetup.step.sowCrop", "Sow Crop")}</span>
          </div>
          <div className="h-2 w-full bg-emerald-50 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-teal-600 transition-all duration-300 ease-out"
              style={{ width: `${(step / 3) * 100}%` }}
            />
          </div>
          {/* Step Indicator Circles */}
          <div className="flex justify-between px-2 pt-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-8 h-8 flex items-center justify-center rounded-full text-xs font-bold transition-all duration-300 ${
                  s === step
                    ? "bg-emerald-600 text-white shadow-lg ring-4 ring-emerald-100 scale-110"
                    : s < step
                    ? "bg-emerald-100 text-emerald-700 font-bold"
                    : "bg-gray-100 text-gray-400"
                }`}
              >
                {s < step ? "✓" : s}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-xl">
          ⚠️ {error}
        </div>
      )}

      {/* Step 1: Create Farm */}
      {step === 1 && (
        <div className="space-y-4 animate-fadeIn">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-gray-800">{t("farmSetup.establishFarm", "Establish Your Farm")}</h2>
            <p className="text-xs text-gray-500">{t("farmSetup.farmDesc", "Provide the master details of your agricultural estate.")}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="farm-name">{t("farmSetup.farmNameLabel", "Farm Name")}</Label>
            <Input
              id="farm-name"
              placeholder={t("farmSetup.farmNamePlaceholder", "e.g. Golden Field, Green Acre")}
              value={farmData.name}
              onChange={(e) => setFarmData({ ...farmData, name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="farm-area">{t("farmSetup.totalAreaLabel", "Total Area")}</Label>
              <Input
                id="farm-area"
                type="number"
                step="any"
                placeholder={t("farmSetup.areaPlaceholder", "e.g. 5")}
                value={farmData.area}
                onChange={(e) => setFarmData({ ...farmData, area: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="farm-area-unit">{t("farmSetup.areaUnitLabel", "Area Unit")}</Label>
              <select
                id="farm-area-unit"
                className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                value={farmData.area_unit}
                onChange={(e) => setFarmData({ ...farmData, area_unit: e.target.value })}
              >
                <option value="ACRE">{t("farmSetup.unit.acre", "Acre")}</option>
                <option value="HECTARE">{t("farmSetup.unit.hectare", "Hectare")}</option>
                <option value="SQM">{t("farmSetup.unit.sqm", "Sqm")}</option>
              </select>
            </div>
          </div>

          <div className="border-t border-emerald-50 pt-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-semibold text-gray-700">{t("farmSetup.coordinatesLabel", "Coordinates (Optional)")}</span>
              <button
                type="button"
                onClick={handleGetLocation}
                disabled={locating}
                className="text-xs text-emerald-600 font-bold hover:underline disabled:text-gray-400"
              >
                {locating ? t("farmSetup.locating", "Locating...") : t("farmSetup.gpsButton", "📍 Get GPS Coordinates")}
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="farm-lat">{t("farmSetup.latitudeLabel", "Latitude")}</Label>
                <Input
                  id="farm-lat"
                  placeholder={t("farmSetup.latPlaceholder", "e.g. 22.7195")}
                  value={farmData.latitude}
                  onChange={(e) => setFarmData({ ...farmData, latitude: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="farm-lng">{t("farmSetup.longitudeLabel", "Longitude")}</Label>
                <Input
                  id="farm-lng"
                  placeholder={t("farmSetup.lngPlaceholder", "e.g. 75.8577")}
                  value={farmData.longitude}
                  onChange={(e) => setFarmData({ ...farmData, longitude: e.target.value })}
                />
              </div>
            </div>
          </div>

          <Button onClick={handleNext} className="w-full mt-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl py-6 font-bold shadow-lg shadow-emerald-100">
            {t("farmSetup.nextAddPlot", "Next: Add Plot")}
          </Button>
        </div>
      )}

      {/* Step 2: Add Plot */}
      {step === 2 && (
        <div className="space-y-4 animate-fadeIn">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-gray-800">{t("farmSetup.addSubPlot", "Add a Sub-Plot")}</h2>
            <p className="text-xs text-gray-500">{t("farmSetup.plotDesc", "Farms are split into plots for crop cycles. Let's map your first plot.")}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="plot-name">{t("farmSetup.plotNameLabel", "Plot Name")}</Label>
            <Input
              id="plot-name"
              placeholder={t("farmSetup.plotNamePlaceholder", "e.g. North Plot, Slope A")}
              value={plotData.name}
              onChange={(e) => setPlotData({ ...plotData, name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="plot-area">{t("farmSetup.plotAreaLabel", "Plot Area")}</Label>
              <Input
                id="plot-area"
                type="number"
                step="any"
                placeholder={t("farmSetup.plotAreaPlaceholder", "e.g. 2.5")}
                value={plotData.area}
                onChange={(e) => setPlotData({ ...plotData, area: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="plot-area-unit">{t("farmSetup.areaUnitLabel", "Area Unit")}</Label>
              <select
                id="plot-area-unit"
                className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none"
                value={plotData.area_unit}
                onChange={(e) => setPlotData({ ...plotData, area_unit: e.target.value })}
              >
                <option value="ACRE">{t("farmSetup.unit.acre", "Acre")}</option>
                <option value="HECTARE">{t("farmSetup.unit.hectare", "Hectare")}</option>
                <option value="SQM">{t("farmSetup.unit.sqm", "Sqm")}</option>
              </select>
            </div>
          </div>

          <div className="text-xs text-emerald-700 bg-emerald-50/50 p-3 rounded-xl border border-emerald-100/50">
            {t("farmSetup.limitRemaining", "💡 Farm limit remaining:")} <span className="font-bold">{parseFloat(farmData.area) - (parseFloat(plotData.area) || 0)} {t("farmSetup.unit." + farmData.area_unit.toLowerCase(), farmData.area_unit)}</span>
          </div>

          <div className="flex gap-4 pt-4">
            <Button variant="outline" onClick={handleBack} className="w-1/3 rounded-xl py-6 border-emerald-200 text-emerald-800">
              {t("farmSetup.back", "Back")}
            </Button>
            <Button onClick={handleNext} className="w-2/3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl py-6 font-bold">
              {t("farmSetup.nextSelectCrop", "Next: Select Crop")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 3: Add Crop */}
      {step === 3 && (
        <div className="space-y-4 animate-fadeIn">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-gray-800">{t("farmSetup.sowCropCycle", "Sow a Crop Cycle")}</h2>
            <p className="text-xs text-gray-500">{t("farmSetup.cropDesc", "Start a new seasonal crop cycle on your plot.")}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="crop-select">{t("farmSetup.cropTypeLabel", "Crop Type")}</Label>
              <select
                id="crop-select"
                className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none"
                value={cropData.crop_type}
                onChange={(e) => setCropData({ ...cropData, crop_type: e.target.value })}
              >
                {CROP_OPTIONS.map((c) => (
                  <option key={c} value={c}>{t("crop." + c.toLowerCase(), c)}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="season-select">{t("farmSetup.seasonLabel", "Season")}</Label>
              <select
                id="season-select"
                className="flex h-10 w-full rounded-md border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none"
                value={cropData.season}
                onChange={(e) => setCropData({ ...cropData, season: e.target.value })}
              >
                {SEASON_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{t(getSeasonKey(s.value), s.label)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="sowing-date">{t("farmSetup.sowingDateLabel", "Sowing Date")}</Label>
            <Input
              id="sowing-date"
              type="date"
              value={cropData.sowing_date}
              onChange={(e) => setCropData({ ...cropData, sowing_date: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="harvest-date">{t("farmSetup.expectedHarvestLabel", "Expected Harvest Date")}</Label>
            <Input
              id="harvest-date"
              type="date"
              value={cropData.expected_harvest_date}
              onChange={(e) => setCropData({ ...cropData, expected_harvest_date: e.target.value })}
            />
          </div>

          <div className="flex gap-4 pt-4">
            <Button variant="outline" onClick={handleBack} className="w-1/3 rounded-xl py-6 border-emerald-200 text-emerald-800" disabled={isSubmitting}>
              {t("farmSetup.back", "Back")}
            </Button>
            <Button onClick={handleSubmit} className="w-2/3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white rounded-xl py-6 font-bold shadow-lg shadow-emerald-100" disabled={isSubmitting}>
              {isSubmitting ? t("farmSetup.creatingFarm", "Creating Farm...") : t("farmSetup.establishFarmBtn", "Establish Farm")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 4: Success Screen */}
      {step === 4 && (
        <div className="text-center space-y-6 py-6 animate-scaleIn">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-600 flex items-center justify-center rounded-full mx-auto text-3xl shadow-inner animate-pulse">
            🌱
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-gray-800">{t("farmSetup.successTitle", "Farm Established!")}</h2>
            <p className="text-sm text-gray-500 max-w-sm mx-auto">
              {t("farmSetup.successDesc", "Your farm, plot, and crop cycle have been saved successfully. If offline, updates have been enqueued and will sync automatically when your network returns.")}
            </p>
          </div>
          <Button onClick={() => router.push("/")} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl py-6 font-bold max-w-xs mx-auto block shadow-lg shadow-emerald-100">
            {t("farmSetup.goToDashboard", "Go to Dashboard")}
          </Button>
        </div>
      )}
    </div>
  );
}
