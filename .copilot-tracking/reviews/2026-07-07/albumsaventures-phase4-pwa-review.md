<!-- markdownlint-disable-file -->
# Review: Phase 4 — PWA Conversion (installable + offline app shell)

**Reviewer**: `tester` role (member Delta) — Review stage, FINAL phase
**Review Date**: 2026-07-07
**Related Plan**: `.copilot-tracking/plans/albumsaventures-modernization.md` (Phase 4)
**Handoff Contract**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment8-changes.md` (Phase 4 PWA Handoff Note)
**Change Record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase4-pwa-changes.md`
**Research**: n/a (handoff contract + change record serve as source of truth)

## Verdict: ✅ APPROVE

All 8 review items **PASS**. Every mandatory service-worker council condition is verified against the **GENERATED** `frontend/spa/dist/sw.js` (built during this review), not merely the source config. **None** of the Request-changes triggers were hit: TUS is not cached; auth/API is `NetworkOnly` (never stale-served); every media cache is bounded; CSP is unchanged with no inline script; the SW does not shadow the API. Two non-blocking cosmetic follow-ups noted (Low). Modernization goal #4 is delivered.

## Service-Worker Council-Condition Compliance Matrix

Evidence quoted from the **generated** `dist/sw.js` (built this review; 2871 bytes, `generateSW` + `importScripts("./workbox-b80311bd.js")`), the generated `registerSW.js`, `manifest.webmanifest`, `dist/index.html`, and live `TestClient` serving.

| # | Council condition | Result | Evidence from GENERATED artifacts |
|---|-------------------|--------|-----------------------------------|
| 1 | **TUS bypass** — `/be_resizer/tus/` (and `/be_resizer/`) never cached + excluded from nav fallback | ✅ **PASS** | Generated sw.js: `registerRoute(/^\/be_resizer\//, new NetworkOnly({cacheName:"be-resizer-networkonly",plugins:[]}), "GET")` — declared FIRST runtime route, `plugins:[]` (no cache read/write). Nav `denylist:[/^\/be_/,...]` excludes `/be_resizer/` from the shell fallback. **Nuance (strengthens):** routes are `"GET"`-scoped; TUS POST/PATCH/HEAD are not matched by Workbox routing at all → pass natively to network. Both GET (NetworkOnly) and non-GET (native) reach the network untouched; no TUS response is ever cached. |
| 2 | **Auth/API never cached** — `/be_auth/*`, `/be_album|be_user|be_group|be_category/*` never CacheFirst/SWR | ✅ **PASS** | Generated sw.js: `registerRoute(/^\/be_/, new NetworkOnly({cacheName:"be-api-networkonly",plugins:[]}), "GET")`. `/^\/be_/` covers all five families; `NetworkOnly` (no-store) is strictly stronger than the `NetworkFirst` floor the council allowed → a logout/session change cannot leak a prior user's JSON from cache. No `be_*` route uses a caching handler. Live: `GET /be_auth/me` → **401 not shadowed**. |
| 3 | **Bounded media cache** — `/images`, `/thumbnails`, `/static`, `/app/assets/*` LRU + max-age | ✅ **PASS** | Generated sw.js: `/images/` → `CacheFirst` + `ExpirationPlugin({maxEntries:200,maxAgeSeconds:2592e3,purgeOnQuotaError:!0})`; `/thumbnails/` → `StaleWhileRevalidate` + `ExpirationPlugin({500,2592e3,purge})`; `/static/` → `StaleWhileRevalidate` + `ExpirationPlugin({60,2592e3,purge})`; each also `CacheableResponsePlugin({statuses:[0,200]})`. `/app/assets/*` served by the **precache** (revisioned, `cleanupOutdatedCaches`) — bounded + self-invalidating, correctly no runtime rule. No unbounded cache exists. |
| 4 | **SW versioning** — build-hash revisioned precache; explicit skipWaiting/clientsClaim; no stale shell vs API | ✅ **PASS** | Generated sw.js: `self.skipWaiting(), e.clientsClaim(), e.precacheAndRoute([...])` with md5 `revision` on `index.html`/`manifest`/icons/registerSW and `revision:null` on content-hashed assets; `e.cleanupOutdatedCaches()`. `registerType:"autoUpdate"`. **Auto-update choice is sound here**: shell is `no-store` (always re-fetches newest hashed asset refs) and ALL `/be_*` is `NetworkOnly` (no cached API state), so the classic "stale shell vs changed API" desync cannot occur. |
| 5 | **Offline shell + no redirect loop** — `/app` shell precached; `RequireAuth` shows offline state, no hard `/login` redirect | ✅ **PASS** | Generated sw.js: `NavigationRoute(createHandlerBoundToURL("index.html"), {allowlist:[/^\/app\//], denylist:[/^\/be_/,/^\/images\//,/^\/thumbnails\//,/^\/static\//]})`; `index.html` precached (rev `2397ea88…`). `RequireAuth.tsx`: `useOnlineStatus()` → when `isError && !online` renders an OFFLINE state with a `refetch()` retry, **never** redirects to `/login` (only a genuine `UnauthorizedError` 401 or empty session redirects). Live deep-link `GET /app/albums/42` → 200 HTML `no-store`. |
| 6 | **CSP intact** — external `registerSW.js` (no inline script); `worker-src 'self' blob:`; no `unsafe-eval`/`*` | ✅ **PASS** | Generated `dist/index.html` injects `<script id="vite-plugin-pwa:register-sw" src="/app/registerSW.js"></script>` — EXTERNAL `src`, no inline body → `script-src 'self'` holds. `registerSW.js` is a separate same-origin file. `utils/security.py` UNCHANGED; backend CSP tests (`test_csp_never_allows_unsafe_eval_or_wildcard`, `test_spa_csp_is_tightened_same_origin_only`) among the **61 passing**. `injectRegister:"script"` asserted by vitest COUNCIL 6. |
| 7 | **FastAPI serving/scope** — SW at `/app/sw.js` (scope `/app/`); manifest `application/manifest+json`; no `/be_*` shadow; traversal guarded | ✅ **PASS** | Live TestClient: `/app/sw.js` → 200 `text/javascript` `no-cache`; `/app/manifest.webmanifest` → 200 `application/manifest+json`; `/app/registerSW.js` → 200 `text/javascript`; `/app/icons/icon-192.png` → 200 `image/png`; deep-link → 200 HTML `no-store`; traversal `/app/../../utils/security.py` → **404, no SECRET leaked**; `/be_auth/me` → **401 (not shadowed)**. `registerSW.js` registers `('/app/sw.js', {scope:'/app/'})`. `_safe_dist_file` traversal guard (resolved candidate must have `dist/` as parent). App imports clean — **108 routes**. |
| 8 | **Manifest + icons** — valid manifest; real PNG icons 192/512/maskable | ✅ **PASS** | `manifest.webmanifest`: `name`/`short_name` "AlbumsAventures", `start_url` `/app/`, `display` `standalone`, `scope` `/app/`, `theme_color` `#0ea5e9`, `background_color` `#ffffff`, `lang` `fr`, 3 icons. PIL-verified real PNGs: `icon-192.png` (192,192), `icon-512.png` (512,512), `icon-maskable-512.png` (512,512 maskable), `apple-touch-icon.png` (180,180). |

## Request-Changes Trigger Audit (all clear)

| Trigger | Present? | Evidence |
|---------|----------|----------|
| TUS cached | ❌ No | `/be_resizer/` → `NetworkOnly`, `plugins:[]`; non-GET not routed |
| Auth/API cached with stale-serving strategy | ❌ No | `/be_/` → `NetworkOnly` (not CacheFirst/SWR/NetworkFirst) |
| Unbounded media cache | ❌ No | every media rule carries `ExpirationPlugin` (maxEntries + maxAge + purge) |
| CSP regression | ❌ No | external `registerSW.js`, no inline script; `utils/security.py` untouched; 61 CSP-inclusive tests pass |
| SW shadowing the API | ❌ No | all PWA files under `/app`; `/be_auth/me` → 401 live |

## Validation Gate Results

| Gate | Command | Expected | Actual | Status |
|------|---------|----------|--------|--------|
| SPA build | `cd frontend/spa; npm run build` | sw.js + manifest.webmanifest + registerSW.js emitted | Emitted `dist/sw.js`, `dist/workbox-b80311bd.js`, `dist/registerSW.js`, `dist/manifest.webmanifest`; precache **16 entries (695.95 KiB)** | ✅ |
| SPA lint | `npm run lint` (`--max-warnings 0`) | 0 warnings | **0 warnings** | ✅ |
| SPA test | `npm run test` (vitest) | 83 | **83 passed** (8 files, incl. 9 PWA COUNCIL cases) | ✅ |
| Backend test | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | 61 | **61 passed** (CSP tests incl.) | ✅ |
| App import | production `AlbumsAventures-BE.py` imported | clean | clean — **108 routes** | ✅ |
| Serving (TestClient) | sw.js / manifest / registerSW / icons / deep-link / traversal / be_auth | correct types + no shadow | all correct (see item 7) | ✅ |

## Per-Item Results

1. **TUS bypass** — PASS (generated sw.js NetworkOnly + nav denylist + GET-method scoping).
2. **Auth/API never cached** — PASS (generated sw.js `/be_/` NetworkOnly; live 401 not shadowed).
3. **Bounded media cache** — PASS (generated sw.js ExpirationPlugin on all three; assets via precache).
4. **SW versioning** — PASS (revisioned precache, skipWaiting/clientsClaim/cleanup; autoUpdate justified).
5. **Offline shell + no loop** — PASS (precached shell, scoped nav fallback, `RequireAuth` offline state).
6. **CSP intact** — PASS (external registerSW, no inline; security.py unchanged; CSP tests pass).
7. **FastAPI serving/scope** — PASS (correct media types, `/app`-scoped, no `/be_*` shadow, traversal 404).
8. **Manifest + icons** — PASS (valid manifest; PIL-verified 192/512/maskable/apple PNGs).

## Findings

**Severity counts** — Critical: 0 · High: 0 · Medium: 0 · Low: 2

- **Low / cosmetic (FU-PWA-R1)**: The generated precache lists the four icons + `manifest.webmanifest` **twice** (once from `workbox.globPatterns` matching `png`/`webmanifest`, once from `includeAssets`). Because each duplicate carries an identical `revision`, Workbox dedupes silently (no `add-to-cache-list-conflicting-entries` error, no runtime effect). Optional tidy-up: drop the overlap from `includeAssets` or narrow `globPatterns`. Non-blocking.
- **Low / doc nuance (FU-PWA-R2)**: The change record's traversal note reads "404, no file leaked"; the observed 404 is because the HTTP client normalizes `/app/../../utils/security.py` to `/utils/security.py` (an unrouted path) before it reaches `serve_spa`. The server-side `_safe_dist_file` guard independently returns `None` for out-of-`dist/` candidates (falling through to the shell, never the traversed file). The security property (no file leak) holds via two independent mechanisms; the record could clarify the mechanism. Non-blocking.

## Missing Work / Deviations (accepted, from change record)

- `/app/assets/*` handled by precache rather than a discrete runtime rule — **correct** (precache is bounded + self-invalidating; a runtime rule would never match). Storage-bounding intent met.
- `utils/security.py` intentionally UNCHANGED — external registerSW + same-origin SW satisfy the staged Phase 1 CSP; no change needed. Correct.
- No `beforeinstallprompt` custom UI — plan 4.3 optional; native install works from manifest+SW. Deferred (FU-PWA-2).

## Follow-Up Work

**Deferred from scope (carried by developer):**
- **FU-PWA-1**: Playwright PWA/offline e2e (SW registers over HTTPS in a real browser; app shell loads with network disabled; TUS upload bypass verified via network inspection). Aligns with plan 4.2 acceptance and the open FU-2 browser-harness gap. Recommended before production sign-off since offline behaviour and real SW registration are only exercised in a browser.
- **FU-PWA-2**: custom `beforeinstallprompt` UI + documented iOS "Add to Home Screen" path (plan 4.3).
- Production prerequisites (unchanged): apply migrations, enable HTTPS/HSTS (Phase 1 staged) — SW registration and installability require the secure context in prod.

**Discovered during review:**
- **FU-PWA-R1**: de-duplicate precache icon/manifest entries (cosmetic).
- **FU-PWA-R2**: clarify traversal-404 mechanism in the change record (doc).

## Overall Phase-4 / Modernization Assessment

Phase 4 **completes the four-goal modernization** (security → upload reliability → frontend → PWA). The service worker is the highest-risk artifact of the phase (a mis-scoped cache is a silent auth-correctness or upload-integrity hazard), and every council condition was verified against the **compiled** `dist/sw.js` rather than intent — the strongest available evidence. The design is defensively layered: `NetworkOnly` for the entire `/be_*` surface plus GET-method route scoping means neither cached nor non-idempotent API/upload traffic can be served stale or intercepted; media caches are quota-bounded with quota-error self-healing; the SW is tightly scoped to `/app/` and provably does not shadow `/be_*`, the TUS stack, or the media mounts; and CSP was satisfied with **zero** change by choosing external SW registration. Auto-update is a justified simplification given the `no-store` shell + `NetworkOnly` API invariants. The two follow-ups are cosmetic/documentation and do not affect correctness or security.

Recommendation: **APPROVE** and land. Sequence FU-PWA-1 (browser/offline e2e) into the Phase 5 final-validation gate before production, alongside the standing HTTPS + migration prerequisites.
