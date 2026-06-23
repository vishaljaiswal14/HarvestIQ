"use client";

import { Button } from "@/components/ui/button";
import { useDemoMode } from "@/hooks/useDemoMode";
import { useTranslation } from "@/stores/localizationStore";

export function DemoModeToggle() {
  const { demoMode, setDemoMode } = useDemoMode();
  const { t } = useTranslation();

  return (
    <Button
      size="sm"
      variant={demoMode ? "default" : "outline"}
      className="h-9 min-w-[44px] text-xs"
      onClick={() => setDemoMode(!demoMode)}
    >
      {demoMode ? t("demoToggle.on", "Demo: ON") : t("demoToggle.off", "Demo: OFF")}
    </Button>
  );
}
