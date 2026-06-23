"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useInputWindow } from "@/hooks/useInputWindow";
import { useTranslation } from "@/stores/localizationStore";

const ACTIONS = ["SPRAY", "IRRIGATE", "FERTILIZE"] as const;

type InputWindowCardProps = {
  farmId?: string | null;
};

export function InputWindowCard({ farmId }: InputWindowCardProps) {
  const { t } = useTranslation();
  const [selectedAction, setSelectedAction] = useState<(typeof ACTIONS)[number]>("SPRAY");
  const mutation = useInputWindow(farmId);

  useEffect(() => {
    if (!farmId) return;
    mutation.mutate(selectedAction);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farmId, selectedAction]);

  if (!farmId) return null;

  const result = mutation.data;

  const getActionLabel = (act: string) => {
    if (act === "SPRAY") return t("input_optimizer.action.spray", "SPRAY");
    if (act === "IRRIGATE") return t("input_optimizer.action.irrigate", "IRRIGATE");
    return t("input_optimizer.action.fertilize", "FERTILIZE");
  };

  return (
    <Card className="dashboard-card">
      <CardHeader>
        <p className="dashboard-section-title mb-1">{t("input_optimizer.fieldOperations", "Field Operations")}</p>
        <CardTitle className="text-base font-bold text-slate-800">{t("errorBoundary.title.inputRecommendations", "Input Recommendations")}</CardTitle>
        <CardDescription>{t("input_optimizer.ruleSafety", "Rule-based safety for field inputs")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {ACTIONS.map((action) => (
            <Button
              key={action}
              size="sm"
              variant={selectedAction === action ? "default" : "outline"}
              onClick={() => setSelectedAction(action)}
            >
              {getActionLabel(action)}
            </Button>
          ))}
        </div>
        {mutation.isPending && <p className="text-sm text-emerald-700">{t("input_optimizer.evaluating", "Evaluating window...")}</p>}
        {mutation.error && (
          <p className="text-sm text-red-600">
            {mutation.error instanceof Error ? mutation.error.message : t("input_optimizer.failed", "Evaluation failed")}
          </p>
        )}
        {result && (
          <div
            className={`rounded-lg border p-3 ${
              result.safe
                ? "border-emerald-200 bg-emerald-50"
                : "border-red-200 bg-red-50"
            }`}
          >
            <p className="font-semibold">
              {getActionLabel(result.action_type)}: {result.safe ? t("input_optimizer.safe", "SAFE") : t("input_optimizer.unsafe", "UNSAFE")}
            </p>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {result.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
