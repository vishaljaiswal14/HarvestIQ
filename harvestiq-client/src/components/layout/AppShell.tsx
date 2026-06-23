"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api";
import { HarvestIQLogo } from "@/components/branding/HarvestIQLogo";
import { DemoModeToggle } from "@/components/DemoModeToggle";
import { InstallPwaButton } from "@/components/InstallPwaButton";
import { PwaStatusBar } from "@/components/PwaStatusBar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useTranslation, useLocalizationStore } from "@/stores/localizationStore";
import { useAuthStore } from "@/stores/authStore";
import { useHealthCard } from "@/hooks/useHealthCard";
import { useCropStage } from "@/hooks/useCropStage";
import { CropBadge } from "@/lib/agri-identity";
import { SosButton } from "@/components/SosButton";
import {
  LayoutGrid,
  MessageSquare,
  ClipboardList,
  SlidersHorizontal,
  Microscope,
  AlertTriangle,
  Settings,
  User,
  Globe,
  LogOut,
  MapPin
} from "lucide-react";

const LANG_OPTIONS = [
  { code: "hi", label: "हिंदी" },
  { code: "en", label: "English" },
];

type AppShellProps = {
  children: ReactNode;
  userName?: string | null;
  headerEnd?: ReactNode;
  pageTitle?: string;
  pageSubtitle?: string;
  showBack?: { href: string; label?: string };
  className?: string;
  mainClassName?: string;
  narrow?: boolean;
};


export function AppShell({
  children,
  userName,
  headerEnd,
  pageTitle,
  pageSubtitle,
  showBack,
  className,
  mainClassName,
  narrow = false,
}: AppShellProps) {
  const { t } = useTranslation();
  const pathname = usePathname();
  const farm = useAuthStore((state) => state.farm);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const preferredLang = useLocalizationStore((state) => state.preferredLang);
  const refreshUser = useAuthStore((state) => state.refreshUser);

  const [menuOpen, setMenuOpen] = useState(false);

  const handleLanguageChange = async (nextLang: string) => {
    void useLocalizationStore.getState().setLanguage(nextLang);
    try {
      await api.updateProfile({ preferred_lang: nextLang });
      await refreshUser();
    } catch {
      // Keep local label switch even if profile update fails offline.
    }
  };

  // Load metrics data for header details
  const { data: health } = useHealthCard(farm?.farm_id);
  const { data: stage } = useCropStage(farm?.crop_cycle_id ?? null);
  const stageLabel = health?.stage ?? stage?.stage ?? "—";

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const navItems = [
    { label: t("navigation.dashboard", "Dashboard"), href: "/", icon: LayoutGrid },
    { label: t("navigation.advisory", "Advisory"), href: "/advisory", icon: MessageSquare },
    { label: t("navigation.operations", "Operations"), href: "/operations", icon: ClipboardList },
    { label: t("navigation.simulator", "Simulator"), href: "/simulator", icon: SlidersHorizontal },
    { label: t("navigation.diseaseDetection", "Disease Detection"), href: "/disease", icon: Microscope },
  ];

  return (
    <div className={cn("dashboard-shell flex min-h-screen flex-row safe-bottom bg-[#f9faf9]", className)}>
      {/* LEFT NAVIGATION SIDEBAR (Fixed on Desktop) */}
      <aside className="hidden md:flex flex-col w-60 fixed inset-y-0 left-0 bg-white border-r border-slate-100/80 z-30 p-4">
        {/* Logo area */}
        <div className="flex items-center gap-2 px-3 py-2 mb-6">
          <HarvestIQLogo variant="full" size="sm" href="/" priority />
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200",
                  active
                    ? "bg-[#eef8f4] text-[#10b981]"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                <Icon className={cn("h-4 w-4", active ? "text-[#10b981]" : "text-slate-400")} />
                <span>{item.label}</span>
              </Link>
            );
          })}

          <SosButton farmId={farm?.farm_id} variant="sidebar" />
        </nav>
      </aside>

      {/* RIGHT SIDE PANEL CONTENT */}
      <div className="flex-1 flex flex-col md:pl-60 w-full min-w-0">
        {/* STICKY COMPACT CONTEXT HEADER */}
        <header className="sticky top-0 z-50 border-b border-slate-100 bg-white/95 backdrop-blur-md safe-top">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
            <div className="min-w-0 flex-1">
              {farm ? (
                <div className="flex flex-col">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-base font-bold text-slate-800 truncate max-w-[220px]">
                      {farm.farm_name}
                    </h2>
                    <CropBadge cropType={farm.crop_type} />
                    {stageLabel !== "—" && (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-emerald-700 border border-emerald-100/50 select-none leading-none">
                        {stageLabel}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 flex items-center gap-x-2 text-[10px] text-slate-500 font-medium leading-none">
                    <span className="inline-flex items-center gap-0.5">
                      <MapPin className="h-3 w-3 text-slate-400" />
                      {farm.district}, {farm.state}
                    </span>
                    <span className="text-slate-300 select-none">•</span>
                    {farm.soil_type && (
                      <span>
                        {t("shell.soil", "Soil:")} <strong className="font-semibold text-slate-600">{t("onboarding.soilType." + farm.soil_type.toLowerCase(), farm.soil_type)}</strong>
                      </span>
                    )}
                  </p>
                </div>
              ) : (
                <HarvestIQLogo variant="full" size="sm" href="/" priority />
              )}
            </div>

            {/* Top Right Controls */}
            <div className="flex items-center justify-end gap-2 shrink-0">
              <InstallPwaButton />
              <DemoModeToggle />
              
              {user ? (
                <div className="relative">
                  <button
                    onClick={() => setMenuOpen(!menuOpen)}
                    className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <User className="h-4 w-4 text-slate-500" />
                    <span className="hidden sm:inline truncate max-w-[120px]">{user.name}</span>
                  </button>

                  {menuOpen && (
                    <>
                      {/* Backdrop to close menu */}
                      <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
                      
                      <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-100 bg-white p-2 shadow-lg z-40 space-y-1">
                        <div className="px-3 py-2 border-b border-slate-50">
                          <p className="text-xs font-bold text-slate-800 truncate">{user.name}</p>
                          <p className="text-[10px] text-slate-400 truncate">{user.phone}</p>
                        </div>
                        

                        <Link
                          href="/settings"
                          onClick={() => setMenuOpen(false)}
                          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-slate-650 rounded-lg hover:bg-slate-50 hover:text-slate-900 transition-colors w-full text-left"
                        >
                          <Settings className="h-3.5 w-3.5 text-slate-400" />
                          <span>{t("shell.settings", "Settings")}</span>
                        </Link>

                        <div className="px-3 py-2 border-t border-b border-slate-50">
                          <label className="block text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                            {t("shell.language", "Language")}
                          </label>
                          <div className="grid grid-cols-2 gap-1">
                            {LANG_OPTIONS.map((opt) => (
                              <button
                                key={opt.code}
                                onClick={() => void handleLanguageChange(opt.code)}
                                className={cn(
                                  "py-1 text-[10px] font-bold rounded transition-colors text-center cursor-pointer",
                                  preferredLang === opt.code
                                    ? "bg-[#eef8f4] text-[#10b981] border border-emerald-100"
                                    : "bg-slate-50 text-slate-600 border border-slate-100 hover:bg-slate-100"
                                )}
                              >
                                {opt.label}
                              </button>
                            ))}
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            setMenuOpen(false);
                            void logout();
                          }}
                          className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-red-650 rounded-lg hover:bg-red-50 hover:text-red-755 transition-colors w-full text-left cursor-pointer"
                        >
                          <LogOut className="h-3.5 w-3.5 text-red-500" />
                          <span>{t("shell.signOut", "Sign out")}</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ) : null}
              {headerEnd}
            </div>
          </div>

          {/* Simple sub-header for back navigation or titles */}
          {(pageTitle || showBack) && (
            <div className="border-t border-slate-100/80 bg-slate-50/50">
              <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-2 sm:px-6">
                <div className="min-w-0">
                  {pageTitle && (
                    <h1 className="truncate text-sm font-bold tracking-tight text-slate-800">
                      {pageTitle}
                    </h1>
                  )}
                  {pageSubtitle && (
                    <p className="truncate text-[10px] text-slate-500 font-medium">{pageSubtitle}</p>
                  )}
                </div>
                {showBack && (
                  <Button asChild variant="outline" size="sm" className="h-8 min-w-[44px] shrink-0 text-xs">
                    <Link href={showBack.href}>{showBack.label ?? t("dashboard")}</Link>
                  </Button>
                )}
              </div>
            </div>
          )}
        </header>

        {/* MAIN VIEW AREA */}
        <main
          className={cn(
            "w-full flex-1 space-y-5 px-4 py-5 sm:px-6 lg:px-8",
            narrow ? "max-w-3xl mx-auto" : "max-w-7xl mx-auto",
            mainClassName,
          )}
        >
          <PwaStatusBar />
          {children}
        </main>
      </div>
    </div>
  );
}
