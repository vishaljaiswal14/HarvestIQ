"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useDemoMode } from "@/hooks/useDemoMode";
import { api, type SosTriggerResult, type EmergencyContacts } from "@/lib/api";
import { readOutbox } from "@/lib/db";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/authStore";
import { useHealthCard } from "@/hooks/useHealthCard";
import { useCropStage } from "@/hooks/useCropStage";
import { 
  AlertTriangle, 
  User, 
  MapPin, 
  Activity, 
  HelpCircle, 
  PhoneCall, 
  History, 
  Check, 
  X, 
  Smartphone, 
  Users, 
  Loader2,
  Clock,
  Sparkles
} from "lucide-react";
import { useTranslation } from "@/stores/localizationStore";

type SosButtonProps = {
  farmId?: string | null;
  variant?: "default" | "sidebar" | "quickaction";
};

const EMERGENCY_TYPES = ["GENERAL", "FLOOD", "FROST", "HEATWAVE"] as const;

export function SosButton({ farmId, variant = "default" }: SosButtonProps) {
  const { demoMode } = useDemoMode();
  const { t } = useTranslation();
  const showDisclaimer = demoMode || process.env.NODE_ENV === "development";
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"trigger" | "contacts" | "history">("trigger");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SosTriggerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [coords, setCoords] = useState<{ latitude?: number; longitude?: number } | null>(null);
  const [selectedType, setSelectedType] = useState<typeof EMERGENCY_TYPES[number]>("GENERAL");

  // Contacts State
  const [contacts, setContacts] = useState<EmergencyContacts>({
    primary_contact: "",
    secondary_contact: "",
    village_contact: ""
  });
  const [contactsLoading, setContactsLoading] = useState(false);
  const [contactsSaveSuccess, setContactsSaveSuccess] = useState(false);

  // History State
  const [history, setHistory] = useState<SosTriggerResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const user = useAuthStore((state) => state.user);
  const farm = useAuthStore((state) => state.farm);
  const { data: health } = useHealthCard(farmId);
  const { data: stage } = useCropStage(farm?.crop_cycle_id ?? null);
  const stageLabel = health?.stage ?? stage?.stage ?? "—";

  // Reload contacts and history when modal opens
  useEffect(() => {
    if (open && farmId) {
      void loadContacts();
      void loadHistory();

      // Auto fetch coordinates for preview
      if (typeof navigator !== "undefined" && navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            setCoords({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude
            });
          },
          (err) => {
            console.warn("Pre-fetch geolocation failed:", err);
          },
          { timeout: 5000 }
        );
      }
    }
  }, [open, farmId]);

  // Poll history status from backend while modal is open
  useEffect(() => {
    if (!open || !farmId) return;
    const interval = setInterval(() => {
      void loadHistory(true);
    }, 4000);
    return () => clearInterval(interval);
  }, [open, farmId]);

  // Sync current active result with updated history
  useEffect(() => {
    if (result && history.length > 0) {
      const latest = history.find((item) => item.action_id === result.action_id);
      if (latest) {
        setResult(latest);
      }
    }
  }, [history, result?.action_id]);

  // Dynamic reload when outbox/sync finishes
  useEffect(() => {
    if (!open || !farmId) return;
    const handleUpdate = () => {
      void loadHistory();
    };
    window.addEventListener("outbox-updated", handleUpdate);
    window.addEventListener("sos-sync-success", handleUpdate);
    return () => {
      window.removeEventListener("outbox-updated", handleUpdate);
      window.removeEventListener("sos-sync-success", handleUpdate);
    };
  }, [open, farmId]);

  const loadContacts = async () => {
    setContactsLoading(true);
    try {
      const res = await api.getEmergencyContacts();
      setContacts(res);
    } catch (err) {
      console.error("Failed to load emergency contacts", err);
    } finally {
      setContactsLoading(false);
    }
  };

  const loadHistory = async (silent = false) => {
    if (!silent) setHistoryLoading(true);
    try {
      // 1. Fetch server historical dispatches
      const serverHistory = await api.getSosHistory();
      
      // 2. Scan client IndexedDB outbox for any pending TRIGGER_SOS entries
      const outboxEntries = await readOutbox();
      const pendingSos = outboxEntries
        .filter((entry) => entry.operation_type === "TRIGGER_SOS")
        .map((entry) => {
          const payload = entry.payload as any;
          return {
            action_id: "offline-" + entry.client_id,
            farm_id: payload.farm_id,
            emergency_type: payload.emergency_type || "GENERAL",
            checklist: [
              "National Emergency: 112",
              "Ambulance: 108",
              "Fire: 101",
              "Police: 100 / 112"
            ],
            plain_text_message: "Emergency request queued offline waiting for network connectivity.",
            delivery_status: "QUEUED",
            intelligence_snapshot_version: "N/A",
            triggered_at: entry.client_timestamp,
          } as SosTriggerResult;
        });

      // Merge client outbox queued items at the top
      setHistory([...pendingSos, ...serverHistory]);
    } catch (err) {
      console.error("Failed to load SOS dispatch logs history", err);
    } finally {
      if (!silent) setHistoryLoading(false);
    }
  };

  const handleSaveContacts = async (e: React.FormEvent) => {
    e.preventDefault();
    setContactsSaveSuccess(false);
    try {
      const res = await api.saveEmergencyContacts(contacts);
      setContacts(res);
      setContactsSaveSuccess(true);
      setTimeout(() => setContactsSaveSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save emergency contacts", err);
    }
  };

  if (!farmId) return null;

  const trigger = async (emergencyType: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let latitude: number | undefined;
      let longitude: number | undefined;
      if (!demoMode && typeof navigator !== "undefined" && navigator.geolocation) {
        try {
          const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
          });
          latitude = position.coords.latitude;
          longitude = position.coords.longitude;
          setCoords({ latitude, longitude });
        } catch (gpsErr) {
          console.warn("Geolocation capture failed or timed out:", gpsErr);
        }
      }
      const response = await api.triggerSos({
        farm_id: farmId,
        emergency_type: emergencyType,
        latitude,
        longitude,
      });
      setResult(response);
      void loadHistory(); // refresh log list
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sos.dispatchError", "SOS trigger failed"));
    } finally {
      setLoading(false);
    }
  };

  const getEmergencyTypeLabel = (type: string) => {
    if (type === "GENERAL") return t("sos.type.general", "Moisture Stress");
    if (type === "FLOOD") return t("sos.type.flood", "Flood Risk");
    if (type === "FROST") return t("sos.type.frost", "Frost Risk");
    if (type === "HEATWAVE") return t("sos.type.heatwave", "Heat Stress");
    return t("sos.type.general", "Field Emergency");
  };

  const getPublicRecipientStatus = (status: string, callbackAvailable?: boolean) => {
    if (status === "DELIVERED") return t("sos.status.delivered", "Delivered");
    if (status === "DEMO_SENT") return t("sos.status.sandbox", "Delivered (Sandbox)");
    if (status === "FAILED") return t("sos.status.failed", "Needs Review");
    if (status === "SENT" && callbackAvailable === false) return t("sos.status.awaiting", "Awaiting confirmation");
    return t("sos.status.pending", "Pending");
  };

  const getPublicSosMessage = (message?: string) => {
    if (!message) return t("sos.historySummary", "Emergency dispatch request recorded.");
    if (message === "Emergency request queued offline waiting for network connectivity.") {
      return t("sos.offlineRequestQueued", "Emergency request queued offline and will dispatch when connectivity returns.");
    }
    return message
      .replace(/[A-Z0-9]{20,}/g, "")
      .replace(/\b(?:SID|provider|callback|status code|error code)\b[:\s-]*/gi, "")
      .trim();
  };

  // Helpers for pre-deployment SOS polishing
  const getUnifiedStatusBadge = (status: string) => {
    if (status === "DELIVERED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Check className="h-3.5 w-3.5" />
          <span>Delivered</span>
        </span>
      );
    }
    if (status === "DEMO_SENT") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
          <Sparkles className="h-3.5 w-3.5 animate-pulse" />
          <span>Dispatched (Sandbox)</span>
        </span>
      );
    }
    if (status === "FAILED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
          <X className="h-3.5 w-3.5" />
          <span>Failed</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
        <Clock className="h-3.5 w-3.5 animate-spin" style={{ animationDuration: "3s" }} />
        <span>Awaiting Confirmation</span>
      </span>
    );
  };

  const getActionPreview = (type: string) => {
    const isHi = (user?.preferred_lang ?? "hi").toLowerCase() === "hi";
    if (isHi) {
      if (type === "FLOOD") return "24 घंटे के भीतर खेत से अतिरिक्त पानी निकालें।";
      if (type === "FROST") return "खेत की तुरंत हल्की सिंचाई करें।";
      if (type === "HEATWAVE") return "हल्की सिंचाई या मल्चिंग (mulching) करें।";
      return "24 घंटे के भीतर सिंचाई करें।";
    } else {
      if (type === "FLOOD") return "Drain excess water from the field.";
      if (type === "FROST") return "Irrigate field immediately.";
      if (type === "HEATWAVE") return "Apply light watering or mulching.";
      return "Irrigate field within 24 hours.";
    }
  };

  const getIssuePreview = (type: string) => {
    const isHi = (user?.preferred_lang ?? "hi").toLowerCase() === "hi";
    if (isHi) {
      if (type === "FLOOD") return "खेत में जलभराव की समस्या है।";
      if (type === "FROST") return "पाले का प्रभाव है।";
      if (type === "HEATWAVE") return "अत्यधिक गर्मी (लू) का प्रभाव है।";
      return "नमी की कमी है।";
    } else {
      if (type === "FLOOD") return "Waterlogging detected.";
      if (type === "FROST") return "Frost risk detected.";
      if (type === "HEATWAVE") return "Extreme heat wave detected.";
      return "Moisture stress detected.";
    }
  };

  const getRecipientBadges = () => {
    const list: { role: string; phone: string }[] = [];
    if (user?.phone) list.push({ role: t("sos.recipient.role.farmer", "Farmer"), phone: user.phone });
    if (contacts.primary_contact) list.push({ role: t("sos.recipient.role.primary", "Primary Contact"), phone: contacts.primary_contact });
    if (contacts.secondary_contact) list.push({ role: t("sos.recipient.role.secondary", "Secondary Contact"), phone: contacts.secondary_contact });
    if (contacts.village_contact) list.push({ role: t("sos.recipient.role.village", "Village Representative"), phone: contacts.village_contact });
    return list;
  };

  const renderRecipientsList = (recipients: SosTriggerResult["recipients"], callbackAvailable?: boolean) => {
    if (!recipients || recipients.length === 0) return null;
    return (
      <div className="space-y-1.5">
        <span className="text-[10px] font-extrabold uppercase text-slate-400 tracking-wider block">
          {t("sos.recipientDeliveries", "Recipient Deliveries")}
        </span>
        <div className="flex flex-wrap gap-2">
          {recipients.map((rec, index) => {
            const masked = rec.masked_phone || rec.phone || "";
            const phoneToDisplay = demoMode ? (rec.phone || masked) : masked;
            const roleLabel = rec.role === "farmer" ? t("sos.recipient.role.farmer", "Farmer") :
                              rec.role === "primary" ? t("sos.recipient.role.primary", "Primary Contact") :
                              rec.role === "secondary" ? t("sos.recipient.role.secondary", "Secondary Contact") :
                              rec.role === "village" ? t("sos.recipient.role.village", "Village Representative") :
                              rec.role;

            const statusLabel = getPublicRecipientStatus(rec.status, callbackAvailable);

            return (
              <div 
                key={index} 
                className={cn(
                  "px-3 py-1.5 rounded-xl border flex flex-col gap-1 text-xs transition-colors shrink-0",
                  rec.status === "DELIVERED" ? "bg-emerald-50/50 border-emerald-100/50 text-emerald-700" :
                  rec.status === "DEMO_SENT" ? "bg-blue-50/50 border-blue-100/50 text-blue-750" :
                  rec.status === "FAILED" ? "bg-red-50/40 border-red-200 text-red-700" :
                  rec.status === "SENT" ? "bg-blue-50/40 border-blue-200 text-blue-700" :
                  rec.status === "QUEUED" ? "bg-amber-50/40 border-amber-200 animate-pulse text-amber-700" :
                  "bg-slate-50 border-slate-100 text-slate-500"
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-700">
                    {roleLabel} <span className="text-slate-400 font-medium font-mono text-[9px]">({phoneToDisplay})</span>
                  </span>
                  <span className={cn(
                    "text-[8px] font-extrabold px-1.5 py-0.5 rounded leading-none border uppercase tracking-wider",
                    rec.status === "DELIVERED" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                    rec.status === "DEMO_SENT" ? "bg-blue-50 text-blue-705 border-blue-200" :
                    rec.status === "FAILED" ? "bg-red-50 text-red-700 border-red-200" :
                    rec.status === "SENT" ? "bg-blue-50 text-blue-700 border-blue-200" :
                    rec.status === "QUEUED" ? "bg-amber-50 text-amber-700 border-amber-200" :
                    "bg-slate-50 text-slate-500 border-slate-200"
                  )}>
                    {statusLabel}
                  </span>
                </div>
                
                {rec.status === "FAILED" && (rec.error_message || rec.error) && (
                  <div className="text-[9px] font-semibold text-red-650 flex items-start gap-1">
                    <span className="font-extrabold uppercase text-[7px] bg-red-100 text-red-700 px-1 rounded select-none shrink-0">{t("sos.reason", "Reason:")}</span>
                    <span className="leading-tight">{t("sos.deliveryNeedsReview", "Delivery needs review. Please confirm this contact number before retrying.")}</span>
                  </div>
                )}


              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTriggerButton = () => {
    if (variant === "sidebar") {
      return (
        <button
          onClick={() => {
            setResult(null);
            setError(null);
            setOpen(true);
          }}
          className="flex items-center justify-between px-3 py-2.5 text-sm font-semibold rounded-xl text-slate-650 hover:bg-slate-50 hover:text-slate-900 transition-colors w-full cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <span>SOS</span>
          </div>
          <span className="text-[8px] font-bold text-red-700 bg-red-50 border border-red-100 px-1.5 py-0.5 rounded-full select-none leading-none shrink-0">
            {t("sos.worksOffline", "Works offline")}
          </span>
        </button>
      );
    }

    if (variant === "quickaction") {
      return (
        <button
          onClick={() => {
            setResult(null);
            setError(null);
            setOpen(true);
          }}
          className="col-span-2 flex items-center justify-between gap-3 p-3 rounded-xl bg-red-600 hover:bg-red-700 text-white shadow-sm hover:shadow-md transition-all duration-200 min-h-[58px] text-left cursor-pointer w-full"
        >
          <div className="flex items-center gap-3 min-w-0">
            <div className="rounded-lg bg-red-500/30 p-2 text-white shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-bold leading-none">{t("sos.emergencySos", "Emergency SOS")}</span>
                <span className="text-[8px] font-bold text-white bg-red-500 border border-red-400 px-1.5 py-0.5 rounded-full select-none leading-none shrink-0">
                  {t("sos.worksOffline", "Works offline")}
                </span>
              </div>
              <span className="text-[10px] text-red-150 mt-0.5 leading-tight block truncate">
                {t("sos.quickActionDesc", "Press to view context and trigger dispatch")}
              </span>
            </div>
          </div>
          <div className="shrink-0 font-bold text-xs uppercase bg-white/20 px-3 py-1.5 rounded-lg select-none leading-none">
            {t("sos.open", "Open")}
          </div>
        </button>
      );
    }

    return (
      <Button
        variant="default"
        size="sm"
        disabled={loading}
        title={t("sos.emergencySos", "Emergency SOS")}
        className="bg-red-600 text-white hover:bg-red-700 min-h-[44px] min-w-[64px]"
        onClick={() => {
          setResult(null);
          setError(null);
          setOpen(true);
        }}
      >
        SOS
      </Button>
    );
  };

  return (
    <>
      {renderTriggerButton()}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity" onClick={() => setOpen(false)} />

          {/* Modal Container */}
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden border border-slate-100 z-50 animate-in fade-in-50 zoom-in-95 duration-155">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between shrink-0">
              <div>
                <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-red-600 animate-pulse" />
                  <span>{t("sos.modalTitle", "Emergency SOS Dispatch")}</span>
                </h3>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {t("sos.modalSubtitle", "Field emergency guidance and contact dispatch")}
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
                aria-label={t("common.closeModal", "Close modal")}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Sub-Tab Navigation Bar */}
            <div className="px-6 border-b border-slate-100 bg-slate-50/50 flex gap-4 text-xs font-bold text-slate-500 shrink-0">
              <button 
                onClick={() => setActiveTab("trigger")} 
                className={cn(
                  "py-3 border-b-2 px-1 cursor-pointer transition-all",
                  activeTab === "trigger" ? "border-red-500 text-red-600" : "border-transparent hover:text-slate-700"
                )}
              >
                {t("sos.tab.trigger", "Trigger SOS")}
              </button>
              <button 
                onClick={() => setActiveTab("contacts")} 
                className={cn(
                  "py-3 border-b-2 px-1 cursor-pointer transition-all",
                  activeTab === "contacts" ? "border-red-500 text-red-600" : "border-transparent hover:text-slate-700"
                )}
              >
                {t("sos.tab.contacts", "Emergency Contacts")}
              </button>
              <button 
                onClick={() => setActiveTab("history")} 
                className={cn(
                  "py-3 border-b-2 px-1 cursor-pointer transition-all flex items-center gap-1.5",
                  activeTab === "history" ? "border-red-500 text-red-600" : "border-transparent hover:text-slate-700"
                )}
              >
                <History className="h-3.5 w-3.5" />
                {t("sos.tab.history", "Logs & Timeline")}
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="p-4 md:p-5 overflow-y-auto space-y-4 flex-1 text-sm text-slate-600">
              {activeTab === "trigger" && (
                <>
                  {/* Emergency Crop Alert card */}
                  <div className="bg-red-50/30 border border-red-100 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between border-b border-red-100/50 pb-2">
                      <h4 className="text-xs font-bold text-red-800 uppercase tracking-wider flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <span>Emergency Crop Alert</span>
                      </h4>
                      {result && getUnifiedStatusBadge(result.delivery_status)}
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 font-bold block">Affected Crop</span>
                        <span className="font-semibold text-slate-800">{farm?.crop_type ?? health?.crop_type ?? "Unknown Crop"}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 font-bold block">Current Issue</span>
                        <span className="font-semibold text-slate-855 bg-red-50 text-red-700 px-2 py-0.5 rounded border border-red-100 inline-block font-mono">
                          {result ? getEmergencyTypeLabel(result.emergency_type) : getEmergencyTypeLabel(selectedType)}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 font-bold text-xs block mb-1">Recommended Action</span>
                      {result ? (
                        <ul className="list-disc pl-5 text-xs text-slate-700 font-semibold space-y-1">
                          {result.checklist.map((step, idx) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ul>
                      ) : (
                        <div className="text-xs text-slate-700 font-semibold bg-white p-2.5 rounded-lg border border-slate-100">
                          <p className="font-bold text-slate-800">{getIssuePreview(selectedType)}</p>
                          <p className="mt-1 text-slate-650">{getActionPreview(selectedType)}</p>
                        </div>
                      )}
                    </div>

                    <div>
                      <span className="text-slate-400 font-bold text-xs block mb-1">Location</span>
                      <div className="text-xs font-medium text-slate-700 bg-white p-2.5 rounded-lg border border-slate-100 flex items-center justify-between">
                        <span>
                          {coords ? `GPS: ${coords.latitude?.toFixed(6)}, ${coords.longitude?.toFixed(6)}` : "GPS: Fetching location..."}
                        </span>
                        {coords?.latitude && coords?.longitude && (
                          <a
                            href={`https://maps.google.com/?q=${coords.latitude},${coords.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 font-bold underline cursor-pointer"
                          >
                            Open in Maps
                          </a>
                        )}
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 font-bold text-xs block mb-1">Recipients</span>
                      <div className="flex flex-wrap gap-1.5">
                        {getRecipientBadges().map((rec, idx) => (
                          <span key={idx} className="bg-slate-100 border border-slate-200 text-slate-750 text-[10px] font-bold px-2 py-1 rounded-lg">
                            {rec.role}: {demoMode ? rec.phone : (rec.phone.substring(0, 3) + "****" + rec.phone.substring(rec.phone.length - 4))}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Dispatch Summary & Recipients Status */}
                  {result && result.recipients && (
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <Users className="h-4 w-4 text-slate-500" />
                        <span>Dispatch Summary</span>
                      </h4>
                      
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center">
                        <div className="bg-white border border-slate-100 p-2 rounded-lg">
                          <span className="text-[10px] text-slate-400 font-bold block">Recipients</span>
                          <span className="text-sm font-bold text-slate-800">{result.recipients.length}</span>
                        </div>
                        <div className="bg-white border border-slate-100 p-2 rounded-lg">
                          <span className="text-[10px] text-emerald-500 font-bold block">Delivered</span>
                          <span className="text-sm font-bold text-emerald-700">
                            {result.recipients.filter(r => r.status === "DELIVERED").length}
                          </span>
                        </div>
                        <div className="bg-white border border-slate-100 p-2 rounded-lg">
                          <span className="text-[10px] text-blue-500 font-bold block">Sandbox Delivery</span>
                          <span className="text-sm font-bold text-blue-700">
                            {result.recipients.filter(r => r.status === "DEMO_SENT").length}
                          </span>
                        </div>
                        <div className="bg-white border border-slate-100 p-2 rounded-lg">
                          <span className="text-[10px] text-amber-500 font-bold block">Pending</span>
                          <span className="text-sm font-bold text-amber-700">
                            {result.recipients.filter(r => ["QUEUED", "SENT", "LOGGED"].includes(r.status)).length}
                          </span>
                        </div>
                        <div className="bg-white border border-slate-100 p-2 rounded-lg">
                          <span className="text-[10px] text-red-500 font-bold block">Failed</span>
                          <span className="text-sm font-bold text-red-700">
                            {result.recipients.filter(r => r.status === "FAILED").length}
                          </span>
                        </div>
                      </div>

                      <div className="border-t border-slate-200/50 pt-2">
                        {renderRecipientsList(result.recipients, result.callback_available)}
                      </div>
                    </div>
                  )}

                  {error && (
                    <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-xs text-red-800">
                      <p className="font-bold">{t("sos.dispatchError", "Dispatch Error")}</p>
                      <p className="mt-0.5">{error}</p>
                    </div>
                  )}
                </>
              )}

              {activeTab === "contacts" && (
                <form onSubmit={handleSaveContacts} className="space-y-4">
                  <div className="bg-slate-50 border border-slate-100 p-4 rounded-xl space-y-3">
                    <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5 mb-1">
                      <PhoneCall className="h-4 w-4 text-red-500" />
                      {t("settings.contactsSection", "Emergency Contacts Management")}
                    </h4>
                    
                    {/* Primary Contact */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                        <Smartphone className="h-3.5 w-3.5" />
                        {t("settings.primaryContactLabel", "Primary Contact Phone Number")}
                      </label>
                      <input 
                        type="text" 
                        value={contacts.primary_contact}
                        onChange={(e) => setContacts({ ...contacts, primary_contact: e.target.value })}
                        placeholder="e.g. +919876543210"
                        className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg outline-none focus:border-red-500 font-semibold"
                      />
                    </div>

                    {/* Secondary Contact */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                        <Smartphone className="h-3.5 w-3.5" />
                        {t("settings.secondaryContactLabel", "Secondary Contact Phone Number (Optional)")}
                      </label>
                      <input 
                        type="text" 
                        value={contacts.secondary_contact}
                        onChange={(e) => setContacts({ ...contacts, secondary_contact: e.target.value })}
                        placeholder="e.g. +918765432109"
                        className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg outline-none focus:border-red-500 font-semibold"
                      />
                    </div>

                    {/* Village Representative Contact */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-slate-500 flex items-center gap-1">
                        <Users className="h-3.5 w-3.5" />
                        {t("settings.villageContactLabel", "Village extension representative / KVK Helpline Contact (Optional)")}
                      </label>
                      <input 
                        type="text" 
                        value={contacts.village_contact}
                        onChange={(e) => setContacts({ ...contacts, village_contact: e.target.value })}
                        placeholder="e.g. +917654321098"
                        className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg outline-none focus:border-red-500 font-semibold"
                      />
                    </div>
                  </div>

                  {contactsSaveSuccess && (
                    <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-xs text-emerald-800 flex items-center gap-1.5">
                      <Check className="h-4 w-4 text-emerald-600" />
                      <span>{t("settings.contactsSuccess", "Emergency contacts saved and synced successfully.")}</span>
                    </div>
                  )}

                  {showDisclaimer && (
                    <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl space-y-2 text-xs text-blue-800">
                      <div className="flex items-center gap-2 font-bold text-blue-900 border-b border-blue-100 pb-1.5">
                        <Smartphone className="h-4 w-4 text-blue-700" />
                        <span>SMS Delivery Notice (Evaluation Sandbox)</span>
                      </div>
                      <ul className="list-disc pl-4 space-y-1 text-[11px] text-blue-750 font-medium">
                        <li>Twilio Trial accounts can only send SMS to verified recipient numbers.</li>
                        <li>During evaluation, dispatches to unverified numbers use Sandbox Delivery Mode to simulate the transaction.</li>
                        <li>In production environments, all carrier restrictions are removed.</li>
                        <li>HarvestIQ guarantees demo execution for crop stress alerts even if provider constraints or quotas occur.</li>
                      </ul>
                    </div>
                  )}

                  <div className="flex justify-end gap-2 pt-2">
                    <Button 
                      type="submit"
                      disabled={contactsLoading}
                      className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold px-4 py-2 rounded-lg"
                    >
                      {contactsLoading ? t("settings.saving", "Saving...") : t("settings.saveButton", "Save Contacts")}
                    </Button>
                  </div>
                </form>
              )}

              {activeTab === "history" && (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <History className="h-4 w-4 text-slate-500" />
                    {t("sos.historyLogs", "SOS Dispatch History")}
                  </h4>

                  {historyLoading && history.length === 0 ? (
                    <div className="flex items-center justify-center py-10">
                      <Loader2 className="h-6 w-6 text-slate-400 animate-spin" />
                    </div>
                  ) : history.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-8 text-center">
                      <Check className="mx-auto h-7 w-7 text-emerald-500" />
                      <p className="mt-2 text-xs font-bold text-slate-700">{t("sos.noBroadcasts", "No SOS dispatches recorded")}</p>
                      <p className="mx-auto mt-1 max-w-xs text-[11px] leading-relaxed text-slate-500">{t("sos.noBroadcastsDesc", "Emergency history will appear here after a field SOS is dispatched.")}</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {history.map((item) => {
                        const dateStr = new Date(item.triggered_at).toLocaleDateString(undefined, {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit"
                        });
                        return (
                          <div 
                            key={item.action_id}
                            className={cn(
                              "border rounded-xl p-4 space-y-3 bg-white",
                              item.delivery_status === "QUEUED" ? "border-amber-200 bg-amber-50/10" :
                              item.delivery_status === "FAILED" ? "border-red-100" : "border-slate-100"
                            )}
                          >
                            <div className="flex justify-between items-center gap-2">
                              <div className="flex items-center gap-2">
                                {getUnifiedStatusBadge(item.delivery_status)}
                                <span className="text-[10px] font-bold text-slate-400">{dateStr}</span>
                              </div>
                              <span className="text-xs font-extrabold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-lg select-none">
                                {getEmergencyTypeLabel(item.emergency_type)}
                              </span>
                            </div>
                            
                            <p className="text-xs text-slate-650 leading-relaxed font-medium whitespace-pre-line bg-slate-50 p-2.5 rounded-lg border border-slate-100/50">
                              {getPublicSosMessage(item.plain_text_message)}
                            </p>

                            {/* Render Recipients list */}
                             {renderRecipientsList(item.recipients, item.callback_available)}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
              <div className="text-left">
                {demoMode ? (
                  <p className="text-[10px] text-amber-600 font-semibold">
                    {t("sos.disabledInDemo", "SOS disabled in demo mode")}
                  </p>
                ) : (
                  <p className="text-[10px] text-slate-400 font-medium">
                    {t("sos.willQueue", "Will queue request locally if offline")}
                  </p>
                )}
              </div>
              
              <div className="flex gap-2 w-full sm:w-auto justify-end">
                {activeTab === "trigger" && !result && (
                  <div className="flex flex-wrap gap-1.5 mr-2 items-center">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">{t("sos.type", "Type:")}</span>
                    {EMERGENCY_TYPES.map((type) => (
                      <Button
                        key={type}
                        size="sm"
                        variant={selectedType === type ? "default" : "outline"}
                        disabled={loading}
                        onClick={() => setSelectedType(type)}
                        className={cn(
                          "text-[9px] h-7 px-2 font-bold cursor-pointer",
                          selectedType === type ? "bg-red-600 hover:bg-red-700 text-white border-transparent" : "bg-white"
                        )}
                      >
                        {getEmergencyTypeLabel(type)}
                      </Button>
                    ))}
                  </div>
                )}
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setOpen(false)}
                  className="text-xs h-9 px-4 cursor-pointer bg-white"
                >
                  {t("sos.close", "Close")}
                </Button>
                
                {activeTab === "trigger" && !result && (
                  <button
                    disabled={loading}
                    onClick={() => void trigger(selectedType)}
                    className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold h-9 px-4 rounded-md disabled:opacity-50 disabled:pointer-events-none cursor-pointer flex items-center justify-center min-h-[36px]"
                  >
                    {loading ? t("sos.sending", "Sending...") : t("sos.sendSos", "Send SOS")}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
