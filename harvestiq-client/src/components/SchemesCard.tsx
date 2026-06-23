"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSchemes } from "@/hooks/useSchemes";
import { useTranslation } from "@/stores/localizationStore";

type SchemesCardProps = {
  farmId?: string | null;
};

export function SchemesCard({ farmId }: SchemesCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useSchemes(farmId);

  if (!farmId) return null;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("errorBoundary.title.govSchemes", "Government Schemes")}</CardTitle>
          <CardDescription>{t("schemes.checking", "Checking eligible programs...")}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("errorBoundary.title.govSchemes", "Government Schemes")}</CardTitle>
          <CardDescription className="text-red-600">
            {error instanceof Error ? error.message : t("schemes.unableToLoad", "Unable to load schemes")}
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="dashboard-card">
      <CardHeader>
        <p className="dashboard-section-title mb-1">{t("schemes.governmentPrograms", "Government Programs")}</p>
        <CardTitle className="text-base font-bold text-slate-800">{t("errorBoundary.title.govSchemes", "Government Schemes")}</CardTitle>
        <CardDescription>{t("schemes.eligibleCount", "{count} eligible scheme(s)").replace("{count}", String(data.schemes.length))}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {data.schemes.length === 0 ? (
          <p className="text-sm text-slate-600">{t("schemes.noMatching", "No matching schemes for this farm profile.")}</p>
        ) : (
          data.schemes.map((scheme) => (
            <div key={scheme.scheme_id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
              <p className="font-semibold text-slate-900">{scheme.name}</p>
              <p className="mt-0.5 text-sm text-slate-600">{scheme.description}</p>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
