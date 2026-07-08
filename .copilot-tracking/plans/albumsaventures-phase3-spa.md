<!-- markdownlint-disable-file -->
# Implementation Plan: AlbumsAventures Phase 3 — React SPA Migration (Option B)

Author: squad `lead` role (member Beta). Autopilot Turn 5.

**SUPERSEDES:** This document replaces **Phase 3 (Frontend Modernization — HTMX + Alpine + Tailwind build)** of `.copilot-tracking/plans/albumsaventures-modernization.md`. The parent plan's Phase 3.1/3.2/3.3 (HTMX + Alpine + Tailwind CLI build) is **withdrawn**. Phases 1, 2, 4 (PWA), and 5 (Validation) of the parent plan remain in force, with Phase 4 PWA handoff amended per Section 3.9 below.

**Decision provenance:** The user **overrode council recommendation C-1 Option (a)** (`lead`'s HTMX+Alpine+Tailwind-build proposal) and selected **Option (b) — a Single-Page Application**. This plan is built strictly around that confirmed decision. It does **NOT** re-open the framework question and does **NOT** implement anything.

Grounded in: `.copilot-tracking/research/2026-07-07/albumsaventures-modernization.md` (Sections A, B option (b), C, D, E), the parent plan, and Phase 1/Phase 2 delivered state (session memory: `phase1-security-plan.md`, `phase2-uploads-plan.md`, `phase2-scribe-completion.md`).

## Overview

Migrate the AlbumsAventures frontend from server-rendered Jinja2 + Alpine to a **React 18 + Vite + TypeScript SPA**, built to static assets and **served same-origin by the existing FastAPI process**, via an **incremental strangler migration** that converts one page at a time while every un-migrated Jinja2 page keeps working — preserving the HttpOnly-cookie + CSRF-double-submit auth model, adding no runtime hosting (Node is build-time only), and requiring no CORS.

## Confirmed Decision (plan around this — do NOT re-decide)

| Aspect | Confirmed choice | Consequence |
|--------|------------------|-------------|
| Framework | **React 18 + Vite + TypeScript** | Bundler unlocks Uppy v5 ESM (#393), tree-shaking, code-split |
| Serving | **Same-origin, served by FastAPI** | Vite builds to static assets; FastAPI serves SPA `index.html` + hashed assets under a static mount |
| Auth | **Keep HttpOnly cookie session + CSRF double-submit** | **NO tokens in `localStorage`/`sessionStorage`**; browser sends the cookie automatically |
| CORS | **None needed** | Same origin → no cross-origin preflight, no CORS relaxation |
| Node | **Build-time only** | **No new runtime hosting / no second server**; addresses cost-manager condition |
| Migration | **Incremental strangler, page-by-page** | Jinja2 fallbacks remain until each page is migrated; **no big-bang rewrite** |

## Objectives

### User Requirements

* Migrate the frontend to a React SPA (Option B). — Source: user override of council C-1, this turn.
* React 18 + Vite + TypeScript, served same-origin by FastAPI. — Source: confirmed decision, this turn.
* Keep HttpOnly cookie auth + CSRF double-submit; no tokens in localStorage; no CORS; Node build-time only. — Source: confirmed decision, this turn.
* Incremental strangler migration (page-by-page), Jinja2 keeps working during transition. — Source: confirmed decision, this turn.
* Reuse existing Tailwind design tokens from `docs/GUIDELINES_UI.md`. — Source: user request item 1.
* Upgrade upload page to React + Uppy v5, preserving all Phase 2 reliability work. — Source: user request item 5; research Section C; parent plan Phase 2 D2 deferral.
* Tighten Phase 1 CSP as assets localize (retire CDN allowances, prefer hashed/nonce local assets). — Source: user request item 6; `utils/security.py` "EXCEPTION TODO Phase 3".
* PWA handoff to Phase 4 (`vite-plugin-pwa`) respecting Phase 2 upload bypass and Phase 1 cache-partitioning. — Source: user request item 8.

### Derived Objectives

* **Retire the `fe_router` loopback-HTTP hop for migrated pages** — Derived from: research Open Q #3 / council C-8; the SPA calls `be_*` directly, removing the `httpx → localhost:8003` self-call for any page that no longer renders through Jinja2.
* **A shared SPA app-shell (routing, auth guard, API client, layout) landed once in 3.1** — Derived from: strangler pattern requires the shell to exist before the first page can mount; avoids per-page duplication.
* **A deterministic asset-manifest contract between Vite and FastAPI** — Derived from: same-origin serving of hashed filenames requires FastAPI to resolve the current build's entry file (Vite `manifest.json`) rather than a hardcoded path.
* **Per-page e2e spec updates gated on each increment** — Derived from: research Section F; the 7 Playwright specs guard regressions and must track the migrated surface page-by-page.

## Context Summary

### Prior-phase state this plan builds on

* **Phase 1 (Security) — DONE.** `utils/security.py` centralizes CSP + security headers for both prod and test apps. The CSP **already documents the Phase 3 exit**: `script-src`/`style-src` currently allow `'unsafe-inline'` + three CDNs (`cdn.tailwindcss.com`, `unpkg.com`, `releases.transloadit.com`) with an explicit "EXCEPTION TODO (à lever en Phase 3)" to move to `'self'` + nonces/hashes and drop the CDNs. `connect-src 'self'`, `worker-src 'self' blob:`, `manifest-src 'self'` are already set — same-origin SPA fetch and Phase 4 SW are already CSP-compatible.
* **Phase 2 (Upload reliability) — DONE, on Uppy v3.** Delivered on the v3.27 transloadit combined bundle: adaptive chunking (`selectChunkSize`, **256 KB floor / 8 MB cap**, server-authoritative via `GET /be_resizer/upload_config`), `@uppy/golden-retriever` (IndexedDB, `serviceWorker:false`), `@uppy/compressor` client compression (#380), durable per-file thumbnail status (`ImageProcessingStatus` model + `GET /be_resizer/processing_status/{album_id}` polling). **Uppy v3→v5 (#393) was explicitly deferred to Phase 3 because v5 is ESM-only (UMD global removed) and requires a bundler** — which this SPA provides.

### Project Files

* `frontend/routers/fe_router.py` - Jinja2 page router + server-side `require_auth`/`require_superuser` guards; httpx loopback data fetch. Un-migrated pages keep using it; migrated pages bypass it.
* `frontend/templates/` - 14 Jinja2 pages; each is a strangler-migration target (`index.html`, `album_detail.html`, `album_upload.html`, `profile.html`, `admin_users.html`, `admin_groups.html`, `shared_album.html`, auth pages).
* `frontend/static/` - existing StaticFiles source (`favicon.ico`, `images/` mounted at `/images`, `thumbnails/` at `/thumbnails`, `rando/`). SPA build output lands in a new subtree here (or a sibling mount).
* `AlbumsAventures-BE.py` (lines 118-138) - router includes + three StaticFiles mounts. The SPA static mount + SPA fallback route are added here, **after** all `be_*`/`fe_router` includes and **without** shadowing `/be_*` or `/be_resizer/tus/`.
* `utils/security.py` - CSP + security headers; the CDN retirement + nonce/hash tightening lands here (Section 3.9 / user item 6).
* `utils/csrf.py` - double-submit CSRF cookie (`httponly=False` so JS can read it; `samesite="strict"`). The React API client reads this cookie and echoes the header on mutations.
* `backend/routers/be_auth.py` - cookie session, `/be_auth/me`, `/be_auth/logout`; 401 on unauthenticated. React auth guard consumes these.
* `backend/routers/be_resizer.py` - `/be_resizer/tus/`, `/be_resizer/upload_config`, `/be_resizer/processing_status/{album_id}`. The React upload page calls these directly.
* `docs/GUIDELINES_UI.md` - Tailwind conventions/tokens to port into the Vite Tailwind config.
* `tests/e2e/` - 7 Playwright specs: `test_login_ui.py`, `test_navigation_ui.py`, `test_album_ui.py`, `test_profile_ui.py`, `test_admin_users_ui.py`, `test_admin_groups_ui.py`, `test_shared_album_ui.py`.

### References

* `.copilot-tracking/research/2026-07-07/albumsaventures-modernization.md` - Section B Option (b) SPA pros/cons; Section D auth/CSRF; Section E PWA; Open Q #2, #3.
* `.copilot-tracking/plans/albumsaventures-modernization.md` - parent plan; Phase 4 PWA, Phase 5 validation, council table C-1…C-10.

### Standards References

* `.github/copilot-instructions.md` — coding/security/pattern rules (all new TS/config obeys these).
* `docs/GUIDELINES_UI.md` — Tailwind design tokens/component conventions to reuse.

---

## Scale Statement

**This is a large, multi-increment effort.** A full 7-page SPA migration with an Uppy v5 upload rewrite and CSP tightening is far more than one implementation pass. This plan therefore decomposes Phase 3 into **9 numbered sub-phases**, each an independently shippable increment with its own acceptance criteria and validation. **Do not attempt the whole phase at once.** The recommended first increment (Section "Recommended First Increment") is **3.1 scaffold + 3.2 album grid only** — everything after 3.2 is a subsequent increment gated on the prior one landing green.

---

## Implementation Checklist

### [x] Phase 3.1: SPA Scaffold + App-Shell + Same-Origin Serving

<!-- parallelizable: false -->
Foundation increment. Blocks 3.2–3.9. No page behavior changes yet — Jinja2 still serves every page.

* [x] Step 3.1.1: Scaffold the Vite + React 18 + TypeScript app under `frontend/spa/`
  * `package.json`, `vite.config.ts`, `tsconfig.json`, React 18, TypeScript strict.
* [x] Step 3.1.2: Tailwind via PostCSS in the Vite build; port `docs/GUIDELINES_UI.md` tokens
  * `tailwind.config.ts` (darkMode `'class'`, color/spacing/badge tokens), `postcss.config.js`, single entry CSS. Replaces the Tailwind CDN for SPA pages.
* [x] Step 3.1.3: ESLint + Prettier + TS config aligned to repo conventions
* [x] Step 3.1.4: App-shell — router, layout, auth guard placeholder, dark-mode store
  * React Router; a `RequireAuth` wrapper; port the `base.html` login-guard semantics (401 → `/login`).
* [x] Step 3.1.5: FastAPI same-origin serving — static mount + SPA fallback route
  * Mount hashed assets; add a catch-all SPA route that returns `index.html` **only** for non-API paths; **must NOT shadow** `/be_*`, `/be_resizer/tus/`, `/images`, `/thumbnails`, `/static`. Served under the `/app` prefix (structural non-shadowing); FastAPI serves Vite's generated `index.html` verbatim.
* [x] Step 3.1.6: Vite→FastAPI asset-manifest contract (no hardcoded hashed filenames)
* [x] Step 3.1.7: Validate phase changes (see validation block)

**Acceptance 3.1:**

* `npm --prefix frontend/spa run build` produces hashed assets + a Vite `manifest.json`.
* Navigating to the SPA mount serves the React shell same-origin; refresh on a client route returns `index.html` (SPA fallback works).
* **Every existing Jinja2 page still renders unchanged** (`/`, `/album/...`, `/profile`, admin, shared — served by `fe_router`).
* The SPA fallback **does not intercept** any `/be_*` API call or `/be_resizer/tus/` traffic (verified by hitting an API route through the running app and confirming JSON, not HTML).
* Python `pytest` suite (50 tests) still green; `ruff`/`black` green on changed `.py`.

### [x] Phase 3.2: First Page — Album Grid / Main Page (`index.html`)

<!-- parallelizable: false -->
First real strangler increment. Depends on 3.1. **Recommended first page.**

* [x] Step 3.2.1: React album-grid page consuming `be_album` directly (no `fe_router` hop)
* [x] Step 3.2.2: Typed API client + React Query for the album list (server-state cache)
* [x] Step 3.2.3: Route `/` (or a feature-flagged path) to the React grid; keep the Jinja2 `index.html` as fallback behind the flag — implemented via the `/app` feature-flag prefix (Jinja `/` unchanged)
* [x] Step 3.2.4: Update `tests/e2e/test_navigation_ui.py` + `test_album_ui.py` for the migrated grid — added dedicated `tests/e2e/test_spa_album_grid_ui.py` (SPA at `/app`); existing Jinja specs left green
* [x] Step 3.2.5: Validate phase changes

**Acceptance 3.2:**

* The album grid renders in React, fetching `be_album` JSON directly (no `httpx` loopback for this page).
* Auth guard: unauthenticated load → redirect to login (401 handling from 3.1 exercised).
* Visual parity with the Jinja2 grid per `GUIDELINES_UI.md` tokens.
* `test_navigation_ui.py` + `test_album_ui.py` updated and green; other 5 specs unchanged and green.
* The Jinja2 `index.html` fallback still works when the flag is off.

### [x] Phase 3.3: Album Detail (`album_detail.html`)

<!-- parallelizable: false -->
Depends on 3.2 (shared API client + grid patterns).

* [x] Step 3.3.1: React album-detail page (gallery view) over `be_album`/`be_resizer` thumbnails
* [x] Step 3.3.2: Navigation grid→detail within the SPA router; deep-link/refresh works via SPA fallback
* [x] Step 3.3.3: Update `test_album_ui.py` for detail navigation — added dedicated `tests/e2e/test_spa_album_detail_ui.py` (SPA `/app/albums/:id`); existing Jinja specs left green
* [x] Step 3.3.4: Validate

**Acceptance 3.3:** Album detail renders in React with correct thumbnails/originals; SPA deep-link refresh works; `test_album_ui.py` green; un-migrated pages untouched.

### [x] Phase 3.4: Upload Page + Uppy v3→v5 (#393)

<!-- parallelizable: false -->
Depends on 3.3. **Highest-risk increment — preserves ALL Phase 2 reliability work.** LANDED + REVIEWED (Approve-with-followups); change record backfilled at `albumsaventures-phase3-spa-increment3-changes.md`.

* [x] Step 3.4.1: React upload page mounting Uppy **v5 (ESM)** via the Vite bundler
  * `@uppy/core`, `@uppy/dashboard`, `@uppy/tus`, `@uppy/golden-retriever`, `@uppy/compressor`, `@uppy/locales/fr_FR` as ESM deps.
* [x] Step 3.4.2: Re-wire Phase 2 reliability behaviors on v5:
  * golden-retriever resume-after-reload (IndexedDB); client compression (#380);
  * adaptive chunk sizing from `GET /be_resizer/upload_config` with the **256 KB floor / 8 MB cap** enforced client-side;
  * durable status polling of `GET /be_resizer/processing_status/{album_id}` with per-file thumbnail status + compression metric rendered.
* [x] Step 3.4.3: TUS endpoint unchanged (`/be_resizer/tus/`, `withCredentials`); metadata `album_id` preserved
* [x] Step 3.4.4: Update `tests/e2e` upload coverage (new/updated upload spec)
* [x] Step 3.4.5: Validate

**Acceptance 3.4:**

* Upload page runs on **Uppy v5 ESM** (no transloadit CDN bundle for this page).
* **All Phase 2 behaviors preserved:** resume-after-reload, client compression, adaptive chunk with 256 KB floor honored, durable per-file thumbnail status surfaced.
* TUS traffic still flows to `/be_resizer/tus/` with the cookie; `album_id` metadata intact.
* Windows dev loop intact (`win_fcntl_shim` path unaffected — no backend upload change).
* Upload e2e (interrupt/reload resume + status) green.

### [x] Phase 3.5: Profile (`profile.html`)

<!-- parallelizable: true -->
Independent of 3.6/3.7 once 3.4 patterns exist (mutations + CSRF).

* [x] Step 3.5.1: React profile page; mutations echo the CSRF header (double-submit) read from the CSRF cookie — `ProfilePage.tsx` at `/app/profile`; `PUT /be_auth/update_profile` + `/be_auth/update_password` via shared apiClient (added `put`); prefilled from `useSession`; client password-mismatch validation in pure `profileValidation.ts`.
* [x] Step 3.5.2: Update `test_profile_ui.py` — added dedicated `tests/e2e/test_spa_profile_ui.py` (SPA `/app/profile`); existing Jinja `test_profile_ui.py` left green.
* [x] Step 3.5.3: Validate

**Acceptance 3.5:** Profile view + edit work in React; CSRF header sent on POST/PUT; `test_profile_ui.py` green.

**FU-1 (from increment-3 review) — DONE:** Upload page code-split via `React.lazy` + `Suspense`; Uppy stack now a separate `UploadPage` chunk. Main JS 524.47 kB → 238.37 kB; > 500 kB warning resolved. See `albumsaventures-phase3-spa-increment4-changes.md`.

### [x] Phase 3.6: Admin (`admin_users.html`, `admin_groups.html`)

<!-- parallelizable: true -->
Independent of 3.5/3.7. Exercises superuser gating (Phase 1 `is_superuser` fix #485).

* [x] Step 3.6.1: React admin users + admin groups pages; `RequireSuperuser` guard — `AdminPage.tsx` at `/app/admin` (Users + Groups tabs), `RequireSuperuser.tsx`, pure `lib/admin.ts` (+13 vitest incl. superuser-gate smoke). Mirrors Jinja: pending activation + promote/demote (`be_auth/admin/users/{id}/rights`), group CRUD + member/album access (`be_group`). CSRF on all mutations; confirmations on destructive actions. **Bundled F-1 backend fix**: `be_resizer.create_thumbnails` GET→POST + server-side `require_superuser` guard (be_auth) + updated SPA/Jinja callers; +4 pytest.
* [x] Step 3.6.2: Update `test_admin_users_ui.py` + `test_admin_groups_ui.py` — added dedicated `tests/e2e/test_spa_admin_ui.py` (SPA `/app/admin`, superuser-gate + redirect); existing Jinja admin specs left green.
* [x] Step 3.6.3: Validate — build no-warn, lint 0, vitest 48/48, pytest 54, ruff/black green, import 108 routes.

**Acceptance 3.6:** Admin pages render for superusers only; non-superuser blocked; both admin specs green. Change record: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment5-changes.md`.

### [x] Phase 3.7: Shared Album (`shared_album.html`)

<!-- parallelizable: true -->
Independent of 3.5/3.6. Public PIN-protected path — special auth (no session cookie).

* [x] Step 3.7.1: React shared-album page against the public PIN-share flow (`be_album.public_router` / share token) — `SharedAlbumPage.tsx` at PUBLIC `/app/shared/:token` (outside `RequireAuth`/`Layout`). PIN entry → `GET /be_album/shared`; read-only gallery via `GET /album/shared/images`, both `credentials: "omit"`. Pure `lib/shared.ts` (PIN format + backend error/rate-limit mapping) + 11 vitest. Reuses `Lightbox`; restricted view hides back/edit/upload/share/cover/associate; shared badge shown.
* [x] Step 3.7.2: Update `test_shared_album_ui.py` — added dedicated `tests/e2e/test_spa_shared_album_ui.py` (SPA `/app/shared/:token`); existing Jinja `test_shared_album_ui.py` left green.
* [x] Step 3.7.3: Validate — build no-warn, lint 0, vitest 59/59, pytest 54 (auth/albums/upload), import 108 routes. Backend UNCHANGED. No CSP/CORS change.

**Acceptance 3.7:** PIN entry → shared album view works in React; rate-limit behavior (Phase 1 durable limiter) intact; `test_shared_album_ui.py` green. Change record: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment6-changes.md`.

### [ ] Phase 3.8: Auth Pages (`login`, `signup`, `forgot_password`, `reset_password`) + `fe_router` Retirement

<!-- parallelizable: false -->
Depends on all pages above migrated. Completes the strangler.

* [ ] Step 3.8.1: React auth pages; login sets the HttpOnly cookie via `be_auth` (no token stored in JS)
* [ ] Step 3.8.2: Retire the `fe_router` loopback-HTTP data-fetch hop for all now-migrated pages (C-8); keep only what public/SSR paths still require
* [ ] Step 3.8.3: Update `test_login_ui.py`
* [ ] Step 3.8.4: Validate

**Acceptance 3.8:** All 7 UI surfaces served by the SPA; login/session/logout via cookie only (no localStorage token); `fe_router` httpx self-calls removed for migrated pages; `test_login_ui.py` green.

### [~] Phase 3.9: CSP Tightening + Cleanup + Phase 4 PWA Handoff

<!-- parallelizable: false -->
Depends on 3.8 (all assets localized). Closes the CSP "EXCEPTION TODO" for the SPA surface; full closure gated on Jinja decommission (strangler still active).

* [x] Step 3.9.1: Tighten CSP in `utils/security.py` (conservative, two-tier)
  * Two-tier CSP: SPA (`/app`) hardened to `script-src 'self'` (no CDN, no inline script); Jinja/API keeps host-pinned CDNs + `'unsafe-inline'` (still required by live fallbacks). `'unsafe-eval'`/`*` absent on both — test-enforced. Full CDN removal deferred to Jinja decommission. See increment8 change record CSP audit table.
* [~] Step 3.9.2: Remove the obsolete Jinja2 templates + Alpine/CDN tags — DEFERRED (strangler active; every Jinja page is still a live fallback). Gated on Jinja decommission.
* [x] Step 3.9.3: Document the Phase 4 PWA handoff contract (in increment8 change record)
* [x] Step 3.9.4: Validate — 61 backend / 74 vitest pass; built SPA shell = external same-origin assets only; both a representative Jinja and SPA page reasoned to satisfy the tightened CSP.

**Acceptance 3.9:**

* CSP no longer allows the three CDNs nor `'unsafe-inline'` for the SPA surface; local hashed/nonce assets only; `connect-src`/`worker-src`/`manifest-src` remain same-origin (already set in Phase 1).
* No console CSP violations across all migrated pages (Playwright).
* **Phase 4 PWA handoff documented:** `vite-plugin-pwa` will generate the service worker + `manifest.webmanifest` from the Vite build; the SW **must bypass `/be_resizer/tus/`** (Phase 2 upload stack) and honor the Phase 1 **auth/API cache-partitioning** condition (never cache authenticated `be_*` JSON cross-session). The Phase 1 CSP `worker-src 'self' blob:` + `manifest-src 'self'` already accommodate it.

### [ ] Phase 3.N: Phase-Level Validation Gate (runs at the end of each increment)

<!-- parallelizable: false -->

* [ ] Step N.1: `npm --prefix frontend/spa run build` (Vite) + `npm run lint` (ESLint/Prettier) + `vitest run` (unit/component smoke)
* [ ] Step N.2: `.\Scripts\python.exe -m pytest` (full unit suite stays green) + `ruff check` + `black --check` on changed `.py`
* [ ] Step N.3: `pytest -m e2e tests/e2e` for the specs touched by the increment (+ regression on the rest)
* [ ] Step N.4: Report blocking issues; defer large fixes to a new research/plan cycle rather than inline

## Planning Log

See `.copilot-tracking/plans/logs/2026-07-07/albumsaventures-phase3-spa-log.md` for discrepancy tracking, implementation paths considered, and council-condition carry-forward.

## Council Conditions Carried Forward

| Condition | Role | How this plan addresses it |
|-----------|------|----------------------------|
| Same-origin serving (no cross-origin token surface) | security + architect | 3.1.5 SPA served by FastAPI; **no CORS**; cookie sent automatically. |
| CSRF on mutations | security | React API client reads the `httponly=False` CSRF cookie and echoes the header on every mutation (3.5–3.8). |
| **No tokens in localStorage** | security | Auth stays in the HttpOnly cookie; the SPA never persists a token in JS storage (3.1.4, 3.8.1). |
| Refresh-token strategy (#490) | security | Surfaced as **PD-01** below — decision needed before 3.8; default = keep 60-min cookie + 401→login redirect (no refresh) for this phase. |
| CSP tightening | security | 3.9.1 retires CDNs + `'unsafe-inline'`, closing the `utils/security.py` "EXCEPTION TODO Phase 3". |
| **Node build-time only — no runtime hosting added** | cost-manager | Vite builds static assets served by the existing FastAPI process; **no second server, no Node runtime in prod** (3.1.5). Confirmed. |
| Incremental (no big-bang) | architect | Strangler order 3.2→3.8; Jinja2 fallbacks until each page migrates. |
| HTMX/Alpine boundary | architect | **Moot** — the SPA replaces Alpine/HTMX entirely; no HTMX is introduced (parent plan 3.2 withdrawn). |
| Loopback-HTTP coupling (C-8) | architect | Retired **for migrated pages** in 3.8.2 (SPA calls `be_*` directly). |

## Dependencies

* Node.js (build-time only) + npm; Vite, React 18, TypeScript, Tailwind + PostCSS, ESLint, Prettier, Vitest.
* React Query (`@tanstack/react-query`), React Router.
* Uppy v5 ESM packages (`@uppy/core`, `@uppy/dashboard`, `@uppy/tus`, `@uppy/golden-retriever`, `@uppy/compressor`, `@uppy/locales`).
* Existing backend unchanged: `be_*` JSON API, `/be_resizer/tus/`, `/be_resizer/upload_config`, `/be_resizer/processing_status/{id}` (Phase 2), CSRF cookie (`utils/csrf.py`), security middleware (`utils/security.py`).
* CI: a Node/Vite build + lint + Vitest step added alongside the Python pytest/ruff/black gate.

## Success Criteria

* All 7 UI surfaces served by the React SPA, same-origin, cookie auth preserved, no localStorage tokens — Traces to: user confirmed decision.
* Upload page on Uppy v5 with **every Phase 2 reliability behavior preserved** (resume, compression, adaptive chunk 256 KB floor, durable status) — Traces to: user item 5, Phase 2 D2 deferral.
* CSP tightened: CDNs + `'unsafe-inline'` retired for the SPA surface — Traces to: user item 6, `utils/security.py` EXCEPTION TODO.
* Node is build-time only; no runtime hosting added — Traces to: cost-manager condition.
* `fe_router` loopback hop retired for migrated pages — Traces to: research Open Q #3 / C-8.
* Python pytest green throughout; Vite build + Vitest green; per-page Playwright specs updated and green — Traces to: research Section F, user item 7.
* Phase 4 PWA handoff documented with TUS-bypass + cache-partitioning constraints — Traces to: user item 8.

## Decision Point (needs user input before Phase 3.8)

### PD-01: Refresh-token strategy (#490) under the SPA

The SPA does not change the token lifetime question, but a SPA makes silent-session-expiry UX more visible (a background React Query refetch can 401 mid-session).

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Keep current 60-min HttpOnly cookie, no refresh; 401 → redirect to login | Simplest; preserves Phase 1 model; occasional mid-session logout |
| B | Add a refresh-token endpoint + silent renewal (still HttpOnly cookies) | Smoother UX; new endpoint + rotation logic; security review needed |

**Recommendation:** Option A for Phase 3 (defer B to a dedicated security increment); it keeps the confirmed "no new auth surface" posture. **Impact if deferred:** Phase 3.8 proceeds with A as default; #490 stays a Phase-post-3 follow-on.
