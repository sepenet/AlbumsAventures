<!-- markdownlint-disable-file -->
# Implementation Plan: AlbumsAventures Modernization (Security, Upload Reliability, Frontend, PWA)

Author: squad `lead` role (member Beta). Grounded in `.copilot-tracking/research/2026-07-07/albumsaventures-modernization.md` (researcher, member Alpha). This plan sequences the four user goals, makes a concrete frontend recommendation, and flags council-gated decisions. It does NOT implement anything and does NOT decide items reserved for the pre-implementation council.

## Overview

Modernize the AlbumsAventures FastAPI + Jinja2 + Tailwind photo/video album app across four goals — security hardening, upload reliability, frontend framework modernization, and PWA conversion — sequenced so that HTTPS + secure-cookie security lands first (a hard prerequisite for both secure sessions and PWA installability), followed by upload reliability, then the frontend modernization, then PWA conversion.

## User Goals (from the French request)

1. **Modernize the front-end** and pick the best framework for the need.
2. **Secure the application.**
3. **Improve new-image upload reliability** (failures vary by bandwidth, network type, browser).
4. **Convert the app to a PWA.**

## Recommended Phase Ordering and Justification

The four goals are NOT independent; the research surfaces hard coupling that dictates the order:

1. **Phase 1 — Security hardening + HTTPS first.** Research Section D and E establish that HTTPS + `secure=True` cookies are a *prerequisite* for a PWA (service workers and installability require a secure context) and for safe production sessions. Open Question #8 states explicitly: "PWA cannot ship before HTTPS/`secure` cookies are on." Security also has the lowest blast radius (config/middleware changes, no template rewrites) and fixes a live authz correctness bug (`is_superuser`, #485). Doing it first de-risks everything downstream.
2. **Phase 2 — Upload reliability second.** This is the user's most concrete pain point ("uploads fail depending on bandwidth/network/browser") and is *independent of the framework choice* — the TUS/Uppy upload page can be improved in place on the current Jinja2 stack. Delivering this early gives the user value without waiting on the larger frontend decision. It depends on Phase 1 only for the production HTTPS/proxy context that upload tuning assumes.
3. **Phase 3 — Frontend framework modernization third.** This is the largest, highest-uncertainty change and is *gated by a council decision* (architect + cost-manager). Sequencing it after security and upload means the framework work builds on a hardened, reliable base rather than modernizing a moving target. The Tailwind production build introduced here is a shared prerequisite for the PWA asset pipeline.
4. **Phase 4 — PWA conversion last.** PWA depends on BOTH Phase 1 (HTTPS + secure context) and Phase 3 (the asset/build pipeline that generates and versions the service worker and app-shell precache). The service-worker caching strategy must also respect the upload stack from Phase 2 (must not intercept `/be_resizer/tus/`). PWA therefore sits at the end of the dependency chain.
5. **Phase 5 — Final validation** across the full pytest + Playwright + ruff/black suite.

```
Phase 1 (Security + HTTPS) ──► Phase 2 (Upload reliability)
        │                              │
        └──────────────┬───────────────┘
                       ▼
        Phase 3 (Frontend + Tailwind build) ──► Phase 4 (PWA) ──► Phase 5 (Validation)
```

## Frontend Framework Recommendation

### Recommendation: Option (a) — Keep server-rendered progressive enhancement (HTMX + Alpine.js) with a Tailwind CLI build and pinned/bundled assets.

Given THIS project's specific shape — FastAPI + Jinja2 + Tailwind, a clean `be_*` JSON API already in place, **no build step today**, a **small/solo team**, and a **photo/video-heavy** UI — Option (a) is the strongest fit:

* **Lowest migration cost, highest reuse.** All 14 Jinja2 templates and the `docs/GUIDELINES_UI.md` conventions carry forward unchanged. A SPA (Option b) or islands/Node tier (Option c) forces re-implementing 14 pages and adds a second runtime and deploy pipeline — heavy for one maintainer (research Section B, cons).
* **Preserves the same-origin auth model.** The app uses HttpOnly cookie + double-submit CSRF (`utils/csrf.py`, `backend/routers/be_auth.py`). Research Section B notes this "strongly favors same-origin serving; a cross-origin SPA increases security surface." Staying server-rendered keeps CSRF/SameSite simple and avoids cross-origin CORS/CSRF rework.
* **PWA is fully achievable without a SPA.** Research Section E confirms "manifest + service worker work with any HTML." A component framework is not required to ship an installable, offline-capable PWA.
* **Aligns with the already-chosen direction.** README documents the "variante hybride" (Jinja2 + Tailwind + Alpine + Uppy) as the deliberate choice (TODO #010, done). HTMX adds partial-HTML swaps for the few rich interactions (galleries, admin, upload dashboard) that Alpine alone handles awkwardly — closing the main gap cited in Option (a) cons.
* **Addresses Option (a)'s stated cons directly.** The plan pairs HTMX with a **Tailwind CLI build** (replacing the CDN, required in *every* option per research) and **pinned + SRI'd or locally-bundled Alpine/HTMX/Uppy** assets — resolving the supply-chain/reproducibility risk and enabling a workable CSP.

### What this recommendation deliberately does NOT do

* It does NOT introduce React/Vue/Svelte/Astro or a Node build tier. The interactivity ceiling of those frameworks (research Section B, Option b/c pros) is not justified by this app's needs versus the solo-maintainer operational cost.
* It leaves the **loopback-HTTP coupling** (`fe_router` → `httpx` → `localhost:8003`, research Open Question #3) as an *optional, separately-scoped* refactor — not required for this modernization and flagged for the architect.

### Council gate

**This framework choice is a council-relevant decision.** The **architect** must validate the HTMX-vs-SPA architectural tradeoff and the same-origin decision (Open Questions #1, #2, #3); the **cost-manager** must validate the solo-maintainer operational cost of each option. The recommendation above is the `lead`'s proposal, not a final decision — the council confirms or overrides it before Phase 3 begins.

---

## Phase 1: Security Hardening + HTTPS (foundation)

<!-- parallelizable: false -->
Dependency: none. Blocks Phases 2 (prod context), 4 (PWA secure context). **Council gate: security role must confirm the hardening scope before implementation.**

### 1.1 — Enable secure transport and secure cookies

* Set the auth cookie to `secure=True` in production — `backend/routers/be_auth.py` (lines 536-543, the `TODO: mettre True en production`).
* Set the CSRF cookie to `secure=True` in production — `utils/csrf.py` (lines 44-52, the `TODO: passer à True en production`).
* Drive the flag from config/environment (dev = False, prod = True) rather than a hardcoded literal, reading through the existing `utils/config.py` / `utils/secret_store.py` pattern.
* **Acceptance:** In a prod-config run, both `access_token` and CSRF cookies carry `Secure`; dev (Windows/SQLite) still works over HTTP. Verified by inspecting `Set-Cookie` headers in a Playwright login flow against a prod-config instance.

### 1.2 — Add HTTPS redirect, HSTS, TrustedHost, and security-headers/CSP middleware

* Add `HTTPSRedirectMiddleware` (or reverse-proxy-aware equivalent), HSTS, and `TrustedHostMiddleware` in `AlbumsAventures-BE.py` (currently only `CORSMiddleware` at lines 100-116).
* Add a security-headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a **CSP**. Research Section D warns the CSP must accommodate current inline `<script>` blocks and CDN assets — coordinate CSP with the asset-pinning work (1.5) and the Tailwind build (Phase 3).
* **Acceptance:** Security-header middleware present; response headers include CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. CSP is compatible with current templates (no console CSP violations on core pages in Playwright). All e2e specs still pass.

### 1.3 — Fix `is_superuser` propagation (bug #485)

* Include `is_superuser` in `create_access_token` claims and return it from `get_current_user()` — `backend/routers/be_auth.py` (lines 91-100, 278-300). Research Section D: current superuser checks (e.g. `be_resizer.py` line 741) always evaluate False.
* **Acceptance:** JWT carries `is_superuser`; `get_current_user()` exposes it; a superuser passes superuser-gated checks. New pytest cases in `tests/test_auth.py` assert both the claim and an authz path that depends on it. Admin Playwright specs (`admin_users`, `admin_groups`) still pass.

### 1.4 — Move rate limiting to a durable/shared store

* Replace the in-memory `defaultdict` rate limiter (`backend/routers/be_auth.py` lines 126-190, 510-531) with a shared backend (e.g. Redis) so limits survive restarts and work across workers. Research Section D flags the current state as "process-local and volatile."
* Keep the existing thresholds from `utils/config.py` `rate_limiting`.
* **Acceptance:** Rate-limit counters persist across an app restart and are shared across workers; login and PIN-share brute-force limits enforce after N attempts. **Note:** the choice of durable store (Redis vs alternative) is a council/architect input — surface it, do not unilaterally pick infra.

### 1.5 — Pin, SRI, or bundle CDN assets

* Add version pinning + SRI to (or locally bundle) Tailwind, Alpine `3.x.x`, Uppy, and any `unpkg` assets — `frontend/templates/base.html` (lines 7-11, 110), `album_upload.html`. Research Section D: current CDN assets have "no SRI and loose/no version pinning."
* **Acceptance:** No unpinned CDN script tags remain; each retained CDN asset has an `integrity` hash, or the asset is served locally. Feeds the CSP in 1.2.

### 1.6 — (Surface, do not decide) Refresh-token strategy (#490) and CSRF/SameSite coverage audit

* Flag TODO #490 (no refresh tokens) and the research note that mutating `fetch`/TUS endpoints rely on `SameSite` rather than a CSRF token — **security role to confirm coverage of all mutating endpoints**. Documented here as a council/security input, not implemented in this phase unless the council scopes it in.

### Phase 1 validation

* `ruff check` + `black --check` on changed files.
* `pytest tests/test_auth.py` (new `is_superuser` and cookie/rate-limit cases).
* `pytest -m e2e tests/e2e` for login, admin users, admin groups, shared album (CSP/cookie regressions).

---

## Phase 2: Upload Reliability

<!-- parallelizable: false -->
Dependency: Phase 1 (production HTTPS/proxy context). Independent of the framework decision — implemented on the current Jinja2 upload page. Must preserve the Windows `win_fcntl_shim` path (research Open Question #10).

### 2.1 — Add resume-after-reload (`@uppy/golden-retriever`, TODO #394)

* Enable Golden Retriever so a reload / tab crash / mobile app-switch resumes in-progress TUS uploads (server state already persists on disk) — `frontend/templates/album_upload.html` (TUS config lines 193-205). Research Section C, gap #1.
* **Acceptance:** Reloading mid-upload resumes rather than restarting; verified by a Playwright e2e that interrupts and reloads during an upload.

### 2.2 — Migrate Uppy v3.27 (EOL) → v5 (TODO #393)

* Upgrade Uppy to v5 (ESM, `@uppy/locales/fr_FR`, CSP updates) — `album_upload.html` (CSS line 6, JS line 100). Coordinate CSP changes with Phase 1.2 and asset pinning 1.5. Research Section C, gap #2.
* **Acceptance:** Upload page runs on Uppy v5 with French locale; dashboard, restrictions, and TUS behavior preserved; no CSP violations; upload e2e passes.

### 2.3 — Surface post-processing (thumbnail) status instead of swallowing failures

* Add a status/queue signal the UI can poll so a `204`-succeeded upload with a *failed* thumbnail is visible to the user — `backend/routers/be_resizer.py` (fire-and-forget daemon thread, lines 810-849). Research Section C, gap #3. Keep the fast-`204` behavior that protects mobile carriers (lines 810-818). **The processing model (keep daemon thread vs task queue) is Open Question #5 — surface the queue option for the architect; implement the minimal status-surfacing that does not require infra unless the council scopes a queue.**
* **Acceptance:** After upload, the UI reflects thumbnail success/failure per file (not just uploaded/failed counts); a forced thumbnail failure is reported to the user.

### 2.4 — Network-adaptive chunk sizing

* Replace the fixed `chunkSize: 256*1024` with adaptive sizing (small on constrained mobile, larger on good links) — `album_upload.html` (line 196). Preserve the 256 KB floor for the Edge-Android/Caddy carrier-NAT case documented in the code comment. Research Section C, gap #4.
* **Acceptance:** Chunk size adapts to connection quality while never dropping below the documented mobile-safe floor; large uploads on good links complete with fewer round-trips; mobile reliability unchanged.

### 2.5 — Client-side image compression before upload (#380)

* Add pre-upload client compression — research explicitly notes (#380, Section F) this "may deliver the biggest reliability win on mobile." `album_upload.html`. Respect existing size limits (`MAX_IMAGE_SIZE` 30 MB, `be_resizer.py` lines 27-30).
* **Acceptance:** Oversized photos are downscaled/compressed client-side before TUS transfer; upload payloads shrink measurably on mobile; image quality remains acceptable. Included because it directly targets the user's stated bandwidth/network pain.

### 2.6 — Resolve the legacy XHR upload path (#395)

* Decide (retire vs keep as documented fallback) the legacy `POST /be_resizer/upload_images/{album_id}` — `be_resizer.py` (lines 465-484). Research Section C, gap #9. Removing it reduces surface area; keeping it needs justification. **Surface the retire-vs-fallback tradeoff for the architect**; default recommendation is retire once TUS + golden-retriever cover the reliability cases.
* **Acceptance:** Exactly one documented, tested upload path in production; if the legacy endpoint is retained, its role is documented and covered by a test.

### 2.7 — Codify reverse-proxy / TUS timeout + body-size config

* Capture the Caddy timeout / `client_max_body_size` / TUS `Upload-Expires` settings referenced in code comments (`be_resizer.py` lines 810-818) into a repo-tracked config/doc. Research Section C, gap #5; Open Question #6. **Where this config lives (repo vs infra) is an architect input — surface it.**
* **Acceptance:** Proxy/TUS timeout and body-size values are documented in-repo and consistent with the client chunk/retry settings.

### Phase 2 validation

* `ruff check` + `black --check` on changed files.
* `pytest tests/test_upload.py` (chunk/compression/status changes; keep Windows-shim path green).
* `pytest -m e2e tests/e2e` upload spec, including the new interrupt/reload resume case.

---

## Phase 3: Frontend Modernization (HTMX + Alpine + Tailwind build)

<!-- parallelizable: false -->
Dependency: Phases 1-2. **Council gate: architect + cost-manager must confirm the framework recommendation (Option a) before this phase starts.** If the council overrides to Option (b)/(c), this phase is re-planned.

### 3.1 — Introduce a Tailwind CLI production build (replace CDN)

* Add a minimal Tailwind CLI build (input CSS + config + purge) that outputs a hashed stylesheet served locally; remove the `https://cdn.tailwindcss.com` tag — `frontend/templates/base.html` (lines 7-11, comment "remplacer par build Tailwind en production"). Required in every framework option (research Section B, cross-cutting). This build is also the PWA app-shell asset source (Phase 4).
* **Acceptance:** Pages render from a locally-built, purged Tailwind stylesheet; no Tailwind CDN tag remains; CSP (Phase 1.2) allows the local stylesheet; visual parity verified via Playwright screenshots/specs.

### 3.2 — Add HTMX for partial-HTML interactions; keep Alpine for local state

* Introduce HTMX (pinned/SRI'd or bundled per 1.5) for partial swaps on the highest-friction pages (galleries `index.html`/`album_detail.html`, admin, upload dashboard); retain Alpine for `x-data`/stores (`base.html` lines 30-99). Preserve `docs/GUIDELINES_UI.md` conventions.
* **Acceptance:** At least the target interaction (e.g. gallery/admin partial update) works via HTMX without a full reload; existing Alpine stores and the login-guard behavior (`base.html` lines 101-136) still function; all e2e specs pass.

### 3.3 — (Surface, do not decide) Loopback-HTTP coupling refactor

* Flag the `fe_router` → `httpx` → `localhost:8003` self-call pattern (research Section A "Coupling assessment"; Open Question #3) as an architect decision. Not implemented here unless the council scopes it in.

### Phase 3 validation

* `ruff check` + `black --check`.
* `pytest -m e2e tests/e2e` full suite (navigation, album, profile, admin, login, shared album) for parity after CDN→build and HTMX changes.

---

## Phase 4: PWA Conversion

<!-- parallelizable: false -->
Dependency: Phase 1 (HTTPS/secure context — hard blocker) AND Phase 3 (build pipeline for SW generation + app-shell precache). Must respect Phase 2 upload stack.

### 4.1 — Web app manifest + icon set

* Add `manifest.webmanifest` (name, `start_url`, `display: standalone`, theme/background colors) and generate a maskable multi-size icon set + Apple touch icons — `frontend/static/` currently holds only `favicon.ico` (research Section E).
* **Acceptance:** Manifest served and linked; Lighthouse "installable" criteria met (given HTTPS from Phase 1); icons present for Android + iOS.

### 4.2 — Service worker with photo-aware caching

* Add a service worker that precaches the app shell (built HTML/CSS/JS from Phase 3) and uses a **size-bounded runtime cache** (stale-while-revalidate or cache-first with quota + eviction) for `/images`, `/thumbnails`, `/static` (research Section E). The SW **must NOT intercept or cache `/be_resizer/tus/` POST/PATCH traffic** (research Section E, explicit).
* **Acceptance:** SW registers over HTTPS; app shell loads offline; media cache respects an explicit quota/eviction policy; TUS upload traffic bypasses the SW entirely (verified via network inspection during an upload).

### 4.3 — Offline UX + install prompt + SW-aware login guard

* Add an offline fallback page and `beforeinstallprompt` handling; make the `DOMContentLoaded` `checkSession()` → `/login` redirect SW-aware so it does not misbehave offline — `base.html` (lines 101-136; research Section E flags this redirect).
* **Acceptance:** Offline navigation shows the fallback (not a broken redirect loop); install prompt works on supported browsers; iOS install path documented.

### 4.4 — (Surface, do not decide) PWA scope

* Full offline album browsing vs "installable + app-shell cache" first pass is Open Question #7 — **surface the scope + storage-quota policy for the council**; default recommendation is the lighter app-shell-first pass, with bounded media caching.

### Phase 4 validation

* `ruff check` + `black --check`.
* Playwright checks for SW registration, offline fallback, and TUS-bypass; Lighthouse PWA audit (installable, HTTPS, manifest, SW).

---

## Phase 5: Final Validation

<!-- parallelizable: false -->
Dependency: all prior phases.

* Run the full project quality gate: `ruff check .`, `black --check .`, `pytest` (all unit tests), `pytest -m e2e tests/e2e` (all 7 UI specs + new upload/PWA cases).
* Iterate on minor fixes inline (lint/format/small test breaks).
* For any failure needing more than a minor fix, document it and hand back to research/planning rather than large-scale inline refactoring.
* **Acceptance:** Green ruff/black, green pytest unit suite, green Playwright e2e; Windows/SQLite dev loop still works (`win_fcntl_shim` intact).

---

## Council-Relevant Decisions (surfaced, NOT decided here)

| # | Decision | Council role(s) | Research ref |
|---|----------|-----------------|--------------|
| C-1 | Frontend framework: adopt `lead` recommendation Option (a) HTMX+Alpine+Tailwind-build, or override to SPA (b) / islands (c) | **architect + cost-manager** | Open Q #1, #2; Section B |
| C-2 | Same-origin vs split-origin serving (auth/CSRF scope) | architect + security | Open Q #2 |
| C-3 | Security hardening scope: HTTPS + secure cookies + HSTS/TrustedHost + CSP + durable rate limiting + `is_superuser` #485 + refresh tokens #490 | **security** | Open Q #8; Section D |
| C-4 | Durable rate-limit store choice (Redis vs alternative) | architect + cost-manager | Section D |
| C-5 | Post-upload processing model: keep daemon thread vs task queue + status endpoint | architect | Open Q #5 |
| C-6 | Legacy XHR endpoint (#395): retire vs documented fallback | architect | Section C gap #9 |
| C-7 | Proxy/TUS config location: repo vs infra | architect | Open Q #6 |
| C-8 | Loopback-HTTP coupling refactor: in scope now or deferred | architect | Open Q #3 |
| C-9 | PWA scope: full offline browsing vs app-shell-first + quota policy | architect + cost-manager | Open Q #7 |
| C-10 | AI/ML involvement (RAI) | **rai** | see below |

### RAI note (C-10)

The app uses **OpenCV + Pillow** for image/video **processing** — EXIF-orientation correction, thumbnail generation, video frame extraction (`backend/routers/be_resizer.py`). This is deterministic image manipulation, **not ML-model inference** (no classification, generation, face/object detection, or trained model). On the current evidence there is **no AI/ML in scope** for RAI review. **Flag to the RAI role to confirm** this assessment — if any future feature adds model inference (e.g. auto-tagging, content moderation), RAI review would then apply.

## Validation Strategy Summary

Every phase uses the existing harness (research Section F):

* **Lint/format:** `ruff check` (E,W,F,I,B,UP; line-length 120) + `black --check` — `pyproject.toml`.
* **Unit:** `pytest` against `tests/test_auth.py`, `tests/test_upload.py`, `tests/test_albums.py` with new cases per phase.
* **E2E:** `pytest -m e2e tests/e2e` — the 7 Playwright specs (login, navigation, album, profile, admin users, admin groups, shared album) guard regressions; new specs added for upload resume, PWA SW registration, and offline fallback.
* **Windows parity:** every phase must keep the `win_fcntl_shim` dev loop (Windows + SQLite) working (Open Q #10).

## Dependencies

* Existing stack: Python ≥3.12, FastAPI/uvicorn, tuspyserver, Uppy, Tailwind, Alpine, Pillow/OpenCV, Playwright, ruff/black/pre-commit (`requirements.txt`, `pyproject.toml`).
* New (framework-recommendation-dependent): Tailwind CLI build toolchain (Phase 3); HTMX (Phase 3); `@uppy/golden-retriever` + Uppy v5 (Phase 2); a durable rate-limit store e.g. Redis (Phase 1.4, council-gated); Workbox or hand-written SW (Phase 4).
* Production HTTPS reverse proxy (Caddy, per code comments) — config captured in Phase 2.7.

## Success Criteria

* All four user goals delivered in dependency order, each phase green on ruff/black + pytest + Playwright.
* Security: prod runs with `secure` cookies, HTTPS redirect/HSTS/TrustedHost, CSP/security headers, durable rate limiting, correct `is_superuser` — Traces to: Goal 2, research Section D, Open Q #8.
* Upload: resume-after-reload, Uppy v5, surfaced thumbnail status, adaptive chunking, client compression, single upload path — Traces to: Goal 3, research Section C.
* Frontend: Tailwind production build + HTMX interactions, no unpinned CDN assets, same-origin auth preserved — Traces to: Goal 1, research Section B, `lead` recommendation.
* PWA: installable over HTTPS with manifest + SW, photo-aware bounded cache that bypasses `/be_resizer/tus/`, offline fallback — Traces to: Goal 4, research Section E.
* Council decisions C-1…C-10 surfaced and resolved before their gating phase; nothing council-reserved decided by this plan.
