<!-- markdownlint-disable-file -->
# Review Record — Phase 2 (Upload Reliability)

> AI-assisted review. Findings are advisory and require human engineering review before merge/deploy. This record does not modify application code.

## Metadata

| Field | Value |
|---|---|
| Reviewer | squad `tester` role (member Delta) |
| Date | 2026-07-07 |
| Topic | AlbumsAventures modernization — Phase 2 (Upload reliability) |
| Plan | [.copilot-tracking/plans/albumsaventures-modernization.md](../../plans/albumsaventures-modernization.md) (Phase 2) |
| Council Verdict | [.copilot-tracking/squad/decisions.md](../../squad/decisions.md) — `Council Verdict 2026-07-07 albumsaventures-modernization` |
| Change record | None produced by developer — change set reconstructed from the working tree (`git diff`) |
| Overall verdict | **Request-changes** |

## Reconstructed change set (working tree)

Phase-2-relevant files reviewed via `git diff` / `git ls-files`:

- [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py) (modified, +420/-…)
- [backend/db/models.py](../../../backend/db/models.py) (modified — `ImageProcessingStatus`)
- [backend/db/crud.py](../../../backend/db/crud.py) (modified — durable-status CRUD)
- [utils/config.py](../../../utils/config.py) (modified — `max_thumbnail_workers`, `legacy_xhr_upload_enabled`)
- [frontend/templates/album_upload.html](../../../frontend/templates/album_upload.html) (modified — Uppy plugins + status wiring)
- [backend/db/migrations/0002_image_processing_status.sql](../../../backend/db/migrations/0002_image_processing_status.sql) (new)
- No changed `frontend/static/` upload JS (upload logic is inline in `album_upload.html`).

Note: `utils/security.py` (CSP), `utils/rate_limit.py`, `be_auth.py`, `csrf.py`, migration `0001` belong to **Phase 1** and were **not** modified by Phase 2.

## Severity summary

| Severity | Count |
|---|---|
| Critical | 1 |
| High | 1 |
| Medium | 1 |
| Low | 1 |

## Per-condition verdicts

### 1. Durable per-file processing status (architect UPL-01) — ✅ PASS (backend)

- Model `ImageProcessingStatus` (`album_id` FK + `filename` + `media_type` + `status` pending|processing|success|failed|skipped + `detail` + epoch `created_at`/`updated_at`, `UniqueConstraint(album_id, filename)`): [backend/db/models.py](../../../backend/db/models.py).
- Migration [backend/db/migrations/0002_image_processing_status.sql](../../../backend/db/migrations/0002_image_processing_status.sql) creates the table + unique constraint + `album_id` index; documented as a **manual production prerequisite** (no Alembic; `create_all` only in dev/tests).
- CRUD `upsert_image_processing_pending`, `set_image_processing_status`, `get_image_processing_status_by_album`, `get_image_processing_entry`: [backend/db/crud.py](../../../backend/db/crud.py).
- The `pending` row is written on the **request session** (committed immediately) **before** the thumbnail work is handed to the pool — see `_finaliser` in [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py). `_run_tus_finalize` then opens its own `SessionLocal` and transitions `processing` → `success`/`skipped`/`failed`, so a restart mid-thumbnail leaves a visible `pending`/`processing` row rather than a silently orphaned original.
- **Written AND read** on the backend: `GET /be_resizer/processing_status/{album_id}` reads the durable rows and returns a per-file list + aggregate summary. Not a write-only field.

### 2. Bounded worker pool (architect UPL-02) — ✅ PASS

- The unbounded fire-and-forget `threading.Thread(target=…, daemon=True).start()` per file is **removed** (the `import threading` is deleted) and replaced by a module-level bounded `_THUMBNAIL_POOL = ThreadPoolExecutor(max_workers=image_config.max_thumbnail_workers, …)`; the complete-hook now calls `_THUMBNAIL_POOL.submit(_run_tus_finalize, …)`: [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py).
- `image.max_thumbnail_workers` is config-driven (`THUMBNAIL_MAX_WORKERS`, floor-clamped to ≥1, default 2): [utils/config.py](../../../utils/config.py).

### 3. 256KB chunk floor preserved — ✅ PASS (server-authoritative)

- `CHUNK_SIZE_FLOOR = 256 * 1024`, `CHUNK_SIZE_CEILING = 8 MB`; `select_adaptive_chunk_size()` always returns `max(CHUNK_SIZE_FLOOR, min(taille, CHUNK_SIZE_CEILING))`, and `save_data`/`2g`/`slow-2g` pin the floor: [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py).
- `GET /be_resizer/upload_config` exposes the server-computed `chunk_size` + floor/ceiling, so the floor holds even if the client omits its own guard. The backend floor is solid. (Caveat: the **client** floor guard is not effective — see Critical defect D1.)

### 4. Uppy v3→v5 (#393) / golden-retriever (#394) / adaptive chunk / compression (#380) — ❌ FAIL / PARTIAL

- **#393 Uppy v3→v5 — FAIL (deviation).** The page still loads **Uppy v3.27.0** — [frontend/templates/album_upload.html](../../../frontend/templates/album_upload.html#L7) (CSS) and [album_upload.html](../../../frontend/templates/album_upload.html#L94) (JS). Plan 2.2 acceptance ("upload page runs on Uppy v5") is not met. Developer left no change record; per the session plan the v5 ESM cutover was consciously deferred to Phase 3 — acceptable **only if explicitly re-scoped**, but as written it does not satisfy the plan condition.
- **#394 golden-retriever — PARTIAL.** Plugin is wired defensively (`if (Uppy.GoldenRetriever) { … serviceWorker: false }`): [album_upload.html](../../../frontend/templates/album_upload.html#L279-L283). Functionally reachable only if the init path completes — currently blocked by D1.
- **#380 client compression — PARTIAL.** `Uppy.Compressor` is wired (`quality: 0.8, limit: 10`): [album_upload.html](../../../frontend/templates/album_upload.html#L272-L277). Also blocked by D1; the compression **metric** is broken (D1).
- **Adaptive client chunk sizing — FAIL.** The client is supposed to call `selectChunkSize()` (fetch `/upload_config` + apply the client floor guard): [album_upload.html](../../../frontend/templates/album_upload.html#L209). The method is **never defined** — see Critical defect D1.
- **CSP — ✅ PASS, no regression.** Phase 2 did **not** modify [utils/security.py](../../../utils/security.py). `script-src`/`style-src` already include `https://releases.transloadit.com` (`_CDN_UPPY`) for both Uppy v3 and v5; `worker-src 'self' blob:`, `img-src 'self' data: blob:`, `connect-src 'self'` cover the Compressor blob/worker and same-origin TUS + `/upload_config` + `/processing_status`. **No `unsafe-eval`, no wildcard `*`** (the policy was explicitly tightened away from `*`). No CSP hole re-opened.

### 5. Legacy XHR path retired as default (#395, UPL-06) — ✅ PASS

- `POST /be_resizer/upload_images/{album_id}` is gated on `app_config.legacy_xhr_upload_enabled()` and returns **410 Gone** when disabled; docstring marked `[DÉPRÉCIÉ — repli]`: [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py).
- Kept only as an explicit, config-gated fallback (`LEGACY_XHR_UPLOAD`, default `true` for compatibility; intended `false` in prod): [utils/config.py](../../../utils/config.py). The default production upload path is TUS. Matches UPL-06 (retire-as-default, keep documented fallback).

### 6. User-facing processing/reliability status surfaced — ❌ FAIL (client side)

- Backend surfaces the durable status correctly (see Condition 1). **But the frontend never consumes it.** The success handler calls `self.startProcessingStatusPolling()` ([album_upload.html](../../../frontend/templates/album_upload.html#L284)) which is **undefined** (D1), and the `processingFiles` / `processingSummary` / `metrics` state fields ([album_upload.html](../../../frontend/templates/album_upload.html#L102-L112)) are **never rendered** anywhere in the template. End-to-end, the user still cannot see per-file thumbnail success/failure or the reliability metric — the product-owner "reliability success metric" condition is not delivered on the client.

## Defects

### D1 (Critical) — Three upload-page methods are called but never defined → upload page is broken

`frontend/templates/album_upload.html` references three methods on the `uploadManager()` object that do **not exist** anywhere in the returned object (state fields + only `init()` and `regenerateThumbnails()` are defined):

- `self.selectChunkSize()` — [album_upload.html](../../../frontend/templates/album_upload.html#L209), **inside `init()`**.
- `self.computeCompressionMetric(result.successful)` — [album_upload.html](../../../frontend/templates/album_upload.html#L253).
- `self.startProcessingStatusPolling()` — [album_upload.html](../../../frontend/templates/album_upload.html#L284).

Because `selectChunkSize()` is invoked during `init()` (before `this.uppy.use(Uppy.Tus, …)`), Alpine's `x-data="uploadManager()"` initialization throws `TypeError: self.selectChunkSize is not a function` on page load. Consequences:

- `Uppy.Tus`, `Uppy.Compressor`, and `Uppy.GoldenRetriever` are **never registered**, and the `complete`/`error` handlers are never attached.
- The upload dashboard renders (Dashboard is `use()`'d before the throw) but has **no transport** — Phase 2's entire upload flow (resume #394, compression #380, adaptive chunk, status polling) is non-functional.

This is not caught by the Python test suite because those tests do not execute the template JavaScript (see Validation below). Fix: implement the three methods (client adaptive-chunk fetch of `/upload_config` with a `Math.max(floor, …)` guard; compression-savings metric; `/processing_status/{album_id}` polling that populates `processingFiles`/`processingSummary`), and add the status/metric markup to render them.

### D2 (High) — Uppy still on v3.27.0; #393 not delivered

Plan 2.2 requires Uppy v5. The template still loads v3.27.0 assets. Either complete the v5 cutover in Phase 2 or obtain an explicit council/plan re-scope moving #393 to Phase 3 and record it. Evidence: [album_upload.html](../../../frontend/templates/album_upload.html#L7), [album_upload.html](../../../frontend/templates/album_upload.html#L94).

### D3 (Medium) — `ruff check` fails on a Phase 2 file

`ruff check backend/routers/be_resizer.py` reports 2 errors (Phase 2 validation requires ruff clean):

- `F401` — `import time` is unused: [backend/routers/be_resizer.py](../../../backend/routers/be_resizer.py#L4).
- `I001` — import block un-sorted/un-formatted.

Both auto-fixable (`ruff check --fix`). Not out-of-scope `.agents/skills/**` findings. `black --check` passes on all Phase 2 files.

### D4 (Low) — Declared-but-unrendered client state

`processingFiles`, `processingSummary`, `metrics`, `statusPollTimer`, `statusPollCount`, `originalSizes` are declared but not surfaced in any template markup: [album_upload.html](../../../frontend/templates/album_upload.html#L102-L112). Subsumed by D1's fix, but flagged so the fix includes the UI render, not just the JS methods.

## Validation results

| Check | Command | Result |
|---|---|---|
| Unit tests | `.\Scripts\python.exe -m pytest tests/test_upload.py tests/test_auth.py tests/test_albums.py -q` | ✅ 48 passed |
| App import | app-context import via pytest app construction + running `AlbumsAventures-BE.py` (exit 0) | ✅ Clean (modules import within the SecretStore-initialized app; a naive direct `import` fails only because `SecretStore.init()` must run first — by design, not a defect) |
| Ruff (Phase 2 files) | `.\Scripts\python.exe -m ruff check be_resizer.py models.py crud.py config.py test_upload.py` | ❌ 2 errors in `be_resizer.py` (see D3) |
| Black (Phase 2 files) | `.\Scripts\python.exe -m black --check …` | ✅ 5 files unchanged |

**Test-coverage gap:** the suite is backend-only and cannot detect D1 (the broken template JS). The Phase 2 plan calls for a Playwright e2e interrupt/reload upload spec — it was not added, so the frontend break slipped past green tests.

## Missing work / deviations

- Client-side `selectChunkSize`, `computeCompressionMetric`, `startProcessingStatusPolling` implementations + status/metric UI (D1, D4).
- Uppy v5 upgrade #393 (D2) or an explicit re-scope decision.
- Ruff cleanliness on `be_resizer.py` (D3).
- No developer change record was produced (`.copilot-tracking/changes/2026-07-07/albumsaventures-phase2-uploads-changes.md` is absent).
- Plan 2.7 (proxy/TUS timeout + body-size config doc) not evidenced in this change set — verify separately if in Phase 2 scope.
- No Playwright e2e for upload resume (plan Phase 2 validation).

## Follow-ups

Deferred-from-scope (acceptable if re-scoped):

- Uppy v5 ESM cutover coupled to the Phase 3 bundler (developer's stated rationale for D2).
- Golden-retriever Service Worker storage for large files (Phase 4).

Discovered-during-review (should be fixed this cycle):

- D1 (Critical), D3 (Medium), D4 (Low) — required to make Phase 2 actually functional and pass its own validation gate.
- Add the backend-authored durable status to a rendered UI element.
- Add the Playwright upload/resume e2e to prevent silent frontend regressions.

## Overall verdict

**🚫 Request-changes.**

The backend half of Phase 2 is well-built and satisfies UPL-01 (durable status, written and read), UPL-02 (bounded pool), the 256KB server-authoritative floor, and UPL-06 (legacy XHR retired as default). **No CSP regression** was introduced (no `unsafe-eval`, no `*`, Uppy origin already permitted). However, the frontend is **broken**: three methods are called but never defined, and the one on the `init()` path throws on page load, disabling the entire upload dashboard — so the user-facing status (Condition 6), client adaptive chunking, compression metric, resume, and compression are not actually delivered end-to-end. Combined with #393 not done (D2) and a failing `ruff` gate on a Phase 2 file (D3), Phase 2 must return to the developer for a fix cycle.

---

## Re-validation (cycle 1)

> Re-validated by squad `tester` role (member Delta) against the working tree and the developer change record [.copilot-tracking/changes/2026-07-07/albumsaventures-phase2-uploads-changes.md](../../changes/2026-07-07/albumsaventures-phase2-uploads-changes.md) after developer (member Gamma) fix cycle 1. This record does not modify application code.

### Defect closure

| Defect | Prior severity | Re-validation status | Evidence |
|---|---|---|---|
| **D1** — 3 upload methods called but never defined; `selectChunkSize()` threw in `init()` | Critical | ✅ **Resolved** | All six methods now defined in [frontend/templates/album_upload.html](../../../frontend/templates/album_upload.html): `selectChunkSize()` (L399), `refineChunkSizeFromServer()` (L424), `computeCompressionMetric()` (L450), `startProcessingStatusPolling()` (L468) + `stopProcessingStatusPolling()` (L505), `formatBytes()` (L513). Every `self.<m>()` call site now resolves. `init()` calls only defined methods (`selectChunkSize()` @L269, `refineChunkSizeFromServer()` @L332); the `complete` handler calls the defined `computeCompressionMetric()` / `startProcessingStatusPolling()`. `node --check` on the extracted script exits **0** (no throw), so `Uppy.Tus` / `Uppy.Compressor` / `Uppy.GoldenRetriever` now register. Client reads the durable backend status via `GET /be_resizer/processing_status/{albumId}` and the server-authoritative chunk via `GET /be_resizer/upload_config`. 256KB floor honored in **both** `selectChunkSize()` (`Math.max(FLOOR, min(taille, CEILING))`) and `refineChunkSizeFromServer()` (`Math.max(FLOOR, cfg.chunk_size)`). |
| **D4** — reliability state declared but never rendered | Low | ✅ **Resolved** | Template now renders the compression metric (`metrics.compressedSavedBytes` block, L69-83), the aggregate `processingSummary` counters, and the per-file `processingFiles` status list (L86-119). Data is surfaced to the user, not just declared. |
| **D3** — `ruff` fails on `be_resizer.py` (F401 unused `import time`; I001 order) | Medium | ✅ **Resolved** | `import time` removed (`Select-String '^import time'` → not present); `import logging` consolidated into the top stdlib group. `ruff check` on all 5 Phase 2 files → **All checks passed**. |
| **D2** — Uppy still v3.27.0; #393 not delivered | High | ✅ **Accepted deferral (Phase 3)** | Deferral is now **explicitly recorded** — change-record "D2 deferral decision" section (rationale + acceptance) and an in-template note at the Uppy CDN links ([album_upload.html](../../../frontend/templates/album_upload.html#L7-L10)). CSP forward-allowance verified: `_CDN_UPPY = "https://releases.transloadit.com"` is documented for **v3 and v5** and present in `script-src` + `style-src` ([utils/security.py](../../../utils/security.py#L86-L94)); no CSP change is required when v5 lands. **Engineering judgment: reasonable.** Uppy v5 is ESM-only — the UMD combined bundle exposing the global `Uppy` plus the `Uppy.GoldenRetriever` / `Uppy.Compressor` namespaces is removed — so the bump is bundler-first and genuinely couples to the Phase 3 build system, while every Phase 2 reliability behavior (adaptive chunk w/ 256KB floor, GoldenRetriever resume #394, Compressor #380, durable status polling) is fully deliverable on the v3.27 bundle and is delivered here. Deferring a major ESM-only upgrade to the frontend-build phase is sound. |

### Guard-test assessment (D1 regression protection)

`tests/test_upload.py::TestUploadTemplateContract` ([tests/test_upload.py](../../../tests/test_upload.py#L183)) — **meaningful** against the exact D1 regression:

- `test_called_upload_methods_are_defined` asserts, for each of `selectChunkSize` / `computeCompressionMetric` / `startProcessingStatusPolling`, that both a `self.<m>(` call **and** a line-anchored `<m>(` definition exist. The definition regex `\n\s*<name>\s*\(` cannot be satisfied by a `self.<name>(` call site (the `.` breaks the leading-whitespace match) or by a `// <name>(` comment, so it does not self-satisfy — a removed/renamed definition fails the test. This is exactly the "called-but-undefined" failure mode of D1.
- `test_reliability_state_is_rendered` guards D4 (asserts `metrics.compressedSavedBytes` + `processingSummary` + `processingFiles` appear in the rendered markup).
- **Coverage gap (non-blocking):** the guard is static and covers only the three originally-broken methods — it would not catch a *new* undefined helper on the `init()` path (e.g. `refineChunkSizeFromServer`), nor runtime/signature errors. Full runtime interrupt/reload/resume coverage is a Playwright e2e spec appropriately deferred to Phase 4.

### Validation results (re-run)

| Check | Command | Result |
|---|---|---|
| Unit tests | `.\Scripts\python.exe -m pytest tests/test_upload.py tests/test_auth.py tests/test_albums.py -q` | ✅ **50 passed** (was 48; +2 guard tests) |
| Ruff (Phase 2 files) | `.\Scripts\python.exe -m ruff check be_resizer.py models.py crud.py config.py test_upload.py` | ✅ All checks passed |
| Black (Phase 2 files) | `.\Scripts\python.exe -m black --check …` | ✅ 5 files unchanged |
| JS syntax | `node --check` on extracted `uploadManager()` (Jinja token stubbed) | ✅ exit 0 — `init()` no longer throws |
| App import | pytest app construction (50 passed) + prior `AlbumsAventures-BE.py` run (exit 0) | ✅ Clean in SecretStore-initialized context |
| CSP regression | `utils/security.py` unchanged by Phase 2 (Phase 1 file) | ✅ **No regression** — no `unsafe-eval`, no `*`; `worker-src 'self' blob:`, `connect-src 'self'`, Uppy origin allowed for v3+v5 |

### Residual items (non-blocking)

- **Playwright e2e** for real interrupt/resume/status coverage — accepted **Phase 4** follow-up.
- **Uppy v3→v5 (#393)** ESM cutover — accepted **Phase 3** follow-on (coupled to bundler; CSP already forward-allows v5).
- Guard-test static-coverage gap for helper methods on the `init()` path — subsumed by the Phase 4 Playwright spec.

### Final verdict

**✅ Approve-with-followups.** All four review defects (D1 Critical, D2 High, D3 Medium, D4 Low) are resolved or carry an explicit, well-reasoned acceptance. The upload dashboard now initializes without JS errors; Tus transport, client compression (#380), and GoldenRetriever resume (#394) register; adaptive chunking honors the 256KB floor and aligns to the server-authoritative value; the durable per-file processing status and compression metric are read from the backend and rendered to the user. Lint/format gates are green, the full suite (50) passes, and there is **no CSP regression**. The remaining items (Playwright e2e → Phase 4; Uppy v5 ESM cutover → Phase 3) are appropriate follow-ups, not blockers.
