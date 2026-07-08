<!-- markdownlint-disable-file -->
---
applyTo: '.copilot-tracking/changes/2026-07-08/albumsaventures-jinja-decommission-changes.md'
---
# Implementation Plan: AlbumsAventures Jinja2 Template Decommission

Author: squad `lead` role (member Beta). Autopilot run `albumsaventures-jinja-decommission`, turn 16. PLANNING ONLY — no application code modified by this document.

Grounded in: `.copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission.md` (researcher role Alpha, same run) plus direct verification of `frontend/routers/fe_router.py`, `AlbumsAventures-BE.py`, `utils/security.py`, and `backend/routers/be_album.py` performed during planning.

> DISCLAIMER: AI-assisted plan. Every step is evidence-linked but MUST be reviewed by a human engineer before execution. The three open questions in the Council Decision Points section are NOT plan assumptions — they gate execution.

## Overview

Remove the entire legacy server-rendered Jinja2 frontend tier (14 templates, 18 render routes, the `jinja2` dependency, the two-tier CDN CSP, and Jinja docs/tests) while keeping the React SPA (`/app`) and its data plane fully working — by first relocating the two SPA-facing JSON endpoints to their exact same bare URLs, then deleting the Jinja view layer.

## Confirmed Constraints (plan around these — do NOT re-decide)

| Aspect | Constraint | Consequence |
|--------|-----------|-------------|
| SPA-facing JSON | `GET /album/{album_id}/images` (fe_router L1184) + `GET /album/shared/images` (fe_router L1096) | Called by `AlbumDetailPage.tsx` L30 and `SharedAlbumPage.tsx` L72 at BARE URLs → must survive at the SAME bare paths, no client change |
| Router prefixes | `be_album.router` and `be_album.public_router` both carry `prefix="/be_album"` | Relocating INTO those routers would change URLs to `/be_album/...` and break the SPA → relocation must use a prefix-less router to preserve bare paths |
| SPA fallback | `configure_spa` binds `/app` + `/app/{path}` ONLY, registered LAST | Bare `/`, `/login`, `/album/{id}` become 404 after Jinja removal unless explicitly handled |
| Media/static | `/static`, `/images`, `/thumbnails` mounts shared with SPA | Never touch |

## Objectives

### User Requirements

* Remove ALL code related to the use of Jinja templates. — Source: user request "enlève tous le précédent code relatif à l'utilisation de template jinja".
* Do NOT break the React SPA or any endpoint the SPA still calls. — Source: research Risk 1; user task item 3 DO-NOT-TOUCH list.
* Sequence relocation of SPA-facing endpoints BEFORE deletion. — Source: user task item 1; research Preferred Approach.

### Derived Objectives

* Collapse the two-tier CSP to the single hardened SPA policy and drop the three CDN hosts + script-src `'unsafe-inline'`. — Derived from: research Category H (security win once Jinja is gone).
* Drop `jinja2` from `requirements.txt` and update the `pyproject.toml` description. — Derived from: research Category E (no remaining consumer).
* Update or remove Jinja-coupled tests so CI stays green. — Derived from: research Category G (`TestSecurityHeaders` asserts CDNs present; `test_frontend_login.py` asserts Jinja HTML).
* Update README / `frontend/spa/README.md` stack sections to mark the strangler migration complete. — Derived from: research Category I.

## Context Summary

### Project Files

* frontend/templates/ — 14 `.html` files, the entire Jinja view layer (research Category A). All deletable.
* frontend/routers/fe_router.py — Jinja binding (L8 import, L21 `Jinja2Templates`), 22 routes: 18 Jinja + 4 non-Jinja; 2 of the non-Jinja are the SPA-facing JSON endpoints.
* AlbumsAventures-BE.py — `from frontend.routers import fe_router` (L39), `app.include_router(fe_router.router)` (after `be_resizer.tus_router`), then `/static` `/thumbnails` `/images` mounts, then `configure_spa(app)` LAST.
* AlbumsAventures_BE_test.py — `fe_router` import (L19) + include (L53); `configure_spa(app)` (L61).
* frontend/spa_serving.py — SPA fallback scoped to `/app` only.
* utils/security.py — `_CDN_TAILWIND`/`_CDN_UNPKG`/`_CDN_UPPY` constants (L106-108), `_CSP_DIRECTIVES_JINJA` (L124-131 verified), `_CSP_DIRECTIVES_SPA` (hardened), middleware branch selecting by `/app` prefix.
* backend/routers/be_album.py — `router` (prefix `/be_album`, `get_current_user` dependency, L27) and `public_router` (prefix `/be_album`, L30). Relocation reference, but note the prefix constraint above.
* requirements.txt — `jinja2` direct dependency, no other app consumer.
* pyproject.toml — description string "(FastAPI + Jinja2)" (L4), doc-only.
* tests/test_auth.py — `TestSecurityHeaders` asserts CDNs + `'unsafe-inline'` present on non-`/app` (L419-426) and `/app` hardened (stays valid).
* test_frontend_login.py — asserts Jinja-rendered HTML (already likely stale: targets `/fe_router/login`).
* README.md / frontend/spa/README.md — Jinja stack description sections.

### References

* .copilot-tracking/research/2026-07-08/albumsaventures-jinja-decommission.md — full removal inventory, risks, open questions.
* frontend/spa/src/pages/AlbumDetailPage.tsx (L19-30) — SPA consumer of `/album/{id}/images`; comment confirms bare-URL contract.
* frontend/spa/src/pages/SharedAlbumPage.tsx (L49, L61, L72) — SPA consumer of `/album/shared/images` (token+PIN).
* frontend/spa/src/types/api.ts (L61-74) — `AlbumMediaPage` contract mirrors the relocated endpoint response shape.

### Standards References

* .github/instructions/python-script.instructions.md — Python authoring conventions for any new router module.

## Council Decision Points (resolve BEFORE execution — NOT plan assumptions)

These are the research open questions plus one relocation-home question surfaced during planning. Each blocks a specific phase. The plan carries a default so it stays executable if the council defers, but execution SHOULD wait for explicit answers.

### PD-1: Bare removed routes — redirect to SPA or 404?

After Jinja routes are removed, bare paths (`/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`, `/profile`, `/admin/users`, `/admin/groups`, `/album/{id}`, `/album/{id}/edit`, `/album/new`, `/album/{id}/upload`, `/album/shared`) resolve to 404 (research Risk 2 / Category F).

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Thin redirect router: bare → `/app/...` equivalents (301/302) | Preserves bookmarks + external links; adds a small compat shim to maintain path mapping (singular→plural, 2 admin pages → 1) |
| B | Return 404 for all bare paths | Cleanest removal; breaks any bookmark, external link, or email/share link pointing at a bare path |

**Recommendation**: Option A for the paths reachable from outside (see PD-2), Option B for internal-only navigational paths — but this is a council call, gated by PD-2 evidence.

**Impact if deferred**: Phase 4 (bare-path handling) cannot be finalized. Default if unanswered: implement Option A for `/reset-password` and `/album/shared` only (mandatory-safe subset), 404 for the rest.

### PD-2: External reachability of bare Jinja paths

Do password-reset emails (`backend/routers/be_auth.py` reset-email builder) and share links (`create_share_token` `share_url` in `backend/routers/be_album.py`) point at BARE Jinja paths (`/reset-password?token=`, `/album/shared?token=`)? (research Open Q2 / Risk 3.)

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | They point at bare paths → redirects for `/reset-password` and `/album/shared` are MANDATORY | Must ship a redirect shim (couples with PD-1 Option A) |
| B | They already point at `/app/...` (or are updated to) → no redirect needed | Cleaner; requires confirming/patching the email + share URL builders |

**Recommendation**: Option A unless a quick audit of the two URL builders proves the links already target `/app/...`.

**Impact if deferred**: PD-1 cannot be closed. This decision requires reading the two URL builders — a 5-minute verification the council should authorize before deletion. Default if unanswered: assume Option A (ship the two mandatory redirects).

### PD-3: SPA functional-parity gaps

Does the SPA cover 100% of the Jinja pages before deletion? Specific concerns (research Open Q3): (a) two Jinja admin pages (`admin_users.html` + `admin_groups.html`, incl. user↔group and album↔group linking) map to a single SPA `AdminPage`; (b) no SPA route observed for `/album/new` and `/album/{id}/edit` (album create/edit) — only `/app/albums/:id/upload`.

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Parity confirmed → proceed with full deletion | Fastest; risk of silently dropping a feature |
| B | Parity gap found → build the missing SPA feature FIRST (separate work item), then delete | Safe; adds scope outside this plan |

**Recommendation**: Run a parity audit (SPA AdminPage vs the two Jinja admin pages; SPA album create/edit presence) as a gate. If a gap exists, split it into a follow-on work item and hold deletion of ONLY the affected templates/routes; the rest of the decommission can still proceed.

**Impact if deferred**: Phase 3 (delete Jinja routes/templates) risks removing a feature with no SPA equivalent. Default if unanswered: block deletion of `admin_users.html`/`admin_groups.html`/`/admin/*` and `album_form.html`/`album_edit.html`/`/album/new`/`/album/{id}/edit` pending audit; proceed with all other removals.

### PD-4: Relocation home for the 2 SPA-facing endpoints (URL preservation)

`be_album.router` and `be_album.public_router` both have `prefix="/be_album"`, so adding routes there yields `/be_album/...` URLs, which the SPA does NOT call. The SPA calls bare `/album/{id}/images` and `/album/shared/images`.

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | New prefix-less router module (e.g. `backend/routers/be_media_bridge.py`) hosting the two endpoints verbatim at their bare paths | Zero SPA/client change; URLs preserved; lowest risk (RECOMMENDED) |
| B | Move into `be_album` under `/be_album/...` and repoint `AlbumDetailPage.tsx`, `SharedAlbumPage.tsx`, `types/api.ts`, and vitest | Architecturally cleaner (all album data under `be_album`), but touches SPA code + tests; contradicts "no client change" |

**Recommendation**: Option A. It satisfies the hard "SPA keeps working at the SAME URLs" constraint with no frontend edits. Option B is a valid later consolidation but is out of scope for a decommission that must not disturb the SPA.

**Impact if deferred**: Phase 2 (relocation) cannot start. Default if unanswered: Option A.

## Implementation Checklist

### [ ] Phase 1: Parity + Reachability Gate (verification only, no code)

<!-- parallelizable: true -->

Resolves PD-2 and PD-3 evidence so later phases are unblocked. Read-only; changes nothing.

* [ ] Step 1.1: Audit external URL builders for PD-2
  * Read `backend/routers/be_auth.py` reset-email builder and `backend/routers/be_album.py` `create_share_token` `share_url`. Record whether they emit bare (`/reset-password`, `/album/shared`) or `/app/...` paths.
* [ ] Step 1.2: Audit SPA parity for PD-3
  * Compare `frontend/spa/src/pages/AdminPage.tsx` against `admin_users.html` + `admin_groups.html` (user↔group, album↔group linking). Confirm/deny a SPA route for album create + edit.
* [ ] Step 1.3: Record gate outcomes
  * Write PD-2/PD-3 findings into the run's decision log; hand to council. Deletion of gap-affected templates/routes stays blocked until resolved.

### [ ] Phase 2: Relocate SPA-facing JSON endpoints (URL-preserving) — MUST precede deletion

<!-- parallelizable: false -->

Depends on PD-4. Default = Option A (new prefix-less router). No SPA/client change.

* [ ] Step 2.1: Create prefix-less bridge router
  * New file `backend/routers/be_media_bridge.py` (or equivalent): `APIRouter()` with NO prefix. Move `GET /album/{album_id}/images` and `GET /album/shared/images` verbatim, plus the helpers they need: `_get_album_media_page`, `_album_folder_info`, and constants `_PAGE_SIZE`, `_IMAGE_EXTENSIONS`, `_VIDEO_EXTENSIONS`, `_ALL_EXTENSIONS`. Preserve the httpx-to-backend behavior, auth checks (`require_auth` for the authenticated one, token+PIN for the shared one), and response shape exactly (must still satisfy `types/api.ts` `AlbumMediaPage`).
* [ ] Step 2.2: Register the bridge router in place of fe_router's slot
  * In `AlbumsAventures-BE.py`: add `app.include_router(be_media_bridge.router)` in the SAME position `fe_router` occupied (after `be_resizer.tus_router`, before mounts). In `AlbumsAventures_BE_test.py`: same registration at L53's slot. Keep `configure_spa(app)` LAST.
* [ ] Step 2.3: Validate relocation before any deletion
  * Run the two SPA smoke checks (see Validation Strategy): album-detail media pagination and shared-album media load must return 200 with the correct JSON at the bare URLs. Do NOT proceed to Phase 3 until green.

### [ ] Phase 3: Delete Jinja view layer (routes + templates + helpers)

<!-- parallelizable: false -->

Depends on Phase 2 green and PD-3 gate. If PD-3 found a gap, EXCLUDE the affected templates/routes here and split them to a follow-on item.

* [ ] Step 3.1: Remove the 18 Jinja routes from `fe_router.py`
  * Delete routes: `GET /` (L24), `GET/POST /login`, `GET /forgot-password`, `GET /reset-password`, `GET/POST /signup`, `GET /profile`, `GET /admin/users`, `GET /admin/groups`, `GET/POST /album/new`, `GET/POST /album/{album_id}/edit`, `GET/POST /album/shared` (Jinja render pair), `GET /album/{album_id}`, `GET /album/{album_id}/upload`. Remove the Jinja binding (L8 import, L21 `templates = Jinja2Templates(...)`) and Jinja-only helpers `_get_categories`, `_get_album_folder_path`, `_save_cover_image`. Do NOT delete the two endpoints already relocated in Phase 2 (they now live in the bridge router).
* [ ] Step 3.2: Decide + handle `POST /category/create` (L408) and `GET /rando` (L1250)
  * `/category/create`: if Phase 1/PD-3 audit shows the SPA AdminPage does NOT call it → delete with the Jinja tier; if it DOES → relocate to the bridge/`be_category` preserving its URL. `/rando`: static redirect to `/static/rando/...`; keep it (move into the bridge router or `spa_serving` redirect set) or drop per council — it is not Jinja-coupled.
* [ ] Step 3.3: Retire the now-empty `fe_router` wiring
  * If `fe_router.py` has no remaining routes, delete the file and remove `from frontend.routers import fe_router` + `app.include_router(fe_router.router)` from BOTH `AlbumsAventures-BE.py` (L39, include line) and `AlbumsAventures_BE_test.py` (L19, L53). If `/category/create` or `/rando` stay in `fe_router`, keep a minimal `fe_router` with only those and keep its include. Keep `configure_spa(app)` LAST either way.
* [ ] Step 3.4: Delete the 14 template files
  * Remove all of `frontend/templates/*.html` (base, index, login, signup, forgot_password, reset_password, profile, admin_users, admin_groups, album_form, album_edit, album_detail, album_upload, shared_album) — subject to the PD-3 exclusion. Remove the `frontend/templates/` directory if empty.
* [ ] Step 3.5: Validate backend imports + SPA still green
  * App must import and start with no `Jinja2Templates` reference. Re-run the two Phase 2 smoke checks — still 200.

### [ ] Phase 4: Bare-path handling

<!-- parallelizable: false -->

Depends on PD-1 + PD-2. Implements the mandatory-safe subset by default.

* [ ] Step 4.1: Implement the chosen bare-path strategy
  * Per PD-1/PD-2: add a thin redirect router (bare → `/app/...`) for at least `/reset-password?token=` → `/app/reset-password` and `/album/shared?token=` → `/app/shared/:token` (mandatory if PD-2 = Option A), and for the remaining bare paths per council. Register in the fe_router slot ordering (before mounts, before `configure_spa`). Alternatively, return 404 for paths the council marks internal-only.
* [ ] Step 4.2: Validate bare-path behavior
  * External-link paths resolve to their SPA equivalent; internal-only paths behave per council choice. `configure_spa` still LAST.

### [ ] Phase 5: Collapse CSP to single hardened policy

<!-- parallelizable: false -->

Security win; must land with the `TestSecurityHeaders` update to keep CI green.

* [ ] Step 5.1: Remove the Jinja CSP tier in `utils/security.py`
  * Delete `_CDN_TAILWIND`, `_CDN_UNPKG`, `_CDN_UPPY` (L106-108), delete `_CSP_DIRECTIVES_JINJA` (L124-131), and simplify the middleware branch so ALL non-media responses get the hardened `_CSP_DIRECTIVES_SPA` (drop the `/app` vs non-`/app` split). Leave `_CSP_SHARED`, `_CSP_DIRECTIVES_SPA` (retain its residual style-src `'unsafe-inline'` — separate deferral, NOT Jinja), and `_MEDIA_CSP` untouched.
* [ ] Step 5.2: Update `tests/test_auth.py::TestSecurityHeaders`
  * Replace the assertions that the CDNs (L419-421) and script-src `'unsafe-inline'` (L426) ARE present with assertions that they are ABSENT on all app surfaces; the `/app` hardened assertions (L436-446) become the single universal expectation.

### [ ] Phase 6: Drop `jinja2` dependency + docs

<!-- parallelizable: true -->

Independent of CSP/route files; safe to run alongside Phase 5 once Phase 3 lands.

* [ ] Step 6.1: Remove `jinja2` from `requirements.txt`
  * Delete the `jinja2` line. After removal, run a fresh `pip install -r requirements.txt` in a clean venv to confirm nothing transitively needed it.
* [ ] Step 6.2: Update `pyproject.toml` description
  * Change the "(FastAPI + Jinja2)" description (L4) to reflect the SPA-only frontend.
* [ ] Step 6.3: Update README + SPA README stack sections
  * `README.md` (Jinja/Templates/CDN lines ~L97-101, ~L286-290, L332-333) and `frontend/spa/README.md` (L4, L19, L63-65): mark the strangler migration complete; remove Jinja/CDN stack claims.
* [ ] Step 6.4: Delete or rewrite `test_frontend_login.py`
  * It asserts Jinja HTML (and targets a non-existent `/fe_router/login`). Delete it, or rewrite against the SPA login surface. Verify `run_test_login.py` has no Jinja/HTML assertions (research flagged low risk); leave `test_share_album.py` (backend-only) intact.

### [ ] Phase 7: Final Validation

<!-- parallelizable: false -->

* [ ] Step 7.1: Run full backend suite
  * `pytest` — all 61 backend tests must pass, including the updated `TestSecurityHeaders`.
* [ ] Step 7.2: Run SPA suite
  * `vitest` (in `frontend/spa/`) — all green; confirms no client contract for `/album/{id}/images` or `/album/shared/images` regressed.
* [ ] Step 7.3: SPA media smoke check
  * Load a normal album detail page in the SPA (`/app/albums/:id`) — media paginates. Load a shared album (`/app/shared/:token`, token+PIN) — media loads. Both hit the relocated bare endpoints and return 200.
* [ ] Step 7.4: Fix minor issues inline; escalate blockers
  * Iterate on lint/import fixes. If a failure needs more than a minor correction (e.g. an unexpected `jinja2` transitive consumer, or a parity gap surfacing at runtime), document it and route back to research/council rather than large-scale inline fixes.

## DO NOT TOUCH

* `/static`, `/images`, `/thumbnails` mounts in `AlbumsAventures-BE.py` (and test app) — shared with the SPA and API.
* The SPA bundle and all `frontend/spa/**` source — including `AlbumDetailPage.tsx` and `SharedAlbumPage.tsx` client URLs (they must keep calling the bare `/album/{id}/images` and `/album/shared/images`). No SPA edit is required under the recommended PD-4 Option A.
* The runtime BEHAVIOR + response shape of the two relocated endpoints (`/album/{album_id}/images`, `/album/shared/images`) — same URLs, same auth, same JSON (`AlbumMediaPage`).
* `configure_spa(app)` LAST-registration position in both app files.
* `_CSP_DIRECTIVES_SPA` hardened policy, `_CSP_SHARED`, and `_MEDIA_CSP` in `utils/security.py` (only the Jinja tier + CDN constants are removed).
* `test_share_album.py` (backend share flow), `tests/test_albums.py`, `tests/test_upload.py`, `tests/conftest.py` — no Jinja coupling.
* `apm_modules/**` — vendored HVE-Core skills; their "template" concepts are unrelated to the app's `jinja2` package.

## Validation Strategy

* Must PASS unchanged: full `pytest` backend suite (61 tests) minus the two updated below; `vitest` SPA suite; app import/startup.
* Must be UPDATED (and then pass): `tests/test_auth.py::TestSecurityHeaders` (invert CDN + `'unsafe-inline'` presence assertions → absence; single hardened policy); `test_frontend_login.py` (delete or rewrite for the SPA).
* Smoke gate (blocks progression past Phase 2 and again at Phase 7): SPA album-detail pagination via bare `/album/{id}/images` returns 200 + correct JSON; SPA shared-album load via bare `/album/shared/images` (token+PIN) returns 200 + correct JSON. If either fails, STOP — relocation is not correct.
* Post-removal dependency check: fresh `pip install` in a clean venv after dropping `jinja2` confirms no transitive breakage.

## Rollback Note

Each phase is independently revertible via git. The single highest-risk change is the Phase 2 endpoint relocation. Rollback order is reverse of application: (1) if the SPA smoke check fails after Phase 2, revert the bridge-router commit and restore `fe_router`'s two JSON routes — the SPA is immediately whole again with zero client change. (2) Because deletion (Phase 3+) is gated behind a green Phase 2, no template/route deletion is committed until the data plane is proven relocated. (3) CSP tightening (Phase 5) and `jinja2` drop (Phase 6) are isolated commits — reverting either restores the prior policy/dependency without affecting the SPA. Keep Phase 2 and Phase 3 as separate commits so a data-plane rollback never forces a re-creation of the deleted view layer.

## Dependencies

* Python 3 + FastAPI/Starlette test client for `pytest`.
* Node build-time toolchain in `frontend/spa/` for `vitest`.
* Council answers to PD-1 through PD-4 (PD-4 defaulted to Option A).

## Success Criteria

* No `Jinja2Templates` reference, no `frontend/templates/*.html`, and no `jinja2` in `requirements.txt` remain. — Traces to: user request (remove ALL Jinja code).
* SPA album-detail and shared-album media still load via the same bare URLs. — Traces to: research Risk 1 / DO-NOT-TOUCH.
* `pytest` (61) + `vitest` green with `TestSecurityHeaders` updated and `test_frontend_login.py` resolved. — Traces to: research Category G.
* Single hardened CSP applied to all app surfaces; three CDN hosts + script-src `'unsafe-inline'` gone. — Traces to: research Category H (security win).
* Bare-path behavior matches the council's PD-1/PD-2 decision; external links (reset/share) still resolve if PD-2 = Option A. — Traces to: research Risk 3 / Open Q2.
