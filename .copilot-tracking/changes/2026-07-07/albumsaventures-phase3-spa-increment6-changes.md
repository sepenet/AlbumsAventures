<!-- markdownlint-disable-file -->
# Release Changes: Phase 3.7 — Shared Album (public PIN-secured flow) — SPA increment 6

**Related Plan**: albumsaventures-phase3-spa.md (Phase 3.7)
**Implementation Date**: 2026-07-07
**Role**: developer (member Gamma), squad autopilot

## Summary

Migrated the **public, unauthenticated shared-album flow** to the React SPA as an
additive strangler increment. A new PUBLIC route `/app/shared/:token` (NOT behind
the `RequireAuth` guard and NOT wrapped in the authenticated `Layout`) presents a
6-character PIN entry page, verifies it against the existing public share
endpoints, and then renders a RESTRICTED read-only gallery reusing the Phase 3.3
`Lightbox`. The backend is unchanged: it remains the sole source of truth for
token validity, PIN verification, expiry, and rate limiting. The existing Jinja
shared pages continue to work.

## Changes

### Added

* `frontend/spa/src/lib/shared.ts` — Pure helpers for the public share flow:
  `isValidPinFormat` (6 alphanumeric chars, mirrors backend `create_share_token`
  validation), `normalizePin` (trim + upper-case like `verify_share_token`),
  `sharedErrorMessage` (maps backend structured `detail` payloads to French user
  messages, mirroring the Jinja `shared_album_verify` mapping and surfacing the
  HTTP 429 lockout wording — including a status-based 429 fallback), and the
  `SharedAccessError` type. No DOM/`fetch` dependency (unit-testable).
* `frontend/spa/src/lib/shared.test.ts` — 11 vitest cases covering PIN-format
  validation (length + alphanumeric), normalization, and every error-mapping
  branch (wrong PIN with remaining attempts, lockout, 429 with/without error
  code, expired token, fallback).
* `frontend/spa/src/pages/SharedAlbumPage.tsx` — The public page. PIN entry form
  (`input[name="pin"]`, "Accéder à l'album", red error box
  `bg-red-50 dark:bg-red-900/30`) → on correct PIN, a restricted read-only
  gallery. Fetches album metadata from `GET /be_album/shared?token&pin` and media
  from `GET /album/shared/images?token&pin&offset&limit`, both with
  `credentials: "omit"`. Reuses `Lightbox`; videos show a play overlay, images
  open the lightbox. Renders a standalone `SharedShell` (no authenticated nav).
* `tests/e2e/test_spa_shared_album_ui.py` — SPA Playwright spec for
  `/app/shared/:token` (PIN page loads, wrong PIN error, correct PIN → badge,
  and absence of every owner affordance). Derives the SPA URL from the admin
  share link; skips cleanly without a live server / admin credentials.

### Modified

* `frontend/spa/src/App.tsx` — Registered two PUBLIC routes,
  `/shared/:token` and `/shared`, BEFORE the catch-all and OUTSIDE `RequireAuth`
  / `Layout`. Added the `SharedAlbumPage` import and an explanatory comment on
  the isolation guarantees.

### Removed

* None.

## Restricted read-only view — hidden owner affordances

The shared detail view intentionally omits every affordance present on the
authenticated album detail page, matching the current Jinja "mode partagé":

* No **Retour aux albums** (back-to-albums) link.
* No **Modifier** (edit) button.
* No **Ajouter des photos** (upload) button.
* No **Partager** (share) button.
* No **Choisir couverture** (cover selection) button.
* No **Associer** (associate) button.

Only a **"Accès temporaire par lien de partage"** shared badge, the album header,
and the read-only media gallery are shown.

## Public-route isolation (no authenticated-data leakage)

* **Session-free calls.** All share fetches use `credentials: "omit"`, so the
  browser session cookie is never sent — the public flow cannot read any
  authenticated `be_*` data. Access is gated exclusively by the URL token + the
  typed PIN, which the backend re-validates on every request.
* **No authenticated shell.** The page renders its own minimal `SharedShell`
  instead of `Layout` (which calls `GET /be_auth/me` via `useSession` and shows
  the logged-in navigation + logout). The public viewer never triggers a session
  lookup.
* **No token/PIN persistence.** The share token lives only in the route param;
  the verified PIN is held in React state (memory). Nothing is written to
  `localStorage`/`sessionStorage`.
* **No API shadowing.** `/app/shared/*` is served by the FastAPI SPA fallback
  (`frontend/spa_serving.py`), registered AFTER all routers and media mounts and
  scoped to the `/app` prefix. It cannot intercept `/be_album/shared` or the
  `/album/shared/images` media API (both outside `/app`). Confirmed by the clean
  app import (108 routes, fallback registered last).
* **Rate limiting untouched.** The durable limiter (max 5 attempts / 15 min,
  brute-force protection) stays server-side; the SPA only surfaces the resulting
  403/429 messages. No server-side security was weakened.
* **No CORS / no CSP relaxation.** Same-origin only; no `unsafe-eval`/`*` added.

## Additional or Deviating Changes

* `sharedErrorMessage` gained a status-based HTTP 429 fallback (returns the
  lockout message even when the structured `error` code is absent). This makes
  rate-limit surfacing more robust and gives the `status` parameter a real use
  (required by TypeScript `noUnusedParameters`). Covered by an added test.
* Added a dedicated SPA e2e spec (`test_spa_shared_album_ui.py`) rather than
  editing the Jinja `test_shared_album_ui.py`, consistent with prior increments
  (SPA specs are additive; Jinja specs stay green during the strangler).
* `test_share_album.py` (repo root) was NOT run: it is a live-server script
  (`requests` against `http://localhost:8003` with real credentials) and is not
  part of the pytest `testpaths`. Skipped per the increment instructions.

## Release Summary

* **Files added:** 4 (`lib/shared.ts`, `lib/shared.test.ts`,
  `pages/SharedAlbumPage.tsx`, `tests/e2e/test_spa_shared_album_ui.py`).
* **Files modified:** 1 (`App.tsx`).
* **Files removed:** 0.
* **Backend:** unchanged (no `.py` backend edits).
* **Validation:**
  * `npm run build` — green (330 modules; main JS 260.29 kB gzip 78.33 kB;
    UploadPage chunk unchanged).
  * `npm run lint` (`--max-warnings 0`) — green.
  * `npm run test` (vitest) — 59 passed (6 files; +11 new shared-flow tests).
  * `pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py` —
    54 passed.
  * App import — clean, 108 routes (unchanged); SPA fallback registered last.
  * `tests/e2e/test_spa_shared_album_ui.py` — added; requires a live server
    (not run here).
* **Deployment notes:** Local edits only — no deploy/push/merge, no migrations.
  The `frontend/spa/dist` build output was regenerated by `npm run build`.
