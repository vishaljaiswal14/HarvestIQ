"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { AuthBrandLayout } from "@/components/layout/AuthBrandLayout";
import { FarmSetupFlow } from "@/components/onboarding/FarmSetupFlow";
import { useTranslation } from "@/stores/localizationStore";

function FarmSetupPageContent() {
  const { t } = useTranslation();

  return (
    <AuthBrandLayout
      title={t("farmSetup.title", "Farm Database Setup")}
      description={t("farmSetup.desc", "Establish your agricultural database by adding your first farm, plot, and crop cycle.")}
    >
      <FarmSetupFlow />
    </AuthBrandLayout>
  );
}

export default function FarmSetupPage() {
  return (
    <AuthGuard requireOnboarding>
      <FarmSetupPageContent />
    </AuthGuard>
  );
}
