<!-- markdownlint-disable-file -->
# Review — Phase 3 Increment 7 (sub-phase 3.8: auth pages + C-8 loopback retire + FU-group hardening)

- **Role**: tester (member Delta) — Review stage
- **Date**: 2026-07-07
- **Related plan**: `/memories/session/phase3.8-auth-plan.md` (session memory)
- **Change record**: MISSING — developer output was truncated and left no `.copilot-tracking/changes/` record. Reconstructed from the working tree. Recommend backfill (see Follow-ups).
- **Verdict**: ✅ **Approve**

## Change surface (reconstructed)

| Area | Files |
|------|-------|
| Auth pages (SPA) | `frontend/spa/src/pages/{LoginPage,SignupPage,ForgotPasswordPage,ResetPasswordPage}.tsx`, `components/AuthCard.tsx`, `lib/authApi.ts`, `lib/authValidation.ts` (+`.test.ts`), `App.tsx` (routes) |
| C-8 loopback | `utils/auth.py` (in-process conversion) |
| FU-group (OWASP A01) | `backend/routers/be_group.py` (13 mutating routes + `require_superuser` import), `tests/test_auth.py` (`TestGroupMutationSuperuserGate`) |
| fe_router | **unchanged** (data-fetch loopback deferred per plan) |

## Per-item results

### 1. Auth pages — PASS
- `authApi.ts`: login uses form-encoded `POST /be_auth/login` with `credentials: "same-origin"`, reads `detail` on `!ok` via a dedicated `fetch` (not shared `api.post`, so 401 stays inline as `AuthError`). Stores **NO** token in JS — cookie set HttpOnly server-side (PD-01). signup → `api.post /be_auth/create/` with `is_active:false`/`is_superuser:false`; forgot/reset map to the matching endpoints.
- No `localStorage`/`sessionStorage` token anywhere. Only non-sensitive `darkMode` pref uses localStorage.
- LoginPage: on success invalidates `["session"]` + `navigate("/", { replace: true })`; already-authed guard `Navigate to="/"`; 401/400 shown inline via `AuthError`; reads `?registered=true`.
- SignupPage: on success `navigate("/login?registered=true")`.
- ResetPasswordPage: token read from URL via `useSearchParams().get("token")`; malformed-link guard when absent.
- CSRF: mutations carry `X-CSRF-Token` double-submit header via shared `apiClient` (`credentials: "same-origin"`).
- Public routes `/login /signup /forgot-password /reset-password` are OUTSIDE `RequireAuth`/`Layout`, placed before the catch-all.

### 2. C-8 loopback conversion — PASS (no behavior change)
- `utils/auth.py::verify_authentication` now `await get_current_user(request)` IN-PROCESS, then loads the user via `crud.get_user_info_by_id` on a dedicated `SessionLocal()` (closed in `finally`), returning a `UserAdmin`-shaped dict. `HTTPException` → `None` preserves the historical "auth failed → None" contract that the old non-200 `/me` response provided.
- No live httpx / localhost / backend_api round-trip remains. The **only** `httpx`/`localhost` mention is in the docstring (line 18) explaining what was removed — not live code.
- Behavior unchanged: 58 backend tests pass, including full `test_auth.py` (auth guard exercised by the `client` fixture which builds the whole app).
- **Converted**: the auth-guard `/me` self-call used by all authed Jinja pages (require_auth / require_superuser). **Deferred**: fe_router data-fetch loopback — `fe_router.py` is unchanged (no diff), matching the plan's documented deferral; Jinja rendering still holds (strangler intact).

### 3. FU-group hardening (OWASP A01) — PASS (403 enforced server-side)
- `be_group.py` adds `dependencies=[Depends(require_superuser)]` to all 13 state-mutating routes (create/update/delete group, user-group, album-group bulk variants, user-album). Router keeps `Depends(get_current_user)`; GET/read routes gain no superuser gate (still auth-only).
- The gate is `be_auth.require_superuser` (the FastAPI dependency that raises `403`), which re-checks `is_superuser` **in the DB** (not the token claim) — a demotion takes effect immediately.
- `tests/test_auth.py::TestGroupMutationSuperuserGate`: non-superuser → 403, superuser → 200 (asserts created group name), unauthenticated → 401 on the representative `create_group` mutation.
- Client-side button masking is no longer the only control; server rejects non-admin mutations.

### 4. Strangler — PASS
- Jinja auth flow untouched: `fe_router.py` unchanged, no Jinja templates modified. Both SPA and server-rendered auth pages coexist.

### 5. Security posture — PASS
- No CSP/CORS files touched (scope limited to `be_group.py` + `utils/auth.py` on the backend). No `unsafe-eval`/`unsafe-inline` introduced.
- Node used at build-time only. Code-split preserved: build emits a separate `UploadPage-*.js` (295 kB) chunk distinct from `index-*.js`.

## Validation evidence

| Gate | Command | Result |
|------|---------|--------|
| Backend tests | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **58 passed** |
| Ruff | `ruff check utils/auth.py backend/routers/be_group.py tests/test_auth.py` | All checks passed |
| Black | `black --check` (same files) | 3 files unchanged |
| App import | full app imported by `client` fixture across 58 passing tests | clean |
| SPA build | `npm run build` | built; separate `UploadPage` chunk |
| SPA lint | `npm run lint` (`--max-warnings 0`) | 0 warnings |
| SPA test | `npm run test` | **74 passed** (7 files) |

## Findings

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 1 |

- **Low** — No change record was written for this increment (developer output truncated). Traceability relies on session memory + working-tree reconstruction.

## Follow-ups

- Backfill the change record at `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment7-changes.md` documenting: SPA auth pages, C-8 conversion (converted auth-guard self-call; deferred fe_router data-fetch loopback), and FU-group 13-route `require_superuser` hardening.
- (Deferred from scope) fe_router data-fetch loopback conversion remains open — tracked as C-8 remaining work.

## Reviewer note

This is an AI-assisted review and should be validated by a qualified human reviewer before merge.
