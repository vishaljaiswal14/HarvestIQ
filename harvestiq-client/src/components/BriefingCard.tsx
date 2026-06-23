"use client";

import { Calendar, Sparkles } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useBriefing } from "@/hooks/useBriefing";
import { useTranslation } from "@/stores/localizationStore";

type BriefingCardProps = {
  farmId?: string | null;
  language?: string;
};

function cleanBriefingText(text: string, language: string): string {
  if (!text) return "";

  // Check if it's the technical deterministic context string
  if (text.includes("Morning briefing (deterministic):") || text.includes("Farm ID:")) {
    const cropMatch = text.match(/-\s*Crop:\s*(.*?)(?=\s+-\s+|$)/i);
    const stageMatch = text.match(/-\s*Stage:\s*(.*?)(?=\s+-\s+|$)/i) || text.match(/-\s*State crop cycle stage:\s*(.*?)(?=\s+-\s+|$)/i);
    const crop = cropMatch ? cropMatch[1].trim() : "";
    const stage = stageMatch ? stageMatch[1].trim() : "";

    if (language === "hi") {
      let insight = "आपके खेत की दैनिक स्थिति का विवरण यहाँ है। ";
      if (crop) insight += `आपकी ${crop} की फसल वर्तमान में ${stage || "विकास"} चरण में है। `;
      insight += "आज की सलाह हाल के मौसम, फसल अवस्था और खेत की स्थिति पर आधारित है।";
      return insight;
    } else {
      let insight = "Here is your daily field intelligence briefing. ";
      if (crop) insight += `Your ${crop} crop is currently in the ${stage || "growth"} stage. `;
      insight += "Today's guidance is based on recent weather, crop stage, and field conditions.";
      return insight;
    }
  }

  // General cleanup for LLM-generated synthesis
  let cleaned = text.replace(/^Morning briefing\s*\([^)]*\):\s*/i, "");
  cleaned = cleaned.replace(/[a-f0-9]{24}/g, "");
  cleaned = cleaned.replace(/\bFSI\b/gi, "crop stress");
  cleaned = cleaned.replace(/Field Stress Index/gi, "crop stress");
  cleaned = cleaned.replace(/Rainfall Deficit Index/gi, "rainfall shortage");
  cleaned = cleaned.replace(/\bGDD\b/g, "crop growth stage");
  cleaned = cleaned.replace(/\b(?:HIGH|MEDIUM|LOW)_STRESS\b/g, (match) => {
    if (match.startsWith("HIGH")) return "high crop stress";
    if (match.startsWith("MEDIUM")) return "moderate crop stress";
    return "low crop stress";
  });
  cleaned = cleaned.replace(/\s+-\s+/g, " ");
  return cleaned;
}

export function BriefingCard({ farmId, language }: BriefingCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useBriefing(farmId, language);

  if (!farmId) return null;

  if (isLoading) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("briefing.title", "Daily Intelligence Briefing")}</CardTitle>
          <CardDescription>{t("briefing.preparing", "Preparing morning summary…")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-40 animate-pulse rounded-xl bg-slate-100" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle>{t("briefing.title", "Daily Intelligence Briefing")}</CardTitle>
          <CardDescription className="text-amber-750">
            {t("briefing.unavailable", "Daily briefing unavailable offline — last briefing shown when cached.")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="dashboard-card overflow-hidden border-indigo-100">
      <div className="h-1 bg-gradient-to-r from-indigo-500 via-violet-500 to-indigo-600" />
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="dashboard-section-title mb-1">{t("briefing.morningIntelligence", "Morning Intelligence")}</p>
            <CardTitle className="flex items-center gap-2 text-base font-bold text-slate-800">
              <Sparkles className="h-4.5 w-4.5 text-indigo-500" />
              {t("briefing.dailyBriefing", "Daily Briefing")}
            </CardTitle>
            <CardDescription className="mt-1 flex items-center gap-1.5 text-xs text-slate-400 font-medium">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(data.generated_at).toLocaleString()}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="compact-card-content pb-4">
        <blockquote className="relative rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/40 to-white p-4">
          <div className="absolute -left-1 top-4 h-8 w-1 rounded-full bg-indigo-400" />
          <p className="text-sm leading-relaxed text-slate-700">
            {cleanBriefingText(data.synthesis, language ?? "hi")}
          </p>
        </blockquote>
      </CardContent>
    </Card>
  );
}
