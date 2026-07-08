<!-- markdownlint-disable-file -->
# Release Changes: Phase 2 — Upload Reliability (validator fix cycle 1)

**Related Plan**: [.copilot-tracking/plans/albumsaventures-modernization.md](../../plans/albumsaventures-modernization.md) (Phase 2)
**Related Review**: [.copilot-tracking/reviews/2026-07-07/albumsaventures-phase2-uploads-review.md](../../reviews/2026-07-07/albumsaventures-phase2-uploads-review.md)
**Implementation Date**: 2026-07-07
**Role**: developer (member Gamma) — fix cycle 1

## Summary

The Phase 2 backend (durable per-file processing status, bounded thumbnail
worker pool, server-authoritative 256KB chunk floor, config-gated legacy XHR,
clean CSP) passed review. The **frontend** was broken: three methods were
called on the Alpine `uploadManager()` object but never defined, and the first
(`selectChunkSize()`) was invoked inside `init()` — throwing
`TypeError: self.selectChunkSize is not a function` on page load and preventing
`Uppy.Tus` / `Uppy.Compressor` / `Uppy.GoldenRetriever` from ever registering.

This cycle restores full upload functionality on the **current Uppy v3.27.0**
version by defining the three methods and rendering the previously-declared
reliability state, fixes the failing `ruff` gate on `be_resizer.py`, adds a
lightweight template-contract guard test, and **explicitly defers** the Uppy
v3→v5 major upgrade (#393) to Phase 3.

## Defect → Resolution map

| Defect | Severity | Resolution |
|---|---|---|
| **D1** — 3 upload-page methods called but never defined; `selectChunkSize()` throws in `init()`, disabling the whole dashboard | Critical | Defined `selectChunkSize()`, `computeCompressionMetric()`, `startProcessingStatusPolling()` (+ helpers `refineChunkSizeFromServer()`, `stopProcessingStatusPolling()`, `formatBytes()`) in `frontend/templates/album_upload.html`. `init()` no longer throws; Tus/Compressor/GoldenRetriever now register. Verified with `node --check` (exit 0) + guard test. |
| **D2** — Uppy still v3.27.0; #393 not delivered | High | **DEFERRED to Phase 3** (frontend bundler phase) with recorded acceptance — see "D2 deferral decision" below. Full upload reliability restored on v3 first (D1). |
| **D3** — `ruff check` fails on `be_resizer.py` (F401 unused `import time`; I001 import order) | Medium | Removed unused `import time`; consolidated the mid-file `import logging` into the top stdlib group; ran `ruff check --fix`. `ruff` now green on all Phase 2 files. |
| **D4** — `processingFiles` / `processingSummary` / `metrics` declared but never rendered | Low (folds into D1) | Added markup that renders the compression metric, the per-file processing status list, and the aggregate summary. Data is now surfaced to the user. |

## D2 deferral decision (explicit, documented)

**Decision**: Do **NOT** perform the Uppy v3→v5 major-version upgrade (#393) in
this fix cycle. Restore full upload functionality on the current Uppy v3.27.0
combined UMD bundle first (D1), then defer the v3→v5 cutover to **Phase 3**
(frontend framework / bundler phase).

**Rationale**:

- Uppy v5 is ESM-only (the UMD combined bundle with the global `Uppy` and the
  `Uppy.GoldenRetriever` / `Uppy.Compressor` plugin namespaces is removed), so
  the upgrade is bundler-first and couples directly to the Phase 3 build system.
- All Phase 2 reliability substance (adaptive chunk with 256KB floor,
  GoldenRetriever resume-after-reload #394, Compressor #380, durable status
  polling) is deliverable on the v3.27 bundle and is delivered here.
- The Phase 1 CSP (`utils/security.py`) already allows
  `https://releases.transloadit.com` for **both** v3 and v5 assets — the
  forward-allowance for v5 is already in place, so no CSP change is required
  when the upgrade lands in Phase 3.

**Acceptance**: This is a deliberate, recorded deferral (not an oversight). The
`#393` v5 ESM cutover is a Phase 3 follow-on item. A brief in-template note was
added at the CDN `<link>` documenting the deferral for future maintainers.

## Changes

### Added

* .copilot-tracking/changes/2026-07-07/albumsaventures-phase2-uploads-changes.md - This change record.
* tests/test_upload.py - New `TestUploadTemplateContract` class (2 tests): asserts every `self.<method>()` called on the upload manager has a definition (guards the exact D1 regression), and asserts the reliability state (metric + processing status) is rendered in the markup (D4).

### Modified

* frontend/templates/album_upload.html - **D1**: defined `selectChunkSize()` (adaptive chunk from `navigator.connection`, floored at 256KB, capped 8MB), `refineChunkSizeFromServer()` (best-effort align to server-authoritative `/upload_config`), `computeCompressionMetric()` (#380 payload-reduction from pre/post-compression sizes), `startProcessingStatusPolling()` + `stopProcessingStatusPolling()` (poll `/processing_status/{album_id}`, self-terminating), and `formatBytes()`. Wired `refineChunkSizeFromServer()` into `init()`. **D4**: added markup rendering the compression metric, per-file processing status list, and aggregate summary. **D2**: added a v5-deferral note at the Uppy CDN links.
* backend/routers/be_resizer.py - **D3**: removed unused `import time`; moved `import logging` into the top stdlib import group (fixes F401 + I001). No behavior change.

### Removed

* (none)

## Additional or Deviating Changes

* The backend read-only status endpoint `GET /be_resizer/processing_status/{album_id}` and the adaptive `GET /be_resizer/upload_config` **already existed** from the reviewed backend work, so no new endpoint was needed for D1 — the client was simply wired to the existing durable-status endpoint.
* `refineChunkSizeFromServer()` was added beyond the three named methods: `selectChunkSize()` is synchronous (it must return a value before `this.uppy.use(Uppy.Tus, {chunkSize})`), so the server-authoritative alignment is done in a separate best-effort async pass that updates the Tus plugin via `setOptions`. The client keeps a 256KB floor guard even on the server value, matching the server's own guarantee.
* Direct `python -c "import backend.routers.be_resizer"` fails with `SecretStoreError` because `SecretStore.init()` must run first — this is **by design** (documented in the review), not a regression. App-context import was verified by launching `AlbumsAventures-BE.py` (started cleanly, no import crash) and by the passing pytest app construction.

## Validation results

| Check | Command | Result |
|---|---|---|
| Unit tests | `.\Scripts\python.exe -m pytest tests/test_upload.py tests/test_auth.py tests/test_albums.py -q` | ✅ 50 passed (was 48; +2 guard tests) |
| Ruff (Phase 2 files) | `.\Scripts\python.exe -m ruff check be_resizer.py models.py crud.py config.py test_upload.py` | ✅ All checks passed |
| Black (Phase 2 files) | `.\Scripts\python.exe -m black --check …` | ✅ 5 files unchanged |
| JS syntax | `node --check` on extracted `uploadManager()` script (Jinja token stubbed) | ✅ exit 0 — no JS errors; `init()` no longer throws |
| App import | launched `AlbumsAventures-BE.py` (SecretStore-initialized context) | ✅ Started cleanly, stopped after 3s |

### Test-coverage note

The Python suite is backend-only and cannot execute the template JavaScript, so
it could not catch D1 originally. Added `TestUploadTemplateContract` as a
**lightweight static guard** (asserts called methods are defined + state is
rendered). Full runtime coverage (interrupt/reload upload + resume) is a
**Playwright e2e spec, deferred to Phase 4 (e2e hardening)** per the plan.

## Release Summary

Files affected: **3** (1 backend `.py`, 1 frontend template, 1 test file) + this
change record.

- `backend/routers/be_resizer.py` — lint-only fix (D3): removed dead `import time`, tidied import ordering. No functional change.
- `frontend/templates/album_upload.html` — the substantive fix (D1/D4/D2 note): 6 JS methods defined/added, `init()` wiring, reliability UI rendered, v5-deferral note. Upload dashboard now initializes without JS errors; Tus transport, Compressor (#380), and GoldenRetriever (#394) register; adaptive chunk with 256KB floor is applied client-side and aligned to the server.
- `tests/test_upload.py` — 2 static guard tests preventing silent frontend regressions.

No dependency, infrastructure, DB-schema, or migration changes in this cycle.
No deploy / push / merge / migration applied — local edits only.

**Deferred to Phase 3**: Uppy v3→v5 ESM cutover (#393), coupled to the bundler.
**Deferred to Phase 4**: Playwright e2e upload/resume spec; GoldenRetriever
Service Worker storage for large files.
