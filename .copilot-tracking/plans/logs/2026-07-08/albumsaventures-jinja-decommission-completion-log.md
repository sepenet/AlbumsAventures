<!-- markdownlint-disable-file -->
# Planning Log: AlbumsAventures Jinja Decommission — FULL Completion (Option B)

## Discrepancy Log

Gaps and differences identified between research findings and the implementation plan.

### Unaddressed Research Items

* DR-01: Server-side superuser authz missing on `be_album` create/update/create_album_folder + `be_category.create_category`.
  * Source: research/2026-07-08/albumsaventures-jinja-decommission-completion.md (§2 Gap A)
  * Reason: FULLY addressed in Phase 1 Step 1.1 (this is the mandatory security fix, not a gap).
  * Impact: high — closes a pre-existing authorization regression.
* DR-02: No backend multipart cover endpoint; cover written only by fe_router `_save_cover_image`.
  * Source: research (§3)
  * Reason: Addressed in Phase 1 Step 1.2 (Option 3a — new `POST /upload_cover/{id}` relocating helper).
  * Impact: high — required for full parity + fe_router deletion.
* DR-03: fe_router leftovers `/category/create` + `/rando`.
  * Source: research (§6)
  * Reason: Addressed in Phase 5 Step 5.1 (delete /category/create, move /rando to fe_redirects).
  * Impact: medium — blocks fe_router deletion otherwise.
* DR-04: CSP still branches Jinja-vs-SPA; `_CDN_*`/`_CSP_DIRECTIVES_JINJA` live; Jinja CSP test asserts CDN presence.
  * Source: research (§7)
  * Reason: Addressed in Phase 6 Steps 6.2-6.3 (collapse + test inversion in same commit).
  * Impact: medium — security hardening + test correctness.
* DR-05: Gap B — backend `create_album` auto-links group `all_albums`; fe_router additionally linked `Tous les Albums` (divergent names).
  * Source: research (§2 Gap B)
  * Reason: NOT replicated in the SPA (see DD-01); flagged to architect via PD context. Low behavioral risk.
  * Impact: low — SPA relies on backend auto-link only.

### Plan Deviations from Research

* DD-01: SPA create page does NOT reproduce the fe_router "Tous les Albums" group link.
  * Research recommends: surface Gap B; do not replicate the redundant link unless intentional.
  * Plan implements: SPA calls only `create_album` (backend auto-links `all_albums`); the second link is dropped.
  * Rationale: avoids divergent group membership; canonical group is a decision point (not assumed). If the architect confirms both links are required, add a follow-up.
* DD-02: `apiClient` CSRF echo scaffolding is KEPT (not removed) even though the server never validates it.
  * Research recommends: removal is optional; scaffolding is harmless dead code.
  * Plan implements: keep `csrfHeader()` in the new `postForm` helper for consistency; defer removal.
  * Rationale: out of scope for decommission; removing it is a separable cleanup follow-up.

## Council Decision Points

### PD-01: Authz model for album create/edit — superuser vs owner

Research recommends applying `@require_superuser_gate` (mirroring FU-group hardening and the Jinja `require_superuser` guard). The alternative is an owner/creator model (e.g. any authenticated user may create; only the creator may edit).

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Superuser-only for create + edit (mirrors deleted Jinja guard) | Matches prior behavior exactly; simplest; may be stricter than desired for multi-contributor use |
| B | Owner/creator model (author edits own; admins edit all) | More flexible; requires ownership column + per-row checks not present today (larger scope) |

**Recommendation**: Option A — it restores the exact authz the Jinja routes enforced and closes Gap A with the minimum footprint. Option B is a product decision, not a decommission task.

**Impact if deferred**: Defaults to Option A (superuser gating shipped in Phase 1). Reversible if the product-owner later chooses ownership.

### PD-02: Cover image at create — optional vs required

Both Jinja forms treat the cover as optional. The user brief also states OPTIONAL in both.

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Cover optional at create + edit (parity with Jinja) | Exact parity; album can be created cover-less and set later |
| B | Cover required at create | Guarantees every album has a cover; diverges from Jinja + user brief |

**Recommendation**: Option A — matches the field-parity contract and the user's stated "OPTIONAL in both".

**Impact if deferred**: Defaults to Option A (optional). No regression.

## Implementation Paths Considered

### Selected: SPA-native create/edit + backend cover endpoint (Option 3a)

* Approach: Build both React pages calling `/be_album/*` directly; add a superuser-gated `POST /upload_cover/{id}` relocating `_save_cover_image`; close Gap A; then delete fe_router/templates/jinja2/csrf and collapse CSP.
* Rationale: only path that fully satisfies Option B (FULL decommission) while preserving the working cover feature and fixing the authz gap.
* Evidence: research (Technical Scenario — selected; §3 Option 3a).

### IP-01: Ship create/edit WITHOUT cover upload (Option 3b — MVP)

* Approach: Create album empty; set cover later; skip the multipart endpoint for now.
* Trade-offs: smaller SPA scope, but drops a working feature and misses full parity.
* Rejection rationale: violates Option B "FULL decommission / full parity"; still requires most of the same work.

### IP-02: Keep fe_router as a thin non-Jinja shim (retain httpx loopback)

* Approach: Strip only the Jinja render, keep the loopback create/edit proxy.
* Trade-offs: less SPA work now.
* Rejection rationale: leaves `Jinja2Templates` binding + httpx loopback, blocking the jinja2/CSP/csrf removals that are the entire point of Option B.

### IP-03: Add global CSRF-validating middleware while removing csrf.py

* Approach: Replace the double-submit helper with real server-side CSRF validation.
* Trade-offs: stronger CSRF in theory.
* Rejection rationale: no endpoint validates CSRF today; SameSite auth cookie is the established model; adding middleware diverges from the app and is out of scope.

## Rollback Notes

Structured as three separable commit boundaries so any layer can be reverted independently:

* Commit A (Phases 1) — backend authz gating + `upload_cover` endpoint + backend tests. Standalone; keeps the app fully working with Jinja still present. Revert removes only the new gating/endpoint.
* Commit B (Phases 2-4) — SPA create/edit pages + apiClient helper + routes + link conversion. Depends on Commit A. Revert restores the outbound `<a href>` links to the still-present Jinja pages (do NOT revert Commit A independently while Commit C is live).
* Commit C (Phases 5-6) — Jinja deletion (fe_router, templates, jinja2, csrf) + CSP collapse + test inversion. Depends on B being proven working. Highest-risk boundary; revert restores fe_router + templates + Jinja CSP branch. CSP collapse and its test inversion MUST stay together in this commit (council security condition).
* Ordering invariant: never land Commit C before Commit B is validated; never drop jinja2/csrf (Phase 6) before fe_router is deleted (Phase 5).

## Suggested Follow-On Work

* WI-01: Tighten residual `style-src 'unsafe-inline'` via hashes/nonces — Source: research §7 + council security follow-up. (Medium) Dependency: CSP collapse (Phase 6) landed.
* WI-02: Remove `apiClient` CSRF echo scaffolding if confirmed fully unused — Source: DD-02. (Low) Dependency: none.
* WI-03: Resolve Gap B canonical album group (`all_albums` vs `Tous les Albums`) with the architect; add second group link only if intentional — Source: DR-05/DD-01. (Low) Dependency: PD-01 answer + architect input.
* WI-04: Optional pyproject.toml L4 description-string cleanup (remove "Jinja2" mention) — Source: research §8. (Low) Dependency: none.
* WI-05: ADR for full Jinja decommission + strangler completion (closes the deferred Option B consolidation noted in the increment-1 council follow-ups) — Source: council architect follow-up. (Medium) Dependency: Phase 6 complete.
