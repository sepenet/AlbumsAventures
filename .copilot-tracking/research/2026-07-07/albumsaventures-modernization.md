<!-- markdownlint-disable-file -->
# Task Research: AlbumsAventures Modernization (Frontend, Security, Upload Reliability, PWA)

Research artifact for the squad `researcher` role (member Alpha). Documents the current state and modernization options for the AlbumsAventures FastAPI + Jinja2 photo/video album application. Scope covers four goals from the user request (French):

1. Modernize the front-end and select the best framework for the need.
2. Secure the application.
3. Improve new-image upload reliability (uploads fail depending on bandwidth, network type, browser).
4. Convert the app to a PWA.

This document is research-only: no code was written and no application files were changed. All findings are grounded in actual workspace files with path + line citations. Decisions are deferred to the planner and architect — this surfaces tradeoffs and open questions.

## Task Implementation Requests

* A. Inventory current frontend architecture (templates, static, routers, CSS/JS approach, backend coupling).
* B. Evaluate realistic frontend framework modernization paths against this project's size and Tailwind investment (no decision).
* C. Analyze image upload reliability (TUS, chunking, retry, thumbnails) and identify concrete gaps for poor networks.
* D. Inventory the security posture (auth, CSRF, secrets, cookies, JWT, PIN share) and flag weak spots for the Security Planner.
* E. Assess PWA readiness (service worker, manifest, offline, HTTPS) and what conversion requires.
* F. Note constraints and references (stack, tests, tooling, conventions).

## Scope and Success Criteria

* Scope: Existing FastAPI monolith at repo root. Covers `frontend/`, `backend/routers/`, `utils/`, `AlbumsAventures-BE.py`, `docs/`, and project tooling. Excludes: deep threat modeling (Security role), full IaC/deployment design, and database schema redesign.
* Assumptions:
  * The app runs as a single FastAPI process serving both server-rendered HTML pages and the `be_*` JSON API.
  * "Frontend framework" means the client-rendering/interaction layer, not the FastAPI routing layer.
  * Production target is HTTPS behind a reverse proxy (Caddy is referenced in code comments); dev is Windows + SQLite.
* Success Criteria:
  * Every section cites concrete files/lines from this workspace.
  * Upload reliability gaps are named against real config values (chunk size, retry, timeout, thumbnail path).
  * Framework options are compared with pros/cons tied to THIS codebase, without a final pick.
  * An explicit "Open questions for planning" list hands off cleanly to planner + architect + security roles.

## Outline

* Summary of key findings
* A. Current frontend architecture
* B. Frontend framework options (tradeoffs only)
* C. Image upload reliability
* D. Security posture
* E. PWA readiness
* F. Constraints and references
* Open questions for planning

## Summary (Key Findings)

* **Frontend is a server-rendered Jinja2 "hybrid" stack**: Jinja2 templates + Tailwind (CDN) + Alpine.js (CDN) + Uppy (CDN), no build step, no bundler, no npm toolchain. Interactivity is progressive enhancement, not a SPA. See `frontend/templates/base.html` lines 7-11, 108-110; README "Frontend (variant hybride)".
* **Backend/frontend coupling is loopback HTTP, not in-process calls**: the frontend router (`frontend/routers/fe_router.py`) calls the `be_*` JSON API over `httpx` to `http://localhost:8003` (`utils/config.py` `backend_api.base_url`) even though both live in the same FastAPI app (`AlbumsAventures-BE.py` lines 118-129). This is an unusual self-call pattern with real latency/timeout implications.
* **Upload uses TUS resumable** (client `@uppy/tus` + backend `tuspyserver`) with `chunkSize=256KB`, aggressive `retryDelays`, sequential `limit:1`. Thumbnail generation runs in a fire-and-forget daemon thread to return `204` fast on mobile. See `frontend/templates/album_upload.html` lines 193-205; `backend/routers/be_resizer.py` lines 660-870.
* **Concrete upload gaps remain**: Uppy v3.27 is EOL (migration to v5 = TODO #393), no `@uppy/golden-retriever` (resume-after-reload = TODO #394), thumbnail failures are swallowed (not surfaced to user), TUS storage is local disk, a legacy XHR multipart endpoint still coexists (TODO #395), and chunk size is fixed (not network-adaptive). See `docs/TODO.md` lines 74-89.
* **Security is "dev-grade" with prod TODOs unresolved**: cookies `secure=False` (auth cookie `be_auth.py` line 540; CSRF cookie `utils/csrf.py` line 50), no security-headers/CSP middleware, no HTTPS redirect / TrustedHost, in-memory rate limiting (single-process only, resets on restart), and `get_current_user()` omits `is_superuser` (TODO #485) causing authz checks to always treat users as non-superuser. See `AlbumsAventures-BE.py` lines 100-116; `backend/routers/be_auth.py` lines 91-100, 500-546.
* **PWA is greenfield**: no service worker, no web manifest, only `frontend/static/favicon.ico`. Conversion requires HTTPS (currently off), a manifest, a service worker with a caching strategy tuned for a photo-heavy app, and offline UX.
* **Solid engineering baseline exists**: Python 3.12, ruff + black + pre-commit (`pyproject.toml`), pytest unit tests (`tests/`), and Playwright e2e (`tests/e2e/`). Secrets abstraction supports `.env` (dev) and Azure Key Vault (prod) via `utils/secret_store.py`.

## A. Current Frontend Architecture

### Templates (`frontend/templates/`)

14 Jinja2 pages, all extending `base.html`:

* `base.html`, `index.html`, `login.html`, `signup.html`, `forgot_password.html`, `reset_password.html`, `profile.html`
* `album_detail.html`, `album_edit.html`, `album_form.html`, `album_upload.html`
* `admin_users.html`, `admin_groups.html`
* `shared_album.html` (public PIN-protected share view)

`base.html` establishes the whole client runtime:

* Tailwind via CDN with inline config — `frontend/templates/base.html` lines 7-11 (`<script src="https://cdn.tailwindcss.com">`, `darkMode: 'class'`). Comment explicitly says "remplacer par build Tailwind en production".
* Alpine.js via CDN, `defer` — `frontend/templates/base.html` line 110 (`https://unpkg.com/alpinejs@3.x.x`).
* A global Alpine store `auth` for session/user state and pending-user counts — `frontend/templates/base.html` lines 30-99. It calls `/be_auth/me`, `/be_auth/logout`, `/be_auth/admin/users/pending-count` via `fetch(..., {credentials:'include'})`.
* Client-side route guarding: a `DOMContentLoaded` handler redirects to `/login` if `checkSession()` fails, with a hardcoded `publicPages` allowlist — `frontend/templates/base.html` lines 101-136.
* Dark mode persisted in `localStorage` — `frontend/templates/base.html` lines 22-27.

### Static assets (`frontend/static/`)

* `favicon.ico`
* `images/` — album originals, organized by category folders (`Amis/`, `Natation/`, `Randonnée/`, `Ski/`, `Ski-de-Rando/`, `Triathlon/`, `Vacances/`) plus `video-placeholder.svg`. Mounted at `/images` (`AlbumsAventures-BE.py` lines 137-138).
* `thumbnails/` — generated thumbnails. Mounted at `/thumbnails` (`AlbumsAventures-BE.py` lines 134-135).
* `rando/` — a static microsite (`propositions-rando.html`, `photos/`), served under `/static`.
* No `.js` or `.css` source files, no `package.json`, no bundler config. All JS is inlined in templates; all CSS comes from the Tailwind CDN.

### Frontend router (`frontend/routers/fe_router.py`)

* Uses `Jinja2Templates(directory="frontend/templates")` — `fe_router.py` line 20.
* Every page route does a **server-side** auth check via `utils.auth.require_auth` / `require_superuser` (`fe_router.py` lines 12, 33) which themselves call `GET {auth_url}/me` over httpx (`utils/auth.py` lines 17-47).
* Data for pages is fetched by the frontend router calling the backend API over httpx, forwarding the `access_token` cookie — e.g. index page calls `{album_url}/get_albums_by_user/{user_id}` (`fe_router.py` lines 40-70). Errors (timeout, connect, generic) are caught and degrade to empty lists.
* CSRF helpers are imported and used for form pages — `fe_router.py` line 14 (`get_csrf_token`, `set_csrf_cookie`, `validate_csrf_token`).

### CSS / JS approach and page serving

* **CSS**: Tailwind utility classes only, conventions codified in `docs/GUIDELINES_UI.md` (page structure, components, responsive grids, badges, action-icon hover colors). Currently CDN-loaded; README and `base.html` both flag the need for an npm Tailwind build in production to purge unused classes.
* **JS framework**: Alpine.js (declarative `x-data`, `x-show`, stores) + vanilla `fetch`. Uppy is used only on the upload page.
* **Serving**: FastAPI serves HTML through `fe_router` + Jinja2, and static/media through three `StaticFiles` mounts (`/static`, `/thumbnails`, `/images`) — `AlbumsAventures-BE.py` lines 131-138.

### Coupling assessment

* **Presentation coupling is loose** (templates only depend on Tailwind classes + small Alpine snippets), which makes an incremental frontend modernization feasible page-by-page.
* **Runtime coupling is a notable smell**: the frontend layer talks to the backend layer via loopback HTTP (`httpx` to `localhost:8003`) rather than direct function/dependency calls, even though they run in one process. This doubles request latency, adds a `default_timeout = 10.0` failure surface (`utils/config.py`), and complicates a future split (SPA + API) — but it also means the `be_*` routers already behave like a clean JSON API a SPA could consume directly.
* CORS is configured for `http://localhost:5003` with `allow_credentials=True` (`AlbumsAventures-BE.py` lines 100-116), suggesting a separate frontend origin was anticipated at some point.

## B. Frontend Framework Options (tradeoffs only — no decision)

Context that shapes every option: small personal/family app, single maintainer, existing Tailwind + Alpine investment, a clean `be_*` JSON API already exists, no current build toolchain, photo/video-heavy UI, and a stated desire for PWA + better upload UX.

### Option (a): Keep server-rendered + progressive enhancement (HTMX / Alpine.js)

* **Description**: Stay on Jinja2 + Tailwind; deepen interactivity with HTMX (partial HTML swaps) and/or keep Alpine for local state. Add a Tailwind npm build to replace the CDN.
* **Pros for THIS project**:
  * Lowest migration cost; reuses all 14 templates and `GUIDELINES_UI.md` conventions.
  * No SPA build/deploy complexity; keeps single-process simplicity.
  * PWA is still achievable (manifest + service worker work with any HTML).
  * Aligns with the already-chosen "variante hybride" (TODO #010, marked done).
* **Cons**:
  * Rich client interactions (drag-reorder galleries, optimistic UI, complex upload dashboards) are harder than in a component framework.
  * The loopback-HTTP frontend→backend pattern stays unless refactored.
  * Alpine `3.x.x` via CDN has no version pinning/SRI (supply-chain + reproducibility risk).

### Option (b): Migrate to a SPA (React / Vue / Svelte / SolidJS)

* **Description**: Build a client app that consumes the existing `be_*` JSON API; FastAPI becomes API-only (+ static host or separate host).
* **Pros for THIS project**:
  * The `be_*` routers are already a usable JSON API (auth via cookie, CRUD, TUS).
  * Best ceiling for interactive galleries, upload UX, and offline/PWA behavior (mature service-worker tooling in Vite/SvelteKit).
  * Component reuse and testability improve.
* **Cons**:
  * Highest cost for a single maintainer: new build/deploy pipeline, routing, auth handling (cookie CSRF/SameSite across origins), and re-implementation of 14 pages.
  * Tailwind investment transfers, but Alpine snippets and Jinja logic are rewritten.
  * SEO/first-paint tradeoffs (mitigated by SSR frameworks, which add more complexity).
  * Cookie-based auth (`SameSite=Lax`, HttpOnly) needs careful CORS/CSRF rework if the SPA is a different origin (CORS already hints at `localhost:5003`).
* **Framework nuance** (surface only): React = largest ecosystem/tooling; Vue = gentle curve, good for Tailwind; Svelte/SvelteKit = smallest bundles + first-class PWA/offline; SolidJS = React-like DX with fine-grained reactivity and small bundles. For a photo-heavy PWA, bundle size and image-handling ergonomics matter.

### Option (c): Hybrid / islands (Astro, or Next/Nuxt with FastAPI as API)

* **Description**: Astro islands for mostly-static content with interactive components where needed; or Next/Nuxt as a frontend tier calling FastAPI as the API.
* **Pros for THIS project**:
  * Astro fits a content-heavy gallery: ships minimal JS, great Lighthouse/PWA scores, can embed React/Vue/Svelte islands only where interactivity is needed (upload, admin, share).
  * Keeps FastAPI as the API (reuses `be_*`), so the backend investment is preserved.
* **Cons**:
  * Adds a second runtime (Node) to build/deploy — heavier ops for a solo maintainer.
  * Next/Nuxt SSR duplicates some concerns FastAPI already handles (routing, auth), raising integration complexity.
  * Auth/session sharing between the Node frontend and FastAPI API needs design (token forwarding, CSRF).

### Cross-cutting considerations for the planner/architect

* **Tailwind production build** is needed in every option (CDN is prototype-only per `base.html` line 7 and README).
* **Auth model** (HttpOnly cookie + CSRF double-submit) strongly favors same-origin serving; a cross-origin SPA increases security surface.
* **The loopback-HTTP coupling** should be a decision input: a SPA/hybrid would let the client call `be_*` directly, removing the frontend→backend httpx hop entirely.

## C. Image Upload Reliability

### Current implementation

**Client (Uppy + TUS)** — `frontend/templates/album_upload.html`:

* Uppy `v3.27.0` loaded via CDN (CSS line 6, JS line 100).
* Dashboard inline, `autoProceed:false`, restrictions `maxFileSize = 500MB`, allowed types `image/*`, `video/mp4`, `.avi`, `.heic` — lines 110-131.
* TUS plugin config — lines 193-205:
  * `endpoint: '/be_resizer/tus/'`
  * `chunkSize: 256 * 1024` (256 KB) with a detailed comment explaining that 2 MB PATCHes were silently dropped on Edge Android → Caddy on mobile (prod logs 2026-04-27), so small chunks finish before carrier NAT timeouts.
  * `retryDelays: [0, 1000, 3000, 5000, 10000, 20000, 40000, 60000]` (8 retries, backoff to 60s).
  * `removeFingerprintOnSuccess: true`, `withCredentials: true` (sends JWT cookie), `limit: 1` (sequential, one file at a time).
  * `setMeta({ album_id })` passes the album id in TUS metadata — line 189.
* `complete`/`error` handlers surface counts (uploaded/failed) and error messages into an Alpine `uploadResult` banner — lines 207-249.
* A "Régénérer vignettes" button calls `GET /be_resizer/create_thumbnails/{album.id}` — lines 251-283.

**Backend (tuspyserver)** — `backend/routers/be_resizer.py`:

* Size limits: `MAX_IMAGE_SIZE = 30MB`, `MAX_VIDEO_SIZE = 500MB`, `MAX_TOTAL_SIZE = 2GB` — lines 27-30.
* `create_tus_router(prefix="be_resizer/tus", files_dir=image.tus_files_dir, max_size=MAX_VIDEO_SIZE, auth=get_current_user, pre_create_dep=..., upload_complete_dep=..., days_to_keep=2)` — lines 861-870. Temp dir `uploads_tus/` is outside `frontend/static` to avoid public exposure (`utils/config.py` `image.tus_files_dir`).
* **Pre-create hook** validates `album_id` metadata, album existence, per-user access (`verify_album_access`), and announced size vs image/video limit (413 if exceeded) — lines 752-786.
* **Upload-complete hook** moves the temp file into the album folder and generates the thumbnail **in a daemon background thread** so the worker returns `204 No Content` immediately. The comment (lines 810-818) explains this exists because PIL/OpenCV thumbnailing (3-15 s per photo) held the connection open long enough for mobile carriers to kill the TCP socket (~10 s), producing Uppy "network error" on subsequent files.
* Video thumbnails via OpenCV (`video_create_thumbnail`, lines 66-160); image thumbnails via PIL with EXIF-orientation correction (lines 720-742).
* A legacy XHR multipart endpoint (`POST /be_resizer/upload_images/{album_id}`) still exists with its own size checks (lines 465-484) — TODO #395 flags it for removal/fallback decision.

### Reliability gaps for poor bandwidth / mobile / browser variance

Grounded in `docs/TODO.md` lines 74-89 and the code above:

1. **No resume-after-reload**: `@uppy/golden-retriever` is not enabled (TODO #394). A page reload / tab crash / mobile app-switch loses in-progress uploads even though TUS server state persists on disk.
2. **EOL client library**: Uppy `v3.27` (TODO #393). Migrating to v5 (ESM modules, `@uppy/locales/fr_FR`, CSP updates) is needed for continued fixes and browser compatibility.
3. **Fire-and-forget thumbnailing hides failures**: the daemon thread (`be_resizer.py` lines 820-849) logs errors but never surfaces them to the client. A file can "succeed" (204) yet have no thumbnail; the user only finds out visually later. There is no post-processing status/queue the UI can poll.
4. **Fixed chunk size**: 256 KB is tuned for the worst mobile case but is inefficient on good Wi-Fi/fixed lines (more round-trips). No network-adaptive chunk sizing.
5. **Server timeout/proxy config not codified in-repo**: the code comments reference Caddy behavior and carrier timeouts, but there is no documented reverse-proxy timeout / `client_max_body_size` / TUS `Upload-Expires` tuning in the repo — a real source of browser/network variance.
6. **Local-disk TUS storage**: `uploads_tus/` on the app host doesn't scale horizontally and risks orphaned files (mitigated only by `days_to_keep=2`).
7. **Duplicate/skip feedback is coarse**: backend returns `skipped` for existing files, but the client banner mostly aggregates uploaded/failed counts; skipped duplicates surface weakly (`album_upload.html` lines 40-52 handle `skipped` but the TUS `complete` handler sets `skipped: 0`, lines 217-245).
8. **Sequential `limit:1`** maximizes reliability but minimizes throughput; there is no adaptive concurrency for good networks.
9. **Two upload paths** (TUS + legacy XHR) increase surface area and confusion until TODO #395 is resolved.

### Note on documentation mismatch

* `docs/Bulk-upload.md` is about **server-side bulk import from a JSON manifest** (CLI/optional API), not client resumable upload — it is a separate feature from the TUS reliability work. Do not conflate the two during planning.
* TODO #392 text says `chunkSize=5MB` and the code comment at `be_resizer.py` line 665 says "chunks de 5 Mo", but the **actual** client value is 256 KB (`album_upload.html` line 196). The 256 KB value is the current, incident-driven truth; the docs/comments are stale.

## D. Security Posture

Inventory of `utils/` and auth flow (high-level flags only — full threat model is the Security role's job).

### Cookies and transport

* **Auth cookie `secure=False`** with `httponly=True`, `samesite="lax"`, value `"Bearer <jwt>"`, `max_age = ACCESS_TOKEN_EXPIRE_MINUTES*60` — `backend/routers/be_auth.py` lines 536-543. Explicit `TODO: mettre True en production`.
* **CSRF cookie `secure=False`**, `httponly=False` (readable by JS for AJAX), `samesite="strict"`, `max_age=3600` — `utils/csrf.py` lines 44-52. Explicit `TODO: passer à True en production`.
* No HTTPS redirect middleware, no HSTS, no `TrustedHostMiddleware` in `AlbumsAventures-BE.py`.

### CSRF

* Manual double-submit cookie: token in cookie + hidden form field, constant-time compare (`secrets.compare_digest`) — `utils/csrf.py` lines 55-84. Applied to form pages via `fe_router` (login/signup, etc.).
* Note: state-changing JSON API calls that rely on the SameSite cookie (e.g. TUS, admin actions via `fetch`) depend on `SameSite=Lax`/`Strict` rather than a CSRF token — the Security role should confirm coverage of all mutating endpoints.

### JWT / sessions

* `create_access_token` encodes only `sub` (email) + `id` + `exp` — `be_auth.py` lines 91-100. **`is_superuser` is NOT in the token** and `get_current_user()` returns only email/id (TODO #485). Impact: superuser checks like `current_user.get("is_superuser", False)` in `be_resizer.py` (line 741) are always False, so superusers fall through to normal `verify_album_access`. This is fail-closed for uploads (safe) but indicates authz data is unreliable app-wide.
* HS256, single `SECRET_KEY` from `SecretStore`, 60-minute expiry, **no refresh tokens** (TODO #490).
* Token extraction supports cookie OR `Authorization` header — `be_auth.py` lines 278-300.

### Album PIN share

* `generate_pin`: 6 chars from `A-Z0-9` via `secrets.choice` — `be_auth.py` lines 104-107.
* Share token stores a **SHA-256 hash of the PIN** (SEC-05), not the PIN — `be_auth.py` lines 111-123. PIN checked with hash comparison — lines 250-269.
* **Rate limiting**: in-memory `defaultdict` keyed by token hash; max 5 attempts / 15 min then 15-min block (`utils/config.py` `rate_limiting`, `be_auth.py` lines 126-190). Also applied to login keyed by email (`be_auth.py` lines 510-531, SEC-21).
* Weakness: rate-limit state is **process-local and volatile** — resets on restart and does not work across multiple workers/instances. Not a durable brute-force control at scale.

### Secrets

* `utils/secret_store.py`: unified secret access — Azure Key Vault when `KEY_VAULT_URL` is set (Managed Identity → DefaultAzureCredential fallback), else `.env` via python-dotenv. Secrets are cached in memory with TTL and "never transit through `os.environ`". Mandatory secrets raise on absence. Env→KV name mapping table lines 33-54.
* `utils/config.py` reads all secrets through `SecretStore` (JWT, DB, SMTP, URLs). `SECRET_KEY`, DB creds are mandatory (no defaults).

### CORS

* `CORSMiddleware` with fixed origin `http://localhost:5003`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`, and TUS headers in `expose_headers` — `AlbumsAventures-BE.py` lines 100-116. The wildcard methods/headers with credentialed requests are acceptable only because the origin is a single fixed value; production origin must be set correctly.

### Other

* No security-headers middleware (no CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy). Given inline `<script>` blocks in templates and CDN dependencies, a CSP will require care.
* CDN assets (Tailwind, Alpine `3.x.x`, Uppy, unpkg) have **no SRI and loose/no version pinning** — supply-chain exposure.
* `password.py` (passlib) and `email.py` (SMTP) exist but were not deep-read here — the Security role should review password hashing scheme parameters and SMTP credential handling.

### What the Security Planner should examine

* Enable `secure=True` cookies + HTTPS/HSTS/TrustedHost for production (TODO #480 partially done, cookie flags outstanding).
* Fix `is_superuser` propagation (TODO #485) — current authz relies on data the token doesn't carry.
* Move rate limiting to a shared/durable store (Redis) for multi-worker prod.
* Add a security-headers middleware + CSP compatible with the (to-be-built) asset pipeline; add SRI/pinning to any remaining CDN assets.
* Confirm CSRF/SameSite coverage for all mutating `fetch`/TUS endpoints.
* Review refresh-token strategy (TODO #490) and JWT expiry/rotation.

## E. PWA Readiness

* **No existing PWA assets**: repo-wide search for `serviceWorker|manifest|sw.js|workbox|offline|beforeinstallprompt` found **no matches inside the application** (only in unrelated `.agents/skills/**` and `.github/**` docs). `frontend/static/` contains only `favicon.ico`, `images/`, `thumbnails/`, `rando/`.
* **Blockers/prerequisites for conversion**:
  * **HTTPS is mandatory** for service workers and installability — currently cookies are `secure=False` and there is no HTTPS/HSTS config in-repo (see Section D). PWA and the security hardening are coupled.
  * **Web app manifest** (`manifest.webmanifest`): name, icons (multiple sizes/maskable), `start_url`, `display: standalone`, theme/background colors. Only a single `favicon.ico` exists today — icon set must be produced.
  * **Service worker** with a caching strategy tuned for a **photo/video-heavy** app: app-shell (HTML/CSS/JS) precache, but originals/thumbnails need a size-bounded runtime cache (e.g. stale-while-revalidate or cache-first with quota + eviction) to avoid unbounded storage. The three media mounts (`/images`, `/thumbnails`, `/static`) define the cacheable surface.
  * **Offline UX**: an offline fallback page, and graceful behavior for the login-guard redirect in `base.html` (the `DOMContentLoaded` `checkSession()` → `/login` redirect will misbehave offline and needs SW-aware handling).
  * **Install prompt** handling (`beforeinstallprompt`) and iOS Safari specifics (Apple touch icons, no `beforeinstallprompt`).
  * **Build integration**: if a Tailwind/JS build is introduced (Section B), Workbox or a framework PWA plugin (e.g. Vite PWA, SvelteKit) can generate the SW; on the current no-build stack, a hand-written SW + manifest is possible but caching/versioning is more manual.
* **Upload interaction**: TUS resumable uploads and a service worker can coexist, but the SW must **not** intercept/cache the `/be_resizer/tus/` PATCH/POST traffic. Background-sync for queued uploads is a possible enhancement but is complex with TUS.

## F. Constraints and References

* **Stack**: Python `>=3.12`, FastAPI + uvicorn, SQLAlchemy/SQLModel, PostgreSQL (prod) / SQLite (Windows dev, reset each run — `AlbumsAventures-BE.py` lines 58-92), python-jose (JWT), passlib, Pillow + PyExifTool + OpenCV, tuspyserver, Azure Key Vault SDKs. See `requirements.txt`.
* **Single-process app**: all routers (`be_album`, `be_user`, `be_auth`, `be_category`, `be_formatter`, `be_group`, `be_resizer`, `be_resizer.tus_router`, `fe_router`) mounted in one FastAPI app — `AlbumsAventures-BE.py` lines 118-129.
* **Windows shim**: `utils/win_fcntl_shim.py` patches `fcntl`/`os.rename` for tuspyserver on Windows — `AlbumsAventures-BE.py` lines 6-9, 40-45. Any upload rework must keep Windows-dev working.
* **Testing**: pytest unit tests in `tests/` (`test_albums.py`, `test_auth.py`, `test_upload.py`, `conftest.py`); Playwright e2e in `tests/e2e/` (7 UI specs: login, navigation, album, profile, admin users/groups, shared album). Config in `pyproject.toml` `[tool.pytest.ini_options]` (marker `e2e`). Playwright provides a ready harness to validate frontend/PWA/upload changes.
* **Code quality**: ruff (E,W,F,I,B,UP; line-length 120; several legacy ignores E402/B904/B007/E712) + black + pre-commit — `pyproject.toml` lines 10-58; `.pre-commit-config.yaml` present.
* **Conventions**: `.github/copilot-instructions.md` is the source of coding/security/pattern rules (README points to it). `docs/GUIDELINES_UI.md` defines Tailwind conventions. `docs/TODO.md` is the live backlog (numbered tasks referenced throughout, e.g. #391-395 upload, #480/#485/#490 security, #230 error pages, #370/#380 perf).
* **Known perf TODOs adjacent to this work**: #370 (API caching/debounce search), #380 (client-side image compression before upload — directly relevant to upload reliability), #350/#360 (lazy-load/infinite scroll, already done).

## Open Questions for Planning

1. **Framework direction (planner + architect)**: Does the team want to preserve the no-build server-rendered stack (Option a), or accept a build toolchain to unlock a SPA/islands approach (b/c)? This single decision gates PWA tooling, Tailwind build, and whether the frontend→backend loopback-HTTP hop is removed.
2. **Same-origin vs split-origin**: Should the modernized frontend stay same-origin with FastAPI (simplest for HttpOnly-cookie auth + CSRF), or move to a separate origin (the CORS config hints at `localhost:5003`)? This drives the auth/CSRF rework scope.
3. **Loopback-HTTP coupling**: Is refactoring `fe_router`'s httpx self-calls into direct in-process calls (or moving data-fetching to the client) in scope now, or deferred?
4. **Upload reliability priority order**: Which of TODO #393 (Uppy v5), #394 (golden-retriever resume), thumbnail-status surfacing, adaptive chunking, and #395 (retire legacy XHR) are must-have vs later? #380 (client-side compression) may deliver the biggest reliability win on mobile — include it?
5. **Post-upload processing model**: Keep the fire-and-forget daemon thread, or introduce a real task queue / status endpoint so the UI can report thumbnail success/failure? Affects both reliability UX and horizontal scaling.
6. **TUS storage & proxy**: Is production behind Caddy (as comments imply)? The reverse-proxy timeout / body-size / TUS-expiry settings need to be captured and tuned — where should that config live (repo vs infra)?
7. **PWA scope**: Full installable PWA with offline browsing of cached albums, or a lighter "installable + app-shell cache" first pass? Photo-heavy caching needs an explicit storage-quota/eviction policy.
8. **Security gating (security role)**: Confirm the production hardening set (HTTPS + `secure` cookies + HSTS/TrustedHost + CSP/security headers + durable rate limiting + `is_superuser` fix TODO #485 + refresh tokens TODO #490). PWA cannot ship before HTTPS/`secure` cookies are on.
9. **CDN vs bundled assets**: Replace CDN Tailwind/Alpine/Uppy with pinned, SRI'd, or bundled assets? Required for both CSP and reproducibility, and interacts with the framework decision.
10. **Windows-dev parity**: Any upload/backend change must preserve the `win_fcntl_shim` path so the maintainer's Windows/SQLite dev loop keeps working.

## Research Executed

### File Analysis

* `README.md` (lines 1-150) — functional overview, chosen "variante hybride" stack (Jinja2 + Tailwind + Alpine + Uppy), data model, JWT+PIN share, doc index.
* `frontend/templates/base.html` (lines 1-200) — Tailwind/Alpine CDN, `auth` Alpine store, client-side login guard, dark mode.
* `frontend/templates/album_upload.html` (lines 1-320) — Uppy v3.27 + TUS config (chunkSize 256KB, retryDelays, limit 1), result banner, regenerate-thumbnails.
* `frontend/routers/fe_router.py` (lines 1-80) — Jinja2 serving, server-side auth guard, httpx calls to backend API, CSRF helpers.
* `backend/routers/be_resizer.py` (lines 1-200, 660-870) — size limits, video/image thumbnail generation, TUS hooks (pre-create auth/size, upload-complete background thread), `create_tus_router` config, legacy XHR endpoint.
* `backend/routers/be_auth.py` (lines 85-300, 500-560) — JWT create (no is_superuser), PIN generation + hashed-PIN share token, in-memory rate limiting, login cookie flags (`secure=False`, `samesite=lax`).
* `utils/config.py` (lines 1-200) — logging, image/thumbnail/tus paths, rate_limiting, auth_config (JWT), backend_api (loopback base_url + 10s timeout), DB/email config.
* `utils/csrf.py` (lines 1-84) — double-submit CSRF, cookie flags (`secure=False`, `httponly=False`, `samesite=strict`).
* `utils/auth.py` (lines 1-75) — httpx-based auth verification against `{auth_url}/me`.
* `utils/secret_store.py` (lines 1-120) — Key Vault vs .env secret backend, env→KV mapping.
* `AlbumsAventures-BE.py` (lines 1-138) — Windows shim, SecretStore init, lifespan (SQLite reset on Windows), CORS, router mounts, StaticFiles mounts.
* `pyproject.toml` (lines 1-130) — ruff/black/pytest/coverage config, Python 3.12, legacy lint ignores.
* `requirements.txt` (lines 1-40) — dependency inventory incl. tuspyserver, Playwright, ruff/black/pre-commit, Azure SDKs.
* `docs/TODO.md` (lines 1-120) — backlog with upload (#391-395), security (#480/#485/#490), perf (#370/#380) tasks.
* `docs/GUIDELINES_UI.md` (lines 1-120) — Tailwind component/grid/badge conventions.
* `docs/Bulk-upload.md` (lines 1-400) — server-side JSON bulk-import feature (distinct from resumable upload).

### Code Search Results

* `serviceWorker|manifest|sw.js|workbox|offline|beforeinstallprompt` — no matches in application code (only in `.agents/skills/**`, `.github/**`), confirming PWA is greenfield.
* TUS/size markers in `be_resizer.py` — `MAX_IMAGE_SIZE`/`MAX_VIDEO_SIZE`/`MAX_TOTAL_SIZE`, `create_tus_router`, 413 responses.
* Cookie/middleware markers — only `CORSMiddleware` in `AlbumsAventures-BE.py`; cookie `set_cookie` with `secure=False` in `be_auth.py` and `csrf.py`.
* Rate-limit/PIN markers — `failed_attempts_cache` defaultdict, `check_rate_limit`, `generate_pin`, `pin_hash`, `compare_digest`.

### Project Conventions

* Standards referenced: `.github/copilot-instructions.md` (coding/security/patterns), `docs/GUIDELINES_UI.md` (Tailwind), `docs/TODO.md` (numbered backlog).
* Tooling: ruff + black + pre-commit; pytest + Playwright e2e.

## Potential Next Research

* Deep-read `utils/password.py` and `utils/email.py` for hashing parameters and SMTP credential handling — Reasoning: needed for the Security role's threat model. Reference: `utils/` inventory.
* Inspect `.github/copilot-instructions.md` in full for mandated security/patterns constraints — Reasoning: any modernization must comply. Reference: README doc index.
* Read `frontend/templates/index.html` and `album_detail.html` in full — Reasoning: gallery interactions define the hardest cases for a framework choice and for SW caching. Reference: Section A/B.
* Confirm production reverse-proxy (Caddy?) config source of truth — Reasoning: upload timeouts/body-size are decisive for reliability. Reference: `be_resizer.py` comments (lines 810-818).
