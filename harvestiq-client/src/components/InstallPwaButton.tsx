"use client";

import { useState } from "react";
import { Check, Download, Smartphone } from "lucide-react";

import { Button } from "@/components/ui/button";
import { usePwaInstall } from "@/hooks/usePwaInstall";
import { cn } from "@/lib/utils";
import { useTranslation } from "@/stores/localizationStore";

type InstallPwaButtonProps = {
  className?: string;
  size?: "sm" | "default";
};

export function InstallPwaButton({ className, size = "sm" }: InstallPwaButtonProps) {
  const { canInstall, isInstalled, installSuccess, isInstalling, install, showIosHint } =
    usePwaInstall();
  const [iosOpen, setIosOpen] = useState(false);
  const { t } = useTranslation();

  if (isInstalled || installSuccess) {
    return (
      <span
        className={cn(
          "inline-flex h-8 items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 text-xs font-semibold text-emerald-800",
          className,
        )}
      >
        <Check className="h-3.5 w-3.5" />
        {t("pwa.install.installed", "Installed")}
      </span>
    );
  }

  if (showIosHint) {
    return (
      <div className="relative">
        <Button
          type="button"
          size={size}
          variant="outline"
          className={cn("h-8 gap-1 text-xs", className)}
          onClick={() => setIosOpen((v) => !v)}
        >
          <Smartphone className="h-3.5 w-3.5" />
          {t("pwa.install.install", "Install")}
        </Button>
        {iosOpen && (
          <div
            className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 shadow-lg"
            dangerouslySetInnerHTML={{
              __html: t(
                "pwa.install.iosHint",
                "Tap <strong>Share</strong> → <strong>Add to Home Screen</strong> in Safari to install HarvestIQ."
              ),
            }}
          />
        )}
      </div>
    );
  }

  if (!canInstall) return null;

  return (
    <Button
      type="button"
      size={size}
      variant="outline"
      className={cn("h-8 gap-1 border-emerald-200 text-xs text-emerald-800 hover:bg-emerald-50", className)}
      disabled={isInstalling}
      onClick={() => void install()}
    >
      <Download className="h-3.5 w-3.5" />
      {isInstalling ? t("pwa.install.installing", "Installing…") : t("pwa.install.installApp", "Install App")}
    </Button>
  );
}
