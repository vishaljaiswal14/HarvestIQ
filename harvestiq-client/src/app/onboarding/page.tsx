"use client";

import { AuthGuard } from "@/components/AuthGuard";
import { AuthBrandLayout } from "@/components/layout/AuthBrandLayout";
import { OnboardingForm } from "@/components/onboarding/OnboardingForm";
import { Card, CardContent } from "@/components/ui/card";
import { useTranslation } from "@/stores/localizationStore";

function OnboardingPageContent() {
  const { t } = useTranslation();

  return (
    <AuthBrandLayout
      title={t("onboarding.title", "Farmer onboarding")}
      description={t("onboarding.desc", "Tell us about your farm. State and district are required. GeoJSON boundary can be added later.")}
    >
      <Card className="dashboard-card w-full border-emerald-100/80 shadow-md">
        <CardContent className="pt-6">
          <OnboardingForm />
        </CardContent>
      </Card>
    </AuthBrandLayout>
  );
}

export default function OnboardingPage() {
  return (
    <AuthGuard allowIncompleteOnboarding>
      <OnboardingPageContent />
    </AuthGuard>
  );
}
