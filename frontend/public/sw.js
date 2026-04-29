/* eslint-disable no-restricted-globals */

// Minimal service worker for PWA lifecycle.
// Intentionally does NOT cache API/auth responses.
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // No offline caching: just let the network handle requests.
});

