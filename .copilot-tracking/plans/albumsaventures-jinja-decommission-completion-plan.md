<!-- markdownlint-disable-file -->
---
applyTo: '.copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-completion-changes.md'
---
# Implementation Plan: AlbumsAventures Jinja Decommission — FULL Completion (Option B)

## Overview

Build SPA-native album create + edit pages, close the pre-existing `be_album`/`be_category` superuser-authz gap and add a superuser-gated cover-upload endpoint, then fully decommission Jinja (delete the last 3 templates + `fe_router.py`, drop `jinja2`, collapse CSP to one hardened policy, delete `utils/csrf.py`).

## Objectives

### User Requirements

* Build SPA-native album create (`/app/album/new`) + edit (`/app/album/:id/edit`) with full field parity — Source: turn-17 user directive (Option B, FULL completion).
* FULLY decommission Jinja: remove last 2 templates + `base.html`, delete `frontend/routers/fe_router.py`, drop `jinja2`, full CSP collapse, remove `utils/csrf.py` — Source: turn-17 user directive.
* Add server-side superuser gating on `be_album` create/update/create_album_folder + `be_category.create_category` (security fix, not optional) — Source: turn-17 user directive + research Gap A.
* Add a NEW superuser-gated `POST /be_album/upload_cover/{id}` relocating `_save_cover_image` — Source: turn-17 user directive + research §3.

### Derived Objectives

* Add a `FormData`/multipart helper to `apiClient` (currently JSON-only) — Derived from: cover upload needs multipart; research §4.
* Add a DOM-free `lib/albumForm.ts` for participants/tags Web↔DB pipe transform + validation (unit-testable) — Derived from: parity behavior + repo `lib/*.ts` convention; research §1.
* Convert 2 outbound `<a href>` links to react-router `<Link>` so navigation stays in-SPA — Derived from: research §4 (`AlbumGridPage.tsx` L144, `AlbumDetailPage.tsx` L176).
* Move `GET /rando` 302 into `fe_redirects.py` and delete `POST /category/create` so `fe_router.py` can be deleted — Derived from: research §6.

## Context Summary

### Project Files

* backend/routers/be_album.py - `router = APIRouter(prefix="/be_album", dependencies=[Depends(get_current_user)])` (L26, AUTH-only). Create L112-L124, update L128-L155, create_album_folder L158-L165, get_album_by_id L101-L106. No UploadFile endpoint.
* backend/routers/be_category.py - `create_category` AUTH-only (L9, L36) — same Gap A.
* backend/routers/be_auth.py - Hosts `@require_superuser_gate` decorator (applied to `be_group` all 13 + `be_resizer.create_thumbnails`). This is the server-side RBAC pattern to reuse.
* backend/db/schemas.py - `AlbumBase` L82-L90, `AlbumCreate` L93, `AlbumUpdate` (all-optional) L123-L132, `Album_Category` L104-L109.
* frontend/routers/fe_router.py - To DELETE. `Jinja2Templates` L8/L21; create route L118-L330; edit route L336-L520; `/category/create` L45-L100; `/rando` L516-L519; helpers `_get_categories` L523, `_get_album_folder_path` L544, `_save_cover_image` L563-L620.
* frontend/routers/fe_redirects.py - Existing explicit 302-shim router (open-redirect-safe). Add `/rando` here.
* frontend/templates/ - To DELETE: `base.html`, `album_form.html`, `album_edit.html` (only 3 remaining).
* frontend/spa/src/lib/apiClient.ts - Same-origin JSON client; `api.post/patch` JSON only (L111-L133); injects `X-CSRF-Token` from cookie (L58-L83, returns `{}` when cookie absent). Add multipart helper.
* frontend/spa/src/App.tsx - React Router table; superuser routes wrap `<RequireSuperuser>` (`/admin` L92-L103); `*` → `Navigate to="/"` L128. Add 2 routes.
* frontend/spa/src/pages/AlbumGridPage.tsx - L143-L150 `<a href="/album/new">` gated on `user?.is_superuser`.
* frontend/spa/src/pages/AlbumDetailPage.tsx - L174-L181 `<a href={`/album/${album.id}/edit`}>` gated on `isSuperuser`.
* frontend/spa/src/pages/AdminPage.tsx - Reuse template: GroupsPanel `useMutation` `createGroup` L228-L230, `submitCreate` L288-L289, controlled `<form>` + `disabled={createGroup.isPending}` L341-L371.
* utils/csrf.py - To DELETE. Only importer is fe_router. Server never validates the token.
* utils/security.py - `_CDN_TAILWIND` L74, `_CDN_UNPKG` L75, `_CSP_SHARED` L83-L110, `_CSP_DIRECTIVES_JINJA` L120-L124, `_CSP_DIRECTIVES_SPA` L127-L135, `_MEDIA_CSP` L140, `_SPA_PATH_PREFIX` L79, path-branch in `SecurityHeadersMiddleware.dispatch`.
* requirements.txt - `jinja2` L16 (remove).
* AlbumsAventures-BE.py / AlbumsAventures_BE_test.py - fe_router import + `include_router(fe_router.router)` (BE.py L47/L132; test L28/L65). `configure_spa(app)` LAST.
* tests/test_auth.py - `TestSecurityHeaders`: `test_jinja_csp_cdn_allowances_are_host_pinned` L411 (invert/delete), `test_spa_csp_is_tightened_same_origin_only` L431 (keep/broaden), `test_security_headers_present_on_response` L382, `test_csp_never_allows_unsafe_eval_or_wildcard` L397.

### References

* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md - Full field-parity contract, authz gaps, cover-endpoint design, CSP collapse scope, orphan analysis (this plan's evidence base).
* .copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-changes.md - Prior SAFE PARTIAL record: 11 templates removed, media-bridge + redirect shim added, D1 test fix; DEFERRED items = exactly this increment's scope.
* .copilot-tracking/squad/decisions.md - Council Verdict 2026-07-08 jinja-decommission (Go-With-Conditions): CSP test inversion in SAME commit; open-redirect-safe redirect shim; preserve authz verbatim + regression test; separate commits for separable phases; clean-venv pip check after dropping jinja2.

### Standards References

* backend/routers/be_auth.py `@require_superuser_gate` — server-side RBAC pattern to apply to the new/edited endpoints.
* frontend/spa/src/lib/admin.ts, frontend/spa/src/lib/shared.ts — DOM-free `lib/` transform+validation convention for `albumForm.ts`.
* .github/instructions/hve-core-location.instructions.md — artifact-root resolution.

## Implementation Checklist

### [ ] Implementation Phase 1: Backend authz gating + cover endpoint + helper relocation

<!-- parallelizable: false -->

Backend-only; must land BEFORE any SPA page calls these endpoints. Independently testable via pytest.

* [ ] Step 1.1: Apply `@require_superuser_gate` to `create_album`, `update_album`, `create_album_folder` (be_album.py) and `create_category` (be_category.py)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 12-40)
* [ ] Step 1.2: Add `POST /be_album/upload_cover/{album_id}` (UploadFile, superuser-gated); relocate `_save_cover_image` + `_get_album_folder_path` from fe_router into the backend
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 42-78)
* [ ] Step 1.3: Add backend tests — 403 for non-superuser on create/update/create_album_folder/create_category/upload_cover; cover-upload happy path (superuser)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 80-104)
* [ ] Step 1.4: Validate phase — run `pytest --ignore=tests/e2e -q` (backend green, new authz+cover tests pass)

### [ ] Implementation Phase 2: SPA API client multipart helper + transform lib + create page

<!-- parallelizable: false -->

Depends on Phase 1 endpoints existing. Delivers `AlbumCreatePage.tsx`.

* [ ] Step 2.1: Add a `postForm`/`upload` multipart helper to `apiClient.ts` (FormData, `credentials: "same-origin"`, no manual `Content-Type`, still injects `X-CSRF-Token`)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 106-128)
* [ ] Step 2.2: Add `lib/albumForm.ts` — participants/tags Web(comma)↔DB(pipe) transform + field validation (DOM-free)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 130-150)
* [ ] Step 2.3: Add `AlbumCreatePage.tsx` — full field parity, inline category-create modal (create only), cover drag/drop preview, submit spinner; sequence `POST create_album/` → `GET create_album_folder/{id}` → optional `POST upload_cover/{id}` → `useNavigate("/admin")`
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 152-186)
* [ ] Step 2.4: Add vitest for `lib/albumForm.ts` (transform round-trip + validation) and `AlbumCreatePage.tsx` (render + submit sequence)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 188-206)

### [ ] Implementation Phase 3: SPA edit page + prefill

<!-- parallelizable: false -->

Reuses `lib/albumForm.ts` + multipart helper from Phase 2.

* [ ] Step 3.1: Add `AlbumEditPage.tsx` — prefill via `GET get_album_by_id/{id}` (DB-pipe → Web-comma), same field set MINUS category-create modal, current-cover preview, dir-rename warning banner (static copy); save via `PATCH update_album/{id}` + optional `POST upload_cover/{id}` → `useNavigate(`/albums/${id}`)`
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 208-240)
* [ ] Step 3.2: Add vitest for `AlbumEditPage.tsx` (prefill mapping + save sequence)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 242-256)

### [ ] Implementation Phase 4: Wire SPA routes + convert outbound links

<!-- parallelizable: false -->

Makes the two new pages reachable; must succeed BEFORE Jinja deletion (Phase 5).

* [ ] Step 4.1: Add `App.tsx` routes `/album/new` → `AlbumCreatePage` and `/album/:albumId/edit` → `AlbumEditPage`, both wrapped `<RequireAuth><RequireSuperuser>` (mirror `/admin`)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 258-278)
* [ ] Step 4.2: `AlbumGridPage.tsx` L144 `<a href="/album/new">` → `<Link to="/album/new">`; `AlbumDetailPage.tsx` L176 edit `<a>` → `<Link>`
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 280-296)
* [ ] Step 4.3: Validate phase — `vitest run` green; manual/route smoke that both pages mount behind superuser guard
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 298-310)

### [ ] Implementation Phase 5: Delete fe_router + last 3 templates + relocate /rando + delete /category/create

<!-- parallelizable: false -->

Only after Phases 1-4 prove the SPA replacements work. Separable commit (rollback boundary).

* [ ] Step 5.1: Move `GET /rando` 302 into `fe_redirects.py`; delete `POST /category/create`
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 312-330)
* [ ] Step 5.2: Delete `frontend/routers/fe_router.py`; delete `frontend/templates/base.html`, `album_form.html`, `album_edit.html` (entire `frontend/templates/`)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 332-350)
* [ ] Step 5.3: Drop fe_router import + `include_router(fe_router.router)` from `AlbumsAventures-BE.py` and `AlbumsAventures_BE_test.py`; keep `be_media_bridge` + `fe_redirects` + `configure_spa` LAST; remove orphaned `require_superuser` (utils/auth.py) only after confirming zero other importers
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 352-372)

### [ ] Implementation Phase 6: Drop jinja2 + full CSP collapse + delete utils/csrf.py

<!-- parallelizable: false -->

Separable commit (rollback boundary). CSP collapse + test inversion land in the SAME commit (council security condition).

* [ ] Step 6.1: Remove `jinja2` from `requirements.txt` L16 (pyproject.toml L4 description mention is cosmetic, optional)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 374-388)
* [ ] Step 6.2: Collapse CSP in `utils/security.py` — delete `_CDN_TAILWIND`, `_CDN_UNPKG`, `_CSP_DIRECTIVES_JINJA`, and the path-branch; single policy = current SPA policy for all non-media surfaces; keep `_MEDIA_CSP` unchanged
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 390-412)
* [ ] Step 6.3: In the SAME commit as 6.2 — invert/delete `tests/test_auth.py::TestSecurityHeaders::test_jinja_csp_cdn_allowances_are_host_pinned` (L411); keep/broaden `test_spa_csp_is_tightened_same_origin_only` (L431) to assert the hardened policy on a non-`/app` route too
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 414-434)
* [ ] Step 6.4: Delete `utils/csrf.py` (zero importers after fe_router deletion; SameSite cookie is the CSRF defense)
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 436-450)

### [ ] Implementation Phase 7: Tests + full validation + end-to-end smoke

<!-- parallelizable: false -->

* [ ] Step 7.1: Run full `pytest --ignore=tests/e2e -q` — all green (authz 403 tests, cover happy path, inverted CSP test, media-bridge regression untouched)
* [ ] Step 7.2: Run `vitest run` — all green (albumForm transforms, create page, edit page)
* [ ] Step 7.3: Clean-venv `pip install -r requirements.txt` after dropping jinja2 — confirm no `jinja2` resolves and app imports (council cost-manager condition)
* [ ] Step 7.4: End-to-end smoke — create album → folder scaffold → cover upload → edit prefill → save, verifying dir-rename behavior preserved and 403 for non-superuser
* [ ] Step 7.5: Report any blocking issue requiring new research/planning rather than large-scale inline fixes
  * Details: .copilot-tracking/details/2026-07-08/albumsaventures-jinja-decommission-completion-details.md (Lines 452-478)

## Do-Not-Touch (explicit)

* `_MEDIA_CSP` (utils/security.py L140) — sandbox policy for `/images`,`/thumbnails`; unchanged.
* Residual `style-src 'self' 'unsafe-inline'` — KEEP (runtime-injected styles, e.g. Uppy); hash/nonce is a tracked follow-up, NOT this increment.
* `/static`, `/images`, `/thumbnails` static mounts — unchanged.
* `be_media_bridge.py` endpoints + intra-router order (`/album/shared/images` BEFORE `/album/{album_id}/images`) + their authz — unchanged.
* `frontend/routers/fe_redirects.py` existing redirect shims (reset-password, share, etc.) — only ADD `/rando`; do not alter existing entries.
* `configure_spa(app)` registered LAST in both app files — unchanged.

## Council Decision Points (flag — do NOT assume)

See `.copilot-tracking/plans/logs/2026-07-08/albumsaventures-jinja-decommission-completion-log.md` PD-01, PD-02.

## Planning Log

See `.copilot-tracking/plans/logs/2026-07-08/albumsaventures-jinja-decommission-completion-log.md` for discrepancy tracking, implementation paths considered, decision points, and suggested follow-on work.

## Dependencies

* Python: FastAPI `UploadFile`/`File`, Pillow (PIL) — already present (used by resizer/thumbnails).
* Node/SPA: react-router-dom (`Link`, `useNavigate`, `useParams`), `@tanstack/react-query` (`useMutation`), vitest — already present.
* `@require_superuser_gate` decorator in be_auth.py — already present.
* Prior SAFE PARTIAL (turn 16) landed: `be_media_bridge` + `fe_redirects` exist; only 3 templates remain.

## Success Criteria

* `AlbumCreatePage.tsx` + `AlbumEditPage.tsx` reproduce every Jinja field + validation + category-create modal (create) + cover drag/drop + prefill (edit) — Traces to: research §1 parity contract; user requirement.
* Non-superuser receives 403 on `create_album`/`update_album`/`create_album_folder`/`create_category`/`upload_cover` (server-side, not SPA-guard-only) — Traces to: research Gap A; user "security fix, not optional".
* `POST /be_album/upload_cover/{id}` writes cover + thumbnail identically to the old `_save_cover_image` — Traces to: research §3 Option 3a.
* `frontend/routers/fe_router.py` + `frontend/templates/` deleted; `jinja2` has zero importers and is removed from requirements; `utils/csrf.py` deleted — Traces to: research §6, §8; user requirement.
* CSP is one hardened policy (`script-src 'self'`; `style-src 'self' 'unsafe-inline'`) for all non-media surfaces; `_MEDIA_CSP` intact; CSP test inverted in the same commit — Traces to: research §7; council security condition.
* Full `pytest` + `vitest` green; clean-venv `pip install` succeeds without jinja2; end-to-end create→folder→cover→edit smoke passes — Traces to: research success criteria; council cost-manager condition.
