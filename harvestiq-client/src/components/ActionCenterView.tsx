"use client";

import { useEffect, useState } from "react";
import { api, type CopilotAction, type CopilotPlan } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  ShieldAlert, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Info, 
  Sparkles, 
  Heart, 
  XOctagon,
  Calendar,
  AlertCircle,
  Loader2,
  Check
} from "lucide-react";
import { cn } from "@/lib/utils";

type ActionCenterViewProps = {
  farmId: string;
  language: string;
};

export function ActionCenterView({ farmId, language }: ActionCenterViewProps) {
  const { t } = useTranslation();
  const [data, setData] = useState<CopilotPlan | null>(null);
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
      // reload actions
      const res = await api.getCopilotPlan(farmId);
      setData(res);
    } catch (err) {
      setSosError(err instanceof Error ? err.message : t("sos.dispatchFailed", "Dispatch failed"));
    } finally {
      setSosDispatching(false);
    }
  };

  useEffect(() => {
    const fetchActions = async () => {
      setLoading(true);
      try {
        const res = await api.getCopilotPlan(farmId);
        setData(res);
      } catch (err) {
        console.error("Failed to load Action Center actions", err);
      } finally {
        setLoading(false);
      }
    };
    fetchActions();
  }, [farmId, language]);

  if (loading) {
    return (
      <div className="space-y-4 py-6 animate-pulse">
        <div className="h-28 bg-slate-55 rounded-2xl border border-slate-100" />
        <div className="grid gap-4 md:grid-cols-2">
          <div className="h-36 bg-slate-55 rounded-2xl border border-slate-100" />
          <div className="h-36 bg-slate-55 rounded-2xl border border-slate-100" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-10 bg-slate-50/50 rounded-2xl border border-dashed border-slate-150">
        <Info className="h-8 w-8 text-slate-350 mx-auto mb-2" />
        <p className="text-xs font-semibold text-slate-500">{t("actionCenter.noData", "No action items available.")}</p>
      </div>
    );
  }

  const isEmergency = data.priority === "EMERGENCY";
  const isHigh = data.priority === "HIGH" || isEmergency;
  const isMedium = data.priority === "MEDIUM";
  const isLow = data.priority === "LOW";

  const renderCard = (card: CopilotAction, index: number) => {
    const isRed = card.card_type === "RED";
    const isYellow = card.card_type === "YELLOW";
    
    return (
      <div 
        key={`${card.card_type}-${index}`}
        className={cn(
          "relative p-4 rounded-xl border flex flex-col justify-between transition-all hover:shadow-md",
          isRed ? "border-red-200 bg-red-50/20" :
          isYellow ? "border-amber-200 bg-amber-50/20" :
          "border-emerald-100 bg-emerald-50/10"
        )}
      >
        <div className="space-y-3">
          {/* Card Badge & Deadline */}
          <div className="flex items-center justify-between gap-2">
            <span className={cn(
              "text-[8px] font-extrabold uppercase px-2 py-0.5 rounded border tracking-wider leading-none",
              isRed ? "bg-red-50 border-red-200 text-red-750" :
              isYellow ? "bg-amber-50 border-amber-200 text-amber-700" :
              "bg-emerald-50 border-emerald-250 text-emerald-750"
            )}>
              {isRed ? t("actionCenter.immediate", "Immediate Action") :
               isYellow ? t("actionCenter.monitor", "Monitor Closely") :
               t("actionCenter.healthy", "Farm Healthy")}
            </span>

            {card.deadline && (
              <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {card.deadline}
              </span>
            )}
          </div>

          {/* Problem Descriptor */}
          <div className="space-y-1">
            <p className="text-[9px] uppercase font-bold text-slate-400 leading-none">
              {t("actionCenter.problem", "Problem / Condition")}
            </p>
            <h5 className="text-xs font-extrabold text-slate-800 leading-tight">
              {card.title}
            </h5>
          </div>

          {/* Action To Take */}
          <div className="space-y-1 bg-white/70 p-2.5 rounded-lg border border-slate-100/50">
            <p className="text-[9px] uppercase font-bold text-slate-400 leading-none">
              {t("actionCenter.action", "Required Action")}
            </p>
            <p className={cn(
              "text-xs font-bold flex items-start gap-1 leading-snug",
              isRed ? "text-red-750" : isYellow ? "text-amber-800" : "text-emerald-800"
            )}>
              <Sparkles className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              {card.action}
            </p>
          </div>

          <div className="space-y-1.5 text-[10px] text-slate-600 bg-slate-50/80 p-2 rounded-lg border border-slate-100">
            <p><span className="font-bold text-slate-700">{t("copilot.why", "Why")}:</span> {card.why}</p>
            <p><span className="font-bold text-slate-700">{t("copilot.ifIgnored", "If ignored")}:</span> {card.if_ignored}</p>
            <p><span className="font-bold text-slate-700">{t("copilot.expectedBenefit", "Expected benefit")}:</span> {card.expected_benefit}</p>
          </div>
        </div>

        {/* Expected Impact */}
        <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center gap-1.5 text-[10px] text-slate-500">
          <span className="font-bold text-slate-400 uppercase tracking-wider text-[8px]">
            {t("actionCenter.impact", "Expected Impact")}:
          </span>
          <span className="font-semibold text-slate-650 truncate">
            {card.expected_impact}
          </span>
        </div>

        {card.is_sos && (
          <div className="mt-3 pt-2.5 border-t border-slate-100">
            <Button
              size="sm"
              disabled={sosDispatching || sosSuccess}
              onClick={() => handleOneClickSos()}
              className="w-full bg-red-600 hover:bg-red-700 text-white font-bold text-xs gap-1.5 h-9 rounded-lg flex items-center justify-center cursor-pointer"
            >
              {sosDispatching ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                  <span>{t("sos.sending", "Sending...")}</span>
                </>
              ) : sosSuccess ? (
                <>
                  <Check className="h-3.5 w-3.5 shrink-0" />
                  <span>{t("sos.dispatched", "Dispatched!")}</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3.5 w-3.5 animate-pulse shrink-0 text-white" />
                  <span>{t("sos.oneClickDispatch", "One-click Dispatch SOS")}</span>
                </>
              )}
            </Button>
            {sosError && (
              <p className="text-[10px] text-red-650 font-bold mt-1 text-center">
                {sosError === "Dispatch failed" ? t("sos.dispatchFailed", "Dispatch failed") : sosError}
              </p>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* 1. Situation Summary Box */}
      <Card className={cn(
        "border overflow-hidden rounded-2xl shadow-sm",
        isHigh ? "border-red-200/60 bg-red-50/10" :
        isMedium ? "border-amber-200/60 bg-amber-50/10" :
        "border-emerald-100 bg-emerald-50/10"
      )}>
        <div className="h-1 bg-gradient-to-r from-blue-500 via-emerald-500 to-indigo-600" />
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">
              {t("actionCenter.status", "Situation Overview")}
            </span>
            <Badge className={cn(
              "font-extrabold text-[9px] px-2 py-0.5 rounded-full border tracking-wider",
              isHigh ? "bg-red-50 border-red-200 text-red-650" :
              isMedium ? "bg-amber-50 border-amber-200 text-amber-700" :
              "bg-emerald-50 border-emerald-200 text-emerald-700"
            )}>
              {isHigh ? t("actionCenter.priority.high", "HIGH PRIORITY") :
               isMedium ? t("actionCenter.priority.medium", "MEDIUM PRIORITY") :
               t("actionCenter.priority.low", "NORMAL PRIORITY")}
            </Badge>
          </div>
          <CardTitle className="text-sm font-extrabold text-slate-800 leading-snug mt-1.5">
            {data.situation_summary}
          </CardTitle>
        </CardHeader>
      </Card>

      {/* 2. Today's Actions (RED Priority) */}
      {data.today_actions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="h-4 w-4 text-red-600 animate-pulse" />
            {t("actionCenter.todayTitle", "Today's Immediate Actions")}
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.today_actions.map((card, idx) => renderCard(card, idx))}
          </div>
        </div>
      )}

      {/* 3. This Week's Actions (YELLOW/GREEN Priority) */}
      {data.this_week_actions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Calendar className="h-4 w-4 text-amber-500" />
            {t("actionCenter.weekTitle", "Scheduled Weekly Recommendations")}
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.this_week_actions.map((card, idx) => renderCard(card, idx))}
          </div>
        </div>
      )}

      {/* 4. Risk reduction impact */}
      {data.risk_reduction_impact && (
        <Card className="border-amber-200 bg-amber-50/30 rounded-xl">
          <CardContent className="p-3.5 flex items-start gap-2.5">
            <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 shrink-0" />
            <div className="space-y-1">
              <span className="text-[8px] font-extrabold uppercase text-amber-800 tracking-wider">
                {t("copilot.lossPrevention", "Potential Loss Prevention")}
              </span>
              <p className="text-xs font-semibold text-amber-900 leading-snug">
                {data.risk_reduction_impact}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* preventive actions */}
      {data.preventive_actions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-extrabold text-slate-400 uppercase tracking-wider">
            {t("copilot.preventive", "Preventive Actions")}
          </h4>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.preventive_actions.map((card, idx) => renderCard(card, idx))}
          </div>
        </div>
      )}

      {/* Explainability triggers */}
      <Card className="border-slate-100 bg-slate-50/50 rounded-xl">
        <CardContent className="p-4 space-y-2">
          <h4 className="text-xs font-extrabold text-slate-800 flex items-center gap-1.5">
            <Info className="h-4 w-4 text-blue-600" />
            {t("actionCenter.whyTitle", "Why was this recommendation generated?")}
          </h4>
          <ul className="grid gap-1.5 sm:grid-cols-2">
            {data.why_generated.map((factor, idx) => (
              <li 
                key={idx}
                className="text-[11px] font-semibold text-slate-650 bg-white border border-slate-100 p-2 rounded-lg flex items-center gap-2"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" />
                {factor}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
