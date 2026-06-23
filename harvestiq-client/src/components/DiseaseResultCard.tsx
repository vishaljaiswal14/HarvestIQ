"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DiseaseDetectResult } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";

type DiseaseResultCardProps = {
  result: DiseaseDetectResult;
};

const STATUS_STYLES: Record<string, string> = {
  CONFIRMED_DISEASE: "bg-emerald-100 text-emerald-800 border-emerald-200",
  POSSIBLE_DISEASE: "bg-blue-100 text-blue-800 border-blue-200",
  LOW_CONFIDENCE: "bg-amber-100 text-amber-800 border-amber-200",
  UNKNOWN: "bg-gray-100 text-gray-800 border-gray-200",
  HEALTHY: "bg-emerald-100 text-emerald-800 border-emerald-200",
  INVALID_IMAGE: "bg-red-100 text-red-800 border-red-200",
  UNAVAILABLE: "bg-gray-100 text-gray-800 border-gray-200",
};

const getStatusKey = (status: string) => {
  if (status === "CONFIRMED_DISEASE") return "status.highRisk";
  if (status === "POSSIBLE_DISEASE") return "status.needsAttention";
  if (status === "LOW_CONFIDENCE" || status === "UNKNOWN") return "status.needsReview";
  if (status === "HEALTHY") return "status.healthy";
  if (status === "INVALID_IMAGE") return "status.needsReview";
  return "status.needsReview";
};

const getStatusLabel = (status: string) => {
  if (status === "CONFIRMED_DISEASE") return "High Risk";
  if (status === "POSSIBLE_DISEASE") return "Needs Attention";
  if (status === "HEALTHY") return "Healthy";
  return "Needs Review";
};

const getRiskLabel = (value?: string) => {
  if (!value) return "Healthy";
  const normalized = value.toLowerCase();
  if (normalized === "high" || normalized === "higher" || normalized === "उच्च") return "High Risk";
  if (normalized === "medium" || normalized === "moderate" || normalized === "मध्यम") return "Moderate Risk";
  return "Healthy";
};

const getSeverityStyle = (severity?: string) => {
  if (!severity) return "bg-gray-50 text-gray-700 border-gray-200";
  const s = severity.toLowerCase();
  if (s === "high" || s === "higher" || s === "उच्च") return "bg-red-50 text-red-700 border-red-200";
  if (s === "medium" || s === "moderate" || s === "मध्यम") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-emerald-50 text-emerald-700 border-emerald-200";
};

const getRiskLevelStyle = (riskLevel?: string) => {
  if (!riskLevel) return "bg-gray-50 text-gray-700 border-gray-200";
  const r = riskLevel.toLowerCase();
  if (r === "high" || r === "उच्च") return "bg-red-50 text-red-700 border-red-200";
  if (r === "medium" || r === "moderate" || r === "मध्यम") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-emerald-50 text-emerald-700 border-emerald-200";
};

export function DiseaseResultCard({ result }: DiseaseResultCardProps) {
  const { t } = useTranslation();

  // STAGE 1 & 2: Conditional Validation Failure Card
  if (result.valid === false) {
    const isBlurry = result.reason === "LOW_IMAGE_QUALITY" && result.message?.toLowerCase().includes("blurry");
    const isDark = result.reason === "LOW_IMAGE_QUALITY" && result.message?.toLowerCase().includes("dark");
    const isWhite = result.reason === "LOW_IMAGE_QUALITY" && result.message?.toLowerCase().includes("white");
    const isLowResolution = result.reason === "LOW_IMAGE_QUALITY" && result.message?.toLowerCase().includes("resolution");
    const isHuman = result.image_type === "HUMAN";
    const isBlank = result.image_type === "BLANK_IMAGE";
    const isScreenshot = result.image_type === "SCREENSHOT" || result.image_type === "DOCUMENT";
    
    let errorTitle = t("disease.validationFailed", "Image Validation Failed");
    let errorDesc = result.message || t("disease.invalidImageDesc", "Please upload a valid crop leaf image.");
    
    if (isHuman) {
      errorTitle = t("disease.validation.humanTitle", "Human Detected");
      errorDesc = t("disease.validation.humanDesc", "We detected a human or face in the photo. Please scan only the affected crop leaves.");
    } else if (isScreenshot) {
      errorTitle = t("disease.validation.screenshotTitle", "Screenshot/Document Detected");
      errorDesc = t("disease.validation.screenshotDesc", "Screenshots or digital documents are not allowed. Please take a live photo of the crop in the field.");
    } else if (isBlank || isWhite || isDark) {
      errorTitle = t("disease.validation.blankTitle", "Blank or Extreme Lighting Detected");
      errorDesc = t("disease.validation.blankDesc", "The photo is completely blank, white, or dark. Please ensure there is adequate, even lighting.");
    } else if (isBlurry) {
      errorTitle = t("disease.validation.blurryTitle", "Image Too Blurry");
      errorDesc = t("disease.validation.blurryDesc", "The image is too blurry to extract crop disease patterns. Please hold the camera steady and re-focus.");
    } else if (isLowResolution) {
      errorTitle = t("disease.validation.lowResTitle", "Low Resolution");
      errorDesc = t("disease.validation.lowResDesc", "The image size is too small. Please use a standard camera setting.");
    } else if (result.reason === "NOT_CROP_IMAGE") {
      errorTitle = t("disease.validation.notCropTitle", "Not a Crop Image");
      errorDesc = t("disease.validation.notCropDesc", "This image does not appear to show crop leaves, canopy, or field foliage.");
    }

    return (
      <Card className="overflow-hidden border border-red-200 shadow-sm transition-all hover:shadow-md bg-red-50/5">
        <CardHeader className="border-b border-red-100 bg-red-50/20 pb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl" role="img" aria-label="warning">⚠️</span>
            <div>
              <CardTitle className="text-lg font-bold text-red-900">
                {errorTitle}
              </CardTitle>
              <CardDescription className="text-xs text-red-700">
                {t("disease.validation.warningSubtitle", "Crop Doctor Screening Blocked")}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-4 text-sm text-gray-700 bg-white">
          <p className="font-medium text-red-950 bg-red-50/40 border border-red-100 rounded-lg p-3">
            {errorDesc}
          </p>

          <div className="space-y-2">
            <h4 className="font-bold text-gray-900">
              {t("disease.validation.howToRetake", "Guidelines for a successful scan:")}
            </h4>
            <ul className="space-y-2">
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>{t("disease.guideline.focus", "Focus on a single leaf or small group of leaves showing clear symptoms.")}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>{t("disease.guideline.lighting", "Ensure even lighting. Avoid intense direct flash, deep shadows, or dark conditions.")}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 font-bold">✗</span>
                <span>{t("disease.guideline.noHumans", "Avoid capturing hands, faces, shoes, or any human presence.")}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-500 font-bold">✗</span>
                <span>{t("disease.guideline.noScreenshots", "Do not upload screenshots, scanned PDF pages, or downloaded documents.")}</span>
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>
    );
  }

  const badgeClass = STATUS_STYLES[result.deterministic_status] ?? "bg-gray-100 text-gray-800";
  const severityClass = getSeverityStyle(result.severity);
  const riskLevelClass = getRiskLevelStyle(result.risk_level);

  const hasGuidance = !!result.disease_name;

  return (
    <Card className="overflow-hidden border border-gray-200 shadow-sm transition-all hover:shadow-md">
      <CardHeader className="border-b border-gray-100 bg-gray-50/50 pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <CardTitle className="text-lg font-bold text-gray-900">
              {t("disease.resultTitle", "Disease Screening Result")}
            </CardTitle>
            <CardDescription className="text-xs text-gray-500">
              {t("disease.resultDesc", "Crop scan result and recommended next steps")}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-center">
            {result.severity && (
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${severityClass}`}>
                {t("disease.severity", "Severity")}: {t("status." + getRiskLabel(result.severity).replace(/\s+/g, "").toLowerCase(), getRiskLabel(result.severity))}
              </span>
            )}
            {result.risk_level && (
              <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${riskLevelClass}`}>
                {t("disease.riskLevel", "Risk Level")}: {t("status." + getRiskLabel(result.risk_level).replace(/\s+/g, "").toLowerCase(), getRiskLabel(result.risk_level))}
              </span>
            )}
            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badgeClass}`}>
              {t(getStatusKey(result.deterministic_status), getStatusLabel(result.deterministic_status))}
            </span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-6 space-y-6 text-sm">
        {/* Core details row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 rounded-lg bg-gray-50 p-4 border border-gray-100">
          <div>
            <span className="block text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t("disease.candidateLabel", "Detected Anomaly")}
            </span>
            <span className="text-sm font-semibold text-gray-900">
              {result.disease === "OFFLINE_MODE" || result.deterministic_status === "UNAVAILABLE" 
                ? t("errorBoundary.unavailable", "Unavailable") 
                : (result.disease_name || result.disease)}
            </span>
          </div>
          {result.disease !== "OFFLINE_MODE" && result.deterministic_status !== "UNAVAILABLE" && (
            <>
              <div>
                <span className="block text-xs font-medium text-gray-500 uppercase tracking-wider">
                  {t("disease.cropLabel", "Crop")}
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {t("crop." + result.crop_type.toLowerCase(), result.crop_type)}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Actionable guidance sections */}
        {hasGuidance && (
          <div className="space-y-4">
            {/* What it means */}
            {result.what_it_means && (
              <div className="space-y-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                  {t("disease.whatItMeans", "What it means")}
                </h4>
                <p className="text-gray-700 leading-relaxed bg-white border border-gray-100 rounded-lg p-3">
                  {result.what_it_means}
                </p>
              </div>
            )}

            {/* Immediate Actions */}
            {result.immediate_actions && result.immediate_actions.length > 0 && (
              <div className="space-y-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                  {t("disease.immediateActions", "Immediate Actions")}
                </h4>
                <ul className="grid grid-cols-1 gap-2">
                  {result.immediate_actions.map((action, idx) => (
                    <li key={idx} className="flex items-start gap-2 bg-red-50/30 border border-red-100/50 rounded-lg p-3 text-gray-700 leading-normal">
                      <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-800">
                        {idx + 1}
                      </span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommended Treatment */}
            {result.recommended_treatment && (
              <div className="space-y-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                  {t("disease.recommendedTreatment", "Recommended Treatment")}
                </h4>
                <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-4 text-emerald-900 shadow-sm leading-relaxed">
                  <div className="flex gap-2">
                    <span className="font-bold text-emerald-800">🧪</span>
                    <p className="font-medium text-emerald-950">{result.recommended_treatment}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Prevention Advice */}
            {result.prevention_advice && result.prevention_advice.length > 0 && (
              <div className="space-y-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                  {t("disease.preventionAdvice", "Prevention Advice")}
                </h4>
                <ul className="grid grid-cols-1 gap-2">
                  {result.prevention_advice.map((advice, idx) => (
                    <li key={idx} className="flex items-start gap-2 bg-emerald-50/20 border border-emerald-100/30 rounded-lg p-3 text-gray-700 leading-normal">
                      <span className="text-emerald-600 font-bold">✓</span>
                      <span>{advice}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Fallback rule summary */}
        {!hasGuidance && result.explanation?.summary && (
          <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3 text-emerald-800 leading-relaxed">
            {result.explanation.summary}
          </div>
        )}

        {/* LOW_CONFIDENCE Warning notice */}
        {result.deterministic_status === "LOW_CONFIDENCE" && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 font-medium leading-relaxed text-sm">
            ⚠️ {t("disease.uncertainWarning", "Result uncertain. Please upload a clearer crop image.")}
          </div>
        )}

        {/* UNKNOWN Warning notice */}
        {result.deterministic_status === "UNKNOWN" && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-gray-900 font-medium leading-relaxed text-sm">
            ⚠️ {t("disease.unknownWarning", "Unable to confidently identify a disease. Please upload a clearer close-up image of the affected leaf.")}
          </div>
        )}

        {/* Warning footer */}
        {(result.deterministic_status === "CONFIRMED_DISEASE" || result.deterministic_status === "POSSIBLE_DISEASE" || result.deterministic_status === "LOW_CONFIDENCE") && (
          <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-3 text-amber-700 leading-relaxed text-xs">
            ⚠️ {t("disease.nonFinalWarning", "This vision result is not final. Confirm with a local KVK or agriculture officer before treatment.")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
