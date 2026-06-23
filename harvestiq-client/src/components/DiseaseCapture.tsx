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
import { DiseaseResultCard } from "@/components/DiseaseResultCard";
import { useDiseaseDetect } from "@/hooks/useDiseaseDetect";
import type { DiseaseDetectResult } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";

type DiseaseCaptureProps = {
  farmId: string;
};

export function DiseaseCapture({ farmId }: DiseaseCaptureProps) {
  const { t } = useTranslation();
  const mutation = useDiseaseDetect();
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<DiseaseDetectResult | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setSelectedFile(file);
    setResult(null);
    setPreview(URL.createObjectURL(file));
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      return;
    }

    // 1. Force a local-first fallback bypass if offline
    if (typeof window !== 'undefined' && !navigator.onLine) {
      console.log("[CROP DOCTOR UI DEBUG] Local-first bypass active for disease detection.");
      
      const offlineResult = {
        report_id: "offline-report",
        farm_id: farmId,
        crop_type: "Unknown",
        disease: "OFFLINE_MODE",
        confidence: 0.0,
        deterministic_status: "UNAVAILABLE",
        explanation: {
          summary: t("disease.offlineUnavailable", "Disease diagnosis is currently unavailable offline."),
          inputs: {},
          primary_factor: "NONE",
        },
      };
      
      setResult(offlineResult as any);
      return; // Terminate early so mutation never runs and never sets an error state
    }

    try {
      const response = await mutation.mutateAsync({ farmId, image: selectedFile });
      setResult(response);
    } catch (error) {
      console.error("[CROP DOCTOR UI DEBUG] Disease analysis failed gracefully:", error);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t("disease.captureTitle", "Capture Crop Image")}</CardTitle>
          <CardDescription>
            {t("disease.captureDesc", "Upload a clear leaf or canopy photo for vision-based disease screening.")}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            className="block w-full text-sm"
          />
          {preview && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt={t("disease.previewAlt", "Crop preview")} className="max-h-64 rounded-lg border object-cover" />
          )}
          <Button onClick={() => void handleSubmit()} disabled={!selectedFile || mutation.isPending}>
            {mutation.isPending ? t("disease.analyzing", "Analyzing...") : t("disease.runDetection", "Run disease detection")}
          </Button>
          {mutation.error instanceof Error && (
            <p className="text-sm text-red-600">{mutation.error.message}</p>
          )}
        </CardContent>
      </Card>

      {result && <DiseaseResultCard result={result} />}
    </div>
  );
}
