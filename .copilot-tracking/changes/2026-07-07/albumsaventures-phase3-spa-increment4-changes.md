<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 Increment 4 — Profile Page (3.5) + Uppy Code-Split (FU-1)

**Related Plan**: albumsaventures-phase3-spa.md (sub-phase 3.5; follow-up FU-1)
**Implementation Date**: 2026-07-07
**Developer**: `developer` role (member Gamma), squad autopilot

## Summary

Two changes on top of the landed SPA increments 1–4:

1. **Sub-phase 3.5 — React profile page.** Added the `/app/profile` route: a deep-linkable React variant of `frontend/templates/profile.html` with a profile-update form (prefilled from the cookie session) and a password-change section. Client-side validation (including the password-mismatch check) mirrors the Jinja page; both mutations use `PUT` through the shared apiClient, which sends the HttpOnly session cookie same-origin and echoes the CSRF double-submit header — no token in JS storage. The Jinja `/profile` page stays live (strangler).
2. **FU-1 — Code-split the Uppy upload page.** Converted the upload route to a lazy-loaded chunk (`React.lazy` + `Suspense`). The heavy `@uppy/*` ESM stack (and its `useUploader` hook, the sole importer of `@uppy/*`) now builds into a separate `UploadPage` chunk fetched only when the upload page is opened, shrinking the initial album-grid bundle and resolving the > 500 kB warning.

Backend unchanged. Local edits only — no deploy/push/merge/migration.

## Changes

### Added

* frontend/spa/src/lib/profileValidation.ts - Pure, DOM-free validators mirroring the Jinja profile rules: `validateProfileForm` (firstname/lastname ≥ 2 chars, email regex), `validatePasswordForm` (current required; new ≥ 8 chars with lower/upper/digit; **confirmation must match** the new password), plus `isValid`.
* frontend/spa/src/lib/profileValidation.test.ts - 9 Vitest cases including the Phase 3.5 password-mismatch smoke test.
* frontend/spa/src/pages/ProfilePage.tsx - React profile page: prefill from `useSession` (`GET /be_auth/me`), profile + password forms, `useMutation` on `PUT /be_auth/update_profile` and `PUT /be_auth/update_password`, per-field errors, loading/error/success states (success message on update; password form cleared on success).
* tests/e2e/test_spa_profile_ui.py - Playwright smoke spec: prefill-from-session, password-mismatch blocks submit, deep-link refresh serves the SPA shell.

### Modified

* frontend/spa/src/lib/apiClient.ts - Added a `put<T>` method (CSRF-guarded like `post`/`patch`) because the profile endpoints are `PUT`. Same double-submit + `credentials: "same-origin"` semantics as the existing mutating verbs.
* frontend/spa/src/App.tsx - FU-1: `UploadPage` now imported via `lazy(() => import("./pages/UploadPage")…)` and rendered inside `<Suspense>` with a lightweight fallback. Added the `/profile` route.
* frontend/spa/src/components/Layout.tsx - Added a "Mon profil" header `Link` to `/profile` (in-SPA router link), shown when a session is present.

### Removed

* (none) — additive strangler increment; no files deleted.

## FU-1 Result — Bundle Before vs After

`npm run build` (frontend/spa), production, minified + gzipped:

| Artifact | Before (increment 3) | After (this increment) |
|----------|----------------------|------------------------|
| Main JS chunk | `index-*.js` **524.47 kB** (gzip 161.99 kB) | `index-*.js` **238.37 kB** (gzip 74.25 kB) |
| Upload/Uppy JS chunk | *(none — folded into main)* | `UploadPage-*.js` **295.75 kB** (gzip 90.25 kB) — lazy |
| Main CSS | `index-*.css` 86.86 kB (gzip 14.64 kB) | `index-*.css` 21.25 kB (gzip 4.60 kB) |
| Upload CSS | *(folded into main)* | `UploadPage-*.css` 66.22 kB (gzip 10.51 kB) — lazy |
| > 500 kB warning | **present** | **resolved** |

**Initial-load JS dropped ~54.5%** (524.47 → 238.37 kB; gzip 161.99 → 74.25 kB). The Uppy stack + its Dashboard CSS are now in a separate chunk loaded only when the user opens `/app/albums/:id/upload`. No Phase 2 upload behavior changed — the upload page is unchanged apart from being reached via a dynamic import.

## Additional or Deviating Changes

* **Backfilled the missing 3.4 change record.** Authored `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment3-changes.md` (the increment-3 developer output was truncated; reconstructed from the working tree and the increment-3 review), documenting the React upload page, the Uppy v3→v5 ESM cutover, and the six-item Phase 2 preservation checklist.
* **Profile field scope matches the Jinja page.** Editable fields are `firstname`, `lastname`, `email` (per `schemas.UserProfileUpdate`); no extra fields were introduced.
* **No CSP / CORS change.** `utils/security.py` untouched: no `unsafe-eval`, no `*`, no CORS; same-origin cookie + CSRF only. Node is build-time only. CDN/`unsafe-inline` retirement remains a 3.9 item.
* **Server remains authoritative.** Client validation is UX-only; `PUT /be_auth/update_profile` re-validates and rejects duplicate emails, and `PUT /be_auth/update_password` re-verifies the current password server-side.

## Validation Status

| Gate | Result |
|------|--------|
| `npm run build` (frontend/spa) | ✅ PASS — 325 modules; main 238.37 kB, UploadPage 295.75 kB; **no > 500 kB warning** |
| `npm run lint` (max-warnings 0) | ✅ PASS — 0 warnings |
| `npm run test` (vitest) | ✅ PASS — 35/35 (profileValidation 9, upload 14, apiClient 4, format 8) |
| `pytest tests/test_auth.py test_albums.py test_upload.py -q` | ✅ PASS — 50 passed |
| App import | ✅ PASS — 108 routes, SPA mounts registered |

## Release Summary

SPA-only increment: 4 files added, 3 modified, 0 removed; backend untouched. Delivered the React profile page (3.5) with cookie-only auth + CSRF-guarded `PUT` mutations and client-side password-mismatch validation, and the FU-1 Uppy code-split that cut the initial JS bundle ~54.5% and cleared the > 500 kB warning. Backfilled the increment-3 (3.4) change record. All front-end and back-end gates green. Deferrals: full Playwright upload/profile flow coverage remains a Phase 4 item (FU-2); the e2e specs added are smoke-level and require a running server with a built SPA. No deployment/migration.
