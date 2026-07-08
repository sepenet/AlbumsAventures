<!-- markdownlint-disable-file -->
# Review — Phase 3 Increment 3 (sub-phase 3.4): React Upload Page + Uppy v3→v5 ESM

- **Reviewer:** `tester` role (member Delta), Task Reviewer
- **Date:** 2026-07-07
- **Scope:** SPA upload page and Uppy v5 ESM port; Phase 2 upload-reliability preservation
- **Change record:** MISSING — reconstructed from the working tree (developer output truncated)
- **Related plan:** `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (sub-phase 3.4)
- **Prior review:** `.copilot-tracking/reviews/2026-07-07/albumsaventures-phase2-uploads-review.md` (Phase 2 baseline)

## Reconstructed change set (3.4)

SPA-only; backend untouched by this increment.

| File | Role |
|------|------|
| `frontend/spa/package.json` | Uppy v5 ESM deps (core `^5.2.0`, tus/golden-retriever/dashboard/react/locales `^5.x`, compressor `^3.1.0`) |
| `frontend/spa/src/lib/upload.ts` | Pure adaptive-chunk + compression-metric helpers (256 KB floor / 8 MB ceiling) |
| `frontend/spa/src/lib/upload.test.ts` | 14 vitest cases (floor/ceiling/scaling/metric/format/query) |
| `frontend/spa/src/hooks/useUploader.ts` | Uppy v5 lifecycle: Tus + Compressor + GoldenRetriever, server chunk alignment, durable polling |
| `frontend/spa/src/pages/UploadPage.tsx` | `@uppy/react` Dashboard, compression metric UI, per-file processing status, regen button |
| `frontend/spa/src/types/api.ts` | `UploadConfig`, `ProcessingFile/Summary/StatusResponse` types |
| `frontend/spa/src/App.tsx` | Route `/albums/:albumId/upload` |
| `frontend/spa/src/pages/AlbumDetailPage.tsx` | Upload affordance → in-SPA `Link` |
| `tests/e2e/test_spa_upload_ui.py` | e2e smoke (deferred/Playwright) |

Backend files in `git status` (`be_resizer.py`, `crud.py`, `models.py`, `be_auth.py`, `utils/*`) are **pre-existing uncommitted Phase 1/2 work**, already reviewed; not part of 3.4. Backend contract unchanged.

## Phase 2 preservation checklist (the critical review)

| # | Phase 2 reliability behavior | Verdict | Evidence |
|---|------------------------------|---------|----------|
| 1 | **Golden-retriever resume-after-reload (#394)** | ✅ PRESERVED | `@uppy/golden-retriever@^5.2.1` in [package.json](../../../frontend/spa/package.json#L14); wired `uppy.use(GoldenRetriever, { serviceWorker: false })` in [useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L104). `serviceWorker:false` (IndexedDB only) matches Phase 2 — SW storage remains a Phase 4 PWA concern. |
| 2 | **Client-side compression (#380) + payload-reduction metric** | ✅ PRESERVED | `@uppy/compressor@^3.1.0` (its independent line, Uppy-v5-compatible) wired `uppy.use(Compressor, { quality: 0.8, limit: 10 })` in [useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L99) — identical params to Phase 2. Metric computed: original size captured pre-compression at `file-added` ([useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts) `onFileAdded`), aggregated via `computeCompressionMetric` on `complete`, surfaced in the UI ([UploadPage.tsx](../../../frontend/spa/src/pages/UploadPage.tsx) "Compression : … économisés"). Pure metric fn in [upload.ts](../../../frontend/spa/src/lib/upload.ts#L94) + 3 tests. |
| 3 | **Adaptive chunk, /upload_config authoritative, 256 KB floor NEVER breached** | ✅ PRESERVED | Floor `CHUNK_SIZE_FLOOR = 256*1024` and ceiling `8 MB` in [upload.ts](../../../frontend/spa/src/lib/upload.ts#L17-L20). `clampChunkSize` re-floors both the local value AND the server value ([useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L243) `setOptions({ chunkSize: clampChunkSize(cfg.chunk_size) })`). `selectChunkSize` seeds from `navigator.connection`, floors on saveData/absent. `/be_resizer/upload_config` fetched and applied best-effort. Floor asserted by tests: `clampChunkSize(1024)/0/-5/NaN → FLOOR` and `selectChunkSize` floor cases in [upload.test.ts](../../../frontend/spa/src/lib/upload.test.ts#L13-L60). |
| 4 | **Durable processing-status polling → `/processing_status/{albumId}` in UI** | ✅ PRESERVED | Poll loop every 3 s, self-terminating when `pending+processing == 0`, 40-tick (~2 min) guard in [useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L157) (`GET /be_resizer/processing_status/${albumIdRef.current}`). Per-file status + summary rendered ("Traitement des vignettes", labels/counts) in [UploadPage.tsx](../../../frontend/spa/src/pages/UploadPage.tsx). Failed-thumbnail hint wired to the regen action. |
| 5 | **TUS resumable → `/be_resizer/tus/` (same-origin) via `@uppy/tus`** | ✅ PRESERVED | `@uppy/tus@^5.1.1`; endpoint `TUS_ENDPOINT = "/be_resizer/tus/"` ([useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L34)); `uppy.use(Tus, { endpoint, chunkSize, retryDelays, removeFingerprintOnSuccess: true, withCredentials: true, limit: 1 })` ([useUploader.ts](../../../frontend/spa/src/hooks/useUploader.ts#L88-L96)). `album_id` meta set via `setMeta`. Endpoint and options match Phase 2 exactly. |
| 6 | **Auth/CSRF: cookie-only, no localStorage token; mutations carry headers** | ✅ PRESERVED | TUS `withCredentials: true` sends the HttpOnly session cookie same-origin. `api` client uses `credentials: "same-origin"` and injects `X-CSRF-Token` from the JS-readable `csrf_token` cookie on POST/PUT/PATCH/DELETE ([apiClient.ts](../../../frontend/spa/src/lib/apiClient.ts#L64-L79)). No auth token in storage — the only `localStorage` use is the dark-mode preference ([Layout.tsx](../../../frontend/spa/src/components/Layout.tsx#L11)). |

**All six Phase 2 reliability behaviors PRESERVED. No regression.**

## Additional assessments

| Area | Verdict | Evidence |
|------|---------|----------|
| **Uppy v5 ESM-bundled by Vite (not UMD CDN global)** | ✅ PASS | No `Uppy.*` global reference in SPA source; all usage is instance methods on the local `uppy` from `new Uppy(...)`. No `releases.transloadit`/CDN `<script>` in the SPA path; [index.html](../../../frontend/spa/index.html) loads only `/src/main.tsx`. Uppy is bundled into `dist/assets/index-*.js`. |
| **CSP — no new CDN, no `unsafe-eval`/`*`** | ✅ PASS | `security.py` unchanged by 3.4: `connect-src 'self'` (same-origin TUS OK), `worker-src 'self' blob:`, no `unsafe-eval`, no `*`. `script-src` CDN + `unsafe-inline` allowances persist for the **Jinja** pages only (documented for 3.9). No SPA-driven CSP change. |
| **Strangler intact — Jinja `album_upload.html` still works** | ✅ PASS | `frontend/templates/album_upload.html` still present and functional (Phase 2 fix-cycle state); SPA route is additive. |
| **Bundle size** | ⚠️ FOLLOW-UP | Main chunk `524.47 kB` (gzip 162 kB) > 500 kB warning — Uppy is heavy and currently loads with the album-grid initial bundle. See follow-up FU-1. |

## Validation results

| Gate | Result |
|------|--------|
| `npm run build` (frontend/spa) | ✅ PASS — built in 2.55s; >500 kB chunk warning only |
| `npm run lint` (max-warnings 0) | ✅ PASS — 0 warnings |
| `npm run test` (vitest) | ✅ PASS — 26/26 (upload.test 14, apiClient 4, format 8) |
| `pytest tests/test_upload.py test_auth.py test_albums.py -q` | ✅ PASS — 50 passed |
| App import | ✅ PASS — 108 routes, SPA mounts registered |

## Findings / follow-ups

- **FU-1 (Medium) — Lazy-load / code-split the Uppy upload page.** The 524 kB main chunk bloats the album-grid initial load with the full Uppy stack that is only needed on `/albums/:id/upload`. Recommend a dynamic `import()` (React `lazy` + `Suspense`) for `UploadPage`, or `manualChunks` to isolate `@uppy/*`. **Non-blocking** — build passes and reliability is unaffected. Severity Medium (perf/UX, initial-load weight on mobile — the same constrained links this feature targets).
- **FU-2 (Low) — e2e coverage.** `tests/e2e/test_spa_upload_ui.py` is a smoke stub; full Playwright upload-flow coverage remains a Phase 4 item (carried from the Phase 2 review). Non-blocking.
- **Note** — No change record was produced for 3.4 (developer output truncated). Recommend authoring `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment3-changes.md` for traceability. Non-blocking to the code verdict.

## Verdict

**✅ Approve-with-followups**

All six Phase 2 upload-reliability behaviors (golden-retriever #394, compression #380 + metric, adaptive-chunk 256 KB floor, durable processing-status polling, same-origin TUS, cookie+CSRF) are preserved in the React + Uppy v5 ESM port with file:line evidence. The v5 ESM cutover is complete (no UMD global, no CDN in the SPA path), CSP is unregressed, and the Jinja strangler remains intact. Every front-end and back-end gate passes. The only open item is the non-blocking bundle-size follow-up (FU-1). No Phase 2 regression → not Request-changes.
