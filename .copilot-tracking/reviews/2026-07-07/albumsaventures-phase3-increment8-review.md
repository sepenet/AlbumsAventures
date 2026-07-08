<!-- markdownlint-disable-file -->
# Review: Phase 3 Increment 8 (sub-phase 3.9 — CSP tightening + PWA handoff prep)

**Review date**: 2026-07-07
**Reviewer**: member Delta (`tester` role)
**Plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (Phase 3.9)
**Change record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment8-changes.md`
**Backfill record reviewed**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment7-changes.md`
**Scope**: FINAL Phase 3 SPA increment. Changed `utils/security.py`, `tests/test_auth.py`; 2 change records added. No code modified during review.

## Verdict

**✅ Approve-with-followups**

Two-tier CSP is correct and safe: the SPA `/app` surface is hardened to `script-src 'self'` (no CDN, no inline script, no `unsafe-eval`, no `*`); the Jinja/API fallback keeps only host-pinned CDNs genuinely still required by live templates. Neither tier contains `unsafe-eval` or a wildcard `*` — now test-enforced. No regression on either surface. All six review items PASS. Follow-ups are pre-documented deferrals gated on Jinja decommission (not review-discovered defects) plus one low-severity gap (Playwright CSP-violation check satisfied by reasoning + build inspection rather than a live run).

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 0 |
| Low      | 1 |
| Follow-Up (documented deferrals) | 3 |

## Per-item results

### 1. Two-tier CSP correct and safe — ✅ PASS

* `_CSP_DIRECTIVES_SPA` = shared base + `script-src ['self']` and `style-src ['self','unsafe-inline']`. No CDN, no `unsafe-inline` in `script-src`, no `unsafe-eval`, no `*`. Verified in [utils/security.py](utils/security.py#L152-L160).
* `_CSP_DIRECTIVES_JINJA` = shared base + host-pinned CDNs (`https://cdn.tailwindcss.com`, `https://unpkg.com`, `https://releases.transloadit.com`) + `'unsafe-inline'` in `script-src`/`style-src`. Exact https hosts, no scheme/host wildcards. Verified in [utils/security.py](utils/security.py#L144-L149).
* CDN necessity audited against live templates — all three are still referenced:
  * `cdn.tailwindcss.com` → [frontend/templates/base.html](frontend/templates/base.html#L8)
  * `unpkg.com` → [base.html](frontend/templates/base.html#L114) (Alpine) + [album_detail.html](frontend/templates/album_detail.html#L7) (PhotoSwipe/Masonry/imagesLoaded)
  * `releases.transloadit.com` → [album_upload.html](frontend/templates/album_upload.html#L10) (Uppy)
* Tier selection: `est_spa = chemin == "/app" or chemin.startswith("/app/")` routes `/app` to the tight policy, everything else to the Jinja fallback; media mounts (`/images`, `/thumbnails`) keep the sandbox `_MEDIA_CSP`. Routing is correct. Verified in [utils/security.py](utils/security.py#L215-L226).

### 2. No regression — ✅ PASS

* Representative SPA page: built `frontend/spa/dist/index.html` references only same-origin external assets `/app/assets/index-*.js` (module) and `/app/assets/index-*.css`, with **no inline `<script>` and no inline `<style>`** — satisfies the hardened SPA CSP. Verified in [frontend/spa/dist/index.html](frontend/spa/dist/index.html#L7-L8).
* Representative Jinja page (`album_detail.html`) still receives host-pinned CDNs + `'unsafe-inline'` → PhotoSwipe/Masonry/imagesLoaded and inline scripts remain allowed. Behavior unchanged.
* SPA built assets confirmed same-origin `/app/assets/*` (Vite `base:/app/`).

### 3. No `unsafe-eval` or `*` on either tier — ✅ PASS

* `test_csp_never_allows_unsafe_eval_or_wildcard` (Jinja tier via `/be_auth/me`): asserts `'unsafe-eval'` absent and no bare `*` token in any directive. [tests/test_auth.py](tests/test_auth.py#L397-L409)
* `test_jinja_csp_cdn_allowances_are_host_pinned`: asserts the three CDNs appear as exact https hosts and that `https:*` / `https://*` are absent. [tests/test_auth.py](tests/test_auth.py#L411-L427)
* `test_spa_csp_is_tightened_same_origin_only` (`/app`): asserts `script-src` is exactly `script-src 'self'`, no CDNs, no `'unsafe-eval'`, retains `worker-src 'self' blob:` + `manifest-src 'self'`, no `*` per directive. [tests/test_auth.py](tests/test_auth.py#L429-L456)
* Both tiers are therefore covered for `unsafe-eval` and `*`, and host-pinning is asserted.

### 4. Deferred items documented — ✅ PASS

* Change record "Deferred / gated on Jinja decommission" records: (a) collapse to a single tight CSP by removing CDNs + `'unsafe-inline'` from the Jinja tier, then (b) drop `style-src 'unsafe-inline'` on the SPA tier once Uppy runtime inline styles are hashed, and (c) obsolete-template removal (Step 3.9.2) folded into decommission. Plan marks Step 3.9.2 as `[~]` DEFERRED. Nothing silently dropped.

### 5. PWA handoff note — ✅ PASS

Complete "Phase 4 PWA Handoff Note" captures the full contract: `vite-plugin-pwa`; SW **bypass** of `/be_resizer/tus/*`; authenticated-API cache partitioning (network-first/no-store, never cache `be_*` JSON cross-session); hash-versioned SW with `skipWaiting: true` + `clientsClaim: true`; bounded media cache (`ExpirationPlugin` maxEntries/maxAgeSeconds/`purgeOnQuotaError`); `manifest.webmanifest` + maskable icons (192/512); and confirmation that `worker-src 'self' blob:` + `manifest-src 'self'` are already staged in CSP.

### 6. 3.8 backfill — ✅ PASS

`increment7-changes.md` now exists and documents: 4 SPA auth pages + `AuthCard` + `authApi.ts`/`authValidation.ts` (+15 unit tests) + `App.tsx` public routes; C-8 in-process `/me` in `utils/auth.py` (loopback retired, fe_router page-data loopback deferred); FU-group — 13 `be_group.py` mutation routes gated on `require_superuser` (DB-checked) + `TestGroupMutationSuperuserGate`.

## Validation command results

| Gate | Command | Result |
|------|---------|--------|
| Backend tests | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | ✅ **61 passed** (24.89s) |
| Ruff | `ruff check utils/security.py tests/test_auth.py` | ✅ All checks passed |
| Black | `black --check utils/security.py tests/test_auth.py` | ✅ 2 files unchanged |
| App import | programmatic import of `AlbumsAventures-BE.py` | ✅ clean — **108 routes** |
| SPA build | `cd frontend/spa; npm run build` | ✅ built in 4.45s, no warnings; shell = external same-origin assets only |
| SPA lint | `npm run lint` (`--max-warnings 0`) | ✅ 0 warnings |
| SPA test | `npm run test` (vitest) | ✅ **74 passed** (7 files) |

## Findings

### Low

* **L-1 (Acceptance coverage):** Acceptance 3.9 lists "No console CSP violations across all migrated pages (Playwright)". This was satisfied by manual CSP-satisfaction reasoning + built-shell inspection rather than a live Playwright run (the e2e specs skip without a running server). Confidence is high because the built shell provably contains no inline script/style and only same-origin assets, but a live e2e CSP-violation check should be run when a server is available. Non-blocking.

## Follow-Up work (documented deferrals — not review defects)

1. **FU-1:** Collapse to a single tight CSP by removing the three CDNs + `'unsafe-inline'` from the Jinja tier. Gated on Jinja decommission (strangler still active).
2. **FU-2:** Drop `style-src 'unsafe-inline'` on the SPA tier once Uppy/runtime library inline styles are hashed or eliminated. Gated on FU-1.
3. **FU-3:** Step 3.9.2 — remove obsolete Jinja templates + Alpine/CDN tags. Folded into the Jinja decommission.

## Overall Phase 3 (SPA migration) completion assessment

Increment 8 closes the final Phase 3 sub-phase. The SPA strangler is complete for the app surface: every migrated page has a same-origin, content-hashed React `/app` shell, and this increment tightens the CSP to the maximum safe reduction without breaking the still-live Jinja fallback. Security posture is materially improved — the SPA runs under `script-src 'self'` with no CDN and no inline script, and both tiers are now test-guarded against `unsafe-eval` and wildcard sources. The remaining CSP hardening (single-policy collapse, SPA `style-src` `unsafe-inline` removal, template deletion) is correctly and explicitly gated on Jinja decommission rather than forced prematurely, which is the right call for an active strangler. Phase 4 (PWA) has a clear, self-contained handoff contract. **Phase 3 is complete and in a clean, well-documented state to hand off to Phase 4.**

## Reviewer notes

No code was modified during this review. All seven validation gates reproduced the expected results (61 backend / 74 vitest; ruff+black green; 108-route import). CSP does not break the SPA or the Jinja fallback and contains no `unsafe-eval`/`*` — so the Request-changes triggers do not apply.
