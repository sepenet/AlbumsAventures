<!-- markdownlint-disable-file -->
# Release Changes: Phase 3.6 Admin Page (React) + F-1 Backend Security Fix

**Related Plan**: albumsaventures-phase3-spa.md (Phase 3.6)
**Implementation Date**: 2026-07-07
**Role**: developer (member Gamma), squad autopilot — increment 5

## Summary

Two deliverables in one increment:

1. **Phase 3.6 — React admin page** (`/app/admin`), superuser-only, mirroring the
   Jinja `admin_users.html` + `admin_groups.html` functionality: pending-user
   activation, promote/demote-to-admin, and user/group access management. Cookie-only
   auth; every mutation carries the CSRF double-submit header via the shared apiClient;
   loading/error/success states and confirmation prompts for destructive actions. The
   Jinja admin pages stay live (strangler).

2. **F-1 — backend security fix** for `be_resizer.create_thumbnails`, previously a
   state-changing **GET** that was authenticated but **not** superuser-gated
   server-side. It is now a **POST** (state change must not be a GET → restores the
   CSRF/SameSite posture) and is **superuser-gated server-side** via a reusable
   `require_superuser` dependency (403 for non-admins). All callers (SPA + both Jinja
   pages) updated. This resolves the tracked F-1 escalation from the increment-3.3 review.

## Changes

### Added

* frontend/spa/src/pages/AdminPage.tsx - React admin page: Users panel (filter all/pending/active, activate/deactivate, promote/demote with confirm + self-demotion guard) and Groups panel (list/create/delete groups, view details, add/remove members and albums). React Query + apiClient (CSRF on mutations).
* frontend/spa/src/auth/RequireSuperuser.tsx - superuser route guard; redirects non-admins to the grid (UX gate; server remains the authority).
* frontend/spa/src/lib/admin.ts - pure, DOM-free admin helpers: `canAccessAdmin`, `adminUsersQuery`, `isPending`, `pendingCount`, `isSelfDemotion`, confirmation-message builders, `displayName`.
* frontend/spa/src/lib/admin.test.ts - 13 Vitest cases; core superuser-gate smoke test (`canAccessAdmin` grants superuser / denies non-superuser / denies no-session) plus filter mapping, pending counting, self-demotion guard, and confirmation phrasing.
* tests/e2e/test_spa_admin_ui.py - Playwright smoke: superuser sees the admin page + tab toggle + header Admin link; non-superuser is redirected (no Administration heading, no Admin link).
* tests/test_upload.py::TestCreateThumbnailsSecurity - 4 F-1 backend tests (non-superuser 403, GET 405, superuser POST 200 with mocked thumbnail work, unauthenticated 401).

### Modified

* backend/routers/be_auth.py - added reusable `require_superuser(request, db)` dependency (re-checks `is_superuser` in DB, returns the user or raises 403). Reused by F-1; consistent with the existing SEC-01 inline checks.
* backend/routers/be_resizer.py - **F-1**: `create_thumbnails` changed from `@router.get` to `@router.post`; added `_current_user=Depends(require_superuser)`; imported `require_superuser`. Behavior otherwise unchanged.
* frontend/spa/src/pages/AlbumDetailPage.tsx - **F-1 caller**: regenerate-thumbnails mutation now `api.post(...)` (was `api.get(...)`) → apiClient auto-sends the `X-CSRF-Token` header on POST.
* frontend/templates/album_upload.html - **F-1 caller**: `create_thumbnails` fetch now `method: 'POST'` (keeps the Jinja upload page working post-migration).
* frontend/templates/index.html - **F-1 caller**: `generateThumbnails` fetch now `method: 'POST'`.
* frontend/spa/src/App.tsx - registered the `/admin` route wrapped in `RequireAuth` → `RequireSuperuser` → `Layout`.
* frontend/spa/src/components/Layout.tsx - added a superuser-only `Admin` nav link (`user?.is_superuser`).
* frontend/spa/src/types/api.ts - added admin types: `AdminUser`, `UserRightsUpdate`, `Group`, `SimpleUser`, `SimpleAlbum`, `GroupMemberUser`, `GroupAlbum`, `GroupDetails`.

### Removed

* (none)

## F-1 fix details

* **Server change**: `GET /be_resizer/create_thumbnails/{album_id}` → `POST` with `Depends(require_superuser)`.
* **CSRF posture**: the app has no header-validating CSRF middleware; JSON-endpoint CSRF defense is the SameSite auth cookie + non-GET method (identical to the sibling `be_auth/activate` and `.../rights` admin mutations, which also rely on SameSite + POST/PUT rather than an explicit `require_csrf(form_token)`). Converting the write from GET → POST is precisely what restores that protection; the SPA additionally echoes `X-CSRF-Token` via apiClient on every mutation. No new middleware was introduced, matching the existing app pattern.
* **Superuser enforcement**: server-side in `require_superuser` (re-reads the user from the DB and checks `is_superuser`, so a demotion takes effect immediately). The client button remains hidden for non-superusers, but that is no longer the security boundary.
* **Callers updated**: SPA `AlbumDetailPage.tsx` (POST + CSRF header), Jinja `album_upload.html` and `index.html` (`method: 'POST'`, `credentials: 'include'` unchanged) so both Jinja pages keep working.
* **Test result**: `tests/test_upload.py::TestCreateThumbnailsSecurity` — 4/4 pass (non-superuser POST → 403; GET → 405; superuser POST → 200 with `img_thumbnails`/`get_album_paths` monkeypatched; unauthenticated → 401).

## Validation Results

* **Backend**: `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` → **54 passed** (was 50; +4 F-1). App imports cleanly (`108 routes`). `ruff check` → all checks passed; `black --check` → 4 files unchanged (changed `.py` only; `.agents/skills/**` untouched).
* **Frontend**: `npm run build` → success, no >500 kB chunk warning (main JS 251.48 kB gzip 76.56 kB; UploadPage stays a separate lazy chunk). `npm run lint` (`--max-warnings 0`) → clean. `npm run test` (Vitest) → **48 passed** (was 35; +13 admin).
* **Security posture**: no CSP `unsafe-eval`/`*` introduced; no CORS; Node build-time only. No backend behavior change beyond F-1. No deploy/push/merge; no migrations applied.

## Additional or Deviating Changes

* **CSRF implementation choice (F-1)**: did not add an explicit `require_csrf`/global CSRF middleware to `create_thumbnails`. Rationale: the endpoint's siblings (`be_auth/activate`, `be_auth/admin/users/{id}/rights`) are POST/PUT and rely on the SameSite cookie + method semantics with no `require_csrf(form_token)` call; matching them keeps the change consistent and avoids diverging the JSON-mutation CSRF model. The GET → POST conversion is the substantive, testable server-side fix; the SPA sends the header regardless.
* **Group-management server-side gating**: the `be_group` endpoints are auth-only server-side (not superuser-gated) — this matches the current Jinja admin behavior, which also gates group management client-side only. Not changed here (out of F-1 scope; strangler parity). Flagged as a potential follow-on hardening item.

## Deferrals / Follow-on

* **WI (Low)**: consider server-side superuser gating on the `be_group` admin endpoints (currently auth-only, client-gated) — parity hardening beyond F-1 scope.
* **e2e execution**: `test_spa_admin_ui.py` requires a running server + built SPA + `E2E_ADMIN_PASSWORD`/`E2E_USER_PASSWORD`; not executed in this pass (consistent with prior increments — e2e execution is a Phase 4 hardening item).

## Release Summary

* **Files added**: 5 (`AdminPage.tsx`, `RequireSuperuser.tsx`, `admin.ts`, `admin.test.ts`, `test_spa_admin_ui.py`) + 1 test class in `tests/test_upload.py`.
* **Files modified**: 8 (`be_auth.py`, `be_resizer.py`, `AlbumDetailPage.tsx`, `album_upload.html`, `index.html`, `App.tsx`, `Layout.tsx`, `types/api.ts`).
* **Backend**: 1 new reusable dependency; 1 endpoint hardened (GET→POST + superuser gate); +4 tests → 54 pass.
* **Frontend**: 1 new superuser-only page + guard; +13 Vitest → 48 pass; build/lint green.
* **No** infra/dependency changes, migrations, or deployments.
