<!-- markdownlint-disable-file -->
# Review: AlbumsAventures Jinja Decommission (SAFE PARTIAL)

**Reviewer**: tester (Delta) — autopilot `albumsaventures-jinja-decommission`, turn 16
**Date**: 2026-07-08
**Changes Log**: `.copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-changes.md`
**Council Verdict**: `.copilot-tracking/squad/decisions.md` → `## Council Verdict 2026-07-08 jinja-decommission`
**Research**: `.copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission.md`

## Severity Counts

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 1 |
| Medium   | 0 |
| Low      | 0 |

## Council Conditions

| # | Condition | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Route order: `/album/shared/images` before `/album/{album_id}/images` | ✅ PASS | `backend/routers/be_media_bridge.py` — `shared_album_images_api` declared L~165 before `album_images_api` L~192; media-bridge tests reach the shared route (422, not 404). |
| 2 | Authz preserved verbatim (401 + cookie relay; token+6-char PIN) | ✅ PASS | `/album/{id}/images` calls `require_auth`→401 + relays `access_token` cookie; `/album/shared/images` enforces `pin` min=max=6 and validates token+PIN via backend `/shared` before serving. `tests/test_media_bridge.py` all pass. |
| 3 | Redirect shim: explicit paths, 302, static same-origin `/app/...`, carries query, `/album/new`+`/{id}/edit` still Jinja | ✅ PASS | `frontend/routers/fe_redirects.py` enumerates explicit routes, no `{full_path:path}` catch-all; `_FOUND`=302; `_with_query` preserves `?token=` on reset/login/forgot; share token `quote(token, safe='')` into fixed `/app/shared/` segment; create/edit not redirected. |
| 4 | `configure_spa(app)` LAST | ✅ PASS | `AlbumsAventures-BE.py` L148 (after all routers + mounts); `AlbumsAventures_BE_test.py` L75 (last). |
| 5 | CSP: only deleted-page CDN removed; Tailwind+unpkg kept; `_MEDIA_CSP` + `style-src 'unsafe-inline'` untouched; test inverted | ✅ PASS | `utils/security.py` `_CSP_DIRECTIVES_JINJA` keeps `_CDN_TAILWIND`+`_CDN_UNPKG`+`'unsafe-inline'`, transloadit removed; `_MEDIA_CSP` unchanged. `TestSecurityHeaders.test_jinja_csp_cdn_allowances_are_host_pinned` passes (transloadit ABSENT). |
| 6 | Deferral correctness: base/album_form/album_edit present, routes work, jinja2+csrf in place | ✅ PASS | `frontend/templates/` = `base.html`, `album_form.html`, `album_edit.html`; `/album/new` + `/album/{id}/edit` still render Jinja; `fe_router.py` still imports `utils.csrf` + `Jinja2Templates`. |
| 7 | No dangling references (no kept template extends/includes a deleted one; no code imports removed route/template) | ⚠️ FAIL | Source: clean — album_form/album_edit/base extend only `base.html`; fe_router drops `require_auth`/`Query`/`quote`; `/rando` redirects to a static file. **BUT** `tests/test_upload.py::TestUploadTemplateContract` (L183-217) still `read_text()`s the DELETED `frontend/templates/album_upload.html` → 2 test failures. |

## Test Results

Command: `Scripts\python.exe -m pytest -q -p no:cacheprovider --ignore=tests/e2e tests`

- **66 collected — 64 passed, 2 failed** (21.56s)
- New `tests/test_media_bridge.py`: 5/5 PASS (401 unauth; 422 short/long PIN; 422 missing token; bare URL resolves).
- `TestSecurityHeaders` (incl. inverted transloadit assertion): PASS.
- **Failures** (both `tests/test_upload.py::TestUploadTemplateContract`):
  - `test_called_upload_methods_are_defined` — `FileNotFoundError: frontend/templates/album_upload.html`
  - `test_reliability_state_is_rendered` — `FileNotFoundError: frontend/templates/album_upload.html`

App import/startup: `AlbumsAventures-BE.py` (prod) imports OK — 102 routes. Test app builds via conftest (64 passing tests exercise it).

SPA `vitest`: **NOT RUN** — `frontend/spa` declares `"test": "vitest run"` but deps are not installed (no `node_modules/.bin/vitest`); out of scope for this backend-only change.

## Defects

### D1 (High) — Stale template-contract test references deleted `album_upload.html`
- **Where**: `tests/test_upload.py::TestUploadTemplateContract` (L183-217), field `_TEMPLATE` L195.
- **Cause**: The change deleted `frontend/templates/album_upload.html` (correct, per plan) and removed the stale `test_frontend_login.py`, but missed this equally-stale test class that hard-reads the same deleted template. The suite is RED.
- **Fix**: Delete the `TestUploadTemplateContract` class (the Uppy upload page is decommissioned; SPA owns upload). The rest of `test_upload.py` (upload endpoint + thumbnail-security tests) is unaffected and passing.
- **Council mapping**: violates Condition 7 (no dangling references) and the "run validation, suite must be green" requirement.

## Deferred (expected — NOT defects)

Per Go-With-Conditions: `album_form.html` + `album_edit.html` and their `/album/new` / `/album/{id}/edit` routes retained; `jinja2` dependency kept; full `_CSP_DIRECTIVES_JINJA` collapse deferred; `utils/csrf.py` retained. All gated on SPA-native album create/edit shipping. Confirmed present and functional.

## Follow-Ups

1. (This change, required) Remove `TestUploadTemplateContract` from `tests/test_upload.py` to green the suite — D1.
2. (Backlog) Wire SPA `vitest` into CI once `frontend/spa` deps are installable in the pipeline.
3. (Backlog, from architect condition) ADR for the bridge seam + deferred Option B consolidation; note httpx loopback tech debt.

## Overall Status

⚠️ **CHANGES-REQUESTED** — implementation is correct against all 7 council conditions on the source side, but the validation suite is RED (2 failures) due to one missed stale test (D1). Fix is small and contained (delete one test class); re-run must be green before merge.
