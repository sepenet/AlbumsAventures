<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 React SPA Migration — Increment 2 (sub-phase 3.3)

**Related Plan**: albumsaventures-phase3-spa.md (sub-phase 3.3)
**Implementation Date**: 2026-07-07
**Role**: `developer` (member Gamma), squad autopilot
**Builds on**: Increment 1 (3.1 scaffold + 3.2 album grid) — see
`albumsaventures-phase3-spa-increment1-changes.md`.

## Summary

Delivered **sub-phase 3.3 — the album detail page in React**, the second
strangler increment. A new deep-linkable SPA route `/app/albums/:albumId`
renders the album header (title, date, participants, location, tags,
description, photo count) and a responsive image/video gallery with a
dependency-free fullscreen lightbox (PhotoSwipe-equivalent; videos play with
native controls). Data comes from `be_album` directly (metadata) and the
existing browser-facing `/album/{id}/images` JSON endpoint (media) — the
grid→detail navigation stays inside the React Router SPA. Superuser action
affordances (edit, share, regenerate thumbnails, delete, upload) are gated on
the cookie-session `is_superuser` (Phase 1 #485). The Jinja2 `/album/{id}` page
is untouched and keeps working. Build, lint (0 warnings), Vitest (12/12), and
the 50-test backend subset are all green; the prod app imports cleanly.

## Reused patterns (from increment 1 — NOT rebuilt)

* **Typed same-origin API client** (`src/lib/apiClient.ts`) — `api.get` for all
  reads; the CSRF-cookie→`X-CSRF-Token` mutation path is reused unchanged (the
  regenerate-thumbnails action goes through it). No new client written.
* **React Query** for server state — album metadata via `useQuery`; media via
  `useInfiniteQuery` (new usage of the already-installed lib).
* **Cookie-only auth** — `useSession` (`GET /be_auth/me`) reused for
  `is_superuser`; `RequireAuth` guard wraps the new route. No localStorage token.
* **Same-origin serving under `/app`** — the increment-1 FastAPI SPA fallback
  (`frontend/spa_serving.py`, `GET /app/{full_path:path}` → `index.html`)
  already serves `/app/albums/:id` deep links; **no backend change was needed**.
* **Tailwind design tokens** (`docs/GUIDELINES_UI.md`) — same sky/gray palette,
  card/shadow/rounded conventions, dark-mode classes, responsive grid.
* **Shared display helpers** — extracted the grid's date/participant formatters
  into `src/lib/format.ts` (deduped) and reused them on the detail page.

## Album-detail implementation (3.3)

`AlbumDetailPage` (`src/pages/AlbumDetailPage.tsx`):

* **Metadata**: `GET /be_album/get_album_by_id/{id}` **directly** (no fe_router
  Jinja page-render httpx loopback — C-8). 404 → dedicated "introuvable" state
  with a back link; other errors → retry.
* **Media**: `useInfiniteQuery` over `GET /album/{id}/images?offset=&limit=30`,
  flattening pages; `getNextMediaOffset` (pure, unit-tested) drives
  `getNextPageParam`. A "Charger plus de photos" button fetches the next page
  (deterministic vs. an IntersectionObserver, and testable).
* **Header** parity with the Jinja detail UI: back link, title, date
  (French month/year), participants (`|`→`, `), location, photo count, tags as
  chips, description.
* **Gallery**: responsive `grid-cols-2 md:grid-cols-3 lg:grid-cols-4`; each
  thumbnail is a button opening the lightbox; **videos show a play overlay**.
* **Lightbox** (`src/components/Lightbox.tsx`): fullscreen modal, prev/next
  (buttons + ArrowLeft/ArrowRight), Escape/backdrop close, body-scroll lock,
  `role="dialog"`/`aria-modal`. Images at `full_url`; **videos play inline**
  with native `<video controls autoPlay>`. No CDN `<script>`/`<link>` (unlike
  the Jinja page's unpkg PhotoSwipe), so the same-origin CSP is unaffected.
* **States**: header + gallery loading skeletons; media error/empty states.

## Deep-link handling

* Route `path="/albums/:albumId"` added in `src/App.tsx` (React Router,
  `basename="/app"`).
* A direct load / refresh of `/app/albums/42` is served by the increment-1
  FastAPI catch-all (`index.html`), then resolved client-side by React Router —
  verified by the new e2e `test_detail_deeplink_refresh_serves_shell`.
* Grid cards now use React Router `<Link to="/albums/:id">` (were
  `<a href="/album/:id">` to the Jinja page), so grid→detail is in-SPA.

## Superuser affordances (gated on `is_superuser`)

| Action | Wiring | Owning sub-phase |
|--------|--------|------------------|
| **Upload** (all users) | Link → existing Jinja `/album/{id}/upload` | 3.4 (native upload) |
| **Edit** (superuser) | Link → existing Jinja `/album/{id}/edit` | later admin increment |
| **Share** (superuser) | Link → existing Jinja `/album/{id}` (working associate/share modal); `title` TODO | **3.7** shared-album |
| **Regenerate thumbnails** (superuser) | **Real** `GET /be_resizer/create_thumbnails/{id}` via api client + `window.confirm`; invalidates the media cache on success | — (wired now) |
| **Delete** (superuser) | **Stub** — `window.alert` TODO; no backend album-delete endpoint exists and the backend is unchanged | **3.6** album admin |

All buttons render only when the cookie session reports `is_superuser` (upload
is always shown). Any mutating affordance uses the shared client (CSRF header on
POST/PUT/PATCH/DELETE); the regenerate action is a GET (no body/CSRF) matching
the existing endpoint contract.

## Changes

### Added

* frontend/spa/src/pages/AlbumDetailPage.tsx - React album-detail page (be_album direct + /album/{id}/images infinite query, superuser affordances, states)
* frontend/spa/src/components/Lightbox.tsx - dependency-free fullscreen media viewer (images + video playback, keyboard nav)
* frontend/spa/src/lib/format.ts - shared date/participant formatters + `getNextMediaOffset` pagination helper (pure)
* frontend/spa/src/lib/format.test.ts - Vitest smoke tests (8) for the shared helpers
* tests/e2e/test_spa_album_detail_ui.py - e2e coverage for the /app detail page (4 tests: nav, deep-link refresh, photo count, Jinja parity)

### Modified

* frontend/spa/src/App.tsx - added deep-linkable route `/albums/:albumId`
* frontend/spa/src/pages/AlbumGridPage.tsx - cards navigate in-SPA via `<Link to="/albums/:id">`; formatters imported from `format.ts` (deduped)
* frontend/spa/src/types/api.ts - added `AlbumDetail`, `MediaItem`, `AlbumMediaPage` types (mirror `schemas.Album_Category` + `/album/{id}/images`)

### Removed

* (none)

## Council conditions carried forward — how each is satisfied

| Condition | Satisfied by |
|-----------|--------------|
| **Same-origin / no CORS** | Detail data via `be_album` + `/album/{id}/images` same-origin (`credentials: "same-origin"`); no CORS added. |
| **No token in localStorage** | `is_superuser` read from the cookie session (`/be_auth/me`); nothing persisted in JS storage. |
| **Node build-time only** | Only static `dist/` output changed; no runtime Node. Lightbox is hand-written (no new runtime dep). |
| **CSP unchanged / not loosened** | The React lightbox replaces the Jinja page's unpkg PhotoSwipe CDN `<script>`/`<link>`; the SPA bundle loads under the existing `'self'` policy. **No `unsafe-eval`, no broad `*`, no CORS added.** CDN retirement remains Phase 3.9. |
| **Incremental (no big-bang)** | Detail gated at `/app/albums/:id`; Jinja `/album/{id}` unchanged (verified by e2e `test_jinja_detail_still_served`). |
| **Retire fe_router loopback (migrated pages)** | Album **metadata** now fetched from `be_album` directly (no Jinja page-render loopback). Media list still transits the existing `/album/{id}/images` JSON endpoint (see deviation). |

## Validation results

| Gate | Command | Result |
|------|---------|--------|
| SPA build | `npm run build` (tsc --noEmit + vite build) | **PASS** — hashed assets + `.vite/manifest.json`; JS 228.84 kB (gzip 72.07 kB) |
| SPA lint | `npm run lint` (eslint, `--max-warnings 0`) | **PASS** — 0 warnings |
| SPA unit | `npm run test` (vitest) | **PASS** — 12/12 (4 apiClient + 8 format) |
| Backend subset | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **PASS** — 50 passed |
| Prod app import | importlib load of `AlbumsAventures-BE.py` | **PASS** — 108 routes, SPA wired |
| e2e (new spec) | `pytest tests/e2e/test_spa_album_detail_ui.py --collect-only` | **COLLECTS** (4 tests) — execution needs a live server + `E2E_USER_PASSWORD` (not run here) |

## Additional or Deviating Changes

* **Media list still uses fe_router's `/album/{id}/images` JSON endpoint.** The
  scope asked to fetch images "from the existing `be_album` (and image/thumbnail
  endpoints)". No `be_album` endpoint lists album media — the listing is
  filesystem-derived and lives only in fe_router's browser-facing JSON API
  (which itself does an internal httpx call to `be_album` for metadata). Because
  the validation requires the **backend unchanged**, no new media-list endpoint
  was added. This is distinct from the C-8 "Jinja page-render loopback" the plan
  retires: the detail **page** no longer renders through fe_router. Full
  fe_router retirement (including this JSON endpoint) remains **Phase 3.8**.
* **Date shown formatted (French month/year), not raw ISO.** The Jinja detail
  shows the raw `album.date`; the SPA reuses the grid's `formatMonthYear` for
  cross-page consistency. Falls back to the raw value on an unparseable date.
* **Grid cards re-pointed to the SPA detail.** Increment 1 linked cards to the
  Jinja `/album/{id}`; now that the SPA detail exists they link in-SPA to
  `/albums/{id}`. The Jinja detail route is preserved and still reachable
  directly.
* **"Delete" affordance is a stub** (alert + TODO → 3.6): no backend
  album-delete endpoint exists and the backend is unchanged this increment.
* **"Share" affordance links to the existing Jinja detail** where the working
  associate/share modal lives (TODO → 3.7 native flow), rather than a broken
  native stub.
* **Lightbox is hand-written, not PhotoSwipe.** The scope explicitly allowed a
  "photoswipe-equivalent"; a custom modal avoids the unpkg CDN dependency
  (keeping the CSP posture) and the imperative PhotoSwipe-in-React lifecycle.
* **e2e specs not executed here.** All e2e tests need a running server + real
  credentials (`E2E_USER_PASSWORD`), unavailable in this local run; the new spec
  is validated by collection. Existing 7 Jinja specs left unchanged (still green
  in principle — the Jinja surface is untouched).

## Release Summary

**Increment 2 (sub-phase 3.3) complete.** 5 files added, 3 modified, 0 removed.
The React album-detail page is built and served same-origin under
`/app/albums/:albumId`, deep-linkable via the increment-1 fallback, consuming
`be_album` directly for metadata and the existing media JSON endpoint for the
gallery, with a hand-written lightbox (images + video), superuser affordances
gated on the cookie session, and loading/error/empty states. No production Node
runtime, no CORS, no localStorage token, and no CSP loosening were introduced.
The Jinja2 detail page is preserved. Build, lint, Vitest (12), the 50-test
backend subset, and the app import are green. Deferred to later increments:
native share/associate (3.7), album delete + admin (3.6), native upload (3.4),
and full fe_router `/album/{id}/images` retirement (3.8).
