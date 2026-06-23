"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type AdvisoryActionsResponse } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, CheckCircle2, ArrowRight, ShieldAlert, Clock, Sparkles, Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

type TodayTopActionWidgetProps = {
  farmId: string;
};

export function TodayTopActionWidget({ farmId }: TodayTopActionWidgetProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<AdvisoryActionsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const [sosDispatching, setSosDispatching] = useState(false);
  const [sosSuccess, setSosSuccess] = useState(false);
  const [sosError, setSosError] = useState<string | null>(null);

  const handleOneClickSos = async () => {
    setSosDispatching(true);
    setSosSuccess(false);
    setSosError(null);
    try {
      await api.triggerSos({
        farm_id: farmId,
        emergency_type: "GENERAL"
      });
      setSosSuccess(true);
      const res = await api.getAdvisoryActions(farmId);
      setData(res);
    } catch (err) {
      setSosError(err instanceof Error ? err.message : "Dispatch failed");
    } finally {
      setSosDispatching(false);
    }
  };

  useEffect(() => {
    const fetchActions = async () => {
      setLoading(true);
      try {
        const res = await api.getAdvisoryActions(farmId);
        setData(res);
      } catch (err) {
        console.error("Failed to load today top action widget", err);
      } finally {
        setLoading(false);
      }
    };
    fetchActions();
  }, [farmId]);

  if (loading) {
    return (
      <div className="h-24 bg-slate-55 animate-pulse rounded-2xl border border-slate-100" />
    );
  }

  if (!data) return null;

  const isEmergency = data.priority === "EMERGENCY";
  const isHigh = data.priority === "HIGH";
  const isMedium = data.priority === "MEDIUM";
  const topAction = data.today_actions[0] || data.this_week_actions[0];

  if (!topAction) return null;

  return (
    <Card className={cn(
      "relative border overflow-hidden rounded-2xl shadow-sm transition-all duration-200 hover:shadow-md",
      isEmergency || isHigh ? "border-red-200 bg-red-50/40" :
      isMedium ? "border-amber-200 bg-amber-50/40" :
      "border-emerald-100 bg-emerald-50/20"
    )}>
      {/* Decorative gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-white/10 pointer-events-none" />

      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            {/* Styled status icon indicator */}
            <div className={cn(
              "p-2.5 rounded-xl border shrink-0 mt-0.5 shadow-sm animate-pulse",
              isHigh ? "bg-red-100 border-red-200 text-red-650" :
              isMedium ? "bg-amber-100 border-amber-200 text-amber-600" :
              "bg-emerald-100 border-emerald-200 text-emerald-600 animate-none"
            )}>
              {isHigh ? <ShieldAlert className="h-5 w-5" /> :
               isMedium ? <AlertTriangle className="h-5 w-5" /> :
               <CheckCircle2 className="h-5 w-5" />}
            </div>

            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[9px] uppercase font-extrabold tracking-wider text-slate-400">
                  {t("dashboard.topAction", "Today's Top Action")}
                </span>
                <Badge className={cn(
                  "font-bold text-[9px] px-2 py-0.5 rounded-full uppercase tracking-wide border leading-none",
                  isHigh ? "bg-red-50 border-red-200 text-red-700 hover:bg-red-50" :
                  isMedium ? "bg-amber-50 border-amber-200 text-amber-700 hover:bg-amber-50" :
                  "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                )}>
                  {t(data.priority, data.priority)} {t("common.risk", "Risk")}
                </Badge>
              </div>

              <h4 className="text-sm font-extrabold text-slate-800 leading-tight">
                {topAction.problem}
              </h4>
              
              <div className="flex items-center gap-2 text-[11px] font-bold text-slate-600 leading-normal flex-wrap">
                <span className={cn(
                  "flex items-center gap-1 font-semibold",
                  isHigh ? "text-red-700" : isMedium ? "text-amber-700" : "text-emerald-700"
                )}>
                  <Sparkles className="h-3.5 w-3.5" />
                  {topAction.action}
                </span>
                {topAction.deadline && (
                  <>
                    <span className="text-slate-300 select-none">·</span>
                    <span className="flex items-center gap-1 text-slate-400 font-medium">
                      <Clock className="h-3 w-3" />
                      {topAction.deadline}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          {topAction.is_sos ? (
            <div className="shrink-0 w-full sm:w-auto flex flex-col gap-1">
              <Button
                disabled={sosDispatching || sosSuccess}
                onClick={handleOneClickSos}
                className="w-full h-9 rounded-xl text-xs font-bold gap-1.5 flex items-center justify-center border hover:shadow-sm transition-all select-none px-4 bg-red-600 hover:bg-red-700 text-white border-red-500"
              >
                {sosDispatching ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                    <span>{t("sos.sending", "Sending...")}</span>
                  </>
                ) : sosSuccess ? (
                  <>
                    <Check className="h-3.5 w-3.5 shrink-0" />
                    <span>Dispatched!</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-3.5 w-3.5 animate-pulse shrink-0 text-white" />
                    <span>{t("sos.oneClickDispatch", "One-click Dispatch SOS")}</span>
                  </>
                )}
              </Button>
              {sosError && (
                <p className="text-[10px] text-red-650 font-bold mt-1 text-center">{sosError}</p>
              )}
            </div>
          ) : (
            <Link href="/advisory" className="shrink-0 w-full sm:w-auto">
              <Button className={cn(
                "w-full h-9 rounded-xl text-xs font-bold gap-1.5 flex items-center justify-center border hover:shadow-sm transition-all select-none px-4",
                isHigh ? "bg-red-600 hover:bg-red-700 text-white border-red-500" :
                isMedium ? "bg-amber-600 hover:bg-amber-700 text-white border-amber-500" :
                "bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-500"
              )}>
                {t("dashboard.viewActionCenter", "Action Center")}
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
