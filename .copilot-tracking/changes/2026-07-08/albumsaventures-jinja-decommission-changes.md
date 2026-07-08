<!-- markdownlint-disable-file -->
# Release Changes: AlbumsAventures Jinja2 Template Decommission (SAFE PARTIAL)

**Related Plan**: albumsaventures-jinja-decommission-plan.md
**Implementation Date**: 2026-07-08
**Council Verdict**: Go-With-Conditions (SAFE PARTIAL scope)

## Summary

Partial decommission of the legacy Jinja2 view layer per the council Go-With-Conditions
verdict. Relocated the two SPA-facing JSON media endpoints to a prefix-less compatibility
bridge router (URL preservation), removed 11 page templates and their 12+ Jinja render
routes, added an explicit-path 302 redirect shim for external/bookmarked bare paths, and
surgically tightened the Jinja CSP (removed only the Uppy/transloadit CDN exclusive to the
deleted upload page). Album create/edit (`album_form.html`, `album_edit.html`) and the
`jinja2` dependency, full CSP collapse, and `utils/csrf.py` are DEFERRED because the SPA has
no native album create/edit and still links out to the two kept Jinja pages.

## Changes

### Added

* backend/routers/be_media_bridge.py - Prefix-less compatibility-seam router hosting the two SPA-facing media endpoints (`/album/shared/images` first, `/album/{album_id}/images` second) at their bare URLs, with `_album_folder_info`/`_get_album_media_page` helpers moved verbatim.
* frontend/routers/fe_redirects.py - Explicit bare-path 302 redirect shim to same-origin `/app/...` SPA routes (open-redirect-safe, no reflected next/return param).
* tests/test_media_bridge.py - Regression tests: `/album/{id}/images` returns 401 unauth; `/album/shared/images` rejects short/bad PIN.

### Modified

* frontend/routers/fe_router.py - Removed 11 Jinja render routes + moved 2 media endpoints; kept album create/edit, `/category/create`, `/rando`, and cover-image helpers; import cleanup.
* AlbumsAventures-BE.py - Registered `be_media_bridge` + `fe_redirects` in the fe_router slot; `configure_spa(app)` remains LAST.
* AlbumsAventures_BE_test.py - Same router registration as prod; `configure_spa(app)` remains LAST.
* utils/security.py - Removed the `_CDN_UPPY` (transloadit) allowance exclusive to the deleted `album_upload.html`; kept Tailwind + unpkg (Alpine/base.html).
* tests/test_auth.py - `TestSecurityHeaders.test_jinja_csp_cdn_allowances_are_host_pinned` now asserts transloadit ABSENT; Tailwind + unpkg + residual `'unsafe-inline'` still present.

### Removed

* test_frontend_login.py - Stale test asserting deleted `login.html` at a non-existent route.
* tests/test_upload.py - `TestUploadTemplateContract` class + its `_TEMPLATE` constant (D1 fix): obsolete static contract test that called `read_text()` on the deleted `album_upload.html`, causing 2 `FileNotFoundError` failures. Removed with the now-orphaned `re` and `pathlib.Path` imports (upload is SPA-only, covered by vitest).
* frontend/templates/admin_groups.html, admin_users.html, album_detail.html, album_upload.html, forgot_password.html, index.html, login.html, profile.html, reset_password.html, shared_album.html, signup.html - 11 decommissioned page templates.

## Additional or Deviating Changes

* CSP: PhotoSwipe/Masonry/imagesLoaded were served from `unpkg.com`, which base.html still needs for Alpine (kept album create/edit pages). Only the transloadit (Uppy) host was exclusive to a deleted page, so only `_CDN_UPPY` was removed. No relaxation.
* DEFERRED (per Go-With-Conditions): `album_form.html`, `album_edit.html` + their `/album/new` and `/album/{id}/edit` routes; the `jinja2` dependency; full `_CSP_DIRECTIVES_JINJA` collapse; `utils/csrf.py` removal — all gated on SPA-native album create/edit shipping.

## Release Summary

Final validation green: `pytest --ignore=tests/e2e` reports **64 passed, 0 failed** (was 64 passed / 2 failed before the D1 fix). The two removed defects were `test_called_upload_methods_are_defined` and `test_reliability_state_is_rendered` in the obsolete `TestUploadTemplateContract`, which referenced the decommissioned `frontend/templates/album_upload.html`. No remaining test references the deleted template (only comments in `tests/test_auth.py` and `tests/e2e/test_album_ui.py`). Backend suite is fully green; SPA upload coverage lives in vitest.
