<!-- markdownlint-disable-file -->
# Review Log: AlbumsAventures Jinja Decommission — FULL Completion (Increment 2, Option B)

**Review date**: 2026-07-08
**Reviewer role**: Squad `tester` (member Delta), autopilot run `albumsaventures-jinja-decommission`, turn 17
**Related plan**: `.copilot-tracking/plans/albumsaventures-jinja-decommission-completion-plan.md`
**Changes log**: `.copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-increment2-changes.md` (+ increment-1)
**Council verdict**: `.copilot-tracking/squad/decisions.md#council-verdict-2026-07-08-jinja-decommission-completion`
**Constraint**: read-only review; NOT committed/pushed.

## Severity Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 1 |
| Low      | 3 |

## Test Results

| Suite | Result |
|-------|--------|
| `pytest --ignore=tests/e2e -q` | **75 passed** (independently re-run, 29.30s) |
| `vitest run` (frontend/spa) | **103 passed / 9 files** + **2 errors** — the 2 new component specs (AlbumCreatePage, AlbumEditPage) could not load: `jsdom` declared in package.json (^25.0.1) but NOT installed in node_modules |
| App import/start (test app) | **92 routes**, `/album/new` + `/album/{album_id}/edit` + `/album/{album_id}` + `/rando` + `upload_cover` + `create_album_folder` present; `fe_router` module NOT loaded |

## Council Conditions — PASS/FAIL

### Security

**1. Authz gating on all masked mutations — PASS**
All gated via `dependencies=[Depends(require_superuser)]` (real dep, `backend/routers/be_auth.py:284`):
- `create_album` — be_album.py:117
- `update_album` — be_album.py:135
- `create_album_folder` — be_album.py:169
- `be_album.create_category` — be_album.py:342
- `be_category.create_category` — be_category.py:37
- `upload_cover` — be_album.py:231
None remain `get_current_user`-only. Authority decisions recorded: `export_album_json` gated superuser (be_album.py:180); `create_share_token` left authenticated (be_album.py:356) with IDOR follow-up comment (be_album.py:370). `TestAlbumSuperuserGating` asserts 403 for non-superuser on all six (test_albums.py:203-261).

**2. `create_album_folder` is POST — PASS**
be_album.py:169 `@router.post(...)`. SPA calls `api.postForm(.../create_album_folder/{id})` (AlbumCreatePage.tsx). No other live caller (fe_router deleted).

**3. Cover-upload hardening — PASS**
be_album.py:231-322 — `os.path.basename` + reject `""`/`.`/`..` (L~250); extension allowlist before write (L~256); size cap 10 MB via capped read (L~263); PIL `.verify()` magic-byte check before persist (L~271); `_sanitize_path_component` on category/album folders (L~278); `os.path.commonpath` confinement assertion (L~289). Traversal test `test_upload_cover_rejects_path_traversal` (test_albums.py:295-316) asserts `../../../evil.png` stored as `evil.png` confined under images root and NOT escaped; plus bad-ext + non-image tests.

**4. `utils/csrf.py` deleted + SameSite guard — PASS**
`utils/csrf.py` absent; no live importer. `assert_secure_cookie_config()` (config.py:196) requires `COOKIE_SAMESITE ∈ {lax,strict}` and `cookie_secure()` True in production, wired at startup (`AlbumsAventures-BE.py:77`). Cookie set with `secure=cookie_secure()` + `samesite=cookie_samesite()` (be_auth.py:507-508, 530-531).

**5. CSP collapse — PASS**
`utils/security.py`: single `_CSP_DIRECTIVES` with `script-src ['self']`; `_CDN_TAILWIND`/`_CDN_UNPKG`/`_CSP_DIRECTIVES_JINJA` all removed; `_MEDIA_CSP` kept unchanged; residual `style-src ['self','unsafe-inline']` kept. Test `test_csp_has_no_cdn_after_jinja_decommission` (test_auth.py:411-436) genuinely asserts ABSENCE (`assert "https://cdn.tailwindcss.com" not in csp`, unpkg, transloadit) + `script_src == "script-src 'self'"`. Passes.

### Architecture

**6. In-handler cover + no trailing PATCH + orphan handling — PASS**
`upload_cover` sets `album.image_cover` via `crud.update_album(..., AlbumUpdate(image_cover=filename))` in-handler (be_album.py:~315); create flow does NOT PATCH `update_album` after cover. Orphan: on post-create failure, `AlbumCreatePage.tsx` navigates to `/album/${outcome.albumId}/edit` with a user message (AlbumCreatePage.tsx onSuccess branch).

**7. Dangling-reference sweep — PASS (with LOW cosmetic note)**
Zero LIVE-code hits for `fe_router` / `frontend.templates` / `utils.csrf` / `from utils.auth import require_superuser` / `Jinja2Templates`. `frontend/routers/fe_router.py` + `frontend/templates/` deleted (only `fe_redirects.py` remains in frontend/routers). `configure_spa(app)` LAST in both `AlbumsAventures-BE.py:155` and `AlbumsAventures_BE_test.py:74`. `be_auth.py::require_superuser` intact and imported. Remaining matches are historical past-tense comments only (see LOW-2).

**8. jinja2 removed — PASS**
`jinja2` absent from `requirements.txt`; no live `import jinja2` / `Jinja2Templates` in source.

### Product

**9. Bare deep-link redirects — PASS**
`frontend/routers/fe_redirects.py`: `/album/new` → `/app/album/new`, `/album/{album_id}/edit` → `/app/album/{id}/edit` (302, static same-origin), both declared BEFORE `int`-typed `/album/{album_id}` so `new`/`/edit` are not shadowed; `/rando` moved here; docstring updated. Route import confirms all resolve (no 404).

**10. SPA routes guarded + link conversions + field parity — PASS**
`App.tsx`: `/album/new` and `/album/:albumId/edit` both wrapped `RequireAuth`+`RequireSuperuser` (new declared before edit). `AlbumGridPage.tsx:143` `<Link to="/album/new">`; `AlbumDetailPage.tsx:175` `<Link to={`/album/${id}/edit`}>`. Field parity present: title(req), description, category select + inline create modal, date, participants, location, tags, optional cover (AlbumCreatePage.tsx). `albumForm.ts` performs Web comma ↔ DB pipe transforms (albumForm.ts:9-10). AlbumEditPage prefills via `get_album_by_id/{id}` then `PATCH update_album/{id}` (AlbumEditPage.tsx:39,67-69).

## Defects

- **MEDIUM (environment, not code)** — `frontend/spa/node_modules` is missing `jsdom` (declared `frontend/spa/package.json:37` as `^25.0.1`). Consequently the two NEW component specs `frontend/spa/src/pages/AlbumCreatePage.test.tsx` and `AlbumEditPage.test.tsx` cannot execute (vitest reports `ERR_MODULE_NOT_FOUND: jsdom`, "no tests"). The create/edit page rendering/interaction is therefore UNVERIFIED by automated tests in this run; only the 103 logic-layer tests (incl. `albumForm.test.ts`) ran. Remedy: `npm install` (or `npm ci`) in `frontend/spa`, then re-run `vitest run`. Source + declared dep are correct.
- **LOW (cosmetic)** — Stale historical comments referencing removed modules: `backend/routers/be_media_bridge.py:12`, `frontend/routers/fe_redirects.py:25`, `frontend/spa/src/lib/apiClient.ts:10`, `frontend/spa/src/pages/AlbumDetailPage.tsx:19,29`, `frontend/spa/src/pages/AlbumGridPage.tsx:27`, `utils/config.py:180`, `AlbumsAventures-BE.py:139`. All intentional past-tense docs ("previously lived", "now that fe_router is gone"); no live refs. Optional cleanup.
- **LOW (observation)** — `AlbumDetailPage.tsx:187` uses `href={`/album/${album.id}`}` (raw anchor to a bare path). Bare paths 302-redirect to `/app/...` so harmless, but if this is an in-app nav it should be a `<Link>`; likely a share/copy-URL string — worth a glance.
- **LOW (pre-existing, out of scope)** — `be_album.create_category` passes the class `schemas.CategoryCreate` to `crud.create_category` (developer-flagged). Now superuser-gated and unused by the SPA (which calls `be_category`). Left untouched per scope.

## Overall Verdict

**APPROVE-WITH-FOLLOWUPS.** All 10 council conditions PASS on code evidence; `pytest` 75 green; app starts (92 routes) with no `fe_router`; full Jinja/csrf/CSP-CDN removal confirmed. The sole gap is a local `jsdom` install preventing the two authored create/edit component specs from running — an environment step, not a code defect. Given the no-commit constraint and correct source+deps, this is a follow-up (install jsdom, re-run vitest to green the component tests) rather than CHANGES-REQUESTED.

## Follow-ups

Gating action for this increment:
- Install `jsdom` in `frontend/spa` (`npm install`) and re-run `vitest run` to execute AlbumCreatePage/AlbumEditPage specs before merge/CI reliance.

Council non-gating follow-ups (deferred):
- Transactional `create_full` endpoint (atomic create+folder+cover).
- DRY the cover EXIF/thumbnail logic with `be_resizer`.
- ADR for the superuser-authz + create trade-off.
- `create_share_token` IDOR audit (per be_album.py:370 TODO).
- Residual `style-src 'unsafe-inline'` tightening (hash/nonce).
- CI grep gate for ungated mutations (and a lint for dangling fe_router/csrf/jinja comments).
