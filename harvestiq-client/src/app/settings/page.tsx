"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { api, type EmergencyContacts } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation, useLocalizationStore } from "@/stores/localizationStore";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { 
  Bell,
  User, 
  Smartphone, 
  Globe, 
  PhoneCall, 
  Check, 
  AlertTriangle,
  ArrowRight,
  Shield,
  Loader2,
  Lock,
  MapPin,
  CheckCircle2,
  XCircle
} from "lucide-react";
import { cn } from "@/lib/utils";

const LANG_OPTIONS = [
  { code: "hi", label: "हिंदी" },
  { code: "en", label: "English" },
];

function SettingsPageContent() {
  const { t } = useTranslation();
  const online = useOnlineStatus();
  const user = useAuthStore((state) => state.user);
  const farm = useAuthStore((state) => state.farm);
  const preferredLang = useLocalizationStore((state) => state.preferredLang);
  const refreshUser = useAuthStore((state) => state.refreshUser);

  // Contacts state
  const [contacts, setContacts] = useState<EmergencyContacts>({
    primary_contact: "",
    secondary_contact: "",
    village_contact: ""
  });
  const [contactsLoading, setContactsLoading] = useState(false);
  const [contactsSaveSuccess, setContactsSaveSuccess] = useState(false);
  const [contactsSaveOffline, setContactsSaveOffline] = useState(false);
  
  // Validation states
  const [validationError, setValidationError] = useState<string | null>(null);
  const { subscribe: subscribePush, subscribed: pushSubscribed, error: pushError, loading: pushLoading } = usePushNotifications();

  // Load emergency contacts on mount
  useEffect(() => {
    let active = true;
    const fetchContacts = async () => {
      setContactsLoading(true);
      try {
        const res = await api.getEmergencyContacts();
        if (active) {
          setContacts(res);
        }
      } catch (err) {
        console.error("Failed to load emergency contacts:", err);
      } finally {
        if (active) {
          setContactsLoading(false);
        }
      }
    };
    void fetchContacts();
    return () => {
      active = false;
    };
  }, []);

  const handleLanguageChange = async (nextLang: string) => {
    void useLocalizationStore.getState().setLanguage(nextLang);
    try {
      await api.updateProfile({ preferred_lang: nextLang });
      await refreshUser();
    } catch (err) {
      console.warn("Language update failed or queued offline:", err);
    }
  };

  const validateForm = (): boolean => {
    setValidationError(null);
    const phoneRegex = /^\+[1-9]\d{1,14}$/;

    // 1. E.164 Validation
    const fields: Array<{ name: string; val: string }> = [
      { name: t("settings.primaryContact", "Primary Contact"), val: contacts.primary_contact },
      { name: t("settings.secondaryContact", "Secondary Contact"), val: contacts.secondary_contact },
      { name: t("settings.villageContact", "Village Representative / KVK Contact"), val: contacts.village_contact }
    ];

    for (const field of fields) {
      const cleanVal = field.val.trim();
      if (cleanVal) {
        if (!phoneRegex.test(cleanVal)) {
          setValidationError(
            t(
              "settings.validation.e164Error",
              "{fieldName} number must be in valid E.164 format (e.g. +918441091925)"
            ).replace("{fieldName}", field.name)
          );
          return false;
        }
      }
    }

    // 2. Duplicate Prevention
    const activeNumbers: Record<string, string> = {};
    for (const field of fields) {
      const cleanVal = field.val.trim();
      if (cleanVal) {
        if (activeNumbers[cleanVal]) {
          setValidationError(
            t(
              "settings.validation.duplicateError",
              "Duplicate numbers detected: {number} cannot be assigned to both {firstField} and {secondField}"
            )
              .replace("{number}", cleanVal)
              .replace("{firstField}", activeNumbers[cleanVal])
              .replace("{secondField}", field.name)
          );
          return false;
        }
        activeNumbers[cleanVal] = field.name;
      }
    }

    return true;
  };

  const handleSaveContacts = async (e: React.FormEvent) => {
    e.preventDefault();
    setContactsSaveSuccess(false);
    setContactsSaveOffline(false);
    
    if (!validateForm()) return;

    setContactsLoading(true);
    try {
      const res = await api.saveEmergencyContacts({
        primary_contact: contacts.primary_contact.trim(),
        secondary_contact: contacts.secondary_contact.trim(),
        village_contact: contacts.village_contact.trim(),
      });
      setContacts(res);
      
      if (!online) {
        setContactsSaveOffline(true);
      } else {
        setContactsSaveSuccess(true);
      }
      
      setTimeout(() => {
        setContactsSaveSuccess(false);
        setContactsSaveOffline(false);
      }, 5000);
    } catch (err) {
      setValidationError(err instanceof Error ? err.message : t("settings.failedSaveContacts", "Failed to save emergency contacts"));
    } finally {
      setContactsLoading(false);
    }
  };

  return (
    <AppShell
      userName={user?.name}
      pageTitle={t("settings.title", "Settings & Emergency Contacts")}
      pageSubtitle={t("settings.subtitle", "Manage your farmer profile preference and configure emergency recipient contacts")}
      showBack={{ href: "/", label: t("common.dashboard", "Dashboard") }}
      narrow
    >
      <div className="space-y-6">
        {/* Section 1: Farmer Profile & Language */}
        <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-50 pb-3">
            <User className="h-4 w-4 text-[#10b981]" />
            <span>{t("settings.profileSection", "Farmer Profile Settings")}</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                {t("settings.nameLabel", "Name")}
              </label>
              <div className="flex items-center gap-2 p-2.5 bg-slate-50 border border-slate-100 rounded-xl text-slate-700 font-semibold text-xs">
                <User className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                <span>{user?.name || "—"}</span>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                {t("settings.phoneLabel", "Phone Number")}
              </label>
              <div className="flex items-center gap-2 p-2.5 bg-slate-50 border border-slate-100 rounded-xl text-slate-700 font-semibold text-xs">
                <Smartphone className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                <span>{user?.phone || "—"}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2 pt-2">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Globe className="h-3.5 w-3.5 text-slate-400" />
              {t("settings.languageLabel", "Language Preference")}
            </label>
            <div className="flex gap-2 max-w-xs">
              {LANG_OPTIONS.map((opt) => (
                <button
                  key={opt.code}
                  type="button"
                  onClick={() => void handleLanguageChange(opt.code)}
                  className={cn(
                    "flex-1 py-2 text-xs font-bold rounded-xl border transition-all cursor-pointer text-center",
                    preferredLang === opt.code
                      ? "bg-[#eef8f4] text-[#10b981] border-[#bbf7d0]"
                      : "bg-white text-slate-650 border-slate-200 hover:bg-slate-50"
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-slate-400 leading-normal">
              {t("settings.langHelp", "All reports, syntheses, and advisors will automatically load in this language.")}
            </p>
          </div>
        </div>

        {/* Section 2: Alert Notification Preferences */}
        <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-50 pb-3">
            <Bell className="h-4 w-4 text-amber-500" />
            <span>{t("settings.notificationsSection", "Alert Notifications")}</span>
          </h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            {t(
              "settings.notificationsDesc",
              "Enable push notifications for field alerts. Push is the primary channel; SMS escalates only if alerts stay unread.",
            )}
          </p>
          <Button
            type="button"
            variant={pushSubscribed ? "outline" : "default"}
            disabled={pushLoading || pushSubscribed}
            onClick={() => void subscribePush()}
            className="w-full sm:w-auto"
          >
            {pushLoading
              ? t("settings.enablingPush", "Enabling…")
              : pushSubscribed
                ? t("settings.pushEnabled", "Push notifications enabled")
                : t("settings.enablePush", "Enable push notifications")}
          </Button>
          {pushError && (
            <p className="text-xs text-red-600 font-semibold">{pushError}</p>
          )}
          <p className="text-[10px] text-slate-400">
            {t(
              "settings.quietHoursNote",
              "Quiet hours (10 PM – 6 AM) defer LOW/MEDIUM/HIGH alerts. CRITICAL alerts bypass quiet hours.",
            )}
          </p>
        </div>

        {/* Section 3: Emergency Contacts Configuration */}
        <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-50 pb-3">
            <PhoneCall className="h-4 w-4 text-red-500 animate-pulse" />
            <span>{t("settings.contactsSection", "Emergency Contacts Management")}</span>
          </h3>

          <p className="text-xs text-slate-500 leading-relaxed">
            {t(
              "settings.contactsDesc",
              "Define recipients to notify during agricultural distress alerts or panic SOS dispatches. All configured recipients will automatically receive localized alert details, GPS locations, and helpline instructions."
            )}
          </p>

          <form onSubmit={handleSaveContacts} className="space-y-4">
            {/* Validation alerts */}
            {validationError && (
              <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-xs text-red-800 flex items-start gap-2">
                <XCircle className="h-4 w-4 text-red-650 shrink-0 mt-0.5" />
                <span className="font-semibold">{validationError}</span>
              </div>
            )}

            {contactsSaveSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-xs text-emerald-800 flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-650 shrink-0 mt-0.5" />
                <span className="font-semibold">
                  {t("settings.contactsSuccess", "Emergency contacts saved and synced successfully.")}
                </span>
              </div>
            )}

            {contactsSaveOffline && (
              <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-800 flex flex-col gap-1">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-650 shrink-0 mt-0.5 animate-pulse" />
                  <span className="font-bold">
                    {t("settings.contactsOffline", "Emergency Contacts Saved Offline")}
                  </span>
                </div>
                <p className="text-[10px] text-amber-700 pl-6 leading-normal font-semibold">
                  {t(
                    "settings.contactsOfflineHelp",
                    "HarvestIQ has queued the contacts update in the outbox. It will sync automatically when you are back online."
                  )}
                </p>
              </div>
            )}

            <div className="space-y-4">
              {/* Primary Contact */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Smartphone className="h-3.5 w-3.5 text-slate-400" />
                  {t("settings.primaryContactLabel", "Primary Contact Phone Number")}
                  <span className="text-red-500 font-bold">*</span>
                </label>
                <input 
                  type="text" 
                  value={contacts.primary_contact}
                  onChange={(e) => setContacts({ ...contacts, primary_contact: e.target.value })}
                  placeholder="e.g. +918441091925"
                  className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-xl outline-none focus:border-[#10b981] font-semibold"
                />
              </div>

              {/* Secondary Contact */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Smartphone className="h-3.5 w-3.5 text-slate-400" />
                  {t("settings.secondaryContactLabel", "Secondary Contact Phone Number (Optional)")}
                </label>
                <input 
                  type="text" 
                  value={contacts.secondary_contact}
                  onChange={(e) => setContacts({ ...contacts, secondary_contact: e.target.value })}
                  placeholder="e.g. +919876543210"
                  className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-xl outline-none focus:border-[#10b981] font-semibold"
                />
              </div>

              {/* Village Contact */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Shield className="h-3.5 w-3.5 text-slate-400" />
                  {t("settings.villageContactLabel", "Village extension representative / KVK Helpline Contact (Optional)")}
                </label>
                <input 
                  type="text" 
                  value={contacts.village_contact}
                  onChange={(e) => setContacts({ ...contacts, village_contact: e.target.value })}
                  placeholder="e.g. +917654321098"
                  className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-xl outline-none focus:border-[#10b981] font-semibold"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-50">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                {!online && t("settings.offlineOutboxActive", "Offline Outbox Active")}
              </span>
              <Button
                type="submit"
                disabled={contactsLoading}
                className="bg-[#10b981] hover:bg-[#0e9f6e] text-white text-xs font-bold px-6 py-2 h-9 rounded-xl flex items-center gap-1.5 shrink-0"
              >
                {contactsLoading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>{t("settings.saving", "Saving...")}</span>
                  </>
                ) : (
                  <span>{t("settings.saveButton", "Save Contacts")}</span>
                )}
              </Button>
            </div>
          </form>
        </div>

        {/* Section 3: Farm Config / Setup Redirect */}
        {farm && (
          <div className="bg-emerald-950 border border-emerald-900 rounded-2xl p-6 text-white shadow-sm space-y-3 relative overflow-hidden">
            {/* Background pattern */}
            <div className="absolute right-0 bottom-0 opacity-10 pointer-events-none select-none translation-y-4">
              <MapPin className="h-36 w-36" />
            </div>

            <h4 className="text-sm font-bold flex items-center gap-2">
              <Shield className="h-4 w-4 text-[#34d399]" />
              <span>{t("settings.farmFlowSection", "Farm Setup & Cycles Flow")}</span>
            </h4>
            <p className="text-xs text-emerald-150 leading-relaxed max-w-md">
              {t("settings.farmFlowDesc", "Configure your active sown farm properties, crop characteristics constraints parameters, or add new plots to your profile.")}
            </p>
            <div className="pt-2">
              <Button asChild size="sm" className="bg-[#10b981] text-white hover:bg-[#0e9f6e] text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 w-fit">
                <Link href="/farm-setup">
                  <span>{t("settings.openFarmSetup", "Configure Farm Cycles")}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function SettingsPage() {
  return (
    <AuthGuard requireOnboarding>
      <SettingsPageContent />
    </AuthGuard>
  );
}
