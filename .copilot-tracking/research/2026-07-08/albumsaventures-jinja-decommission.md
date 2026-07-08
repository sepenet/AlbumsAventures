<!-- markdownlint-disable-file -->
---
description: "Evidence-backed inventory of the entire Jinja2 template footprint in AlbumsAventures, scoped for a safe and complete decommission (autopilot run albumsaventures-jinja-decommission, turn 16, researcher role Alpha). RESEARCH ONLY — no application code modified."
---
# Task Research: AlbumsAventures Jinja2 Template Decommission Inventory

Complete inventory of all code, assets, dependencies, tests, security policy, and documentation tied to the legacy server-rendered Jinja2 templates that were kept as a strangler-migration fallback while the React 18 + Vite SPA (served under `/app`) took over the frontend. The user asked (FR): "enlève tous le précédent code relatif à l'utilisation de template jinja" = remove ALL previous code related to the use of Jinja templates. This document is the removal inventory for the `lead` to plan a safe, complete removal.

> DISCLAIMER: This is an AI-assisted research artifact. All findings are evidence-linked but MUST be reviewed by a human engineer before any removal is planned or executed. Nothing here was executed against application code.

## Task Implementation Requests

* Inventory every Jinja template file, serving route, app-wiring point, CDN asset, dependency, test, CSP directive, and doc reference tied to Jinja.
* Distinguish Jinja-only artifacts from artifacts shared with the SPA (must NOT be removed).
* Surface routing-collision and external-reachability risks so the council can gate the removal.

## Scope and Success Criteria

* Scope: The application frontend Jinja layer only — `frontend/templates/*.html`, `frontend/routers/fe_router.py`, its wiring in `AlbumsAventures-BE.py` and `AlbumsAventures_BE_test.py`, the two-tier CSP in `utils/security.py`, `jinja2` dependency, tests, and docs. EXCLUDED: `apm_modules/**` (vendored HVE-Core skills that use unrelated "template" concepts), `frontend/spa/**` SPA source (only inspected to determine coverage/collision), and any backend `be_*` router logic.
* Assumptions:
  * The SPA under `/app` is the intended replacement surface for all Jinja pages.
  * "Remove Jinja" means: delete the templates, delete Jinja-rendering routes, drop the `jinja2` package, and tighten the now-unneeded CSP — WITHOUT breaking the SPA or any endpoint the SPA still calls.
  * Backend `be_*` routers are the canonical data API and stay.
* Success Criteria:
  * Every Jinja template file is listed and confirmed (14 files).
  * Every `fe_router.py` route is classified as Jinja-render vs. JSON/redirect, with SPA-dependency called out.
  * The exact CSP directives that exist "for Jinja/CDN" are enumerated with the tests that assert them.
  * The `jinja2` dependency removal is assessed against remaining consumers.
  * Routing-collision behavior at `/`, `/login`, `/signup`, `/album/...`, `/shared/...` is documented pre- and post-removal.
  * The three open questions are surfaced (not resolved) for planning/council.

## Outline

1. Headline findings (read first)
2. Category A — Template files (14)
3. Category B — Jinja serving code (`fe_router.py`: routes + TemplateResponse map)
4. Category C — App wiring (prod + test) and route-registration order
5. Category D — CDN assets: Jinja-only vs SPA-shared
6. Category E — `jinja2` dependency assessment
7. Category F — Routing collision risk (Jinja URLs vs SPA URLs)
8. Category G — Tests referencing Jinja / CSP
9. Category H — CSP / security coupling
10. Category I — Docs / config references
11. Top 3 risks
12. Open questions for council

## Potential Next Research

* Confirm the exact base URL used in password-reset emails and share links.
  * Reasoning: determines whether bare `/reset-password` / `/album/shared` must be redirected to the SPA to keep external links alive.
  * Reference: `backend/routers/be_auth.py` (reset email builder), `backend/routers/be_album.py` `create_share_token` `share_url`.
* Confirm whether the SPA AdminPage or any SPA code calls `/category/create`.
  * Reasoning: decides if that fe_router JSON route is Jinja-only (removable) or SPA-shared (relocate).
  * Reference: `frontend/spa/src/pages/AdminPage.tsx`, `frontend/spa/src/lib/*`.
* Confirm the SPA fully covers `admin_groups` (user↔group, album↔group linking) functionality.
  * Reasoning: `AdminPage.tsx` is a single page; the Jinja side had separate `admin_users.html` + `admin_groups.html`. A functional gap would be exposed by removal.
  * Reference: `frontend/spa/src/pages/AdminPage.tsx`.

## Research Executed

### File Analysis

* frontend/templates/ (directory listing)
  * Confirmed 14 `.html` files: admin_groups, admin_users, album_detail, album_edit, album_form, album_upload, base, forgot_password, index, login, profile, reset_password, shared_album, signup.
* frontend/routers/fe_router.py (full read, 1–1500+)
  * Line 8 `from fastapi.templating import Jinja2Templates`; line 21 `templates = Jinja2Templates(directory="frontend/templates")`.
  * 22 route decorators total (see Category B). 18 render Jinja `TemplateResponse`; 4 are JSON/redirect utilities.
  * CRITICAL: two JSON routes here are consumed by the SPA (see Category B / Risk 1).
* AlbumsAventures-BE.py (1–137)
  * Line 39 `from frontend.routers import fe_router`; line 40 `from frontend.spa_serving import configure_spa`.
  * Line 129 `app.include_router(fe_router.router)` (last router before mounts).
  * Lines 122–131 static/media mounts; line 138-ish `configure_spa(app)` LAST.
* AlbumsAventures_BE_test.py (1–62)
  * Line 19 `from frontend.routers import fe_router`; line 20 `configure_spa` import; line 53 `app.include_router(fe_router.router)`; line 61 `configure_spa(app)`.
* frontend/spa_serving.py (full read)
  * SPA fallback is scoped to `SPA_URL_PREFIX = "/app"` ONLY (lines ~55, ~200-215). It binds `/app` and `/app/{full_path:path}` — it does NOT catch bare `/`, `/login`, `/album/...`. So removing Jinja routes leaves those bare paths with no handler (404).
* utils/security.py (1–230)
  * Two-tier CSP: `_CSP_DIRECTIVES_JINJA` (lines ~118-124) keeps CDNs + `'unsafe-inline'`; `_CSP_DIRECTIVES_SPA` (lines ~127-135) is hardened. Middleware chooses by `/app` prefix (lines ~200-214). CDN host constants at lines ~106-108.
* frontend/spa/src/App.tsx (1–137)
  * SPA routes use DIFFERENT paths than Jinja (plural `/albums/:id`, `/shared/:token`, plus `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/profile`, `/admin`). Comments (lines 116-122) explicitly note the Jinja auth pages "keep working during the strangler migration."
* frontend/spa/src/pages/AlbumDetailPage.tsx (line 30) and SharedAlbumPage.tsx (lines 49, 72)
  * SPA calls `/album/{albumId}/images` and `/album/shared/images` — both defined in `fe_router.py`.

### Code Search Results

* `@router.(get|post)` in fe_router.py → 22 matches (exact line numbers in Category B).
* `cdn.tailwindcss|unpkg|releases.transloadit` in frontend/templates/** → base.html (Tailwind CDN L8, Alpine unpkg L114), album_detail.html (PhotoSwipe/Masonry/imagesLoaded unpkg L7/L336/L337), album_upload.html (Uppy transloadit L10/L150).
* `Content-Security-Policy|unsafe-inline|_CDN` in tests/test_auth.py → `TestSecurityHeaders` class (L373-460): asserts the 3 CDNs present, `'unsafe-inline'` present on non-`/app`, and `/app` hardened.
* SPA src search for `/album/.../images`, `/album/shared/images`, `/be_album` → confirmed SPA depends on the two fe_router JSON endpoints; album grid/detail metadata come from `/be_album/*`.

### Project Conventions

* Standards referenced: `.github/instructions/python-script.instructions.md` conventions; repo README stack sections.
* Instructions followed: research-only mode; artifact under `.copilot-tracking/research/`; plain-text workspace-relative paths.

## Key Discoveries

### HEADLINE FINDINGS (read first)

1. `fe_router.py` is NOT purely Jinja. It mixes 18 Jinja-render routes with 4 non-Jinja routes, and TWO of those non-Jinja JSON routes are actively called by the live SPA:
   * `GET /album/{album_id}/images` (fe_router.py line 1184) ← called by `frontend/spa/src/pages/AlbumDetailPage.tsx` line 30.
   * `GET /album/shared/images` (fe_router.py line 1096) ← called by `frontend/spa/src/pages/SharedAlbumPage.tsx` line 72.
   * A naive `app.include_router(fe_router.router)` deletion would BREAK SPA album-detail media pagination and SPA shared-album media loading. These two endpoints (and their private helpers `_get_album_media_page`, `_album_folder_info`, `_PAGE_SIZE`, extension constants) MUST be relocated to a backend router (e.g. `be_album`) or otherwise preserved — they are the strangler's data plane, not its view layer.
2. The SPA fallback only serves `/app`. Bare Jinja URLs (`/`, `/login`, `/signup`, `/profile`, `/admin/users`, `/admin/groups`, `/forgot-password`, `/reset-password`, `/album/{id}`, `/album/{id}/edit`, `/album/new`, `/album/{id}/upload`, `/album/shared`) currently resolve ONLY because `fe_router` handles them. After removal they return 404 unless redirects to the SPA equivalents are added. SPA uses different paths (plural `/app/albums/:id`, `/app/shared/:token`).
3. Jinja page URLs differ from SPA URLs, so removal is not a 1:1 path swap: `/album/{id}` (Jinja, singular) vs `/app/albums/:id` (SPA, plural); `/album/shared?token=` (Jinja) vs `/app/shared/:token` (SPA); `/admin/users` + `/admin/groups` (two Jinja pages) vs a single `/app/admin` (SPA AdminPage) — a potential functional gap.

### Category A — Template files (14 confirmed)

All under `frontend/templates/`. Full list confirmed (matches the task's 14):

| # | Template | Rendered by (fe_router route) |
|---|----------|-------------------------------|
| 1 | base.html | Layout base (extended by all); loads Tailwind + Alpine CDN |
| 2 | index.html | GET / |
| 3 | login.html | GET /login, POST /login (errors) |
| 4 | signup.html | GET /signup, POST /signup (errors) |
| 5 | forgot_password.html | GET /forgot-password |
| 6 | reset_password.html | GET /reset-password |
| 7 | profile.html | GET /profile |
| 8 | admin_users.html | GET /admin/users |
| 9 | admin_groups.html | GET /admin/groups |
| 10 | album_form.html | GET /album/new, POST /album/new (errors) |
| 11 | album_edit.html | GET/POST /album/{album_id}/edit |
| 12 | album_detail.html | GET /album/{album_id}, POST /album/shared (shared mode); loads PhotoSwipe/Masonry/imagesLoaded CDN |
| 13 | album_upload.html | GET /album/{album_id}/upload; loads Uppy CDN |
| 14 | shared_album.html | GET/POST /album/shared |

All 14 are removable (they are the view layer). `base.html`, `album_detail.html`, and `album_upload.html` are the CDN carriers (Category D).

### Category B — Jinja serving code (`frontend/routers/fe_router.py`)

Jinja binding: line 8 import, line 21 `templates = Jinja2Templates(directory="frontend/templates")`.

Route inventory (22 decorators). Classification: **[JINJA]** = renders `TemplateResponse` (remove); **[JSON/keep]** = JSON API the SPA still needs (relocate/preserve); **[JSON-verify]** = JSON, likely Jinja-only (verify); **[REDIR]** = redirect only.

| Line | Method + Path | Class | Renders / Notes |
|------|---------------|-------|-----------------|
| 24 | GET `/` | JINJA | index.html (server-side auth guard → /login) |
| 78 | GET `/login` | JINJA | login.html + CSRF cookie |
| 86 | POST `/login` | JINJA | login.html on error; else 303 → `/` (cookie relay) |
| 186 | GET `/forgot-password` | JINJA | forgot_password.html |
| 195 | GET `/reset-password` | JINJA | reset_password.html (token in query) |
| 208 | GET `/signup` | JINJA | signup.html |
| 217 | POST `/signup` | JINJA | signup.html on error; else 303 → `/login?registered=true` |
| 336 | GET `/profile` | JINJA | profile.html |
| 369 | GET `/admin/users` | JINJA | admin_users.html (superuser guard) |
| 387 | GET `/admin/groups` | JINJA | admin_groups.html (superuser guard) |
| 408 | POST `/category/create` | JSON-verify | JSONResponse; AJAX from Jinja base.html inline JS. Verify SPA AdminPage does not use it. |
| 466 | GET `/album/new` | JINJA | album_form.html |
| 489 | POST `/album/new` | JINJA | album_form.html on error; else 303 → /admin/groups; also `_save_cover_image` side-effects |
| 680 | GET `/album/{album_id}/edit` | JINJA | album_edit.html |
| 738 | POST `/album/{album_id}/edit` | JINJA | album_edit.html on error; else 303 → /album/{id} |
| 994 | GET `/album/shared` | JINJA | shared_album.html (public, token in query) |
| 1013 | POST `/album/shared` | JINJA | shared_album.html (PIN error) / album_detail.html (shared mode) |
| 1096 | GET `/album/shared/images` | **JSON/keep** | JSONResponse — **called by SPA SharedAlbumPage.tsx L72**. Preserve/relocate. |
| 1125 | GET `/album/{album_id}` | JINJA | album_detail.html |
| 1184 | GET `/album/{album_id}/images` | **JSON/keep** | JSONResponse — **called by SPA AlbumDetailPage.tsx L30**. Preserve/relocate. |
| 1217 | GET `/album/{album_id}/upload` | JINJA | album_upload.html |
| 1250 | GET `/rando` | REDIR | 302 → `/static/rando/propositions-rando.html` (standalone static; not Jinja). Decide keep vs move. |

Private helpers in this file used by BOTH Jinja routes and the SPA-facing JSON routes (so they cannot all be deleted): `_get_album_media_page` (~L926), `_album_folder_info` (~L888), `_PAGE_SIZE`/`_IMAGE_EXTENSIONS`/`_VIDEO_EXTENSIONS`/`_ALL_EXTENSIONS` (~L884), `_get_categories` (~L1258), `_get_album_folder_path`/`_save_cover_image` (~L1279+, used only by Jinja album create/edit → removable with them).

### Category C — App wiring & registration order

Production `AlbumsAventures-BE.py`:
* Line 39: `from frontend.routers import fe_router`
* Line 40: `from frontend.spa_serving import configure_spa`
* Line 129: `app.include_router(fe_router.router)` — registered AFTER all `be_*` routers, BEFORE mounts.
* Lines 122–131: `app.mount("/static" | "/thumbnails" | "/images", ...)`.
* Final call: `configure_spa(app)` — registers `/app` and `/app/{full_path:path}` LAST (so it never shadows `/be_*`, media, or `fe_router`).

Test app `AlbumsAventures_BE_test.py`:
* Line 19–20 imports; line 53 `app.include_router(fe_router.router)`; line 61 `configure_spa(app)`.

Removal wiring impact:
* Removing the `fe_router` include from BOTH files, plus the `from frontend.routers import fe_router` imports, is required.
* The `configure_spa` call and its LAST-position ordering must remain unchanged so SPA + media mounts still serve.
* If bare-path redirects are chosen (Risk 2 mitigation), they need a small dedicated router (or a replacement in `spa_serving.py`) registered in the same last-but-one slot fe_router occupied.

### Category D — CDN assets: Jinja-only vs SPA-shared

Jinja-ONLY (remove with templates; safe to drop from CSP afterward):
* `frontend/templates/base.html` L8 `https://cdn.tailwindcss.com` (Tailwind CDN, all Jinja pages).
* `frontend/templates/base.html` L114 `https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js` (Alpine).
* `frontend/templates/album_detail.html` L7 `https://unpkg.com/photoswipe@5/...css`, L336 `masonry-layout@4`, L337 `imagesloaded@5` (all unpkg).
* `frontend/templates/album_upload.html` L10 `https://releases.transloadit.com/uppy/v3.27.0/uppy.min.css`, L150 `uppy.min.js`.

SPA-SHARED (DO NOT remove):
* `frontend/static/` mount (`/static`) — holds `favicon.ico`, `images/`, `rando/`, `thumbnails/`. `favicon.ico` and `/static/rando/*` are used independently of Jinja. The SPA bundles its OWN Tailwind (build-time, see `frontend/spa/README.md` L19) and its OWN Uppy v5 (ESM, lazy-loaded via `UploadPage`), so the SPA does NOT need any CDN.
* `/images`, `/thumbnails` media mounts — core app media, shared by SPA and API.

Net: after Jinja removal, NO CDN origin is required by any served page; all three CDN hosts become dead in the CSP.

### Category E — `jinja2` dependency assessment

* `requirements.txt` line ~14: `jinja2` is a DIRECT dependency, listed only for the app's Jinja rendering.
* `pyproject.toml` line 4: project description literally reads "(FastAPI + Jinja2)" — doc string only.
* Consumers of the `jinja2` PyPI package in app code: ONLY `frontend/routers/fe_router.py` via `fastapi.templating.Jinja2Templates` (which imports `starlette.templating`, whose Jinja support is an OPTIONAL extra). No `be_*` router, `utils/*`, or test imports Jinja.
* FastAPI/Starlette themselves do NOT require `jinja2` at runtime unless `Jinja2Templates` is used. Once `fe_router`'s Jinja usage is gone, `jinja2` can be dropped from `requirements.txt`.
* Caveat: `apm_modules/**` vendored HVE-Core skills reference "templates" (python-diagrams, customer-card-render, documentation) but those are unrelated skill assets, not the app's `jinja2` package — they do not block removal. Recommend a fresh `pip install`/lock after removal to confirm nothing transitively needed it.

### Category F — Routing collision risk (current vs post-removal)

| Path | Today (served by) | After Jinja removal (no mitigation) | SPA equivalent |
|------|-------------------|--------------------------------------|----------------|
| `/` | fe_router GET / (Jinja, auth-gated) | 404 | `/app/` |
| `/login` | fe_router (Jinja) | 404 | `/app/login` |
| `/signup` | fe_router (Jinja) | 404 | `/app/signup` |
| `/forgot-password` | fe_router (Jinja) | 404 | `/app/forgot-password` |
| `/reset-password?token=` | fe_router (Jinja) | 404 | `/app/reset-password` |
| `/profile` | fe_router (Jinja) | 404 | `/app/profile` |
| `/admin/users` + `/admin/groups` | fe_router (Jinja, 2 pages) | 404 | `/app/admin` (1 page) |
| `/album/{id}` | fe_router (Jinja) | 404 | `/app/albums/:id` (plural) |
| `/album/{id}/edit`,`/album/new`,`/album/{id}/upload` | fe_router (Jinja) | 404 | `/app/albums/:id/upload` (edit/new have no direct SPA route seen) |
| `/album/shared?token=` | fe_router (Jinja) | 404 | `/app/shared/:token` |
| `/album/{id}/images` | fe_router (JSON) | **404 → SPA detail BREAKS** | (same URL, SPA calls it) |
| `/album/shared/images` | fe_router (JSON) | **404 → SPA shared BREAKS** | (same URL, SPA calls it) |
| `/app/**` | SPA fallback | unchanged | — |
| `/be_*`, `/images`, `/thumbnails`, `/static` | backend/mounts | unchanged | — |

Mitigation options for the bare paths (planning decision): (a) add a thin redirect router mapping bare → `/app/...` (preserves external links, best UX), or (b) return 404 (simplest, breaks any external links/bookmarks). The two JSON rows are NOT optional — they must keep responding.

### Category G — Tests referencing Jinja / CSP

* `test_frontend_login.py` (root) — Jinja-coupled. Asserts `client.get("/fe_router/login")` returns 200 and the rendered HTML contains "Bienvenue — Connectez-vous" and "Mot de passe oublié" (lines 10-15). NOTE: it targets `/fe_router/login` (a path that does not exist since the router has no prefix), so this test is likely ALREADY stale/failing; regardless it asserts on Jinja-rendered HTML and must be deleted or rewritten against the SPA.
* `test_share_album.py` (root) — integration script hitting `/be_auth/login`, `/be_album/create_share_token/...` (backend only). Does NOT assert on Jinja HTML; survives removal (it exercises the backend share API the SPA also uses). No change needed for Jinja, but references the share flow (see Open Q2).
* `run_test_login.py` (root) — not yet opened; grep found no Jinja/HTML assertions. Treat as low risk; verify during planning.
* `tests/test_auth.py::TestSecurityHeaders` (L373-460) — asserts the CSP shape, INCLUDING the Jinja-tier expectations. These assertions will need updating after CSP tightening (Category H):
  * L419: `assert "https://cdn.tailwindcss.com" in csp` (on `/be_auth/me`, i.e. Jinja-tier).
  * L420-421: `assert "https://unpkg.com" in csp`, `assert "https://releases.transloadit.com" in csp`.
  * L426: `assert "'unsafe-inline'" in csp` (Jinja-tier script-src).
  * L436-446: `/app` hardened assertions (these STAY valid and become the single policy).
* `tests/test_auth.py` other classes (login/signup/activate/forgot/reset) target `/be_auth/*` backend endpoints — NOT Jinja; survive removal.
* `tests/test_albums.py`, `tests/test_upload.py`, `tests/conftest.py` — no Jinja route assertions found.

### Category H — CSP / security coupling (`utils/security.py`)

The middleware serves a two-tier CSP explicitly to keep the Jinja fallback working (comment block L82-104). Directives that exist ONLY to support Jinja/CDN:

* CDN host constants (L106-108): `_CDN_TAILWIND = "https://cdn.tailwindcss.com"`, `_CDN_UNPKG = "https://unpkg.com"`, `_CDN_UPPY = "https://releases.transloadit.com"`.
* `_CSP_DIRECTIVES_JINJA` (L118-124):
  * `script-src ['self', 'unsafe-inline', _CDN_TAILWIND, _CDN_UNPKG, _CDN_UPPY]`
  * `style-src  ['self', 'unsafe-inline', _CDN_TAILWIND, _CDN_UNPKG, _CDN_UPPY]`
* Middleware branch (L200-214): non-`/app` requests get `_CSP_DIRECTIVES_JINJA`; `/app` gets `_CSP_DIRECTIVES_SPA`.

The hardened `_CSP_DIRECTIVES_SPA` (L127-135) is `script-src 'self'` and `style-src 'self' 'unsafe-inline'` (the residual `'unsafe-inline'` in style-src is for runtime-injected styles from bundled libs like Uppy — a SEPARATE, already-tracked deferral, NOT a Jinja dependency).

Security assessment after Jinja removal: the two-tier split collapses. All served surfaces become same-origin SPA/API, so the app can drop the three CDN hosts and script-src `'unsafe-inline'` entirely and apply the hardened policy universally. Shared directives in `_CSP_SHARED` (default-src, img-src, connect-src, worker-src, etc.) are unaffected. The media sandbox CSP (`_MEDIA_CSP`, L138) is unrelated to Jinja and stays. This is a security WIN and should be validated by updating `TestSecurityHeaders`.

### Category I — Docs / config references

* `README.md`:
  * L97 / L286: "**Templates** : Jinja2 pour le rendu HTML côté serveur".
  * L98 / L287: Tailwind CDN "acceptable en prototype" guidance.
  * L101 / L290: "upload images + vidéos : uppy.io via CDN".
  * L332: "separation backend/frontend ... templates Jinja2, static files".
  * L333: "frontend dynamique : Utiliser Jinja2 ... privilégier Alpine.js".
  * These are stack-description sections; update to reflect the SPA-only frontend after removal.
* `pyproject.toml` L4: description "(FastAPI + Jinja2)" — update.
* `frontend/spa/README.md`: L4 "strangler migration of the Jinja2", L19 build-time Tailwind "replaces the runtime Tailwind CDN for SPA", L63-65 "the existing Jinja2 pages (`/`, ...) ... increments migrate the remaining pages and then retire the CDN". Update to mark strangler complete.
* No occurrence of the literal phrase "variante hybride" was found in `docs/**` or `README.md`; the "hybrid" concept is captured by the strangler/CSP wording above.
* `docs/` files (agent.md, TODO.md, GUIDELINES_UI.md, Bulk-upload.md, GESTION_*.md) — no Jinja route/template coupling found in the searched set; GUIDELINES_UI.md is the design-token source the SPA already consumes.

## Technical Scenarios

### Complete, safe Jinja decommission (recommended shape for the lead)

Removing Jinja is safe ONLY if the SPA-facing data endpoints are preserved and bare paths are handled. Recommended removal shape (for planning — NOT executed here):

**Requirements:**

* Delete all 14 `frontend/templates/*.html`.
* Remove the 18 `[JINJA]` routes and their Jinja-only helpers (`_get_categories`, `_get_album_folder_path`, `_save_cover_image`) from `fe_router.py`.
* PRESERVE `GET /album/{album_id}/images` and `GET /album/shared/images` (+ helpers `_get_album_media_page`, `_album_folder_info`, page-size/extension constants) by relocating them into a backend router (e.g. `backend/routers/be_album.py`) so the SPA keeps working at the SAME URLs.
* Decide `/category/create` (verify SPA use) and `/rando` (standalone redirect) fate.
* Remove `fe_router` include + import from `AlbumsAventures-BE.py` and `AlbumsAventures_BE_test.py`; keep `configure_spa` LAST.
* Add bare-path handling (redirect to `/app/...` OR 404) — council decision.
* Drop `jinja2` from `requirements.txt`; update `pyproject.toml` description.
* Collapse the CSP to the single hardened policy; delete `_CSP_DIRECTIVES_JINJA` + CDN constants.
* Delete/rewrite `test_frontend_login.py`; update `tests/test_auth.py::TestSecurityHeaders` CDN/`unsafe-inline` assertions.
* Update README/docs stack sections.

**Preferred Approach:**

* Two-step so nothing breaks: (1) relocate the two SPA-facing JSON endpoints to `be_album` (same paths) and repoint nothing on the client; (2) delete templates + Jinja routes + `jinja2` + tighten CSP + add bare-path redirects. Reason: decouples the risky data-plane move from the bulk view deletion, keeping the SPA green throughout.

```text
frontend/
  templates/                 [DELETE all 14 .html]
  routers/fe_router.py       [REMOVE 18 Jinja routes + Jinja-only helpers; RELOCATE 2 JSON endpoints]
AlbumsAventures-BE.py         [REMOVE fe_router import+include; keep configure_spa last; maybe add redirect router]
AlbumsAventures_BE_test.py    [REMOVE fe_router import+include]
utils/security.py             [DELETE _CSP_DIRECTIVES_JINJA + CDN constants; single hardened CSP]
requirements.txt              [REMOVE jinja2]
pyproject.toml                [EDIT description]
tests/test_auth.py            [UPDATE TestSecurityHeaders]
test_frontend_login.py        [DELETE or rewrite for SPA]
README.md / frontend/spa/README.md [EDIT stack + strangler-complete notes]
```

**Implementation Details:**

The single hard constraint: the SPA calls `/album/{id}/images` and `/album/shared/images` (fe_router.py L1184, L1096) at those exact URLs. Any plan that deletes `fe_router.router` wholesale without relocating these two endpoints will break SPA album-detail pagination and shared-album viewing.

#### Considered Alternatives

* "Delete `fe_router.py` and its include in one shot." Rejected: breaks the two SPA-facing JSON endpoints (Risk 1) and leaves bare paths 404 (Risk 2) with no external-link continuity (Risk 3). Not safe as a single step.
* "Keep `jinja2` in requirements just in case." Rejected: no remaining app consumer once Jinja routes go; keeping it contradicts the user's "remove ALL Jinja code" intent. A post-removal lock check covers any surprise transitive need.

## Top 3 Risks

1. SPA breakage via shared JSON endpoints (HIGHEST). `GET /album/{album_id}/images` (fe_router.py L1184) and `GET /album/shared/images` (fe_router.py L1096) are JSON APIs living inside the Jinja router but consumed by the live SPA (`AlbumDetailPage.tsx` L30, `SharedAlbumPage.tsx` L72). Deleting the router removes them → SPA album detail and shared album stop loading media. MUST relocate/preserve at the same URLs before/with removal.
2. Routing collision / dead bare paths. The SPA fallback only covers `/app`. Bare `/`, `/login`, `/album/{id}`, `/album/shared`, etc. become 404 after removal because only `fe_router` served them. Requires an explicit decision: redirect bare → `/app/...` or return 404.
3. CSP-test coupling + external-link continuity. `tests/test_auth.py::TestSecurityHeaders` asserts the CDN hosts and `'unsafe-inline'` are PRESENT (L419-426); tightening the CSP without updating these tests fails CI. Separately, password-reset emails and share links may point at bare Jinja URLs (`/reset-password?token=`, share `share_url`) — if so, removal breaks external links unless redirects are added.

## Open Questions for Council (do not resolve)

1. Removed Jinja routes: redirect to the SPA equivalent (`/` → `/app/`, `/album/{id}` → `/app/albums/:id`, `/album/shared?token=` → `/app/shared/:token`, `/admin/users` + `/admin/groups` → `/app/admin`) or return 404? Redirects preserve bookmarks/external links but add a small compatibility shim; 404 is cleaner but harder-breaking.
2. External reachability: do password-reset emails (`backend/routers/be_auth.py`) and share links (`create_share_token` `share_url` in `backend/routers/be_album.py`) point at bare Jinja paths that MUST keep working via the SPA? If yes, redirects for `/reset-password` and `/album/shared` are mandatory, not optional.
3. Functional-parity gap: does the SPA cover 100% of the Jinja pages? Specific concerns — (a) the two Jinja admin pages (`admin_users.html` + `admin_groups.html`, incl. user↔group and album↔group linking) map to a single SPA `AdminPage`; (b) no obvious SPA route for `/album/new` and `/album/{id}/edit` (album create/edit) was found — only `/app/albums/:id/upload`. Removal would expose any missing SPA feature. Needs a parity audit before deletion.
