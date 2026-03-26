/**
 * RunPulse Service Worker — PWA 오프라인 캐시.
 *
 * 전략:
 *   - Install: CDN 자산 선캐시 (ECharts, Google Fonts, 아이콘)
 *   - Activate: 이전 캐시 버전 정리
 *   - Fetch:
 *     - CDN/정적: Cache First
 *     - HTML 페이지: Network First → 캐시 폴백 → offline.html
 *     - 나머지: Network First
 */

const CACHE_VERSION = "runpulse-v2";
const OFFLINE_URL = "/static/offline.html";

/** Install 시 선캐시할 자산 목록. */
const PRECACHE_URLS = [
  OFFLINE_URL,
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Inter:wght@400;600&display=swap",
];

// ── Install ─────────────────────────────────────────────────────────────

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate ────────────────────────────────────────────────────────────

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_VERSION)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

// ── Fetch ───────────────────────────────────────────────────────────────

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // POST 등 non-GET은 네트워크 직접
  if (request.method !== "GET") return;

  // CDN + 정적 자산: Cache First
  if (
    url.hostname === "cdn.jsdelivr.net" ||
    url.hostname === "fonts.googleapis.com" ||
    url.hostname === "fonts.gstatic.com" ||
    url.pathname.startsWith("/static/")
  ) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // HTML 페이지 (Accept: text/html): Network First → 캐시 → offline.html
  if (request.headers.get("Accept")?.includes("text/html")) {
    event.respondWith(networkFirstHtml(request));
    return;
  }

  // 나머지 (API 등): Network First
  event.respondWith(networkFirst(request));
});

// ── 캐시 전략 함수 ──────────────────────────────────────────────────────

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response("", { status: 503, statusText: "Offline" });
  }
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response("", { status: 503, statusText: "Offline" });
  }
}

async function networkFirstHtml(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // 최후 폴백: 오프라인 페이지
    return caches.match(OFFLINE_URL);
  }
}
