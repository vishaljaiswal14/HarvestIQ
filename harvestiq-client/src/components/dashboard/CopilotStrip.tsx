"use client";

import Link from "next/link";
import { CheckCircle2, ClipboardList, Loader2, Shield, TrendingDown, TrendingUp, Minus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCopilotPlan, useYieldProtection } from "@/hooks/useCopilotPlan";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";
import { useQueryClient } from "@tanstack/react-query";

type CopilotStripProps = {
  farmId: string;
};

export function CopilotStrip({ farmId }: CopilotStripProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: plan, isLoading: planLoading } = useCopilotPlan(farmId);
  const { data: score, isLoading: scoreLoading } = useYieldProtection(farmId);

  const loading = planLoading || scoreLoading;

  if (loading) {
    return <div className="h-28 animate-pulse rounded-2xl bg-slate-100 border border-slate-100" />;
  }

  if (!plan || !score) return null;

  const todayTasks = plan.today_actions.filter((a) => !a.completed);
  const lossBand = score.potential_loss_prevention_band;
  const protectionLabel =
    score.band === "PROTECTED" ? t("farmCondition.stable", "Stable") :
    score.band === "MODERATE" ? t("farmCondition.attention", "Needs Attention") :
    t("farmCondition.highRisk", "High Risk");
  const trendLabel =
    score.trend === "IMPROVING" ? t("dashboard.improving", "Improving") :
    score.trend === "DECLINING" ? t("dashboard.worsening", "Needs Attention") :
    t("dashboard.stable", "Stable");
  const severityLabel =
    plan.severity_tier === "HIGH" ? t("status.highRisk", "High Risk") :
    plan.severity_tier === "MEDIUM" ? t("status.moderateRisk", "Moderate Risk") :
    t("status.healthy", "Healthy");
  const lossLabel =
    lossBand === "HIGH" ? t("status.highRisk", "High Risk") :
    lossBand === "MODERATE" ? t("status.moderateRisk", "Moderate Risk") :
    t("status.healthy", "Healthy");

  const handleComplete = async (actionId: string) => {
    await api.completeCopilotAction(farmId, actionId, plan.plan_id);
    void queryClient.invalidateQueries({ queryKey: ["copilot-plan", farmId] });
    void queryClient.invalidateQueries({ queryKey: ["yield-protection", farmId] });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="dashboard-section-title">{t("copilot.title", "Farm Operations Copilot")}</p>
        <Link href="/advisory" className="text-xs font-bold text-emerald-700 hover:underline">
          {t("copilot.viewFullPlan", "View full plan →")}
        </Link>
      </div>

      <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {/* Yield Protection */}
        <Card className="dashboard-card border-emerald-100/60">
          <CardHeader className="compact-card-header pb-1">
            <CardDescription className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
              {t("copilot.yieldProtection", "Yield Protection")}
            </CardDescription>
            <CardTitle className="text-sm font-bold text-slate-800">
              {protectionLabel}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-center justify-between px-4 pb-3">
            <div>
              <span className={cn(
                "text-xs font-bold",
                score.band === "PROTECTED" ? "text-emerald-600" :
                score.band === "MODERATE" ? "text-amber-600" : "text-red-600"
              )}>
                {protectionLabel}
              </span>
              <p className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
                {score.trend === "IMPROVING" ? <TrendingUp className="h-3 w-3 text-emerald-600" /> :
                 score.trend === "DECLINING" ? <TrendingDown className="h-3 w-3 text-red-500" /> :
                 <Minus className="h-3 w-3 text-slate-400" />}
                {trendLabel}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Top Farm Risk */}
        <Card className="dashboard-card">
          <CardHeader className="compact-card-header pb-1">
            <CardDescription className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
              {t("copilot.topRisk", "Top Farm Risk")}
            </CardDescription>
            <CardTitle className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
              <Shield className="h-4 w-4 text-amber-500" />
              {severityLabel}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <p className="text-xs text-slate-700 font-medium leading-snug">{score.top_risk}</p>
          </CardContent>
        </Card>

        {/* Risk Reduction Impact */}
        <Card className="dashboard-card">
          <CardHeader className="compact-card-header pb-1">
            <CardDescription className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
              {t("copilot.lossPrevention", "Potential Loss Prevention")}
            </CardDescription>
            <CardTitle className={cn(
              "text-sm font-bold",
              lossBand === "HIGH" ? "text-red-600" : lossBand === "MODERATE" ? "text-amber-600" : "text-emerald-600"
            )}>
              {lossLabel}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <p className="text-[10px] text-slate-600 leading-relaxed">{score.risk_reduction_impact}</p>
          </CardContent>
        </Card>

        {/* Today's Tasks */}
        <Card className="dashboard-card">
          <CardHeader className="compact-card-header pb-1">
            <CardDescription className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
              {t("copilot.todaysTasks", "Today's Tasks")}
            </CardDescription>
            <CardTitle className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
              <ClipboardList className="h-4 w-4 text-slate-500" />
              {todayTasks.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 space-y-2">
            {todayTasks.length === 0 ? (
              <p className="text-[10px] text-emerald-700 font-semibold">{t("copilot.noUrgentTasks", "No urgent tasks today")}</p>
            ) : (
              todayTasks.slice(0, 2).map((task) => (
                <div key={task.id} className="text-[10px] border border-slate-100 rounded-lg p-2 bg-slate-50/80">
                  <p className="font-bold text-slate-800 truncate">{task.title}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-1.5 h-6 text-[9px] w-full"
                    onClick={() => void handleComplete(task.id)}
                  >
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    {t("copilot.markDone", "Mark done")}
                  </Button>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
