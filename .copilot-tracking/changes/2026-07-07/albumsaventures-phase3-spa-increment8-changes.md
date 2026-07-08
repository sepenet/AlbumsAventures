<!-- markdownlint-disable-file -->
# Release Changes: Phase 3 Increment 8 (sub-phase 3.9 — CSP tightening + Phase 4 PWA handoff prep)

**Related Plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (Phase 3.9) — working plan in session memory `phase3.9-csp-plan.md`
**Implementation Date**: 2026-07-07
**Status**: LANDED (developer member Gamma). Final Phase 3 increment.

## Summary

Sub-phase 3.9 tightens the Content Security Policy **conservatively**, respecting the still-active strangler (every page has both a React `/app` version and a Jinja fallback). The single application CSP is split into two surfaces in the existing `SecurityHeadersMiddleware`:

* **SPA (`/app`)** now receives a **hardened** CSP: `script-src 'self'` — **no CDN, no `'unsafe-inline'`**. This is safe because the built SPA shell (`frontend/spa/dist/index.html`) references only external, same-origin, content-hashed assets (`/app/assets/*.js`, `/app/assets/*.css`) and contains **no inline `<script>` and no inline `<style>`**; the SPA source uses no `style={{…}}` inline styles.
* **Jinja / API (default)** keeps the **unchanged** fallback CSP (three host-pinned CDNs + `'unsafe-inline'`) because `base.html` (all Jinja pages), `album_detail.html`, and `album_upload.html` still load those CDNs and run inline scripts. Removing them now would break the Jinja fallback.

No CDN source could be removed outright — an audit confirmed all three are still referenced by live Jinja pages (table below). All CDN allowances were already host-pinned; `'unsafe-eval'` and wildcard `*` sources remain absent on both surfaces. This is enforced by new tests.

This increment also documents the **Phase 4 PWA handoff contract** (documentation only — no service worker or manifest implemented here).

## CSP Audit Table (state at 3.9)

| CDN / directive source | Used by (live surface) | Decision in 3.9 | Rationale |
|------------------------|------------------------|-----------------|-----------|
| `https://cdn.tailwindcss.com` (script/style) | Jinja `base.html` → **every** Jinja page (+ inline `tailwind.config`) | **KEPT + host-pinned** on Jinja tier; **REMOVED** from SPA tier | Still required by all Jinja fallbacks; SPA bundles Tailwind at build time (same-origin CSS). |
| `https://unpkg.com` (script/style) | Jinja `base.html` (Alpine, all pages) + `album_detail.html` (PhotoSwipe / Masonry / imagesLoaded) | **KEPT + host-pinned** on Jinja tier; **REMOVED** from SPA tier | Still required by Jinja; SPA uses a bundled custom lightbox, no PhotoSwipe/Alpine. |
| `https://releases.transloadit.com` (script/style) | Jinja `album_upload.html` (Uppy v3) | **KEPT + host-pinned** on Jinja tier; **REMOVED** from SPA tier | Still required by the Jinja upload page; SPA bundles Uppy v5 ESM same-origin (increment 3 / 3.4). |
| `'unsafe-inline'` in **script-src** | Jinja inline scripts (`base.html` Alpine store + `tailwind.config`, `album_*.html`) | **KEPT** on Jinja tier; **REMOVED** from SPA tier | SPA shell has no inline script; Jinja inline scripts would need nonces/hashes (template edits = deferred). |
| `'unsafe-inline'` in **style-src** | Jinja inline styles + runtime lib styles; SPA runtime lib inline styles (e.g. Uppy dashboard) | **KEPT** on **both** tiers | Conservative: Uppy and similar libs inject inline `style="…"` at runtime; removing it risks a visible regression. Deferred to a hash/nonce pass. |
| `'unsafe-eval'` | none | **ABSENT** (both tiers) | Never allowed; asserted by test. |
| wildcard `*` source | none | **ABSENT** (both tiers) | Never allowed; asserted by test. |
| `connect-src 'self'`, `worker-src 'self' blob:`, `manifest-src 'self'` | shared | **UNCHANGED** (both tiers) | Same-origin API/fetch; already PWA-ready for Phase 4. |
| Media mounts (`/images`, `/thumbnails`) sandbox CSP | static media | **UNCHANGED** | `default-src 'none'; sandbox` + `Content-Disposition: attachment` on scriptable files. |

**Removed now (SPA tier only):** all three CDNs and `'unsafe-inline'` in `script-src`.
**Kept and host-pinned (Jinja tier):** all three CDNs (`cdn.tailwindcss.com`, `unpkg.com`, `releases.transloadit.com`) + `'unsafe-inline'` in `script-src`/`style-src`.
**Deferred / gated on Jinja decommission (end of strangler):**
1. Remove the three CDNs and `'unsafe-inline'` from the Jinja tier → collapse to a single tight CSP.
2. Then drop `'unsafe-inline'` from `style-src` on the SPA tier once runtime library inline styles (Uppy) are hashed or eliminated.

## Changes

### Modified

* `utils/security.py`
  * Replaced the single `_CSP_DIRECTIVES` policy with a shared base (`_CSP_SHARED`) plus two policies: `_CSP_DIRECTIVES_JINJA` (fallback, host-pinned CDNs + `'unsafe-inline'`, **unchanged** behavior) and `_CSP_DIRECTIVES_SPA` (`script-src 'self'`, no CDN, no script `'unsafe-inline'`; `style-src 'self' 'unsafe-inline'`).
  * `_build_csp(directives, include_upgrade_insecure)` now takes the policy dict as a parameter.
  * `SecurityHeadersMiddleware.dispatch` selects the SPA policy when the request path is `/app` or starts with `/app/`, otherwise the Jinja policy (media mounts keep the existing sandbox CSP). Added `_SPA_PATH_PREFIX = "/app"` (defined locally to avoid an import coupling to `frontend/`).
  * Rewrote the CSP module documentation to record the two-tier design, the CDN audit, the enforced invariants (no `'unsafe-eval'`, no `*`, host-pinned CDNs), and the deferred Jinja-decommission cleanup. Removed the obsolete "EXCEPTION TODO Phase 3" single-policy note.

* `tests/test_auth.py::TestSecurityHeaders`
  * Kept `test_security_headers_present_on_response` (Jinja tier via `/be_auth/me`).
  * Added `test_csp_never_allows_unsafe_eval_or_wildcard` — asserts no `'unsafe-eval'` and no bare `*` source in any directive.
  * Added `test_jinja_csp_cdn_allowances_are_host_pinned` — asserts the three CDNs appear as exact https hosts and that no broad `https:` scheme / `https://*` wildcard is present.
  * Added `test_spa_csp_is_tightened_same_origin_only` — asserts the `/app` CSP has `script-src 'self'` (exactly), contains none of the three CDNs, no `'unsafe-eval'`, no `*`, and retains `worker-src 'self' blob:` + `manifest-src 'self'` (PWA-ready).

## Additional or Deviating Changes

* **Step 3.9.2 (remove obsolete Jinja templates) intentionally NOT done.** The plan's Step 3.9.2 ("remove the obsolete Jinja2 templates + Alpine/CDN tags") is **deferred**: the strangler is still active and every Jinja page remains a live fallback. Removing templates now would delete working pages and break the fallback contract this increment is explicitly required to preserve. This is folded into the "gated on Jinja decommission" deferral above.
* **No wholesale CDN removal.** The plan's Step 3.9.1 framing assumed all assets would be localized by 3.8; in practice the SPA localizes its own assets but the Jinja fallbacks were never migrated, so the CDNs remain required. The tightening was therefore scoped to the SPA surface — the maximum safe reduction with zero regression.
* **PWA handoff (3.9b) is documentation only** — see the note below. No `vite-plugin-pwa`, service worker, or manifest was added (that is Phase 4).

## Phase 4 PWA Handoff Note (documentation only — no implementation in this increment)

When Phase 4 adds offline/installable support, integrate **`vite-plugin-pwa`** into `frontend/spa/vite.config.ts`. The plugin generates the service worker (Workbox) and `manifest.webmanifest` from the Vite build. Hard requirements carried forward from earlier phases and the architect council:

1. **Bypass the TUS upload stack.** The service worker MUST NOT intercept or cache `/be_resizer/tus/*` (Phase 2 resumable upload endpoints). Resumable uploads rely on raw offset semantics and must reach the network untouched — add a Workbox `NavigationRoute`/`registerRoute` denylist (or `navigateFallbackDenylist`) for `/be_resizer/`.
2. **Partition authenticated API responses (architect council condition).** Authenticated JSON (`/be_auth/*`, and album/admin JSON such as `/be_album/*`, `/be_group/*`) MUST be **network-first / no-store** — never served cross-session from cache. Do not cache any response carrying user-scoped data; a logout/session change must not leak a previous user's data from the SW cache. Prefer `NetworkOnly` (or `NetworkFirst` with a 0-entry/short-TTL cache) for `be_*` JSON.
3. **Version the SW from the Vite build hash** with explicit `skipWaiting: true` + `clientsClaim: true`, so a new deploy activates deterministically (the SPA shell is already served `Cache-Control: no-store`, so the shell always re-fetches the newest hashed asset refs).
4. **Cache media with a bounded LRU + quota.** `/images`, `/thumbnails`, and `/static` are safe to cache (`CacheFirst` / `StaleWhileRevalidate`) but MUST use `ExpirationPlugin` with a `maxEntries` cap and `maxAgeSeconds`, plus `purgeOnQuotaError`, to respect device storage limits.
5. **Manifest + icon set.** Ship `manifest.webmanifest` (name, short_name, theme/background color, `display: standalone`, `start_url: /app/`, `scope: /app/`) plus a maskable icon set (192/512 px).
6. **CSP & transport already staged.** The SPA CSP already includes `worker-src 'self' blob:` and `manifest-src 'self'`, so no CSP change is needed to register the SW or load the manifest. HTTPS is a production prerequisite already staged in Phase 1 (`upgrade-insecure-requests` + HSTS in prod).

## Validation Evidence

| Gate | Command | Result |
|------|---------|--------|
| Backend tests | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **61 passed** (58 prior + 3 new CSP tests) |
| Ruff | `ruff check utils/security.py tests/test_auth.py` | All checks passed |
| Black | `black --check utils/security.py tests/test_auth.py` | unchanged |
| App import | production `AlbumsAventures-BE.py` imported programmatically | clean — **108 routes** |
| SPA build | `cd frontend/spa; npm run build` | built, no warnings; shell = external same-origin assets only |
| SPA lint | `npm run lint` (`--max-warnings 0`) | 0 warnings |
| SPA test | `npm run test` (vitest) | **74 passed** (7 files) |

## Manual CSP satisfaction reasoning (both surfaces)

* **Representative SPA page (`/app/...`)** under the hardened CSP: the shell loads `<script type="module" src="/app/assets/index-*.js">` (same-origin → `script-src 'self'` ✓) and `<link rel="stylesheet" href="/app/assets/index-*.css">` (same-origin → `style-src 'self'` ✓); runtime `fetch` to `/be_*` is same-origin (`connect-src 'self'` ✓); thumbnails/images are same-origin (`img-src 'self'` ✓). No inline script/style in the built shell → no `'unsafe-inline'` needed for scripts. **Works.**
* **Representative Jinja page (`album_detail.html`)** under the unchanged fallback CSP: Tailwind (`cdn.tailwindcss.com`), Alpine + PhotoSwipe/Masonry/imagesLoaded (`unpkg.com`), and inline scripts are all still allowed by the host-pinned CDNs + `'unsafe-inline'`. **Works** (behavior unchanged from before this increment).

## Release Summary

* **Files changed**: 2 modified (`utils/security.py`, `tests/test_auth.py`); 2 change records added (this file + the backfilled increment 7 record). No files removed.
* **Security posture**: SPA surface hardened to `script-src 'self'` (no CDN, no inline script). Jinja surface unchanged (all three CDNs still required, host-pinned). No `'unsafe-eval'`, no wildcard `*` on either surface — now test-enforced.
* **Deferred (gated on Jinja decommission)**: collapse to a single tight CSP by removing the CDNs + `'unsafe-inline'` from the Jinja tier, then drop `style-src 'unsafe-inline'` on the SPA tier. Obsolete-template removal (Step 3.9.2) is part of that decommission.
* **Phase 4**: PWA handoff contract documented; no SW/manifest implemented.
* **No deployment / push / merge / migration** performed — local edits only.
