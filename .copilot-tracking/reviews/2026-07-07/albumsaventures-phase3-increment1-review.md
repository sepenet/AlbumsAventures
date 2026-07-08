<!-- markdownlint-disable-file -->
# Review: AlbumsAventures Phase 3 — SPA Increment 1 (sub-phases 3.1 + 3.2)

**Reviewer role**: `tester` (member Delta)
**Review date**: 2026-07-07
**Related plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (sub-phases 3.1, 3.2)
**Change record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment1-changes.md`
**Scope reviewed**: `frontend/spa/`, [frontend/spa_serving.py](frontend/spa_serving.py), [tests/e2e/test_spa_album_grid_ui.py](tests/e2e/test_spa_album_grid_ui.py), edits to [AlbumsAventures-BE.py](AlbumsAventures-BE.py), [AlbumsAventures_BE_test.py](AlbumsAventures_BE_test.py), [utils/security.py](utils/security.py), `.gitignore`

## Verdict: ✅ Approve (with minor follow-ups)

No Critical or High findings. All council conditions carried into this increment are satisfied. The highest-risk item (route shadowing) was verified empirically and is safe.

| Severity | Count |
|----------|-------|
| Critical | 0     |
| High     | 0     |
| Medium   | 0     |
| Low      | 3     |

## Per-item results

### 1. Same-origin serving is correct and SAFE — ✅ PASS (highest-risk item, empirically verified)

The SPA is served under a dedicated `/app` prefix, registered **after** every `be_*`/`fe_router` include (routers L109–118) and after the `/static`, `/thumbnails`, `/images` media mounts (L121–129) — [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L132). The fallback is bound to `/app` and `/app/{full_path:path}` only ([frontend/spa_serving.py](frontend/spa_serving.py#L109-L116)), with `/app/assets` mounted first as `StaticFiles` so hashed assets serve as files.

Empirical TestClient run against the loaded prod app:

| Request | Result |
|---------|--------|
| `GET /app` | 200 `text/html` (SPA shell) |
| `GET /app/albums/42` | 200 `text/html` (deep-link fallback works) |
| `GET /be_auth/me` | 401 **`application/json`** (not shadowed) |
| `GET /be_album/get_all_albums/` | 401 **`application/json`** (not shadowed) |
| `GET /be_category/get_all_categories/` | 401 **`application/json`** (not shadowed) |
| `GET /be_resizer/upload_config` | 401 **`application/json`** (not shadowed) |

Because the catch-all is prefix-scoped to `/app` and last in registration order, it structurally cannot intercept `/be_*`, `/be_resizer/tus/`, `/images`, `/thumbnails`, or `/static`. Jinja2 fallback (`fe_router` on `/`) remains intact — the strangler boundary holds. The prod app imports cleanly with `configure_spa(app)` wired, and the test app mirrors it ([AlbumsAventures_BE_test.py](AlbumsAventures_BE_test.py#L61)) guarded by `dist/` existence.

### 2. No tokens in localStorage/sessionStorage — ✅ PASS

Grep of `frontend/spa/src/**` for `localStorage|sessionStorage` returns only the dark-mode key in [Layout.tsx](frontend/spa/src/components/Layout.tsx#L11) (`DARK_MODE_KEY = "darkMode"`, shared with the Jinja pages) — no token storage. Session comes solely from the HttpOnly cookie via `GET /be_auth/me` ([useSession.ts](frontend/spa/src/auth/useSession.ts#L9-L15)); `RequireAuth` redirects to `/login` on 401 ([RequireAuth.tsx](frontend/spa/src/auth/RequireAuth.tsx#L31-L34)). The CSRF token is read from the JS-readable `csrf_token` cookie and echoed as `X-CSRF-Token` on POST/PUT/PATCH/DELETE only ([apiClient.ts](frontend/spa/src/lib/apiClient.ts#L58-L79)); it is never persisted. `credentials: "same-origin"` is used throughout.

### 3. No CORS added — ✅ PASS

The only `CORSMiddleware` is the Phase 1 config-driven one in [utils/security.py](utils/security.py#L193) (`configure_cors`), bound to a single fixed origin (`http://localhost:5003`) with `allow_credentials=True`; no wildcard origin. No CORS middleware was added by this increment, and the SPA client is same-origin (`credentials: "same-origin"`), so no cross-origin surface is introduced.

### 4. CSP — ✅ PASS (no regression)

[utils/security.py](utils/security.py) CSP is unchanged this increment. `script-src`/`style-src` still allow `'self'`, `'unsafe-inline'`, and the three CDNs with the documented "EXCEPTION TODO (à lever en Phase 3)" ([utils/security.py](utils/security.py#L89-L93)). No `'unsafe-eval'` and no broad `*` source were introduced. The built `index.html` references only `/app/assets/*` (same-origin, hashed, `'self'`), which loads under the existing policy; `connect-src 'self'`, `worker-src 'self' blob:`, `manifest-src 'self'` remain. CDN + `'unsafe-inline'` retention is intentional (Jinja pages still use them) — acceptable this increment; retirement is Phase 3.9.

### 5. Album grid — ✅ PASS

[AlbumGridPage.tsx](frontend/spa/src/pages/AlbumGridPage.tsx#L37-L60) fetches the session user then calls `GET /be_album/get_albums_by_user/{id}` **directly** (no `fe_router` httpx loopback). Auth guard via `useSession`/`RequireAuth`. States covered: loading ("Chargement des albums…"), error with retry button, empty ("Aucun album trouvé"), and 404→empty grid ([AlbumGridPage.tsx](frontend/spa/src/pages/AlbumGridPage.tsx#L40-L46)). Responsive grid is `grid-cols-1 md:grid-cols-2 lg:grid-cols-4` ([AlbumGridPage.tsx](frontend/spa/src/pages/AlbumGridPage.tsx#L177)) — 1 column mobile, 4 columns desktop as required (an extra 2-column tablet breakpoint is additive and fine). Category-filter chips fed by `GET /be_category/get_all_categories/` and search across title/date/participants/location/tags. Album cards link to the still-Jinja `/album/{id}`, preserving navigation during the strangler transition.

### 6. Node build-time only — ✅ PASS

Vite outputs to `frontend/spa/dist/` (git-ignored); FastAPI serves those files statically via the `/app/assets` mount + `FileResponse` shell. The app-import log confirms `SPA : assets montés sur /app/assets`, i.e. the built `dist/` is served in-process. No runtime Node service is introduced; `node_modules/` and `dist/` are git-ignored.

### 7. Build & tests — ✅ PASS

| Gate | Command | Result |
|------|---------|--------|
| Prod app import | importlib load of `AlbumsAventures-BE.py` | **PASS** — imports clean, 3 `/app` routes registered, no shadowing |
| Route contract | TestClient on `/app`, `/app/{path}`, `/be_*` | **PASS** — SPA served, API returns JSON 401 (see item 1) |
| Python unit (required subset) | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **PASS** — 50 passed |
| SPA lint | `npm run lint` (eslint `--max-warnings 0`) in `frontend/spa/` | **PASS** — 0 errors/warnings |
| SPA build | `npm run build` (per change record: tsc --noEmit + vite, 87 modules) | **PASS** (dist present, assets mounted) |

## Low-severity follow-ups (non-blocking)

1. **[LOW] `dist/` is git-ignored** — the built SPA is not committed, so deployment/CI must run `npm run build` in `frontend/spa/` before serving. Serving degrades gracefully (404 hint) when absent ([frontend/spa_serving.py](frontend/spa_serving.py#L59-L63)), but a CI/CD build step should be added (already anticipated in the plan's Dependencies section). Recommend before any environment that serves `/app`.
2. **[LOW] npm audit** — 5 transitive dev-dependency advisories (build-time only, not shipped), per the change record. Track as a maintenance follow-on.
3. **[LOW] CSRF mutation path minimally exercised** — only the logout POST exercises the `X-CSRF-Token` header this increment; full mutation coverage lands with profile/admin in 3.5–3.6. Acceptable for a read-only grid.

## Notes

- e2e specs (`tests/e2e/test_spa_album_grid_ui.py`, 5 tests) were not executed here: they require a live server + `E2E_USER_PASSWORD`. Spec collects and follows the cookie-only auth-guard pattern. Consistent with the change record's deviation note.
- Deviation from plan 3.2.3 (SPA at `/app` rather than `/`) is a sound, safer strangler feature-flag choice and is explicitly documented — accepted.

---

*This review was produced with AI assistance and should be validated by a human reviewer before it gates a release.*
