<!-- markdownlint-disable-file -->
# Review: Phase 3 Increment 4 — Profile Page (3.5) + Uppy Code-Split (FU-1)

**Reviewer**: `tester` role (member Delta), squad autopilot — Review stage
**Date**: 2026-07-07
**Related Plan**: `.copilot-tracking/plans/albumsaventures-phase3-spa.md` (sub-phase 3.5; FU-1)
**Change Record**: `.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment4-changes.md`
**Verdict**: ✅ **Approve**

## Summary

| Metric | Count |
|--------|-------|
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 0 |
| Low findings | 1 (advisory, pre-existing, out of increment scope) |
| Follow-up items | 1 carried forward (FU-2, unchanged) |

All seven review items PASS. All five validation gates are green. The increment is SPA-only, backend untouched, no CSP/CORS change. FU-1 code-split is verified real against a production build. Recommended: land increment 4; proceed to sub-phase 3.6 (Admin).

## Validation Gate Results (re-run by reviewer)

| Gate | Command | Result |
|------|---------|--------|
| Vite build | `cd frontend/spa; npm run build` | ✅ PASS — `tsc --noEmit` clean; 325 modules; `index-*.js` **238.37 kB** (gzip 74.25), `UploadPage-*.js` **295.75 kB** (gzip 90.25) as a SEPARATE chunk; `index-*.css` 21.25 kB, `UploadPage-*.css` 66.22 kB; **no > 500 kB warning emitted** |
| Lint | `npm run lint` (eslint `--max-warnings 0`) | ✅ PASS — 0 warnings |
| Unit/component | `npm run test` (vitest run) | ✅ PASS — **35/35** (apiClient 4, profileValidation 9, format 8, upload 14) |
| Backend suite | `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | ✅ PASS — **50 passed** in 15.59s |
| App import | `import AlbumsAventures-BE` | ✅ PASS — **108 routes**, SPA mounts registered |

Dev-claimed figures (main 524→238 kB, upload chunk 295 kB, warning cleared, 35/35, 50 passed, 108 routes) reproduced exactly.

## Per-Item Findings

### 1. Profile page — PASS

Evidence: [frontend/spa/src/pages/ProfilePage.tsx](frontend/spa/src/pages/ProfilePage.tsx)
* **Prefill from cookie session**: `useSession()` (GET `/be_auth/me`) feeds a `useEffect` that seeds `firstname`/`lastname`/`email` once the session resolves ([ProfilePage.tsx L45-L66](frontend/spa/src/pages/ProfilePage.tsx#L45-L66)). TypeScript strict build passes, so `useSession` data exposes those fields.
* **Two forms**: "Informations personnelles" (profile update) and "Changer le mot de passe" (password change) sections both render.
* **Client-side password-mismatch validation**: `validatePasswordForm` sets `confirm_password: "Les mots de passe ne correspondent pas"` when `new_password !== confirm_password` ([profileValidation.ts L73-L83](frontend/spa/src/lib/profileValidation.ts#L73-L83)); the page blocks the mutation unless `isValid(errors)` ([ProfilePage.tsx L95-L102](frontend/spa/src/pages/ProfilePage.tsx#L95-L102)); the mismatch case is unit-tested ([profileValidation.test.ts L46-L50](frontend/spa/src/lib/profileValidation.test.ts#L46-L50)) and e2e smoke-tested ([tests/e2e/test_spa_profile_ui.py L47-L58](tests/e2e/test_spa_profile_ui.py#L47-L58)).
* **Loading/error/success states**: profile form shows a `role="status"` success banner on `isSuccess`, a `role="alert"` error banner from `ApiError.message`, and disables the submit button on `isPending`; password form clears on success via `onSuccess`. All present for both forms.
* **Deep-linkable `/app/profile`**: route registered in [App.tsx L72-L84](frontend/spa/src/App.tsx#L72-L84); e2e `test_profile_deeplink_refresh_serves_shell` exercises a refresh.

### 2. CSRF on mutations / cookie-only auth — PASS

Evidence: [frontend/spa/src/lib/apiClient.ts](frontend/spa/src/lib/apiClient.ts)
* New `put<T>` method added ([apiClient.ts L120-L124](frontend/spa/src/lib/apiClient.ts#L120-L124)) routing through the shared `request()`.
* `request()` includes `PUT` in `MUTATING_METHODS` and, for mutating verbs, injects `X-CSRF-Token` read from the JS-readable `csrf_token` cookie via `parseCsrfToken(document.cookie)` ([apiClient.ts L20, L62-L83](frontend/spa/src/lib/apiClient.ts#L62-L83)).
* `credentials: "same-origin"` on every request; **no `localStorage`/`sessionStorage` token** anywhere in apiClient. The only `localStorage` use in the SPA is the dark-mode preference in [Layout.tsx L9-L20](frontend/spa/src/components/Layout.tsx#L9-L20) — not an auth token.
* Backend endpoints exist as `PUT` (`/be_auth/update_password` L523, `/be_auth/update_profile` L549 in `backend/routers/be_auth.py`) — client verb matches server contract; server re-validates.

### 3. FU-1 code-split verified real — PASS

Evidence: production build output + import graph
* `UploadPage` is `React.lazy(() => import("./pages/UploadPage")…)` rendered inside `<Suspense fallback={<UploadFallback />}>` ([App.tsx L16-L18, L57-L67](frontend/spa/src/App.tsx#L57-L67)).
* **Sole `@uppy/*` importers** are `hooks/useUploader.ts` and `pages/UploadPage.tsx` (grep across `frontend/spa/src/**`: 11 matches, all in those two files or the App.tsx comment). Both are reachable only through the lazy import, so Rollup emits them as the separate `UploadPage-*` chunk — confirmed present in the build manifest (`UploadPage-BEL3cvQU.js` 295.75 kB, `UploadPage-Cq0uhHax.css` 66.22 kB).
* Initial JS dropped 524.47 → 238.37 kB (~54.5%); the > 500 kB warning is gone. **The split is real, not cosmetic.**
* **Phase 2 behavior intact**: `UploadPage.tsx`/`useUploader.ts` are unchanged apart from being reached via a dynamic import; the route `/albums/:albumId/upload` still renders the same component behind `RequireAuth` + `Layout`. No regression introduced by lazy-loading (upload chunk fetched on navigation; `Suspense` fallback covers the load). Full interactive upload flow remains a smoke-level e2e gap (FU-2, deferred).

### 4. Strangler (Jinja profile still works) — PASS

Evidence: [frontend/routers/fe_router.py L336-L364](frontend/routers/fe_router.py#L336-L364) — the Jinja `GET /profile` route (`profile_page`, renders `profile.html`) is untouched and still live. The React page is additive at `/app/profile`; app import reports 108 routes including both surfaces.

### 5. No CSP/CORS loosening, Node build-time only, backend unchanged — PASS

Evidence: `utils/security.py` not modified by this increment (change record + increment-3 backfill both confirm; the increment touched only `frontend/spa/**` and one e2e spec). No `unsafe-eval` introduced; `connect-src`/`worker-src` unchanged. The pre-existing `CORSMiddleware` (security.py L194) is Phase-1 test-app infrastructure and was not altered here. Node/Vite is build-time only — no runtime hosting added. Backend `be_*` API consumed as-is.

### 6. 3.4 change-record backfill — PASS

Evidence: [.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment3-changes.md](.copilot-tracking/changes/2026-07-07/albumsaventures-phase3-spa-increment3-changes.md) now exists and documents the Uppy v3→v5 ESM cutover (v5 dep versions listed) and a six-item **Phase 2 Preservation Checklist** (golden-retriever resume, client compression, 256 KB floor / 8 MB cap adaptive chunk, durable status polling, same-origin TUS, cookie-only auth/CSRF). Marked as a reconstructed backfill from the working tree + increment-3 review (Approve-with-followups).

### 7. XSS — PASS

Evidence: grep for `dangerouslySetInnerHTML` across `frontend/spa/src/**` returns **no matches**. All profile fields render as React children (`{value}` text nodes and controlled inputs), which React auto-escapes. Error messages surface `ApiError.message` as text children only.

## Findings

### LOW-1 (advisory, out of scope) — Confirm CORS `allow_origins` is not a wildcard

`utils/security.py` L194-L195 registers `CORSMiddleware` with `allow_origins=origins`. This is pre-existing Phase-1 code and **not part of increment 4**, so it does not affect this verdict. As a hygiene note for a future security pass, confirm `origins` resolves to an explicit same-origin/allow-list (not `*`), consistent with the plan's "no CORS" posture for the SPA surface. No action required for this increment.

## Deferrals / Follow-ups Carried Forward

* **FU-2** (from increment-3 review): full Playwright upload/profile interactive-flow coverage remains a Phase 4 item. The e2e specs added here (`test_spa_profile_ui.py`) and in 3.4 are smoke-level and require a running server with a built SPA. Unchanged by this review.

## Reviewer Notes

The increment is tightly scoped, all gates reproduce green, and the FU-1 code-split is verified against a real production build rather than accepted on the dev claim. Cookie-only auth + CSRF-guarded `PUT` are correctly implemented and no XSS sink was introduced. No defects require a fix cycle.

**Next step**: land increment 4; proceed to sub-phase 3.6 (Admin `admin_users`/`admin_groups`, `RequireSuperuser`).
