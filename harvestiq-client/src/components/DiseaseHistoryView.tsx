"use client";

import { useEffect, useState } from "react";
import { api, type DiseaseDetectResult } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ClipboardList, AlertTriangle, Calendar, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type DiseaseHistoryViewProps = {
  farmId: string;
};

export function DiseaseHistoryView({ farmId }: DiseaseHistoryViewProps) {
  const { t } = useTranslation();
  const [reports, setReports] = useState<DiseaseDetectResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(5);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<DiseaseDetectResult | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getDiseaseHistory(page, limit, farmId);
      setReports(res.reports);
      setTotal(res.total);
    } catch (err) {
      console.error("Failed to load disease history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [farmId, page]);

  // Status Badge styling helper
  const getStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s.includes("CONFIRMED")) {
      return <Badge className="bg-red-500 hover:bg-red-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full">{t("status.highRisk", "High Risk")}</Badge>;
    }
    if (s.includes("POSSIBLE")) {
      return <Badge className="bg-amber-500 hover:bg-amber-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full">{t("status.needsAttention", "Needs Attention")}</Badge>;
    }
    if (s.includes("HEALTHY")) {
      return <Badge className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full">{t("status.healthy", "Healthy")}</Badge>;
    }
    if (s.includes("LOW_CONFIDENCE")) {
      return <Badge className="bg-slate-500 hover:bg-slate-600 text-white font-bold text-[10px] px-2 py-0.5 rounded-full">{t("status.needsReview", "Needs Review")}</Badge>;
    }
    return <Badge className="bg-slate-400 hover:bg-slate-500 text-white font-bold text-[10px] px-2 py-0.5 rounded-full">{t("status.needsReview", "Needs Review")}</Badge>;
  };

  // Severity/Risk styling helper
  const getSeverityBadge = (severity?: string) => {
    if (!severity || severity.toUpperCase() === "NONE") return null;
    const sev = severity.toUpperCase();
    if (sev === "HIGH" || sev === "CRITICAL") {
      return <span className="text-[10px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-md border border-red-100">{t("status.highRisk", "High Risk")}</span>;
    }
    if (sev === "MEDIUM" || sev === "MODERATE") {
      return <span className="text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-100">{t("status.moderateRisk", "Moderate Risk")}</span>;
    }
    return <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">{t("status.healthy", "Healthy")}</span>;
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <Card className="dashboard-card border border-slate-100 bg-white/95 shadow-sm backdrop-blur-md">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5 text-emerald-600" />
          <div>
            <CardTitle className="text-base font-bold text-slate-800">{t("disease.historyTitle", "Disease Scan History")}</CardTitle>
            <CardDescription className="text-xs text-slate-400 mt-0.5">{t("disease.historyDesc", "Review recent crop scan results and recommended next steps")}</CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="space-y-2 py-4 animate-pulse">
            <div className="h-10 bg-slate-50 rounded-xl" />
            <div className="h-10 bg-slate-50 rounded-xl" />
            <div className="h-10 bg-slate-50 rounded-xl" />
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-10 rounded-xl border border-dashed border-slate-100 bg-slate-50/50">
            <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700">{t("disease.noScans", "No disease incidents detected")}</p>
            <p className="text-[10px] text-slate-500 mt-1 max-w-[240px] mx-auto leading-normal">{t("disease.noScansDesc", "Your crop appears healthy based on recent monitoring. Scan a leaf anytime symptoms appear.")}</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="overflow-x-auto rounded-xl border border-slate-100">
              <table className="min-w-full divide-y divide-slate-100 text-left text-xs">
                <thead className="bg-slate-55/60 text-slate-500 font-bold uppercase tracking-wider text-[9px]">
                  <tr>
                    <th className="px-4 py-3">{t("disease.historyTable.date", "Date")}</th>
                    <th className="px-4 py-3">{t("disease.historyTable.disease", "Disease")}</th>
                    <th className="px-4 py-3 text-center">{t("disease.historyTable.status", "Status")}</th>
                    <th className="px-4 py-3 text-center">{t("disease.historyTable.severity", "Severity")}</th>
                    <th className="px-4 py-3 text-right">{t("disease.historyTable.action", "Action")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 bg-white">
                  {reports.map((report) => {
                    const dateStr = report.created_at
                      ? new Date(report.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                      : "N/A";
                    return (
                      <tr key={report.report_id} className="hover:bg-slate-50/50 transition-colors duration-150">
                        <td className="px-4 py-3.5 whitespace-nowrap text-slate-650 font-medium">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5 text-slate-400" />
                            {dateStr}
                          </div>
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap font-bold text-slate-800">
                          {t(report.disease_name || report.disease, report.disease_name || report.disease)}
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap text-center">
                          {getStatusBadge(report.deterministic_status)}
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap text-center">
                          {getSeverityBadge(report.severity) || <span className="text-slate-400 font-medium">-</span>}
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap text-right">
                          <Button
                            onClick={() => setSelectedReport(report)}
                            variant="ghost"
                            className="h-7 text-[10px] font-bold text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 px-2 py-0.5 rounded-lg border border-emerald-100"
                          >
                            {t("disease.viewDetails", "Details")}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-100 pt-3">
                <span className="text-[10px] font-semibold text-slate-400">
                  {t("disease.pageTracker", "Page {page} of {total}").replace("{page}", String(page)).replace("{total}", String(totalPages))}
                </span>
                <div className="flex gap-2">
                  <Button
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                    variant="outline"
                    className="h-7 text-[10px] px-2.5 rounded-lg border-slate-200 text-slate-650"
                  >
                    {t("common.prev", "Prev")}
                  </Button>
                  <Button
                    disabled={page === totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    variant="outline"
                    className="h-7 text-[10px] px-2.5 rounded-lg border-slate-200 text-slate-650"
                  >
                    {t("common.next", "Next")}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>

      {/* Detailed Diagnostics Modal Overlay */}
      {selectedReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
          {/* Backdrop blur overlay */}
          <div 
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" 
            onClick={() => setSelectedReport(null)} 
          />

          {/* Modal Card Content */}
          <div className="relative bg-white rounded-2xl border border-emerald-100 shadow-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto z-10 p-6 space-y-4">
            
            {/* Header */}
            <div className="pb-3 border-b border-slate-100 flex items-start justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
                <div>
                  <h3 className="text-base font-bold text-slate-800">
                    {t("disease.dialogTitle", "Crop Doctor Scan Details")}
                  </h3>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {selectedReport.created_at ? new Date(selectedReport.created_at).toLocaleString() : ""}
                  </p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedReport(null)}
                className="text-slate-400 hover:text-slate-600 font-bold text-xs leading-none bg-slate-100 hover:bg-slate-200 h-6 w-6 flex items-center justify-center rounded-full"
              >
                ✕
              </button>
            </div>

            {/* Body contents */}
            <div className="space-y-4 mt-3">
              {/* Image and Status summary */}
              <div className="grid gap-3 sm:grid-cols-2">
                {/* Visual */}
                <div className="relative rounded-xl border border-slate-100 overflow-hidden bg-slate-50 aspect-video flex items-center justify-center">
                  {selectedReport.report_id && (
                    <img
                      src={`/api/v1/disease/history/${selectedReport.report_id}/image`}
                      alt="Crop Scan"
                      className="object-cover w-full h-full"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  )}
                  <div className="absolute bottom-2 left-2">
                    {getStatusBadge(selectedReport.deterministic_status)}
                  </div>
                </div>

                {/* Quick details */}
                <div className="flex flex-col justify-between p-3 rounded-xl bg-slate-50/50 border border-slate-100">
                  <div className="space-y-1">
                    <p className="text-[9px] uppercase font-bold text-slate-400">{t("disease.cropLabel", "Crop Type")}</p>
                    <p className="text-xs font-extrabold text-slate-850">{t("crop." + selectedReport.crop_type.toLowerCase(), selectedReport.crop_type)}</p>
                  </div>
                  <div className="space-y-1 mt-2">
                    <p className="text-[9px] uppercase font-bold text-slate-400">{t("disease.diseaseLabel", "Diagnosis")}</p>
                    <p className="text-xs font-extrabold text-slate-850">{t(selectedReport.disease_name || selectedReport.disease, selectedReport.disease_name || selectedReport.disease)}</p>
                  </div>
                  <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-100">
                    <div className="space-y-0.5">
                      <p className="text-[8px] uppercase font-bold text-slate-400">{t("disease.severity", "Severity")}</p>
                      {getSeverityBadge(selectedReport.severity) || <span className="text-[10px] text-slate-550 font-semibold">{t("common.low", "Low")}</span>}
                    </div>
                    <div className="space-y-0.5 ml-auto text-right">
                      <p className="text-[8px] uppercase font-bold text-slate-400">{t("disease.riskLevel", "Risk")}</p>
                      <span className="text-[10px] font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">{t(selectedReport.risk_level || "Low", selectedReport.risk_level || "Low")}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Farmer-facing scan explanation */}
              <div className="rounded-xl border border-slate-100 bg-slate-50/30 p-3.5 space-y-3">
                <h4 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                  <Info className="h-4 w-4 text-emerald-600" />
                  {t("disease.explainabilityHeader", "Why this matters")}
                </h4>

                <p className="text-[11px] text-slate-600 bg-white p-2.5 rounded-lg border border-slate-100 leading-relaxed">
                  {selectedReport.explanation.summary}
                </p>
              </div>

              {/* Actionable guidance sections */}
              {selectedReport.deterministic_status !== "HEALTHY" && selectedReport.deterministic_status !== "UNKNOWN" && (
                <div className="space-y-3">
                  {/* What it means */}
                  {selectedReport.what_it_means && (
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-slate-800">{t("disease.whatItMeans", "What it means")}</h4>
                      <p className="text-[11px] text-slate-650 leading-relaxed bg-slate-55 p-2 rounded-lg border border-slate-100">{selectedReport.what_it_means}</p>
                    </div>
                  )}

                  {/* Immediate actions */}
                  {selectedReport.immediate_actions && selectedReport.immediate_actions.length > 0 && (
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-slate-800">{t("disease.actions", "Immediate Actions")}</h4>
                      <ul className="list-decimal list-inside space-y-1 pl-1">
                        {selectedReport.immediate_actions.map((act, idx) => (
                          <li key={idx} className="text-[11px] text-slate-650 leading-normal">{act}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Recommended treatment */}
                  {selectedReport.recommended_treatment && (
                    <div className="rounded-xl border border-red-100 bg-red-50/50 p-3">
                      <h4 className="text-xs font-bold text-red-800 mb-1">{t("disease.treatment", "Recommended Treatment")}</h4>
                      <p className="text-[11px] font-semibold text-red-700 leading-normal">{selectedReport.recommended_treatment}</p>
                    </div>
                  )}

                  {/* Prevention advice */}
                  {selectedReport.prevention_advice && selectedReport.prevention_advice.length > 0 && (
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-slate-800">{t("disease.prevention", "Prevention Advice")}</h4>
                      <ul className="list-disc list-inside space-y-1 pl-1">
                        {selectedReport.prevention_advice.map((prev, idx) => (
                          <li key={idx} className="text-[11px] text-slate-650 leading-normal">{prev}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
