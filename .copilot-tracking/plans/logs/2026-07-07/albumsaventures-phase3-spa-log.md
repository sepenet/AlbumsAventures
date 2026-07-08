<!-- markdownlint-disable-file -->
# Planning Log: AlbumsAventures Phase 3 — React SPA Migration (Option B)

Supersedes Phase 3 of `.copilot-tracking/plans/albumsaventures-modernization.md`. Author: `lead` (Beta), autopilot Turn 5.

## Discrepancy Log

### Unaddressed Research Items

* DR-01: Split-origin SPA option (research Section B Option (b), CORS at `localhost:5003`)
  * Source: research Section B / Open Q #2
  * Reason: Confirmed decision is **same-origin**; split-origin explicitly rejected to preserve HttpOnly cookie + CSRF and avoid CORS. Not planned.
  * Impact: low
* DR-02: SvelteKit/Vue/Solid framework nuance (research Section B "Framework nuance")
  * Source: research Section B
  * Reason: User confirmed **React 18 + Vite + TS**; other frameworks out of scope.
  * Impact: low

### Plan Deviations from Research / Parent Plan

* DD-01: Parent plan Phase 3 recommended Option (a) HTMX+Alpine+Tailwind-CLI-build
  * Parent plan implements: HTMX + Alpine + Tailwind CLI (3.1/3.2/3.3)
  * This plan implements: React 18 + Vite + TS SPA (3.1–3.9)
  * Rationale: **User override of council C-1 to Option (b)**. Parent Phase 3 withdrawn; Phases 1/2/4/5 retained.
* DD-02: Uppy v3→v5 (#393) moves from Phase 2 to Phase 3.4
  * Research/Phase 2: v5 ESM deferred because it needs a bundler
  * This plan: the Vite bundler in 3.1 unblocks v5 ESM; 3.4 does the cutover preserving all Phase 2 behaviors
  * Rationale: bundler-first dependency now satisfied.
* DD-03: `fe_router` loopback-HTTP retirement (C-8) partially in-scope
  * Parent plan/research: deferred as optional architect decision
  * This plan: retired **for migrated pages** in 3.8.2 (SPA calls `be_*` directly); public/SSR-only paths keep what they need
  * Rationale: SPA direct API calls make the hop dead weight per migrated page.

## Implementation Paths Considered

### Selected: React 18 + Vite + TS SPA, same-origin, strangler migration

* Approach: Vite builds static assets under `frontend/spa/`; FastAPI serves SPA index + hashed assets via static mount + fallback route; page-by-page migration with Jinja2 fallbacks.
* Rationale: Matches the user's confirmed decision exactly; preserves auth/CSRF/no-CORS/no-runtime-Node; incremental (no big-bang).
* Evidence: research Section B Option (b) pros; `utils/security.py` CSP already same-origin-ready; Phase 2 backend endpoints already JSON.

### IP-01: Big-bang full SPA rewrite

* Approach: convert all 14 pages in one pass, remove Jinja2 immediately.
* Trade-offs: fastest "done" state but highest risk; breaks the app during transition; no incremental validation.
* Rejection rationale: user explicitly required **incremental strangler, no big-bang**.

### IP-02: Split-origin SPA (separate dev/host origin, CORS)

* Approach: SPA on its own origin calling FastAPI cross-origin.
* Trade-offs: cleaner separation but reintroduces CORS + cross-origin CSRF/SameSite complexity + a token-in-JS temptation.
* Rejection rationale: confirmed decision is same-origin, HttpOnly cookie, no CORS, no localStorage tokens.

## Suggested Follow-On Work

* WI-01: Refresh-token endpoint + silent renewal (#490) — see PD-01 (medium)
  * Source: council security condition; SPA makes mid-session 401 visible
  * Dependency: Phase 3.8 (auth pages) landed on default Option A
* WI-02: Phase 4 PWA via `vite-plugin-pwa` — SW + manifest from the Vite build (high)
  * Source: user item 8 / parent plan Phase 4
  * Dependency: Phase 3.9 (assets localized, CSP tightened)
  * Constraint: SW must bypass `/be_resizer/tus/` (Phase 2) and honor auth/API cache-partitioning (Phase 1)
* WI-03: Migrate remaining static microsite (`frontend/static/rando/`) or leave as-is (low)
  * Source: it is a standalone static page outside the SPA router
  * Dependency: none
* WI-04: CI pipeline: add Node/Vite build + Vitest job alongside pytest gate (high)
  * Source: user item 7
  * Dependency: Phase 3.1 scaffold
