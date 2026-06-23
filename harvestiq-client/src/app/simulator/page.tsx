"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/layout/AppShell";
import { SimulatorDashboard } from "@/components/SimulatorDashboard";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";

function SimulatorContent() {
  const { t } = useTranslation();
  const farm = useAuthStore((state) => state.farm);
  const user = useAuthStore((state) => state.user);

  return (
    <AppShell
      userName={user?.name}
      pageTitle={t("simulator.pageTitle", "What-If Simulator")}
      pageSubtitle={t("simulator.pageSubtitle", "Scenario planning · stress and yield risk projections")}
      showBack={{ href: "/", label: t("common.dashboard", "Dashboard") }}
    >
      <SimulatorDashboard farmId={farm?.farm_id} cropType={farm?.crop_type} />
    </AppShell>
  );
}

export default function SimulatorPage() {
  return (
    <AuthGuard requireOnboarding>
      <SimulatorContent />
    </AuthGuard>
  );
}
