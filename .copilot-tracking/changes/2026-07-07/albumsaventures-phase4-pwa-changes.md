<!-- markdownlint-disable-file -->
# Release Changes: Phase 4 — PWA Conversion (installable + offline app shell)

**Related Plan**: `.copilot-tracking/plans/albumsaventures-modernization.md` (Phase 4) — handoff contract in `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment8-changes.md`
**Implementation Date**: 2026-07-07
**Status**: LANDED (developer member Gamma). Final phase (goal #4).

## Summary

Turns the React SPA (`frontend/spa/`, served same-origin under `/app` by FastAPI) into an installable, offline-capable PWA using **`vite-plugin-pwa` v1.3.0** (Workbox `generateSW`). The build now emits a service worker (`dist/sw.js`), the Workbox runtime (`dist/workbox-<hash>.js`), an external registration script (`dist/registerSW.js`) and the web app manifest (`dist/manifest.webmanifest`); FastAPI serves those root-level artifacts at `/app/*` so the SW (at `/app/sw.js`) controls exactly the `/app` scope.

Every mandatory architect-council condition on the service worker is implemented and, where the config is testable, locked in by a unit test. **No CSP change was needed** — Phase 1 already staged `worker-src 'self' blob:` and `manifest-src 'self'`, and the plugin registers the SW via an EXTERNAL same-origin script (not inline), so the hardened SPA CSP (`script-src 'self'`) is satisfied unchanged.

## Council-condition compliance checklist

| # | Council condition | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | **TUS bypass** — SW must NOT intercept `/be_resizer/tus/` | **SATISFIED** | `runtimeCaching[0]`: `urlPattern /^\/be_resizer\//` → **`NetworkOnly`** (transparent passthrough, no cache read/write), declared FIRST so nothing else can catch it. Also in `navigateFallbackDenylist`. Generated `dist/sw.js` shows `registerRoute(/^\/be_resizer\//, new e.NetworkOnly…)`. Test `COUNCIL 1`. |
| 2 | **Auth/API network-first/no-store** — `/be_auth/*`, `/be_album/*`, `/be_user/*`, `/be_group/*`, `/be_category/*` never CacheFirst/SWR | **SATISFIED** | `runtimeCaching[1]`: `urlPattern /^\/be_/` → **`NetworkOnly`** (no-store, strictly stronger than NetworkFirst) → user-scoped JSON is never cached, so a logout/session change cannot leak a prior user's data. Test `COUNCIL 2` asserts NetworkOnly for all five families and that no `be_*` rule uses a caching handler. |
| 3 | **Bounded media/static LRU + quota** — `/images`, `/thumbnails`, `/static`, `/app/assets/*` | **SATISFIED** | `/images` → `CacheFirst` (maxEntries 200, 30 d, `purgeOnQuotaError`); `/thumbnails` → `StaleWhileRevalidate` (500, 30 d, purge); `/static` → `StaleWhileRevalidate` (60, 30 d, purge). `/app/assets/*` (hashed SPA bundle) is served by the **precache** (content-revisioned + `cleanupOutdatedCaches`), which is itself bounded and self-invalidating — a runtime rule would be redundant and never match (precache wins). Test `COUNCIL 3`. |
| 4 | **SW versioned from build hash + explicit skipWaiting/clientsClaim** | **SATISFIED** | `generateSW` stamps each precache entry with a content revision (hashed assets are content-addressed by filename; `index.html`/manifest/icons get md5 revisions), so the SW changes and the browser detects an update whenever any asset changes. `skipWaiting: true` + `clientsClaim: true` + `cleanupOutdatedCaches: true` + `registerType: "autoUpdate"`. **Decision: autoUpdate** (see rationale below). Generated `dist/sw.js` shows `self.skipWaiting(); e.clientsClaim();`. Test `COUNCIL 4`. |
| 5 | **Offline app shell** — precache the shell; no offline redirect loop | **SATISFIED** | `globPatterns` precache `index.html` + hashed JS/CSS (16 entries); `navigateFallback: "index.html"` with `navigateFallbackAllowlist: [/^\/app\//]` serves the precached shell for `/app/*` offline navigations. `RequireAuth` now shows an explicit **offline state with retry** (via `navigator.onLine` + `online`/`offline` events) and NEVER redirects to `/login` when offline — killing the loop hazard. Verified: `GET /app/albums/42` → 200 HTML `no-store` shell. Test `COUNCIL 5`. |
| 6 | **CSP** — SW/manifest work under hardened SPA CSP; no `unsafe-eval`/`*` | **SATISFIED (no change)** | `injectRegister: "script"` → external `/app/registerSW.js` (no inline `<script>`), so SPA `script-src 'self'` holds. SW = same-origin worker (`worker-src 'self' blob:`), manifest link (`manifest-src 'self'`) — both already staged Phase 1. `utils/security.py` UNCHANGED; existing CSP tests (no `unsafe-eval`, no `*`) still pass (61 backend). Test `COUNCIL 6` asserts `injectRegister === "script"`. |
| 7 | **HTTPS prod prerequisite** | **NOTED** | SW registers on `localhost` for dev (secure-context exemption). Production HTTPS + HSTS + `upgrade-insecure-requests` already staged in Phase 1; no new work. |

## FastAPI serving / scope

`frontend/spa_serving.py` `serve_spa` now serves any REAL file in `dist/` at `/app/<path>` (behind a path-traversal guard) BEFORE falling back to `index.html`:

* `/app/sw.js` → `text/javascript`, `Cache-Control: no-cache` (served from `/app/` so its default control **scope is `/app/`** — it can govern the whole SPA surface and nothing else). Verified 200 + contains `skipWaiting`.
* `/app/manifest.webmanifest` → `application/manifest+json` (`scope`/`start_url` = `/app/`). Verified 200.
* `/app/registerSW.js`, `/app/workbox-<hash>.js` → `text/javascript`. Verified 200.
* `/app/icons/*.png` → `image/png`. Verified 200.
* `/app/<react-route>` → `index.html` (`no-store`). Verified 200 HTML.
* `/app/../../utils/security.py` (traversal) → **404, no file leaked**. Verified.
* `/be_auth/me` → **401 (not shadowed)** — PWA files are all under `/app`, so they cannot shadow `/be_*`, `/be_resizer/tus/`, `/images`, `/thumbnails`, `/static`. Verified.

## Web app manifest & icons

* `dist/manifest.webmanifest`: `name` "AlbumsAventures", `short_name` "AlbumsAventures", `description` "Aventures planquées dans les cartes", `display: standalone`, `start_url: /app/`, `scope: /app/`, `theme_color: #0ea5e9` (sky-500), `background_color: #ffffff`, `lang: fr`.
* Icons (`frontend/spa/public/icons/`) — **real PNGs**, brand-derived (sky→blue gradient + white "A"), generated by a committed Pillow script; swap for a designed asset later without touching the manifest (filenames stable):
  * `icon-192.png` 192×192 `purpose: any`
  * `icon-512.png` 512×512 `purpose: any`
  * `icon-maskable-512.png` 512×512 `purpose: maskable` (glyph in ~80% safe zone)
  * `apple-touch-icon.png` 180×180 (iOS home-screen, opaque)

## skipWaiting / clientsClaim decision — autoUpdate (documented)

Chosen **`registerType: "autoUpdate"`** with `skipWaiting`+`clientsClaim` over prompt-for-update because: (a) the HTML shell is served `Cache-Control: no-store` so it always re-fetches the newest hashed asset refs; (b) ALL `/be_*` API is `NetworkOnly` (never cached), so there is **no cached-API state a silent update could desync** — the classic "stale shell vs. changed API" hazard cannot occur here; (c) simplest correct UX. The only tradeoff (a new SW claiming an open tab mid-session) is bounded by the no-store shell + precache cleanup.

## Changes

### Added

* `frontend/spa/src/pwa/pwaConfig.ts` — web app manifest + Workbox `generateSW` options (runtime caching, navigate fallback, skipWaiting/clientsClaim), exported so the caching strategy is unit-testable.
* `frontend/spa/src/pwa/pwaConfig.test.ts` — 9 vitest cases asserting the council conditions (TUS bypass, `be_*` NetworkOnly, bounded media caches, skipWaiting/clientsClaim/autoUpdate, offline shell scope, external SW registration) + manifest correctness.
* `frontend/spa/public/icons/generate_icons.py` — Pillow icon generator (documented, re-runnable).
* `frontend/spa/public/icons/icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `apple-touch-icon.png` — the icon set.

### Modified

* `frontend/spa/vite.config.ts` — register `VitePWA(pwaOptions)`; documented the build-artifact → FastAPI-serving contract.
* `frontend/spa/index.html` — added `theme-color` meta + `apple-touch-icon` link (manifest link + SW registration script are injected by the plugin at build time).
* `frontend/spa/src/auth/RequireAuth.tsx` — added `useOnlineStatus` + an explicit offline state (retry, no redirect) so the auth guard never loops to `/login` when offline.
* `frontend/spa_serving.py` — `serve_spa` serves real `dist/` artifacts (SW/manifest/registerSW/workbox/icons) at `/app/*` with a path-traversal guard + correct media types + `no-cache` on PWA lifecycle files, before the `index.html` fallback; docstring extended with the PWA-artifacts section.
* `frontend/spa/package.json` / `package-lock.json` — `vite-plugin-pwa` dev dependency.

### Removed

* None.

## Additional or Deviating Changes

* **`/app/assets/*` uses the precache, not a separate runtime rule.** The council listed `/app/assets/*` under "bounded runtime cache". The hashed SPA bundle is instead handled by the Workbox **precache** (content-revisioned, cleaned by `cleanupOutdatedCaches`), which is bounded and self-invalidating and is the *correct* mechanism — a runtime rule would never match (precache route wins) and would be redundant. The storage-bounding intent is fully met.
* **`utils/security.py` intentionally UNCHANGED.** The council allowed a minimal SPA-tier CSP change only "if Workbox needs it". It does not: external `registerSW.js` + same-origin SW satisfy `script-src 'self'` / `worker-src 'self' blob:` as staged in Phase 1. Existing CSP tests still assert no `unsafe-eval` / no `*`.
* **No install-prompt (`beforeinstallprompt`) UI** was added (plan 4.3 optional item). Browsers still surface the native install affordance from a valid manifest + SW; a custom prompt is deferred (see below).

## Deferrals

* **FU-PWA-1**: Playwright PWA/offline e2e (SW registers over HTTPS in a real browser; app shell loads with network disabled; TUS upload bypasses the SW verified via network inspection). Deferred — the current suite is server-side/unit; a browser harness with SW + offline emulation is follow-on test infrastructure (aligns with the still-open FU-2).
* **FU-PWA-2**: custom `beforeinstallprompt` UI + documented iOS "Add to Home Screen" path (plan 4.3). Native install works today from the manifest+SW.
* Production prerequisites unchanged from Phase 3: apply migrations, enable HTTPS.

## Validation Evidence

| Gate | Command | Result |
|------|---------|--------|
| SPA install | `npm install -D vite-plugin-pwa` | added (v1.3.0) |
| SPA build | `cd frontend/spa; npm run build` | **built**; emitted `dist/sw.js`, `dist/workbox-b80311bd.js`, `dist/registerSW.js`, `dist/manifest.webmanifest`, precache **16 entries (695 KiB)** |
| SPA lint | `npm run lint` (`--max-warnings 0`) | **0 warnings** |
| SPA test | `npm run test` (vitest) | **83 passed** (8 files; +9 PWA) |
| Backend tests | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **61 passed** (CSP tests incl.) |
| Ruff | `ruff check frontend/spa_serving.py …/generate_icons.py` | All checks passed |
| Black | `black frontend/spa_serving.py …/generate_icons.py` | formatted, then clean |
| App import | production `AlbumsAventures-BE.py` imported | clean — **108 routes** |
| Serving (TestClient) | `/app/sw.js`, `/app/manifest.webmanifest`, `/app/registerSW.js`, `/app/icons/*`, deep-link, traversal, `/be_auth/me` | SW `text/javascript`+`no-cache`; manifest `application/manifest+json` scope `/app/`; icon `image/png`; deep-link 200 HTML `no-store`; traversal **404 (no leak)**; `/be_auth/me` **401 (not shadowed)** |

## Release Summary

* **Files changed**: 6 added (pwaConfig.ts, pwaConfig.test.ts, generate_icons.py, 4 icons counted as one group) + 6 modified (vite.config.ts, index.html, RequireAuth.tsx, spa_serving.py, package.json, package-lock.json). No files removed.
* **Security posture**: unchanged/preserved — CSP untouched (no `unsafe-eval`, no `*`); SW never caches auth/API (`/be_*` NetworkOnly) and never intercepts the TUS stack; media caches are quota-bounded; traversal-guarded serving.
* **Goal #4 (PWA)**: DELIVERED — installable (manifest + icons + SW over secure context), offline app shell precached, deploy-deterministic auto-update.
* **No deployment / push / merge / migration** performed — local edits only.
