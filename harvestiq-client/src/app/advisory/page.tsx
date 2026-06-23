"use client";

import { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { AdvisoryChat } from "@/components/AdvisoryChat";
import { ActionCenterView } from "@/components/ActionCenterView";
import { AppShell } from "@/components/layout/AppShell";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";
import { cn } from "@/lib/utils";

function AdvisoryPageContent() {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const farm = useAuthStore((state) => state.farm);
  const [activeTab, setActiveTab] = useState<"actions" | "chat">("actions");

  return (
    <AppShell
      userName={user?.name}
      pageTitle={t("advisory.pageTitle", "Advisory")}
      pageSubtitle={t("advisory.pageSubtitle", "Context-bound farm guidance powered by compiled intelligence")}
      showBack={{ href: "/", label: t("common.dashboard", "Dashboard") }}
      narrow
    >
      {farm?.farm_id ? (
        <div className="space-y-5">
          {/* Custom premium capsule tabs switcher */}
          <div className="flex bg-slate-100 p-1 rounded-xl w-full sm:w-80 select-none border border-slate-200/50">
            <button
              onClick={() => setActiveTab("actions")}
              className={cn(
                "flex-1 py-2 text-xs font-bold rounded-lg transition-all",
                activeTab === "actions"
                  ? "bg-white text-slate-800 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              )}
            >
              {t("advisory.tabs.actionCenter", "Action Center")}
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              className={cn(
                "flex-1 py-2 text-xs font-bold rounded-lg transition-all",
                activeTab === "chat"
                  ? "bg-white text-slate-800 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              )}
            >
              {t("advisory.tabs.chat", "AI Advisor Chat")}
            </button>
          </div>

          {activeTab === "actions" ? (
            <ActionCenterView farmId={farm.farm_id} language={user?.preferred_lang ?? "hi"} />
          ) : (
            <AdvisoryChat farmId={farm.farm_id} language={user?.preferred_lang ?? "hi"} />
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-600">{t("advisory.completeOnboarding", "Complete onboarding to use advisory.")}</p>
      )}
    </AppShell>
  );
}

export default function AdvisoryPage() {
  return (
    <AuthGuard requireOnboarding>
      <AdvisoryPageContent />
    </AuthGuard>
  );
}
