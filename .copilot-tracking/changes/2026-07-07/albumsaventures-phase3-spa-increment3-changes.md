<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 Increment 3 (sub-phase 3.4) — React Upload Page + Uppy v3→v5 ESM

**Related Plan**: albumsaventures-phase3-spa.md (sub-phase 3.4)
**Implementation Date**: 2026-07-07
**Status**: BACKFILL — the original developer output was truncated and no change record was written at landing time. Reconstructed from the working tree and the review record `.copilot-tracking/reviews/2026-07-07/albumsaventures-phase3-increment3-review.md` (verdict: Approve-with-followups).

## Summary

Migrated the album upload surface to a React page under the SPA (`/app/albums/:albumId/upload`) and cut the Uppy stack over from the Phase 2 **v3.27 transloadit UMD combined bundle** to **Uppy v5 ESM**, bundled by Vite. The v3→v5 jump (#393) was the reason this work waited for the SPA bundler: Uppy v5 dropped the UMD global and is ESM-only. All six Phase 2 upload-reliability behaviors were re-wired on v5 with no backend change. The historical Jinja `album_upload.html` page remains live (strangler).

## Changes

### Added

* frontend/spa/src/lib/upload.ts - Pure adaptive-chunk + compression-metric helpers: `selectChunkSize` (seeds from `navigator.connection`), `clampChunkSize` (re-floors/caps), `computeCompressionMetric`, `formatBytes`, `buildUploadConfigQuery`; constants `CHUNK_SIZE_FLOOR = 256 KB`, `CHUNK_SIZE_CEILING = 8 MB`.
* frontend/spa/src/lib/upload.test.ts - 14 Vitest cases (floor/ceiling/scaling/compression metric/format/query-building).
* frontend/spa/src/hooks/useUploader.ts - Uppy v5 lifecycle hook: `Tus` + `Compressor` + `GoldenRetriever`, server chunk alignment via `/be_resizer/upload_config`, durable `/be_resizer/processing_status/{album_id}` polling (3 s tick, self-terminating, 40-tick guard), compression-metric aggregation.
* frontend/spa/src/pages/UploadPage.tsx - `@uppy/react` Dashboard, compression-metric UI, per-file thumbnail-processing status + summary, regenerate-thumbnails action.
* tests/e2e/test_spa_upload_ui.py - Playwright smoke spec for the SPA upload route (render + deep-link refresh + back-link).

### Modified

* frontend/spa/package.json - Uppy v5 ESM dependencies: `@uppy/core@^5.2.0`, `@uppy/dashboard@^5.1.1`, `@uppy/tus@^5.1.1`, `@uppy/golden-retriever@^5.2.1`, `@uppy/react@^5.2.0`, `@uppy/locales@^5.1.1`, `@uppy/compressor@^3.1.0` (independently versioned, Uppy-v5-compatible).
* frontend/spa/src/types/api.ts - Added `UploadConfig`, `ProcessingFile`, `ProcessingSummary`, `ProcessingStatusResponse` types mirroring the Phase 2 `be_resizer` contract.
* frontend/spa/src/App.tsx - Added route `/albums/:albumId/upload`.
* frontend/spa/src/pages/AlbumDetailPage.tsx - Upload affordance changed to an in-SPA `Link` (was a link to the Jinja upload page).

### Removed

* (none) — additive strangler increment; no files deleted.

## Phase 2 Preservation Checklist

All six Phase 2 upload-reliability behaviors were ported to Uppy v5 with no regression (evidence per the review record):

* **Golden-retriever resume-after-reload (#394)** — `uppy.use(GoldenRetriever, { serviceWorker: false })` (IndexedDB only; SW storage stays a Phase 4 PWA concern).
* **Client-side compression (#380) + payload-reduction metric** — `uppy.use(Compressor, { quality: 0.8, limit: 10 })` (identical params to Phase 2); original size captured pre-compression, aggregated via `computeCompressionMetric`, surfaced in the UI.
* **Adaptive chunk, `/upload_config` authoritative, 256 KB floor never breached** — `clampChunkSize` re-floors both the local seed and the server value; `selectChunkSize` floors on saveData/absent connection; asserted by unit tests.
* **Durable processing-status polling** — `GET /be_resizer/processing_status/{album_id}` every 3 s, self-terminating when `pending+processing == 0`, 40-tick (~2 min) guard; per-file status + summary rendered; failed-thumbnail hint wired to the regen action.
* **Same-origin TUS** — endpoint `/be_resizer/tus/`, `withCredentials: true`, `limit: 1`, `removeFingerprintOnSuccess: true`, `album_id` metadata preserved.
* **Auth/CSRF cookie-only** — TUS `withCredentials` sends the HttpOnly session cookie; the apiClient injects `X-CSRF-Token` from the JS-readable `csrf_token` cookie on mutations; the only `localStorage` use is the dark-mode preference (no auth token in storage).

## Additional or Deviating Changes

* **Backend unchanged.** Backend files appearing in `git status` (`be_resizer.py`, `crud.py`, `models.py`, `be_auth.py`, `utils/*`) are pre-existing uncommitted Phase 1/2 work, not part of 3.4. The Phase 2 upload contract was consumed as-is.
* **CSP unregressed.** `utils/security.py` was not touched by 3.4. `connect-src 'self'` (same-origin TUS), `worker-src 'self' blob:`, no `unsafe-eval`, no `*`. The `script-src` CDN + `unsafe-inline` allowances persist for the Jinja pages only and are scheduled for retirement in 3.9.
* **Bundle-size follow-up (FU-1).** The Uppy stack landed in the single main chunk (`524.47 kB`, > 500 kB warning). Addressed in increment 4 (see `albumsaventures-phase3-spa-increment4-changes.md`).

## Release Summary

SPA-only increment: 5 files added, 4 modified, 0 removed; backend untouched. Delivered the highest-risk sub-phase (Uppy v5 ESM cutover) with all Phase 2 reliability behaviors preserved. Validation at landing (per review): `npm run build` PASS (524 kB warn), `npm run lint` PASS (0 warnings), Vitest 26/26, `pytest` 50 passed, app import 108 routes. Reviewed by the `tester` role — Approve-with-followups (FU-1 bundle size, FU-2 e2e depth). No deployment/migration.
