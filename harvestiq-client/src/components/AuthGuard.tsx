"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useAuthStore } from "@/stores/authStore";
import { useTranslation } from "@/stores/localizationStore";

type AuthGuardProps = {
  children: React.ReactNode;
  requireOnboarding?: boolean;
  redirectIfAuthenticated?: boolean;
  allowIncompleteOnboarding?: boolean;
};

export function AuthGuard({
  children,
  requireOnboarding = false,
  redirectIfAuthenticated = false,
  allowIncompleteOnboarding = false,
}: AuthGuardProps) {
  const router = useRouter();
  const { user, isInitialized, isLoading, hasHydrated } = useAuthStore();
  const online = useOnlineStatus();
  const { t } = useTranslation();

  useEffect(() => {
    // Never redirect if we're offline — the user may have a persisted session.
    // Only redirect when fully initialized AND online (or no session at all).
    if (!hasHydrated || !isInitialized || isLoading) return;

    // Offline + has persisted user → stay on current page
    if (!online && user) return;

    if (redirectIfAuthenticated && user) {
      router.replace(user.onboarding_completed ? "/" : "/onboarding");
      return;
    }

    if (!redirectIfAuthenticated && !user) {
      router.replace("/auth");
      return;
    }

    if (allowIncompleteOnboarding && user?.onboarding_completed) {
      router.replace("/");
      return;
    }

    if (requireOnboarding && user && !user.onboarding_completed) {
      router.replace("/onboarding");
      return;
    }

    if (
      !requireOnboarding &&
      !allowIncompleteOnboarding &&
      !redirectIfAuthenticated &&
      user &&
      !user.onboarding_completed
    ) {
      router.replace("/onboarding");
    }
  }, [
    user,
    isInitialized,
    isLoading,
    hasHydrated,
    online,
    requireOnboarding,
    redirectIfAuthenticated,
    allowIncompleteOnboarding,
    router,
  ]);

  if (!hasHydrated || !isInitialized || isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-emerald-800">
        {t("common.loading", "Loading...")}
      </div>
    );
  }

  // Offline with persisted user — render children without redirect
  if (!online && user) {
    return <>{children}</>;
  }

  if (redirectIfAuthenticated && user) {
    return null;
  }

  if (!redirectIfAuthenticated && !user) {
    // Offline and no session — show friendly message instead of blank screen
    if (!online) {
      return (
        <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
          <p className="text-lg font-semibold text-slate-800">{t("common.youAreOffline", "You are offline")}</p>
          <p className="text-sm text-slate-500">
            {t("auth.connectAndLogin", "Connect to the internet and log in to use HarvestIQ.")}
          </p>
        </div>
      );
    }
    return null;
  }

  if (allowIncompleteOnboarding && user?.onboarding_completed) {
    return null;
  }

  if (requireOnboarding && user && !user.onboarding_completed) {
    return null;
  }

  if (
    !requireOnboarding &&
    !allowIncompleteOnboarding &&
    !redirectIfAuthenticated &&
    user &&
    !user.onboarding_completed
  ) {
    return null;
  }

  return <>{children}</>;
}
