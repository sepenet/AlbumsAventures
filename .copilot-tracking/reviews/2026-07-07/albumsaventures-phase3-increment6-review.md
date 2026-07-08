<!-- markdownlint-disable-file -->
# Review — Phase 3.7 Shared Album (public PIN flow) — SPA increment 6

**Reviewer**: tester (member Delta) · **Date**: 2026-07-07 · **Stage**: Review
**Plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (Phase 3.7)
**Change record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment6-changes.md`

## Scope reviewed

Public, unauthenticated shared-album flow migrated to the React SPA (additive strangler):

* `frontend/spa/src/lib/shared.ts` (+ `shared.test.ts`)
* `frontend/spa/src/pages/SharedAlbumPage.tsx`
* `frontend/spa/src/App.tsx` (public routes)
* `tests/e2e/test_spa_shared_album_ui.py`

This is a PUBLIC surface, so the review centers on whether the migration introduces any authenticated-data leak or route-shadowing of the share API.

## Verdict

**✅ Approve** — no authenticated-data leakage and no route-shadowing of the share API. All 7 review items PASS. All validation gates green. No defects requiring a fix cycle.

## Severity counts

| Critical | High | Medium | Low |
|----------|------|--------|-----|
| 0 | 0 | 0 | 0 |

## Per-item findings

### 1. Public-route isolation (no authenticated-data leakage) — PASS

* `App.tsx` registers `<Route path="/shared/:token">` and `<Route path="/shared">` **outside** `RequireAuth` and `Layout`, before the `*` catch-all ([App.tsx](frontend/spa/src/App.tsx#L104-L106)).
* All share fetches use a shared `PUBLIC_FETCH_INIT` with `credentials: "omit"` ([SharedAlbumPage.tsx](frontend/spa/src/pages/SharedAlbumPage.tsx#L24-L28)) — the HttpOnly session cookie is never sent, so the public flow cannot read any authenticated `be_*` data.
* `SharedAlbumPage` renders its own standalone `SharedShell`; it does **not** use `Layout`/`useSession`, so `GET /be_auth/me` is never called from this flow. Grep confirms `/be_auth/me` is referenced only in `useSession.ts` and unrelated comments; `SharedAlbumPage` mentions it only in a doc comment stating it never calls it.
* The two fetch targets are the public share endpoints only (`/be_album/shared`, `/album/shared/images`); no authenticated endpoint is invoked.

### 2. No token/PIN in localStorage/sessionStorage — PASS

* Token comes from the route param via `useParams` (URL only); the verified PIN is held in React state (`verified.pin`), memory only ([SharedAlbumPage.tsx](frontend/spa/src/pages/SharedAlbumPage.tsx#L108-L115)).
* The only `localStorage` access in the page is a read of `darkMode` for theme parity ([SharedAlbumPage.tsx](frontend/spa/src/pages/SharedAlbumPage.tsx#L104)) — no write, and neither token nor PIN is ever persisted. Confirmed by grep across the SPA source.

### 3. SPA fallback does not shadow the share API / `/be_*` — PASS

* The FastAPI SPA fallback is scoped to the `/app` prefix and registered **after** all routers and media mounts ([spa_serving.py](frontend/spa_serving.py#L98-L108)); its route-shadowing guarantee is documented and enforced by registration order.
* Backend share endpoints live outside `/app`: `GET /be_album/shared` (backend router) and `GET /album/shared/images` ([fe_router.py](frontend/routers/fe_router.py#L1096-L1123)). `/app/shared/*` cannot intercept them.
* App import confirms 108 routes with the fallback registered last (log: "route de repli enregistrée sur /app/{full_path}").

### 4. Server-side security intact (backend unchanged) — PASS

* Increment 6 change record lists 4 added files + 1 edited file (`App.tsx`) and no backend `.py` edits. The cumulative working-tree diff on backend `.py` files originates from earlier phases (Phase 1 security added `utils/rate_limit.py`, `utils/security.py`; `be_auth.verify_share_token`), not this increment.
* Backend remains the source of truth: `/album/shared/images` re-validates token+PIN via the backend `/be_album/shared` call, with `pin` constrained `min_length=6, max_length=6` ([fe_router.py](frontend/routers/fe_router.py#L1096-L1103)); `verify_share_token` enforces PIN, expiry, and the durable rate limiter (`record_failed_attempt` / `check_rate_limit`, `attempts_remaining`) in `backend/routers/be_auth.py`.
* The SPA only surfaces backend 403/429 messages via `sharedErrorMessage`; it does not implement or weaken any validity/PIN/expiry/rate-limit check.

### 5. Restricted read-only view — PASS

* `SharedAlbumDetail` omits every owner affordance — no back-to-albums, edit, upload, share, cover, or associate action ([SharedAlbumPage.tsx](frontend/spa/src/pages/SharedAlbumPage.tsx#L211-L268)).
* The "Accès temporaire par lien de partage" shared badge is always shown; images open the reused `Lightbox`; videos display a play overlay ([SharedAlbumPage.tsx](frontend/spa/src/pages/SharedAlbumPage.tsx#L295-L320)).
* The added e2e spec asserts the badge is present and each owner affordance is absent ([test_spa_shared_album_ui.py](tests/e2e/test_spa_shared_album_ui.py#L107-L133)).

### 6. PIN format validation mirrors backend (UX pre-check only) — PASS

* `isValidPinFormat` enforces exactly 6 alphanumeric chars (`/^[A-Za-z0-9]{6}$/`), and `normalizePin` trims + upper-cases, mirroring backend `create_share_token` / `verify_share_token` ([shared.ts](frontend/spa/src/lib/shared.ts#L18-L32)).
* It is a pre-network UX gate only; the server re-validates regardless. Not relied on as a security control.

### 7. No CSP/CORS loosening; build-time Node only; strangler intact — PASS

* No CSP/CORS changes in the reviewed diff; fetches are same-origin with credentials omitted.
* SPA is built by Vite at build time and served same-origin by the existing FastAPI process — no new runtime/cross-origin surface.
* The Jinja shared flow (`fe_router.shared_album_page` / `shared_album_verify`) is untouched; the SPA route is the additive `/app` variant.

## Validation gates

| Gate | Command | Result |
|------|---------|--------|
| SPA build | `npm run build` | ✅ green — 330 modules; `index-*.js` 260.29 kB (gzip 78.33 kB); UploadPage chunk unchanged |
| SPA lint | `npm run lint` (`--max-warnings 0`) | ✅ green — 0 warnings |
| SPA unit tests | `npm run test` (vitest) | ✅ 59 passed (6 files; incl. 11 `shared.test.ts`) |
| Backend tests | `pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py` | ✅ 54 passed |
| App import | import `AlbumsAventures-BE.py` | ✅ clean — 108 routes; SPA fallback registered last |
| `tests/e2e/test_spa_shared_album_ui.py` | Playwright (needs live server) | Not run — skips cleanly without live server/admin creds (consistent with prior increments) |

Dev-reported counts (build green, lint 0, vitest 59, pytest 54, 108 routes) reproduced exactly.

## Missing work / deviations

* None material. `sharedErrorMessage` gained a status-based HTTP 429 fallback (surfaces the lockout message when the structured `error` code is absent); this only broadens rate-limit surfacing and is covered by an added test — no security weakening.
* `test_share_album.py` (repo-root live-server script) not run: outside `testpaths`, requires a running server + real credentials; correctly skipped per increment instructions.

## Follow-up recommendations

* Deferred from scope: run `tests/e2e/test_spa_shared_album_ui.py` against a live server with admin credentials as part of an integration/E2E pass to confirm the public PIN flow end-to-end in a browser.
* Discovered during review: none.

## Reviewer notes

Public-route isolation and share-API non-shadowing — the two Request-changes triggers — both hold. Access is gated exclusively by the URL token + typed PIN, re-validated server-side on every request; no authenticated data path is reachable from the public flow. Approve.
