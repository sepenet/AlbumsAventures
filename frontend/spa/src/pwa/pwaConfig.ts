/**
 * PWA configuration (Phase 4) — web app manifest + Workbox service-worker
 * options for `vite-plugin-pwa`.
 *
 * Extracted from `vite.config.ts` into this module so the caching strategy is
 * unit-testable (see `pwaConfig.test.ts`): the mandatory architect-council
 * conditions on the service worker (TUS bypass, no-store auth/API, bounded
 * media cache) are asserted against these exported objects.
 *
 * Serving context: the SPA is served SAME-ORIGIN by FastAPI under `/app`
 * (`frontend/spa_serving.py`). `base` / `scope` are therefore `/app/` so the
 * generated service worker (served at `/app/sw.js`) controls exactly the
 * `/app` surface and nothing else. `/be_*`, `/be_resizer/tus/`, `/images`,
 * `/thumbnails` and `/static` all live OUTSIDE `/app`, so they are only
 * touched by the explicit runtime rules below.
 */

import type { ManifestOptions, VitePWAOptions } from "vite-plugin-pwa";

// URL prefix the SPA is mounted under by FastAPI (mirror of
// frontend/spa_serving.SPA_URL_PREFIX and Vite `base`). The service worker is
// served from this directory so its default control scope is `/app/`.
export const SPA_BASE = "/app/";

// Brand palette (docs/GUIDELINES_UI.md): sky-500 accent on a white surface.
const THEME_COLOR = "#0ea5e9"; // sky-500
const BACKGROUND_COLOR = "#ffffff";

/**
 * Web app manifest. `start_url` / `scope` are the `/app` SPA surface so an
 * installed instance launches straight into the React shell and its navigation
 * stays inside the app.
 */
export const manifest: Partial<ManifestOptions> = {
  name: "AlbumsAventures",
  short_name: "AlbumsAventures",
  description: "Aventures planquées dans les cartes",
  lang: "fr",
  display: "standalone",
  start_url: SPA_BASE,
  scope: SPA_BASE,
  theme_color: THEME_COLOR,
  background_color: BACKGROUND_COLOR,
  icons: [
    { src: "icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
    { src: "icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    {
      src: "icons/icon-maskable-512.png",
      sizes: "512x512",
      type: "image/png",
      purpose: "maskable",
    },
  ],
};

// ── Runtime caching rules (Workbox, in generateSW "config" form) ──────────────
// Order matters: the FIRST matching rule wins, so the most specific / most
// safety-critical patterns are declared first.

/**
 * COUNCIL CONDITION 1 — TUS bypass. The Phase 2 resumable-upload stack under
 * `/be_resizer/tus/` relies on raw offset/PATCH semantics and MUST reach the
 * network untouched. `NetworkOnly` = transparent passthrough (no cache read,
 * no cache write), declared first so no other rule can ever intercept it.
 */
const tusBypassRule = {
  urlPattern: /^\/be_resizer\//,
  handler: "NetworkOnly" as const,
  options: { cacheName: "be-resizer-networkonly" },
};

/**
 * COUNCIL CONDITION 2 — authenticated API is never cached. All `/be_*` JSON
 * (`/be_auth/*`, `/be_album/*`, `/be_user/*`, `/be_group/*`, `/be_category/*`,
 * …) is user-scoped; serving it from cache across a session/logout would be an
 * auth-correctness hazard. `NetworkOnly` (no-store) guarantees a session change
 * can never leak a previous user's data from the SW cache — strictly stronger
 * than the NetworkFirst floor the council allowed.
 */
const authApiRule = {
  urlPattern: /^\/be_/,
  handler: "NetworkOnly" as const,
  options: { cacheName: "be-api-networkonly" },
};

/**
 * COUNCIL CONDITION 3 — bounded media/static caches. Full images are large and
 * effectively immutable per URL → CacheFirst. Every media/static rule carries
 * an `ExpirationPlugin` (`maxEntries` + `maxAgeSeconds` + `purgeOnQuotaError`)
 * so device storage stays bounded and self-heals on a quota error.
 * (`/app/assets/*` — the hashed SPA bundle — is handled by the PRECACHE, which
 * is itself revisioned and bounded, so it needs no runtime rule here.)
 */
const DAYS_30 = 30 * 24 * 60 * 60;

const imagesRule = {
  urlPattern: /^\/images\//,
  handler: "CacheFirst" as const,
  options: {
    cacheName: "media-images",
    expiration: { maxEntries: 200, maxAgeSeconds: DAYS_30, purgeOnQuotaError: true },
    cacheableResponse: { statuses: [0, 200] },
  },
};

const thumbnailsRule = {
  urlPattern: /^\/thumbnails\//,
  handler: "StaleWhileRevalidate" as const,
  options: {
    cacheName: "media-thumbnails",
    expiration: { maxEntries: 500, maxAgeSeconds: DAYS_30, purgeOnQuotaError: true },
    cacheableResponse: { statuses: [0, 200] },
  },
};

const staticRule = {
  urlPattern: /^\/static\//,
  handler: "StaleWhileRevalidate" as const,
  options: {
    cacheName: "static-assets",
    expiration: { maxEntries: 60, maxAgeSeconds: DAYS_30, purgeOnQuotaError: true },
    cacheableResponse: { statuses: [0, 200] },
  },
};

export const runtimeCaching = [
  tusBypassRule,
  authApiRule,
  imagesRule,
  thumbnailsRule,
  staticRule,
];

/**
 * Workbox `generateSW` options.
 *
 * COUNCIL CONDITION 4 — SW versioning + activation. `generateSW` stamps every
 * precached asset with a content revision derived from the Vite build hash, so
 * the SW changes (and the browser detects an update) whenever any hashed asset
 * changes. `skipWaiting` + `clientsClaim` make a new deploy activate and take
 * control immediately; combined with `cleanupOutdatedCaches` the stale precache
 * is purged. This pairs with `registerType: "autoUpdate"` below.
 *
 * COUNCIL CONDITION 5 — offline app shell. `globPatterns` precache the built
 * shell (`index.html` + hashed JS/CSS), and `navigateFallback` serves that
 * precached shell for `/app/*` navigations while offline. `navigateFallback*`
 * lists keep the fallback scoped to `/app` and away from `/be_*` and media so
 * the SW never hijacks an API/Jinja/upload request.
 */
export const workbox: VitePWAOptions["workbox"] = {
  globPatterns: ["**/*.{js,css,html,ico,png,svg,webmanifest}"],
  navigateFallback: "index.html",
  // Only `/app/*` navigations fall back to the precached shell…
  navigateFallbackAllowlist: [/^\/app\//],
  // …and never API, resumable-upload, or media routes (defense in depth).
  navigateFallbackDenylist: [/^\/be_/, /^\/images\//, /^\/thumbnails\//, /^\/static\//],
  cleanupOutdatedCaches: true,
  skipWaiting: true,
  clientsClaim: true,
  runtimeCaching,
};

/**
 * Full `vite-plugin-pwa` options.
 *
 * COUNCIL CONDITION 6 — CSP. `injectRegister: "script"` emits an EXTERNAL,
 * same-origin `registerSW.js` (referenced as `/app/registerSW.js`) instead of
 * an inline `<script>`, so the hardened SPA CSP (`script-src 'self'`, no
 * `'unsafe-inline'`) is satisfied with no CSP change. `worker-src 'self' blob:`
 * and `manifest-src 'self'` were already staged in Phase 1.
 *
 * `registerType: "autoUpdate"` reloads clients onto the new SW automatically —
 * chosen over prompt-for-update because the app shell is served `no-store` and
 * ALL `/be_*` API is `NetworkOnly`, so there is no cached-API state that a
 * silent update could desync; the simplest correct UX wins.
 */
export const pwaOptions: Partial<VitePWAOptions> = {
  registerType: "autoUpdate",
  injectRegister: "script",
  base: SPA_BASE,
  scope: SPA_BASE,
  includeAssets: ["favicon.ico", "icons/apple-touch-icon.png"],
  manifest,
  workbox,
};
