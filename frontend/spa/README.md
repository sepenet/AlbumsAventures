# AlbumsAventures SPA (React 18 + Vite + TypeScript)

Frontend Single-Page Application for AlbumsAventures, introduced in **Phase 3**
of the modernization as an incremental *strangler* migration of the Jinja2
pages. This increment delivers the **app-shell + same-origin serving (3.1)** and
the **album grid, the first migrated page (3.2)**.

## Architecture

- **React 18 + Vite + TypeScript**, built to static assets (`dist/`).
- **Served same-origin by FastAPI** under the `/app` URL prefix — there is
  **no separate Node runtime in production** (Node is build-time only) and
  **no CORS** (same origin).
- **Auth**: consumes the existing **HttpOnly session cookie** (`GET
  /be_auth/me`). **No token is stored in `localStorage`/`sessionStorage`.**
  Mutations echo the CSRF double-submit token: the JS-readable `csrf_token`
  cookie is sent back in the `X-CSRF-Token` header.
- **Tailwind via PostCSS** (local, hashed CSS bundle) reusing the design tokens
  from `docs/GUIDELINES_UI.md` — replaces the runtime Tailwind CDN for SPA
  pages.
- **React Query** (`@tanstack/react-query`) for server-state, **React Router**
  for client routing (`basename="/app"`).

## Commands

Run from `frontend/spa/`:

```bash
npm install        # install build-time dependencies
npm run build      # typecheck (tsc --noEmit) + Vite build -> dist/
npm run lint       # ESLint (0 warnings tolerated)
npm run test       # Vitest unit smoke tests
npm run dev        # Vite dev server (optional; production serves dist/)
```

## Same-origin serving contract

`npm run build` (with `base: "/app/"`) emits:

```
dist/
  index.html                 # references /app/assets/<name>-<hash>.js|css
  assets/<name>-<hash>.js     # hashed, immutable
  assets/<name>-<hash>.css
  .vite/manifest.json         # build.manifest = true
```

FastAPI (`frontend/spa_serving.py`, wired in `AlbumsAventures-BE.py` and
`AlbumsAventures_BE_test.py`) then:

1. Mounts `dist/assets` at **`/app/assets`** (hashed static files).
2. Registers a **SPA fallback** on `/app` and `/app/{full_path:path}` returning
   `dist/index.html` (enables deep-link refresh).

Because serving is scoped to `/app` and registered **after** all `be_*` /
`fe_router` includes and the `/static`, `/images`, `/thumbnails` mounts, the
fallback **never shadows** `/be_*`, `/be_resizer/tus/`, or the media mounts.
FastAPI serves Vite's generated `index.html` verbatim, so **no hashed filename
is hardcoded in Python** — the asset-manifest contract is upheld by the build.

## Strangler status

The React grid lives at **`/app`**; the existing Jinja2 pages (`/`,
`/album/...`, `/profile`, admin, shared) keep working unchanged. Subsequent
increments (3.3–3.9) migrate the remaining pages and then retire the CDN
allowances / `fe_router` loopback.
