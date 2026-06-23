"use client";

import { useCallback, useState } from "react";

import { api } from "@/lib/api";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; ++i) {
    arr[i] = raw.charCodeAt(i);
  }
  return arr;
}

export function usePushNotifications() {
  const [subscribed, setSubscribed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const subscribe = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        throw new Error("Push notifications are not supported in this browser");
      }

      // Explicit notification permission check
      if (typeof window !== "undefined" && "Notification" in window) {
        if (Notification.permission === "denied") {
          throw new Error("Notification permission was denied. Please reset permissions in your browser address bar.");
        }
        if (Notification.permission === "default") {
          const perm = await Notification.requestPermission();
          if (perm !== "granted") {
            throw new Error("Notification permission was not granted.");
          }
        }
      }

      let registration = await navigator.serviceWorker.getRegistration();
      if (!registration) {
        registration = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      }

      const { public_key, enabled } = await api.getVapidPublicKey();
      if (!enabled || !public_key) {
        throw new Error("Push notifications are not configured on the server. VAPID keys are missing.");
      }
      const activeReg = await navigator.serviceWorker.ready;

      let subscription = await activeReg.pushManager.getSubscription();
      if (!subscription) {
        const options: PushSubscriptionOptionsInit = { 
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(public_key) as BufferSource
        };
        subscription = await activeReg.pushManager.subscribe(options);
      }

      const json = subscription.toJSON();
      await api.subscribePush({
        endpoint: json.endpoint!,
        keys: {
          p256dh: json.keys!.p256dh!,
          auth: json.keys!.auth!,
        },
      });
      setSubscribed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to enable push notifications");
      setSubscribed(false);
    } finally {
      setLoading(false);
    }
  }, []);

  return { subscribe, subscribed, error, loading };
}
