"use client";

import { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { DiseaseCapture } from "@/components/DiseaseCapture";
import { DiseaseHistoryView } from "@/components/DiseaseHistoryView";
import { FarmTimelineView } from "@/components/FarmTimelineView";
import { AppShell } from "@/components/layout/AppShell";
import { RadarMap } from "@/components/RadarMap";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";
import { Microscope, ClipboardList, Activity } from "lucide-react";
import { cn } from "@/lib/utils";

function DiseasePageContent() {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const farm = useAuthStore((state) => state.farm);
  const [activeTab, setActiveTab] = useState<"scan" | "history" | "timeline">("scan");

  return (
    <AppShell
      userName={user?.name}
      pageTitle={t("disease.pageTitle", "Disease Detection")}
      pageSubtitle={t("disease.pageSubtitle", "Vision screening with deterministic validation and outbreak radar")}
      showBack={{ href: "/", label: t("common.dashboard", "Dashboard") }}
      narrow
    >
      {farm?.farm_id ? (
        <div className="space-y-6">
          {/* Tabs Selector */}
          <div className="flex border-b border-slate-100 pb-px gap-6">
            <button
              onClick={() => setActiveTab("scan")}
              className={cn(
                "pb-3 text-sm font-bold flex items-center gap-1.5 border-b-2 transition-all duration-200 leading-none select-none",
                activeTab === "scan"
                  ? "border-emerald-600 text-emerald-600"
                  : "border-transparent text-slate-400 hover:text-slate-650"
              )}
            >
              <Microscope className="h-4 w-4" />
              {t("disease.tab.scan", "Visual Scan")}
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={cn(
                "pb-3 text-sm font-bold flex items-center gap-1.5 border-b-2 transition-all duration-200 leading-none select-none",
                activeTab === "history"
                  ? "border-emerald-600 text-emerald-600"
                  : "border-transparent text-slate-400 hover:text-slate-650"
              )}
            >
              <ClipboardList className="h-4 w-4" />
              {t("disease.tab.history", "Disease History")}
            </button>
            <button
              onClick={() => setActiveTab("timeline")}
              className={cn(
                "pb-3 text-sm font-bold flex items-center gap-1.5 border-b-2 transition-all duration-200 leading-none select-none",
                activeTab === "timeline"
                  ? "border-emerald-600 text-emerald-600"
                  : "border-transparent text-slate-400 hover:text-slate-650"
              )}
            >
              <Activity className="h-4 w-4" />
              {t("disease.tab.timeline", "Health Timeline")}
            </button>
          </div>

          {/* Tab Contents */}
          <div className="space-y-6">
            {activeTab === "scan" && (
              <div className="space-y-6">
                <DiseaseCapture farmId={farm.farm_id} />
                <RadarMap farmId={farm.farm_id} cropType={farm.crop_type} />
              </div>
            )}
            {activeTab === "history" && (
              <DiseaseHistoryView farmId={farm.farm_id} />
            )}
            {activeTab === "timeline" && (
              <FarmTimelineView farmId={farm.farm_id} />
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-600">{t("disease.completeOnboarding", "Complete onboarding to use disease detection.")}</p>
      )}
    </AppShell>
  );
}

export default function DiseasePage() {
  return (
    <AuthGuard requireOnboarding>
      <DiseasePageContent />
    </AuthGuard>
  );
}
