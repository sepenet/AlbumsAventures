<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 Increment 7 (sub-phase 3.8 — auth pages + C-8 loopback retire + FU-group hardening)

**Related Plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (Phase 3.8) — working plan in session memory `phase3.8-auth-plan.md`
**Implementation Date**: 2026-07-07
**Status**: BACKFILLED 2026-07-07 (developer output for the original increment was truncated and left no change record; reconstructed from the working tree + review `.copilot-tracking/reviews/2026-07-07/albumsaventures-phase3-increment7-review.md`)

## Summary

Increment 7 migrated the four authentication pages (login, signup, forgot-password, reset-password) to the React SPA, converted the C-8 auth-guard `/me` self-call from an HTTP loopback to an in-process call, and hardened the group-management routes with a server-side superuser gate (OWASP A01). No token is ever stored in JS — the session stays in the server-set HttpOnly cookie (PD-01: 60-minute cookie, no refresh endpoint; a 401 redirects to login). The Jinja auth flow is left fully intact (incremental strangler).

## Changes

### Added

* `frontend/spa/src/pages/LoginPage.tsx` - SPA login; form-encoded `POST /be_auth/login`; on success invalidates `["session"]` and navigates to `/`; already-authed guard; inline 401/400 error; reads `?registered=true`.
* `frontend/spa/src/pages/SignupPage.tsx` - SPA signup via `api.post /be_auth/create/` (`is_active:false`, `is_superuser:false`); on success navigates to `/login?registered=true`.
* `frontend/spa/src/pages/ForgotPasswordPage.tsx` - requests `POST /be_auth/forgot-password` `{email}`.
* `frontend/spa/src/pages/ResetPasswordPage.tsx` - reads `token` from `useSearchParams()`; malformed-link guard when absent; `POST /be_auth/reset-password` `{token,new_password}`.
* `frontend/spa/src/components/AuthCard.tsx` - shared standalone auth layout (no app `Layout`, public surface).
* `frontend/spa/src/lib/authApi.ts` - auth calls; login uses a dedicated `fetch` with `credentials: "same-origin"` and reads `detail` on `!ok` so 401 detail is not masked by the shared `api.post` wrapper.
* `frontend/spa/src/lib/authValidation.ts` - pure client-side validation (login: email format + required, password required; signup: first/last ≥ 2, email regex, password policy `(?=.*[a-z])(?=.*[A-Z])(?=.*\d)` min 8, match; forgot: email; reset: password policy + match).
* `frontend/spa/src/lib/authValidation.test.ts` - unit tests for the validation rules (15 tests).
* `tests/e2e/test_spa_auth_ui.py` - Playwright smoke for the SPA auth pages (skips cleanly without a live server).
* `tests/test_auth.py::TestGroupMutationSuperuserGate` - non-superuser → 403, superuser → 200, unauthenticated → 401 on the representative `create_group` mutation.

### Modified

* `frontend/spa/src/App.tsx` - added public routes `/login`, `/signup`, `/forgot-password`, `/reset-password` OUTSIDE `RequireAuth`/`Layout`, before the catch-all; `RequireAuth` redirect target and `Layout` logout target point at the SPA login.
* `utils/auth.py` - **C-8 conversion**: `verify_authentication` now `await get_current_user(request)` IN-PROCESS (lazy import of `be_auth.get_current_user`), then loads the user via `crud.get_user_info_by_id` on a dedicated `SessionLocal()` (closed in `finally`), returning a `UserAdmin`-shaped dict. `HTTPException → None` preserves the historical "auth failed → None" contract. Removed the live `httpx`/`localhost`/`backend_api` round-trip (only a docstring mention remains, explaining what was removed); added `HTTPException` import.
* `backend/routers/be_group.py` - **FU-group (OWASP A01)**: imported `require_superuser` from `.be_auth` and added `dependencies=[Depends(require_superuser)]` to all 13 state-mutating routes (create/update/delete group, user-group, album-group and their bulk variants, user-album). The router keeps `Depends(get_current_user)`; GET/read routes remain auth-only. The gate re-checks `is_superuser` **in the DB**, so a demotion takes effect immediately.

## Additional or Deviating Changes

* **Deferred (per plan): fe_router data-fetch loopback.** `frontend/routers/fe_router.py` is unchanged. Only the auth-guard `/me` self-call was converted to in-process; the fe_router page-data loopback (album lists, cover URLs) still round-trips while Jinja renders those pages. Reason: replicating the `be_album` cover-URL logic carries higher regression risk and the strangler still holds. Tracked as remaining C-8 work.
* **No CSP/CORS change in this increment.** Scope was limited to `be_group.py` + `utils/auth.py` on the backend and the SPA auth pages on the frontend. No `unsafe-eval`/`unsafe-inline` introduced. (CSP tightening is the separate increment 8 / sub-phase 3.9.)
* **Client-side button masking is no longer the only control** for group mutations — the server now rejects non-admin mutations with 403.

## Validation Evidence

| Gate | Command | Result |
|------|---------|--------|
| Backend tests | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | 58 passed |
| Ruff | `ruff check utils/auth.py backend/routers/be_group.py tests/test_auth.py` | All checks passed |
| Black | `black --check` (same files) | unchanged |
| App import | exercised by the `client` fixture across the passing backend suite | clean |
| SPA build | `npm run build` | built; separate `UploadPage-*.js` chunk preserved |
| SPA lint | `npm run lint` (`--max-warnings 0`) | 0 warnings |
| SPA test | `npm run test` | 74 passed (7 files) |

## Release Summary

* **Auth surface**: 4 SPA auth pages + shared `AuthCard`, backed by `authApi.ts` / `authValidation.ts` (+15 unit tests) and wired into `App.tsx` as public routes. No JS token storage; HttpOnly cookie only (PD-01).
* **C-8**: auth-guard `/me` self-call converted to an in-process call in `utils/auth.py`; no behavior change; the fe_router page-data loopback remains deferred.
* **Security (OWASP A01)**: 13 group-mutation routes in `be_group.py` gated on `require_superuser` (DB-checked), covered by `TestGroupMutationSuperuserGate`.
* **Strangler intact**: Jinja auth flow and templates untouched; SPA and server-rendered auth pages coexist.
* Reviewed by member Delta — **Approve**, 0 critical/high/medium, 1 low (this missing change record — now backfilled).
