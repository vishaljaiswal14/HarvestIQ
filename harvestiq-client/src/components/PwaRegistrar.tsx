"use client";

import { useEffect } from "react";

export function PwaRegistrar() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    if (process.env.NODE_ENV === "production") {
      void navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch(() => {
          // Registration failures should not block the app shell.
        });
    } else {
      // In development, clean up any active service workers to prevent stale Turbopack chunk caching
      navigator.serviceWorker.getRegistrations()
        .then((registrations) => {
          for (const registration of registrations) {
            void registration.unregister().then((success) => {
              if (success) {
                console.log("[PWA Registrar] Successfully unregistered stale service worker in development:", registration.scope);
              }
            });
          }
        })
        .catch((err) => {
          console.warn("[PWA Registrar] Failed to query service worker registrations:", err);
        });
    }
  }, []);

  return null;
}
