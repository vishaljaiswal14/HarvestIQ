"use client";

import { useCallback, useEffect, useState } from "react";

import { DEMO_MODE_KEY, isDemoModeEnabled as readDemoMode } from "@/lib/demoFixtures";

export function useDemoMode() {
  const [demoMode, setDemoModeState] = useState(false);

  useEffect(() => {
    setDemoModeState(readDemoMode());
    const onDemoChange = () => setDemoModeState(readDemoMode());
    window.addEventListener("harvestiq-demo-mode", onDemoChange);
    return () => window.removeEventListener("harvestiq-demo-mode", onDemoChange);
  }, []);

  const setDemoMode = useCallback((enabled: boolean) => {
    localStorage.setItem(DEMO_MODE_KEY, enabled ? "true" : "false");
    setDemoModeState(enabled);
    window.dispatchEvent(new CustomEvent("harvestiq-demo-mode", { detail: enabled }));
  }, []);

  return { demoMode, setDemoMode };
}
