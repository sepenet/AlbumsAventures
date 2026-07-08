<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 React SPA Migration — Increment 1 (sub-phases 3.1 + 3.2)

**Related Plan**: albumsaventures-phase3-spa.md
**Implementation Date**: 2026-07-07
**Role**: `developer` (member Gamma), squad autopilot

## Summary

Delivered the first increment of the Phase 3 strangler migration: the **React 18
+ Vite + TypeScript app-shell served same-origin by FastAPI (3.1)** and the
**album grid — the first migrated page (3.2)**. The existing Jinja2 pages are
untouched and keep serving on `/`; the React surface is gated behind the `/app`
URL prefix. `npm run build` succeeds, the full non-e2e pytest suite (50 tests)
stays green, and the SPA is confirmed to serve same-origin without shadowing any
`be_*` API route or `/be_resizer/tus/`.

## Scaffold structure

```
frontend/spa/
  package.json              # React 18, react-router-dom 6, @tanstack/react-query 5;
                            # dev: Vite 5, TS 5, Tailwind 3 + PostCSS + autoprefixer,
                            # ESLint 8 + @typescript-eslint 8 + react-hooks/react-refresh,
                            # Prettier 3, Vitest 2
  vite.config.ts            # base "/app/", outDir dist, manifest true, vitest (node env)
  tsconfig.json             # strict, bundler resolution, react-jsx, noEmit
  tailwind.config.ts        # darkMode "class", content src/**; tokens from GUIDELINES_UI.md
  postcss.config.js         # tailwindcss + autoprefixer (replaces Tailwind CDN for SPA)
  .eslintrc.cjs             # eslint:recommended + ts + react-hooks + prettier; no-explicit-any
  .prettierrc.json
  .gitignore                # node_modules/, dist/
  index.html                # Vite entry (#root, module script)
  README.md                 # build/serve contract + strangler status
  src/
    main.tsx                # QueryClientProvider + BrowserRouter basename="/app"
    App.tsx                 # Routes: "/" -> RequireAuth>Layout>AlbumGridPage; "*" -> "/"
    index.css               # @tailwind base/components/utilities
    vite-env.d.ts
    types/api.ts            # SessionUser, Album, Category (mirror be_* schemas)
    lib/
      apiClient.ts          # typed same-origin client; CSRF header on mutations; 401->UnauthorizedError
      apiClient.test.ts     # Vitest smoke test for parseCsrfToken (4 cases)
      queryClient.ts        # React Query client; no-retry on 401
    auth/
      useSession.ts         # useQuery GET /be_auth/me (cookie session)
      RequireAuth.tsx       # guard; 401 -> window.location /login
    components/Layout.tsx   # header, dark-mode toggle (shared "darkMode" key), logout
    pages/AlbumGridPage.tsx # album grid over be_album direct; search + category filter
```

Build output (git-ignored) produced by `npm run build`:

```
frontend/spa/dist/
  index.html                       # references /app/assets/index-<hash>.js|css
  assets/index-<hash>.js           # 210 kB (gzip 67.5 kB)
  assets/index-<hash>.css          # 13.6 kB (gzip 3.3 kB)
  .vite/manifest.json
```

## Same-origin serving (exact routes + exclusions)

New module `frontend/spa_serving.py` exposes `configure_spa(app)`, wired into
**both** `AlbumsAventures-BE.py` (prod) and `AlbumsAventures_BE_test.py` (test)
**after** every router include and the `/static`, `/images`, `/thumbnails`
mounts. It registers:

1. **Static mount** `/app/assets` → `frontend/spa/dist/assets` (hashed JS/CSS),
   registered first so asset requests are served as files.
2. **SPA fallback** — two `add_api_route` bindings (`response_model=None`):
   - `GET /app` → `dist/index.html`
   - `GET /app/{full_path:path}` → `dist/index.html` (enables deep-link refresh)
   HTML shell served with `Cache-Control: no-store`; hashed assets are immutable.

Because serving is scoped to the `/app` prefix and registered last, the fallback
**cannot shadow** `/be_*`, `/be_resizer/tus/`, `/images`, `/thumbnails`, or
`/static`. Verified live with a TestClient:

| Request | Result |
|---------|--------|
| `GET /app` | 200, `text/html`, `Cache-Control: no-store`, references `/app/assets/` |
| `GET /app/albums/42` (deep link) | 200, `text/html` (SPA fallback) |
| `GET /app/assets/index-<hash>.js` | 200, `text/javascript` (static, not rewritten) |
| `GET /be_category/get_all_categories/` | 401, **`application/json`** (not shadowed) |
| `GET /be_auth/me` | 401, `application/json` |
| `GET /be_album/get_all_albums/` | 401, `application/json` |

**Asset-manifest contract:** Vite (`base: "/app/"`) rewrites `dist/index.html`
on every build to reference the current content-hashed assets; FastAPI serves
that file verbatim, so no hashed filename is hardcoded in Python. `build.manifest
= true` also emits `dist/.vite/manifest.json` for future programmatic use.

## Auth / CSRF approach

- **Cookie-only session**: `useSession` calls `GET /be_auth/me`, which reads the
  existing HttpOnly cookie server-side. **No token is stored in
  localStorage/sessionStorage.** `RequireAuth` redirects to `/login` on 401.
- **CSRF scaffolding**: `apiClient` reads the JS-readable `csrf_token` cookie
  (`utils/csrf.py`, `httponly=false`) and echoes it in the `X-CSRF-Token` header
  on every mutating request (POST/PUT/PATCH/DELETE). The grid (3.2) is read-only;
  the logout POST already exercises the mutation path. Full mutation coverage
  lands with profile/admin in 3.5–3.6.
- **No CORS**: all requests are same-origin (`credentials: "same-origin"`).

## Album-grid implementation (3.2)

`AlbumGridPage` fetches the session user (`/be_auth/me`) then albums via
`GET /be_album/get_albums_by_user/{id}` **directly** — bypassing the `fe_router`
httpx loopback hop the Jinja2 page uses. It handles:

- **Loading / error / empty states** (spinner text, retry button, "Aucun album
  trouvé"), with the endpoint's 404 (no accessible albums) mapped to an empty
  grid.
- **Search** (title/date/participants/location/tags) and **category filter**
  chips fed by `GET /be_category/get_all_categories/`, via React Query cache.
- **Responsive grid** `grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4` (1 col
  mobile, 4 cols tablet/PC) with cover image, title, French month/year date, and
  participants — visual parity with the Jinja2 grid per `docs/GUIDELINES_UI.md`.
- Album cards link to the still-Jinja `/album/{id}` detail (not migrated until
  3.3), so navigation keeps working during the strangler transition.

## Changes

### Added

* frontend/spa/package.json - SPA manifest + scripts (build/lint/test)
* frontend/spa/vite.config.ts - Vite build (base /app/, manifest) + Vitest config
* frontend/spa/tsconfig.json - strict TypeScript config
* frontend/spa/tailwind.config.ts - Tailwind (class dark mode, token reuse)
* frontend/spa/postcss.config.js - Tailwind + autoprefixer pipeline
* frontend/spa/.eslintrc.cjs - ESLint config (ts + react-hooks + prettier)
* frontend/spa/.prettierrc.json - Prettier config
* frontend/spa/.gitignore - ignore node_modules/ + dist/
* frontend/spa/index.html - Vite entry HTML
* frontend/spa/README.md - build/serve contract + strangler status
* frontend/spa/src/main.tsx - React entry (QueryClient + Router basename /app)
* frontend/spa/src/App.tsx - route table (grid + fallback)
* frontend/spa/src/index.css - Tailwind directives
* frontend/spa/src/vite-env.d.ts - Vite client types
* frontend/spa/src/types/api.ts - SessionUser/Album/Category types
* frontend/spa/src/lib/apiClient.ts - typed same-origin client + CSRF + 401 handling
* frontend/spa/src/lib/apiClient.test.ts - Vitest smoke test (parseCsrfToken)
* frontend/spa/src/lib/queryClient.ts - React Query client (no retry on 401)
* frontend/spa/src/auth/useSession.ts - session hook (GET /be_auth/me)
* frontend/spa/src/auth/RequireAuth.tsx - cookie-auth guard (401 -> /login)
* frontend/spa/src/components/Layout.tsx - shell header/dark-mode/logout
* frontend/spa/src/pages/AlbumGridPage.tsx - album grid (be_album direct)
* frontend/spa_serving.py - FastAPI same-origin SPA serving (mount + fallback)
* tests/e2e/test_spa_album_grid_ui.py - e2e coverage for the /app grid (5 tests)

### Modified

* AlbumsAventures-BE.py - import + `configure_spa(app)` after media mounts
* AlbumsAventures_BE_test.py - import + `configure_spa(app)` (prod/test parity)
* .gitignore - ignore frontend/spa/node_modules/ and frontend/spa/dist/

### Removed

* (none)

## Council conditions carried forward — how each is satisfied

| Condition | Satisfied by |
|-----------|--------------|
| **Same-origin / no CORS** | SPA served by FastAPI under `/app`; client uses `credentials: "same-origin"`; no CORS relaxation added. Verified `be_*` routes return JSON, not the SPA shell. |
| **No token in localStorage** | Session comes only from the HttpOnly cookie via `GET /be_auth/me`; `apiClient`/`useSession` persist nothing in JS storage. CSRF token is read from a cookie, not stored. |
| **Node build-time only** | Vite outputs static files to `dist/`; FastAPI serves them. No Node process in production; `node_modules/`+`dist/` are git-ignored. |
| **CSP handling** | Built `index.html` references only `/app/assets/*` (hashed, `'self'`) with no inline script and no CDN. The Phase 1 CSP already allows `'self'` for script/style and `connect-src 'self'`, so **no CSP change was required** for this increment. **Did NOT** add `unsafe-eval` or broad `*` sources. CDN allowances + `'unsafe-inline'` are intentionally retained (Jinja pages still use them) — their retirement is Phase 3.9. |
| **Incremental (no big-bang)** | React grid gated at `/app`; Jinja `/` and all other pages unchanged and still served by `fe_router`. |
| **Retire fe_router loopback (migrated pages)** | The grid calls `be_album` directly (no httpx loopback for `/app`). Full `fe_router` retirement is Phase 3.8. |

## Validation results

| Gate | Command | Result |
|------|---------|--------|
| SPA build | `npm run build` (tsc --noEmit + vite build) | **PASS** — hashed assets + `.vite/manifest.json` emitted |
| SPA lint | `npm run lint` (eslint, 0 warnings) | **PASS** |
| SPA unit | `npm run test` (vitest) | **PASS** — 4/4 |
| Python unit | `.\Scripts\python.exe -m pytest -m "not e2e"` | **PASS** — 50 passed, 97 e2e deselected |
| Required subset | `pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py` | **PASS** — 50 passed |
| Format/lint (py) | `black --check` + `ruff check` on 3 changed `.py` | **PASS** |
| Prod app import | importlib load of `AlbumsAventures-BE.py` | **PASS** — `configure_spa` wired |
| Serving contract | TestClient on `/app`, `/app/{path}`, `/app/assets/*`, `/be_*` | **PASS** — SPA served, API not shadowed |
| e2e (new spec) | `pytest tests/e2e/test_spa_album_grid_ui.py --collect-only` | **COLLECTS** (5 tests) — execution needs a live server + `E2E_USER_PASSWORD` (not run here) |

## Additional or Deviating Changes

* **SPA route is `/app`, not `/`.** The plan's 3.2.3 offered "`/` or a
  feature-flagged path". Serving the SPA under the dedicated `/app` prefix is the
  chosen feature-flag: it is the safest strangler boundary (structurally cannot
  shadow the Jinja `/` route or any `be_*`/media path) and keeps every existing
  page working untouched. React Router uses `basename="/app"`.
* **`configure_spa` added to the test app too.** Mirrors the prod app so the CSP
  and serving contract are verifiable under the test client (consistent with the
  existing "identical security between prod and test app" convention). Guarded by
  directory existence, so it is a no-op crash-free path when `dist/` is absent.
* **No CSP modification.** The instruction allowed CSP edits "ONLY as needed";
  the same-origin hashed assets load under the existing `'self'` policy, so no
  edit was needed. Explicitly avoided `unsafe-eval`/broad sources.
* **Existing 7 e2e specs left unchanged.** Because the SPA is gated at `/app`,
  the Jinja-surface specs (which test `/`) remain valid and green; a new
  dedicated spec covers the migrated `/app` grid instead of repurposing them.
* **e2e specs not executed here.** All e2e tests require a running server and
  real credentials (`E2E_USER_PASSWORD`), which are not available in this local
  run; the new spec is validated by collection + ruff/black.
* **npm audit** reports 5 transitive dev-dependency advisories (build-time only,
  not shipped). Not addressed this increment; flagged as follow-on.

## Release Summary

**Increment 1 (3.1 + 3.2) complete.** 24 files added, 3 modified, 0 removed.
The React SPA app-shell and album-grid page are built and served same-origin by
FastAPI under `/app`, consuming the existing cookie session with CSRF scaffolding
and calling `be_album` directly. No production Node runtime, no CORS, no
localStorage token, and no CSP loosening were introduced. The Jinja2 surface is
fully preserved. Build, lint, Vitest, and the 50-test Python suite are green.
Next increments (3.3 album detail → 3.9 CSP tightening/PWA handoff) remain gated
on this landing.
