<!-- markdownlint-disable-file -->
# Release Changes: AlbumsAventures Jinja Decommission — FULL Completion (Increment 2, Option B)

**Related Plan**: albumsaventures-jinja-decommission-completion-plan.md
**Implementation Date**: 2026-07-08
**Council Verdict**: Go-With-Conditions (`.copilot-tracking/squad/decisions.md#council-verdict-2026-07-08-jinja-decommission-completion`)
**Fixed decisions**: PD-01 superuser-only mutations; PD-02 cover optional.

## Summary

Completion of the Jinja2 decommission (Option B): close the pre-existing `be_album`/`be_category` superuser-authz gap, add a hardened superuser-gated cover-upload endpoint, build SPA-native album create/edit pages, then fully remove Jinja (templates, `fe_router.py`, `jinja2`, `utils/csrf.py`, CSP collapse). Grouped as 3 logical commit boundaries A / B / C (NOT committed — gated).

## Changes

### GROUP A — Backend authz fix + hardened cover endpoint (Commit A boundary)

#### Modified

* backend/routers/be_album.py
  * Imports: added `File`, `UploadFile`, `BytesIO`, `PILImage`, `TAGS`, `image` config, and `require_superuser` (from `.be_auth`).
  * `create_album` (POST): gated with `dependencies=[Depends(require_superuser)]`.
  * `update_album` (PATCH): gated with `dependencies=[Depends(require_superuser)]`.
  * `create_album_folder`: **converted GET → POST** + gated (state-changing; SameSite=lax does not protect GET). Idempotent via `folder.create_album_folder` `makedirs(exist_ok=True)`.
  * `export_album_json` (POST): triaged as admin/maintenance → gated `require_superuser` (comment records authority).
  * second masked `create_category` (POST, be_album): gated `require_superuser`.
  * `create_share_token` (POST): triaged as user-facing sharing → left authenticated (`get_current_user`); comment records intended authority + IDOR follow-up.
  * NEW `POST /be_album/upload_cover/{album_id}` (superuser-gated, multipart) relocating `_save_cover_image` + folder-path logic; sets `album.image_cover` in-handler (no trailing PATCH). Hardening: `os.path.basename` + reject empty/`.`/`..`; extension allowlist `.jpg/.jpeg/.png/.webp/.gif` before write; size cap (10 MB, capped read); PIL `verify()` magic-byte check; `_sanitize_path_component` on category/album folders; `os.path.commonpath` confinement assertion.
* backend/routers/be_category.py
  * Imports: added `require_superuser`.
  * `create_category` (POST): gated `require_superuser`.
* tests/test_albums.py
  * Switched existing `create_album`/`update_album` happy-path + missing-fields tests to `superuser_auth_headers` (now gated).
  * Added `TestAlbumSuperuserGating`: non-superuser 403 on create_album, update_album, create_album_folder, be_category.create_category, be_album.create_category, upload_cover; superuser create_album_folder OK (tmp paths).
  * Added `TestCoverUpload`: happy path (image + thumbnail written, image_cover persisted); **path-traversal** (`../../../evil.png` cannot escape album dir); bad-extension rejected; non-image bytes rejected. Added `_valid_png_bytes()` helper.

### GROUP A' — (folded into GROUP A above: cover endpoint + hardening + idempotency)

## Additional or Deviating Changes

* `create_album_folder` GET→POST: the SPA create page (GROUP B) will call the POST form; no other live Python caller exists (only fe_router, being deleted).
* Endpoint gating implemented via per-route `dependencies=[Depends(require_superuser)]` (not a decorator — `@require_superuser_gate` does not exist; council mandated `Depends(require_superuser)` from be_auth.py). Router-level `Depends(get_current_user)` retained.
* `export_album_json` triage → **superuser** (admin/maintenance write of album.json).
* `create_share_token` triage → **authenticated** (user-facing share; IDOR audit deferred, comment added).
* Pre-existing bug in `be_album.create_category` (`crud.create_category(db, category=schemas.CategoryCreate)` passes the class) left untouched (out of scope); the endpoint is now superuser-gated and unused by the SPA (SPA uses `be_category`).

## Validation (GROUP A)

* `pytest --ignore=tests/e2e -q`: **75 passed** (24 in test_albums.py incl. all new authz + cover tests).

## Release Summary

_Pending GROUP B and GROUP C completion._
