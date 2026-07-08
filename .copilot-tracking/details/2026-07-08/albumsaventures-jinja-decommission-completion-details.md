<!-- markdownlint-disable-file -->
# Implementation Details: AlbumsAventures Jinja Decommission — FULL Completion (Option B)

## Context Reference

Sources: .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (parity contract, authz gaps, cover endpoint, CSP collapse, orphans); .copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-changes.md (prior SAFE PARTIAL / DEFERRED scope); .copilot-tracking/squad/decisions.md (Council Verdict 2026-07-08 jinja-decommission conditions).

## Implementation Phase 1: Backend authz gating + cover endpoint + helper relocation

<!-- parallelizable: false -->

### Step 1.1: Apply server-side superuser gating

Apply the existing `@require_superuser_gate` (backend/routers/be_auth.py) to the four AUTH-only mutation endpoints. Client-side `RequireSuperuser` remains a UX gate only; the server is now authoritative.

Files:
* backend/routers/be_album.py - Add `@require_superuser_gate` to `create_album` (L112-L124), `update_album` (L128-L155), `create_album_folder` (L158-L165). Router stays `Depends(get_current_user)` (L26); the gate adds the superuser check on top.
* backend/routers/be_category.py - Add `@require_superuser_gate` to `create_category` (L9/L36).

Discrepancy references:
* Addresses DR-01 (research Gap A — CRITICAL authz regression).

Success criteria:
* Non-superuser authenticated request to any of the four endpoints returns 403.
* Superuser request continues to succeed (behavior otherwise unchanged).

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§2 Gap A) - authz evidence.
* backend/routers/be_auth.py - `@require_superuser_gate` definition + existing applications (be_group, be_resizer).

Dependencies:
* `@require_superuser_gate` exists (be_auth.py).

### Step 1.2: Add cover-upload endpoint + relocate helpers

Add `POST /be_album/upload_cover/{album_id}` accepting an `UploadFile`, superuser-gated. Move `_save_cover_image` (fe_router L563-L620) and `_get_album_folder_path` (fe_router L544) logic into the backend (be_album.py or a backend helper module). On success, PATCH `image_cover=filename` on the album row (reuse existing update path). Preserve the disk write to `images/{cat}/{date}_{title}_{participants}/{filename}` + PIL thumbnail into `thumbnails/...`.

Files:
* backend/routers/be_album.py - NEW `POST /upload_cover/{album_id}` (`UploadFile = File(...)`, `@require_superuser_gate`); relocate `_save_cover_image` + `_get_album_folder_path` (or import from a backend helper). Set `image_cover` to the stored filename.
* backend/routers/folder.py (or existing folder helper module) - OPTIONAL home for the relocated path helper if it belongs with `rename_album_folder`/`create_album_folder`; keep it backend-side regardless.

Discrepancy references:
* Addresses DR-02 (research §3 cover gap, Option 3a selected).

Success criteria:
* Uploading a cover as superuser writes the image + thumbnail to the same paths the Jinja flow used and sets `image_cover`.
* Non-superuser upload returns 403.
* No `UploadFile`/multipart handler remains in fe_router (it is deleted in Phase 5).

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§3 Option 3a) - relocation design.
* frontend/routers/fe_router.py (L544, L563-L620) - source logic for `_get_album_folder_path` + `_save_cover_image`.

Dependencies:
* Pillow (PIL) available (already used by resizer).
* Step 1.1 gating decorator in place.

### Step 1.3: Backend tests for gating + cover

Add pytest coverage. Non-superuser (authenticated) must get 403 on create/update/create_album_folder/create_category/upload_cover. Superuser cover-upload happy path writes image + thumbnail and sets `image_cover`.

Files:
* tests/test_albums.py - Add authz-403 cases for `create_album`/`update_album`/`create_album_folder` and a superuser cover-upload happy path (multipart `UploadFile`).
* tests/test_albums.py (or a category test module) - Add authz-403 case for `create_category`.

Success criteria:
* All new authz + cover tests pass; existing album/media-bridge tests remain green.

Context references:
* tests/conftest.py - fixtures for authenticated vs superuser clients (reuse existing pattern from be_group superuser tests).

Dependencies:
* Steps 1.1, 1.2 complete.

### Step 1.4: Phase validation

Validation commands:
* `Scripts\python.exe -m pytest --ignore=tests/e2e -q` - backend suite green including new tests.

## Implementation Phase 2: SPA API client multipart helper + transform lib + create page

<!-- parallelizable: false -->

### Step 2.1: Multipart helper on apiClient

Add a `postForm`/`upload` helper to apiClient.ts that sends `FormData` with `credentials: "same-origin"`, does NOT set `Content-Type` manually (browser sets the multipart boundary), and still injects `X-CSRF-Token` via the existing `csrfHeader()` for consistency. Return typed JSON like `api.post`.

Files:
* frontend/spa/src/lib/apiClient.ts - Add `postForm<T>(path, formData)` alongside `api.post/patch` (L111-L133); reuse `csrfHeader()` (L58-L83) and 401→`UnauthorizedError` handling.

Success criteria:
* `postForm` uploads FormData same-origin, injects CSRF header when cookie present, parses JSON response, throws `UnauthorizedError` on 401.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§4) - helper design.

Dependencies:
* Phase 1 `upload_cover` endpoint exists (contract to call).

### Step 2.2: Transform + validation lib

Add DOM-free `lib/albumForm.ts`: `toDbList(web: string)` = `web.split(",").map(trim).filter(Boolean).join("|")`; `toWebList(db: string)` = `db.split("|").map(trim).filter(Boolean).join(", ")`; field validators (title req/max50, category_id req, date req/ISO, participants/location/tags max512).

Files:
* frontend/spa/src/lib/albumForm.ts - NEW pure transform + validation (matches lib/admin.ts, lib/shared.ts convention).

Success criteria:
* Round-trip `toWebList(toDbList(x))` normalizes whitespace/empties; validators reject over-limit/missing-required.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§1 transforms; fe_router L438-L440 write, L468-L470 read) - exact transform rules.

Dependencies:
* None (pure module).

### Step 2.3: AlbumCreatePage

Add `AlbumCreatePage.tsx` reproducing album_form.html: fields per parity table, `date` default today, inline category-create modal (2-step name entry min3/max128 → confirm calling `POST /be_category/create_category/` then append+select the new option), cover drag/drop + FileReader preview + remove, submit spinner via `mutation.isPending`. Submit sequence: `POST /be_album/create_album/` (AlbumCreate, participants/tags via `toDbList`) → `GET /be_album/create_album_folder/{id}` → if cover chosen `postForm("/be_album/upload_cover/{id}", fd)` → `useNavigate("/admin")`. Do NOT replicate the redundant "Tous les Albums" link (Gap B — backend auto-links `all_albums`).

Files:
* frontend/spa/src/pages/AlbumCreatePage.tsx - NEW. Reuse AdminPage GroupsPanel `useMutation` + controlled-form pattern (L228-L371).

Discrepancy references:
* Deviates from DD-01 (Gap B group-name divergence — deliberately NOT replicated pending PD/architect confirm).

Success criteria:
* Every Jinja create field present with parity validation; category modal creates + selects; cover optional; success navigates to /admin.

Context references:
* frontend/templates/album_form.html (L34-L440) - source form + Alpine dynamics.
* frontend/spa/src/pages/AdminPage.tsx (L228-L371) - mutation/form template.

Dependencies:
* Steps 2.1, 2.2 complete; Phase 1 endpoints live.

### Step 2.4: Vitest for lib + create page

Files:
* frontend/spa/src/lib/albumForm.test.ts - NEW transform round-trip + validation cases.
* frontend/spa/src/pages/AlbumCreatePage.test.tsx - NEW render + submit-sequence (mock apiClient: assert create→folder→cover order + navigate).

Success criteria:
* `vitest run` green for both.

Context references:
* Existing SPA vitest patterns (AdminPage/AlbumGridPage tests) - mocking + render conventions.

Dependencies:
* Steps 2.2, 2.3 complete.

## Implementation Phase 3: SPA edit page + prefill

<!-- parallelizable: false -->

### Step 3.1: AlbumEditPage

Add `AlbumEditPage.tsx`: read `GET /be_album/get_album_by_id/{id}` (`Album_Category`), prefill fields with `toWebList` for participants/tags, mark current category selected, preview current cover via `album.image_cover_url` (new cover replaces). Same field set as create MINUS the category-create modal. Render the dir-rename warning banner as static copy. Save: `PATCH /be_album/update_album/{id}` (AlbumUpdate, `toDbList` transforms, empty→null) → if new cover `postForm("/be_album/upload_cover/{id}", fd)` → `useNavigate(`/albums/${id}`)`. The rename/dir-move behavior is preserved automatically by calling `update_album` (backend `folder.rename_album_folder`).

Files:
* frontend/spa/src/pages/AlbumEditPage.tsx - NEW. Reuse `lib/albumForm.ts` + `postForm` + AdminPage mutation pattern; `useParams` for `albumId`.

Success criteria:
* Prefill maps DB-pipe→Web-comma; save issues PATCH + optional cover; navigates to detail; no category-create modal.

Context references:
* frontend/templates/album_edit.html (L21-L340) - source form, prefill, warning banner, `participants_web`/`tags_web`.
* backend/routers/be_album.py (L128-L155) - update + rename behavior preserved by calling the endpoint.

Dependencies:
* Phase 2 (lib + helper) complete; Phase 1 endpoints live.

### Step 3.2: Vitest for edit page

Files:
* frontend/spa/src/pages/AlbumEditPage.test.tsx - NEW prefill-mapping + save-sequence (mock get_album_by_id, assert PATCH + cover order + navigate).

Success criteria:
* `vitest run` green.

Dependencies:
* Step 3.1 complete.

## Implementation Phase 4: Wire SPA routes + convert outbound links

<!-- parallelizable: false -->

### Step 4.1: App.tsx routes

Add two routes wrapped `<RequireAuth><RequireSuperuser>` (mirror `/admin` L92-L103): `path="/album/new"` → `AlbumCreatePage`; `path="/album/:albumId/edit"` → `AlbumEditPage`. Browser URLs resolve to `/app/album/new` and `/app/album/:id/edit` (basename `/app`). Confirm singular `/album/...` naming matches the outbound links + redirect shims (existing detail route is plural `/albums/:id`).

Files:
* frontend/spa/src/App.tsx - Add 2 routes before the `*` catch-all (L128); import the two new pages.

Success criteria:
* Both routes mount only for superusers; non-superuser is redirected by `RequireSuperuser`.

Context references:
* frontend/spa/src/App.tsx (L92-L103) - `/admin` guard pattern to mirror.

Dependencies:
* Phases 2, 3 pages exist.

### Step 4.2: Convert outbound links

Files:
* frontend/spa/src/pages/AlbumGridPage.tsx - L144 `<a href="/album/new">` → `<Link to="/album/new">` (keep `user?.is_superuser` gate).
* frontend/spa/src/pages/AlbumDetailPage.tsx - L176 `<a href={`/album/${album.id}/edit`}>` → `<Link to={`/album/${album.id}/edit`}>` (keep `isSuperuser` gate).

Success criteria:
* Both links navigate in-SPA (no full page reload); import `Link` from react-router-dom where missing.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§4) - exact link edits.

Dependencies:
* Step 4.1 routes exist.

### Step 4.3: Phase validation

Validation commands:
* `vitest run` - SPA suite green.
* Route smoke - both pages mount behind superuser guard; links resolve to the new routes.

## Implementation Phase 5: Delete fe_router + last 3 templates + relocate /rando + delete /category/create

<!-- parallelizable: false -->

### Step 5.1: Relocate /rando, delete /category/create

Files:
* frontend/routers/fe_redirects.py - Add explicit `GET /rando` → 302 to `/static/rando/propositions-rando.html` (static same-origin, no reflected param — open-redirect-safe per council).
* frontend/routers/fe_router.py - Remove `POST /category/create` (L45-L100); SPA calls `be_category` directly now.

Discrepancy references:
* Addresses DR-03 (research §6 leftover disposition).

Success criteria:
* `/rando` still 302s to the static file from fe_redirects; `/category/create` no longer exists.

Context references:
* frontend/routers/fe_router.py (L45-L100 category, L516-L519 rando) - source routes.

Dependencies:
* Phase 2 category-create modal calls `be_category` directly (so `/category/create` has no consumer).

### Step 5.2: Delete fe_router + templates

Files:
* frontend/routers/fe_router.py - DELETE (all remaining routes relocated/removed; `Jinja2Templates` binding gone).
* frontend/templates/base.html, album_form.html, album_edit.html - DELETE (entire frontend/templates/).

Success criteria:
* No `Jinja2Templates` importer remains; no template file remains.

Dependencies:
* Steps 5.1 complete; Phases 1-4 replacements working.

### Step 5.3: Deregister fe_router, prune orphaned require_superuser

Files:
* AlbumsAventures-BE.py - Remove fe_router import (L47) + `include_router(fe_router.router)` (L132). Keep `be_media_bridge`, `fe_redirects`, mounts, `configure_spa(app)` LAST.
* AlbumsAventures_BE_test.py - Same removal (L28/L65); `configure_spa(app)` LAST.
* utils/auth.py - Remove `require_superuser` ONLY after grep confirms zero remaining importers (backend RBAC uses `require_superuser_gate`, a different symbol — do not remove that).

Success criteria:
* App imports/boots without fe_router; router registration order preserved; no dangling import.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§6, §8) - registration + orphan analysis.

Dependencies:
* Steps 5.1, 5.2 complete.

## Implementation Phase 6: Drop jinja2 + full CSP collapse + delete utils/csrf.py

<!-- parallelizable: false -->

### Step 6.1: Remove jinja2 dependency

Files:
* requirements.txt - Remove `jinja2` (L16). pyproject.toml L4 description-string mention is cosmetic (optional cleanup).

Success criteria:
* `jinja2` has zero importers and is absent from requirements.

Dependencies:
* Phase 5 (fe_router — the only importer — deleted).

### Step 6.2: CSP collapse

Files:
* utils/security.py - Delete `_CDN_TAILWIND` (L74), `_CDN_UNPKG` (L75), `_CSP_DIRECTIVES_JINJA` (L120-L124), and the Jinja-vs-SPA path-branch in `SecurityHeadersMiddleware.dispatch`. Apply the single hardened policy (current `_CSP_DIRECTIVES_SPA`, L127-L135) to all non-media surfaces. `_SPA_PATH_PREFIX` (L79) no longer needed for branching. `_MEDIA_CSP` (L140) UNCHANGED.

Discrepancy references:
* Addresses DR-04 (research §7 CSP collapse).

Success criteria:
* Every non-media response returns `script-src 'self'`; `style-src 'self' 'unsafe-inline'` (residual, kept); no tailwind/unpkg; `_MEDIA_CSP` intact.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§7) - final policy shape.

Dependencies:
* Phase 5 (templates gone → no CDN/inline consumer).

### Step 6.3: CSP test inversion (SAME commit as 6.2)

Files:
* tests/test_auth.py - Delete or invert `TestSecurityHeaders::test_jinja_csp_cdn_allowances_are_host_pinned` (L411) — assert tailwind/unpkg ABSENT and `script-src` has NO `'unsafe-inline'` everywhere. Keep `test_spa_csp_is_tightened_same_origin_only` (L431); optionally broaden to assert the hardened `script-src 'self'` on a non-`/app` route (e.g. `/be_auth/me`). Leave `test_security_headers_present_on_response` (L382) + `test_csp_never_allows_unsafe_eval_or_wildcard` (L397) as-is.

Discrepancy references:
* Addresses DR-04; satisfies council security condition (test inversion in SAME commit as CSP collapse).

Success criteria:
* Inverted/updated CSP tests pass against the collapsed policy in one commit.

Dependencies:
* Step 6.2 in the same commit.

### Step 6.4: Delete utils/csrf.py

Files:
* utils/csrf.py - DELETE (zero importers after fe_router deletion; SameSite auth cookie is the CSRF defense; server never validated the token). SPA `csrfHeader()` returns `{}` harmlessly when the cookie is absent.

Success criteria:
* No importer of `utils.csrf` remains; SPA mutations still succeed.

Context references:
* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§5) - CSRF safety analysis.

Dependencies:
* Phase 5 (fe_router — the only importer — deleted).

## Implementation Phase 7: Tests + full validation + end-to-end smoke

<!-- parallelizable: false -->

### Step 7.1: Full backend suite

Validation commands:
* `Scripts\python.exe -m pytest --ignore=tests/e2e -q` - all green (authz 403, cover happy path, inverted CSP, media-bridge regression, existing suite).

### Step 7.2: Full SPA suite

Validation commands:
* `vitest run` - all green (albumForm, create page, edit page).

### Step 7.3: Clean-venv pip check

Validation commands:
* Fresh venv `pip install -r requirements.txt` then import the app - confirm no `jinja2` resolves and startup succeeds (council cost-manager condition).

### Step 7.4: End-to-end smoke

Manual/scripted: superuser create album → `create_album_folder` scaffold → cover upload (image+thumbnail written) → edit prefill (pipe→comma) → save (dir-rename preserved). Confirm non-superuser gets 403 on the gated endpoints.

### Step 7.5: Report blocking issues

Document any failure needing new research/planning; provide next steps rather than large-scale inline fixes.

Success criteria:
* All suites green; clean-venv install works; smoke passes; separable commits verified for rollback.

## Dependencies

* FastAPI UploadFile/File, Pillow — present.
* react-router-dom, @tanstack/react-query, vitest — present.
* `@require_superuser_gate` (be_auth.py) — present.
* Prior SAFE PARTIAL landed (`be_media_bridge`, `fe_redirects`, 3 remaining templates).

## Success Criteria

* SPA-native create+edit at parity; server-side superuser gating (403 for non-superuser); relocated cover endpoint; fe_router + templates + jinja2 + utils/csrf.py removed; single hardened CSP with `_MEDIA_CSP` intact; full pytest + vitest green + clean-venv install + end-to-end smoke.
