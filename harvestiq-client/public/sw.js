const CACHE_NAME = "harvestiq-shell-v4";
const SHELL_ASSETS = [
  "/",
  "/manifest.json",
  "/branding/logo-icon.webp",
  "/branding/logo-wordmark.png",
  "/icon-192.png",
  "/icon-512.png",
  "/favicon.png",
  "/apple-touch-icon.png",
];

const API_CACHE_PREFIXES = [
  "/api/v1/health-card",
  "/api/v1/briefing/daily",
  "/api/v1/weather/forecast",
  "/api/v1/stress-index/",
  "/api/v1/market/prices",
  "/api/v1/disease-radar/",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Cache Next.js static assets dynamically
  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/_next/image")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request)
          .then((response) => {
            if (response.ok) {
              const clone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
            }
            return response;
          })
          .catch(() => {
            // Offline and not in cache, let it fail gracefully
          });
      })
    );
    return;
  }

  if (API_CACHE_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  if (
    request.mode === "navigate" ||
    SHELL_ASSETS.includes(url.pathname) ||
    url.pathname.startsWith("/branding/") ||
    request.headers.get("RSC") === "1" ||
    ["/", "/auth", "/onboarding", "/simulator", "/advisory", "/disease"].includes(url.pathname)
  ) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match("/"))),
    );
    return;
  }
});

self.addEventListener("push", (event) => {
  let payload = { title: "HarvestIQ Alert", body: "You have a new field alert.", data: {} };
  try {
    if (event.data) {
      payload = { ...payload, ...event.data.json() };
    }
  } catch {
    // use defaults
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: payload.data,
      tag: payload.data?.alert_id || "harvestiq-alert",
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const alertId = event.notification.data?.alert_id;
  const target = alertId ? `/?alert=${alertId}` : "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(target);
      }
    }),
  );
});
