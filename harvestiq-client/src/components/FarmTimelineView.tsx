"use client";

import { useEffect, useState } from "react";
import { api, type TimelineEvent } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, ShieldAlert, Microscope, Calendar, AlertTriangle, Droplets, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type FarmTimelineViewProps = {
  farmId: string;
};

export function FarmTimelineView({ farmId }: FarmTimelineViewProps) {
  const { t } = useTranslation();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTimeline = async () => {
    setLoading(true);
    try {
      const res = await api.getFarmTimeline(farmId, 25);
      setEvents(res.events);
    } catch (err) {
      console.error("Failed to load farm health timeline", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
  }, [farmId]);

  // Color helper for timeline events based on severity/risk
  const getEventColors = (event: TimelineEvent) => {
    const type = event.type;
    const severity = (event.severity || "").toUpperCase();

    if (type === "Disease Alert" || type === "SOS Alert" || severity === "HIGH" || severity === "CRITICAL" || severity === "EMERGENCY" || severity === "AT_RISK") {
      return {
        bg: "bg-red-50 border-red-150",
        border: "border-red-500",
        dot: "bg-red-500",
        text: "text-red-800",
        iconText: "text-red-500",
        badge: "bg-red-100 text-red-800 border-red-200",
      };
    }
    if (type === "Weather Alert" || type === "Yield Protection Alert" || type === "Crop Stress Alert" || severity === "MEDIUM" || severity === "MODERATE" || severity === "WARNING") {
      return {
        bg: "bg-amber-50/70 border-amber-100",
        border: "border-amber-500",
        dot: "bg-amber-500",
        text: "text-amber-800",
        iconText: "text-amber-500",
        badge: "bg-amber-100 text-amber-800 border-amber-200",
      };
    }
    return {
      bg: "bg-emerald-50/50 border-emerald-100",
      border: "border-emerald-500",
      dot: "bg-emerald-500",
      text: "text-emerald-800",
      iconText: "text-emerald-500",
      badge: "bg-emerald-100 text-emerald-800 border-emerald-200",
    };
  };

  // Icon helper
  const getEventIcon = (type: string, iconTextClass: string) => {
    if (type === "Disease Alert" || type === "Scan Result") {
      return <Microscope className={cn("h-4 w-4", iconTextClass)} />;
    }
    if (type === "Yield Protection Alert" || type === "SOS Alert") {
      return <ShieldAlert className={cn("h-4 w-4", iconTextClass)} />;
    }
    if (type === "Advisory Generated") {
      return <Activity className={cn("h-4 w-4", iconTextClass)} />;
    }
    if (type === "Weather Alert") {
      return <AlertTriangle className={cn("h-4 w-4", iconTextClass)} />;
    }
    return <Droplets className={cn("h-4 w-4", iconTextClass)} />;
  };

  return (
    <Card className="dashboard-card border border-slate-100 bg-white/95 shadow-sm backdrop-blur-md">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-emerald-600" />
          <div>
            <CardTitle className="text-base font-bold text-slate-800">{t("timeline.title", "Farm Health Timeline")}</CardTitle>
            <CardDescription className="text-xs text-slate-400 mt-0.5">{t("timeline.desc", "A clear timeline of crop scans, alerts, and recommended actions for this farm.")}</CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="px-6 pb-6">
        {loading ? (
          <div className="space-y-4 py-4 animate-pulse">
            <div className="flex gap-4">
              <div className="rounded-full bg-slate-100 h-8 w-8 shrink-0" />
              <div className="flex-grow space-y-1.5 mt-1">
                <div className="h-4 bg-slate-50 rounded w-1/3" />
                <div className="h-3 bg-slate-50 rounded w-2/3" />
              </div>
            </div>
            <div className="flex gap-4">
              <div className="rounded-full bg-slate-100 h-8 w-8 shrink-0" />
              <div className="flex-grow space-y-1.5 mt-1">
                <div className="h-4 bg-slate-50 rounded w-1/4" />
                <div className="h-3 bg-slate-50 rounded w-1/2" />
              </div>
            </div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-10 rounded-xl border border-dashed border-slate-100 bg-slate-50/50">
            <Info className="h-8 w-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-500">{t("timeline.empty", "No timeline records found")}</p>
            <p className="text-[10px] text-slate-400 mt-1 max-w-[220px] mx-auto leading-normal">{t("timeline.emptyDesc", "Run a crop scan or generate a farm advisory to start building the timeline.")}</p>
          </div>
        ) : (
          <div className="relative border-l-2 border-slate-100 pl-6 ml-2.5 space-y-5 py-2">
            {events.map((event, index) => {
              const colors = getEventColors(event);
              const dateStr = event.timestamp
                ? new Date(event.timestamp).toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
                : "N/A";
              return (
                <div key={event.id || index} className="relative group">
                  {/* Timeline bullet dot */}
                  <div className={cn(
                    "absolute -left-[31px] top-1.5 rounded-full border-2 border-white w-4 h-4 shadow-sm transition-transform duration-200 group-hover:scale-125 z-10",
                    colors.dot
                  )} />

                  {/* Timeline block */}
                  <div className={cn(
                    "rounded-xl border p-3.5 transition-all duration-200 hover:shadow-md hover:translate-x-0.5",
                    colors.bg
                  )}>
                    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1.5">
                        <Calendar className="h-3 w-3" />
                        {dateStr}
                      </span>
                      <Badge className={cn("w-fit text-[8px] font-extrabold uppercase px-1.5 py-0.2 rounded border", colors.badge)}>
                        {event.type}
                      </Badge>
                    </div>

                    <div className="flex gap-2.5 mt-2">
                      <div className="rounded-lg p-1.5 bg-white border border-slate-100 shrink-0 h-fit flex items-center justify-center shadow-sm">
                        {getEventIcon(event.type, colors.iconText)}
                      </div>
                      <div className="min-w-0">
                        <h4 className={cn("text-xs font-bold leading-normal", colors.text)}>
                          {event.title}
                        </h4>
                        <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed font-medium">
                          {event.description}
                        </p>
                        {event.action && (
                          <div className="mt-2.5 rounded-lg border border-white/80 bg-white/80 px-2.5 py-2 shadow-sm">
                            <p className="text-[9px] font-extrabold uppercase tracking-[0.12em] text-slate-400">
                              {t("timeline.recommendedAction", "Recommended action")}
                            </p>
                            <p className="mt-1 text-[11px] font-semibold leading-relaxed text-slate-700">
                              {event.action}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
