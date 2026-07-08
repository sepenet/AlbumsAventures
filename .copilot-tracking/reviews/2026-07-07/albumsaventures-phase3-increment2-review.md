<!-- markdownlint-disable-file -->
# Review: AlbumsAventures Phase 3 — Increment 2 (sub-phase 3.3, album detail page)

**Reviewer**: squad `tester` role (member Delta)
**Review date**: 2026-07-07
**Related plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (sub-phase 3.3)
**Change record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment2-changes.md`
**Scope reviewed**: `AlbumDetailPage.tsx`, `Lightbox.tsx`, `lib/format.ts` (+ `.test.ts`), `App.tsx`, `AlbumGridPage.tsx`, `types/api.ts`, `tests/e2e/test_spa_album_detail_ui.py`; backend endpoints consulted (unchanged): `be_album.get_album_by_id`, `be_resizer.create_thumbnails`, `fe_router.album_images_api`, `frontend/spa_serving.py`, `AlbumsAventures-BE.py`.

## Verdict

**✅ Approve-with-followups.**

All 8 verification items PASS. No Critical or High findings were introduced by this increment. Two Medium/Low follow-ups relate to **pre-existing backend conditions** (backend was intentionally unchanged this increment) and one documented deviation deferred to Phase 3.8. No defects require a fix cycle before merge.

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 1 (pre-existing) |
| Low      | 2 (1 pre-existing, 1 documented deviation) |

## Per-item results

### 1. Deep-link `/app/albums/:albumId` via existing SPA fallback, no `/be_*` shadow — PASS

* Route declared in [App.tsx](frontend/spa/src/App.tsx#L23-L32): `path="/albums/:albumId"` under React Router `basename="/app"` (increment-1 shell).
* Server-side fallback in [spa_serving.py](frontend/spa_serving.py#L74-L110): catch-all `GET /app/{full_path:path}` → `index.html` with `Cache-Control: no-store`; assets mounted at `/app/assets` **before** the catch-all.
* Non-shadowing confirmed: [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L132) calls `configure_spa(app)` **after** every `be_*`/`fe_router` include and after the `/static`, `/images`, `/thumbnails` mounts (lines 109-127). SPA is scoped to the `/app` prefix and structurally cannot intercept `/be_*` or `/be_resizer/tus/`.
* Regression-guarded by e2e `test_detail_deeplink_refresh_serves_shell` in [test_spa_album_detail_ui.py](tests/e2e/test_spa_album_detail_ui.py#L46-L56). No backend change was required.

### 2. Data via typed client + React Query `useInfiniteQuery`; consumes `be_album` directly — PASS (documented deviation)

* Metadata fetched **directly** from `be_album`: [AlbumDetailPage.tsx](frontend/spa/src/pages/AlbumDetailPage.tsx#L19-L21) `api.get('/be_album/get_album_by_id/{id}')` via `useQuery`. This retires the C-8 Jinja **page-render** loopback for the detail page.
* Media via `useInfiniteQuery` over `/album/{id}/images?offset=&limit=30`, flattened, with a pure `getNextMediaOffset` helper driving `getNextPageParam` ([AlbumDetailPage.tsx](frontend/spa/src/pages/AlbumDetailPage.tsx#L47-L53), [format.ts](frontend/spa/src/lib/format.ts#L44-L50)).
* Types are narrow and match the backend shape: [types/api.ts](frontend/spa/src/types/api.ts#L64-L84) `MediaItem`/`AlbumMediaPage` mirror the `album_images_api` payload verified in [fe_router.py](frontend/routers/fe_router.py#L966-L983) (`filename`, `thumbnail_url`, `full_url`, `is_video`, `has_thumbnail`, `width`, `height`; `items`/`total`/`has_more`).
* **Deviation (L-1, documented in change record):** the media list still transits fe_router's `album_images_api`, which itself does an internal httpx call to `be_album` for metadata ([fe_router.py](frontend/routers/fe_router.py#L1197-L1210)). This is distinct from the retired page-render loopback and is explicitly deferred to Phase 3.8. Acceptable under the "backend unchanged" constraint.

### 3. Auth/CSRF cookie-only, no localStorage; CSRF header on mutations — PASS (note)

* Cookie-only: [apiClient.ts](frontend/spa/src/lib/apiClient.ts#L84-L88) uses `credentials: "same-origin"`; no token is written to `localStorage`/`sessionStorage` in any new file. Session read from `GET /be_auth/me` ([useSession.ts](frontend/spa/src/auth/useSession.ts#L8-L16)).
* CSRF mechanism correct: [apiClient.ts](frontend/spa/src/lib/apiClient.ts#L59-L79) reads the JS-readable `csrf_token` cookie and echoes `X-CSRF-Token` for `POST/PUT/PATCH/DELETE`.
* **Note (L-2):** the regenerate-thumbnails action is wired as a **GET** ([AlbumDetailPage.tsx](frontend/spa/src/pages/AlbumDetailPage.tsx#L58-L61)), so no CSRF header is sent. This matches the existing endpoint contract (`@router.get("/create_thumbnails/{album_id}")`), and the double-submit model does not gate GETs. Correct as coded; see follow-up F-2 for the latent state-changing-GET concern.

### 4. Superuser affordances gated on `is_superuser`; stubs TODO-linked — PASS

* [AlbumDetailPage.tsx](frontend/spa/src/pages/AlbumDetailPage.tsx#L64): `isSuperuser = user?.is_superuser ?? false`; Edit/Share/Regenerate/Delete are wrapped in `isSuperuser ? (...) : null` (lines 168-235). Upload is always shown to authenticated users (lines 237-244).
* Stubs are clearly TODO-linked, not silently broken: Delete → `window.alert` referencing `SUBPHASE_ALBUM_ADMIN = "3.6"`; Share → links to the working Jinja detail with a `title` TODO to `SUBPHASE_SHARE = "3.7"`; Edit → links to the existing Jinja edit page; Regenerate → real call (see watch-for below).

### 5. Lightbox dependency-free, keyboard nav, video inline — PASS

* [Lightbox.tsx](frontend/spa/src/components/Lightbox.tsx) imports only from `react`; no CDN `<script>`/`<link>` (replaces the Jinja page's unpkg PhotoSwipe), so no CSP change is implied.
* Keyboard nav: Escape closes, ArrowLeft/ArrowRight navigate ([Lightbox.tsx](frontend/spa/src/components/Lightbox.tsx#L34-L48)); body-scroll lock restored on cleanup; `role="dialog"`, `aria-modal`, `aria-label` set.
* Video inline: `<video controls autoPlay>` at `full_url` ([Lightbox.tsx](frontend/spa/src/components/Lightbox.tsx#L118-L124)).

### 6. Strangler intact (Jinja album-detail still works) — PASS

* The Jinja `/album/{album_id}` route is untouched. Grid cards were re-pointed in-SPA via `<Link to="/albums/:id">` ([AlbumGridPage.tsx](frontend/spa/src/pages/AlbumGridPage.tsx#L160)), but the Jinja route remains reachable and is regression-guarded by e2e `test_jinja_detail_still_served` ([test_spa_album_detail_ui.py](tests/e2e/test_spa_album_detail_ui.py#L72-L86), asserts HTTP 200).

### 7. No CSP loosening, no CORS, Node build-time only — PASS

* `utils/security.py` is not in the changed set; no CSP directive was altered. App import log shows the pre-existing dev CORS (`['http://localhost:5003']`) unchanged — no new CORS was added, and the client uses same-origin fetch (`credentials: "same-origin"`).
* Only static `dist/` output plus `frontend/spa/src` changed; no production Node runtime introduced. The hand-written lightbox adds no runtime dependency.

### 8. Build / lint / tests / pytest / app import — PASS (re-run by reviewer)

| Gate | Command | Result |
|------|---------|--------|
| SPA build | `cd frontend/spa; npm run build` | **PASS** — `tsc --noEmit` + vite build; hashed assets + `.vite/manifest.json`; JS 228.84 kB (gzip 72.07 kB) |
| SPA lint | `npm run lint` (`eslint --max-warnings 0`) | **PASS** — 0 warnings |
| SPA unit | `npm run test` (vitest) | **PASS** — 12/12 (4 apiClient + 8 format) |
| Backend subset | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **PASS** — 50 passed |
| Prod app import | importlib load of `AlbumsAventures-BE.py` | **PASS** — 108 routes, SPA fallback wired |

## Watch-for items

### `GET /be_resizer/create_thumbnails/{id}` — auth ✅ / CSRF ✅(GET) / superuser ⚠️

* **Authenticated:** YES. `be_resizer.router` carries `dependencies=[Depends(get_current_user)]` ([be_resizer.py](backend/routers/be_resizer.py#L22)), so unauthenticated calls return 401.
* **CSRF:** the action is a GET (no body); the double-submit model does not require a header on GET, and the client correctly omits it. Consistent with the endpoint contract.
* **Superuser gating — Medium finding (M-1, pre-existing):** the endpoint requires only `get_current_user`, **not** `require_superuser` ([be_resizer.py](backend/routers/be_resizer.py#L313-L326)). The "superuser affordance" is therefore **client-side/cosmetic only**: any authenticated (non-superuser) user could invoke `GET /be_resizer/create_thumbnails/{id}` directly. This is a **pre-existing backend condition** — the backend was intentionally unchanged this increment, so the developer correctly did not touch it. Flagging for a follow-up (F-1). `be_album.get_album_by_id` is likewise authenticated-only at the router level, which is appropriate for a read.

### XSS in user-supplied metadata — PASS (no risk)

* Title, participants, tags, location, description, and `filename` are all rendered as React children (`{album.title}`, chip `{tag}`, `<img alt={item.filename}>`, etc.) — React escapes by default. **No `dangerouslySetInnerHTML`** appears anywhere in the new files. `tags.split(/[|,]/)` produces plain text chips. `src`/`href` attributes carry server-derived URL paths and are set through React's safe attribute handling. No injection vector introduced.

## Follow-ups (not blocking)

* **F-1 (Medium, pre-existing):** Add server-side superuser enforcement to state-changing `be_resizer` actions (e.g., `create_thumbnails`) so UI gating is backed by an authorization check. Natural home: Phase 3.6 (album admin) or a dedicated security increment. Backend was out of scope this increment.
* **F-2 (Low, pre-existing):** `create_thumbnails` is a state-changing **GET** and is therefore CSRF-exempt by design; consider promoting it to POST + CSRF when the backend is next touched. Latent, low likelihood (authenticated + same-origin posture).
* **L-1 (Low, documented):** Media list still transits fe_router's `/album/{id}/images` JSON endpoint (internal httpx loopback for metadata). Full fe_router retirement is deferred to Phase 3.8 per the plan.

## Notes

* This review validated sub-phase 3.3 only. Deferred work acknowledged by the change record (native share/associate 3.7, album delete/admin 3.6, native upload 3.4, full fe_router retirement 3.8) is out of scope and correctly stubbed/linked.
* e2e specs were validated by collection/read only; execution requires a live server + `E2E_USER_PASSWORD` and was not run here (consistent with the change record).

> **Note** — This review was produced with AI assistance. Findings and verdict should be validated by a qualified human reviewer before merge.
