<!-- markdownlint-disable-file -->
# Review Record — Phase 1: Security Hardening (AlbumsAventures Modernization)

> AI-assisted review. Findings require confirmation by a human reviewer before Phase 1 is closed. This record does not modify application code.

## Metadata

| Field | Value |
|---|---|
| Reviewer | squad `tester` role (member Delta) |
| Stage | Autopilot Review — Phase 1 |
| Date | 2026-07-07 |
| Plan | `.copilot-tracking/plans/albumsaventures-modernization.md` (Phase 1) |
| Council Verdict | `.copilot-tracking/squad/decisions.md` → Council Verdict 2026-07-07 albumsaventures-modernization (Go-With-Conditions) |
| Change record | none produced by developer — change set reconstructed from working tree |
| Developer summary | none provided |

## Reconstructed change set (working tree)

Modified: `AlbumsAventures-BE.py`, `backend/db/models.py`, `backend/routers/be_album.py`, `backend/routers/be_auth.py`, `backend/routers/be_resizer.py`, `utils/config.py`, `utils/csrf.py`, `.gitignore`
New: `utils/security.py`, `utils/rate_limit.py`, `backend/db/migrations/0001_rate_limit_entries.sql`

## Overall Verdict

**🚫 Request-changes.**

The security logic was written to a high standard in the new/modified helper modules, but the production application entrypoint (`AlbumsAventures-BE.py`) was **never wired to it** and is **left in a non-importable state**. The whole transport/header/CSP/CORS layer (conditions 3–5, half of 7) is effectively **not applied** to the running app, and the app **cannot start** as committed. Two required tests are missing/skipped.

### Severity counts

| Severity | Count |
|---|---|
| Critical | 2 |
| High | 3 |
| Medium | 3 |
| Low | 2 |

## Per-condition assessment

| # | Council condition | Verdict | Evidence |
|---|---|---|---|
| 1 | is_superuser authz fix (#485) | **PARTIAL** | Code correct & wired; enforcement test still skipped |
| 2 | JWT algorithm confinement (pin HS256, reject none, enforce exp) + test | **PARTIAL** | Code correct & wired; **required wrong-alg/none test missing** |
| 3 | Secure cookies + HTTPS redirect + HSTS | **PARTIAL** | Cookies wired & config-driven; HTTPS-redirect/HSTS **not wired** |
| 4 | Single security-headers/CSP middleware | **FAIL** | Middleware written but **never registered** on the app |
| 5 | CORS tightening (config-driven, no wildcard-with-creds) | **FAIL** | Tightened `configure_cors` **never called**; old wildcard block remains |
| 6 | Durable rate limiting (DB, not Azure Redis); migration not auto-applied | **PASS** | Fully wired; DB-backed; migration flagged manual |
| 7 | Server-side upload validation + nosniff/Content-Disposition on media | **PARTIAL** | Magic-byte/path-traversal wired; media header hardening **not wired** |

### 1. is_superuser propagation (#485) — PARTIAL

- PASS (code): claim added in `create_access_token` — [backend/routers/be_auth.py](backend/routers/be_auth.py#L129); populated by login with `user.is_superuser`; exposed by `get_current_user` — [backend/routers/be_auth.py](backend/routers/be_auth.py#L272). The `be_resizer` superuser bypass now reads a real value.
- GAP: the authz path that depends on it is still guarded by a skipped test — `test_upload_superuser_bypasses_access_check` remains `@pytest.mark.skip` citing the now-fixed bug — [tests/test_upload.py](tests/test_upload.py#L58). The plan's acceptance required an *enabled* pytest case asserting a superuser-gated path. The `be_auth` admin routes (L305, L319) authorize via a DB lookup, not the token claim, so they do not cover the propagation.

### 2. JWT algorithm confinement — PARTIAL

- PASS (code): `JWT_ALLOWED_ALGORITHMS = ["HS256"]` — [backend/routers/be_auth.py](backend/routers/be_auth.py#L37); hardened `decode_token` pins `algorithms=JWT_ALLOWED_ALGORITHMS` and sets `options={"require_exp": True, "verify_exp": True, "verify_signature": True}` — [backend/routers/be_auth.py](backend/routers/be_auth.py#L70-L71). Applied on **all** decode paths: cookie/header `get_current_user` (L259), share token (L191), password reset (L596). Signing forced to HS256 regardless of config (defensive).
- GAP (required test missing): the condition explicitly requires "a test asserting a wrong-alg/none token is rejected." No such test exists in `tests/` (searched: no `alg`/`none`/`decode_token`/`HS256` assertion). This is a named acceptance item, so the condition is not fully satisfied without it.

### 3. Secure cookies + HTTPS redirect + HSTS — PARTIAL

- PASS (cookies): auth cookie is config-driven — `secure=app_config.cookie_secure()`, `samesite=app_config.cookie_samesite()` on login [backend/routers/be_auth.py](backend/routers/be_auth.py#L491-L492) and matching logout [backend/routers/be_auth.py](backend/routers/be_auth.py#L514-L515). CSRF cookie likewise — [utils/csrf.py](utils/csrf.py#L54). `app_config.cookie_secure()` defaults False in dev, True in prod, with explicit override — [utils/config.py](utils/config.py#L156-L164). Dev (Windows/SQLite, HTTP) remains functional.
- FAIL (transport): `HTTPSRedirectMiddleware` + HSTS live only inside `configure_security` — [utils/security.py](utils/security.py#L217-L221) — which is **never called** (see Critical-1). In production, HTTPS redirect and the `Strict-Transport-Security` header are therefore **not emitted**.

### 4. Single security-headers / CSP middleware — FAIL (present but not applied)

- The design itself is strong: one `SecurityHeadersMiddleware` emitting CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, and prod-only HSTS — [utils/security.py](utils/security.py#L128-L179). A single CSP with **forward-allowances** for Phase 2 (Uppy `releases.transloadit.com`) and Phase 3 (Tailwind/HTMX via `'self'`) — [utils/security.py](utils/security.py#L88-L111); `worker-src 'self' blob:` and `manifest-src` pre-allocated for Phase 4. `frame-ancestors 'none'`, `object-src 'none'`, `base-uri 'self'` present. `unsafe-inline` is explicitly documented as a **tracked temporary exception** to remove in Phase 3 — [utils/security.py](utils/security.py#L82-L86).
- FAIL: the middleware is **never registered** on any app. `configure_security` is imported into `AlbumsAventures-BE.py` (L40) but never invoked, and the test app `AlbumsAventures_BE_test.py` was not updated at all. Net effect: **no security headers or CSP are emitted by the running application.** The 41 passing unit tests exercise the un-hardened test app and so do not detect this.

### 5. CORS tightening — FAIL (not applied)

- `configure_cors` is config-driven, non-wildcard for origins, and restricts methods/headers to the real set — [utils/security.py](utils/security.py#L187-L201). But it is **never called**.
- The production app still contains the **original wildcard CORS block** — `allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True` — [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L103-L124). The origin list is a hardcoded literal (`http://localhost:5003`), not the config-driven whitelist. The tightening did not reach the app.

### 6. Durable rate limiting — PASS

- In-memory `defaultdict` limiter removed; replaced by DB-backed `check_rate_limit` / `record_failed_attempt` / `clear_failed_attempts` keyed by a SHA-256 hash (no plaintext identifiers) — [utils/rate_limit.py](utils/rate_limit.py#L35-L120). Backed by `RateLimitEntry` ORM model — [backend/db/models.py](backend/db/models.py#L96-L112).
- Wired at all call sites with a DB session: login and forgot-password [backend/routers/be_auth.py](backend/routers/be_auth.py#L456-L474), share-PIN lockout `verify_share_token(db, ...)` [backend/routers/be_auth.py](backend/routers/be_auth.py#L159), and the caller threads `db` through [backend/routers/be_album.py](backend/routers/be_album.py#L276). Login and PIN lockouts are durable across restarts/workers.
- No Azure managed Redis — reuses the existing DB (satisfies cost condition C-4).
- Migration correctly **not** auto-applied: prod (Linux) does not run `create_all`; the `.sql` is documented as manual, approval-gated, with rollback — [backend/db/migrations/0001_rate_limit_entries.sql](backend/db/migrations/0001_rate_limit_entries.sql#L1-L45). Dev/test create the table via `create_all` as intended.
- Operational note (Medium, by design): until the migration is applied in prod, every login/forgot/share attempt will hit a missing `rate_limit_entries` table and error. This is a hard **deployment prerequisite** and must be called out in the deploy runbook.

### 7. Server-side upload validation — PARTIAL

- PASS (upload move, always active — router code): `sanitize_upload_filename` rejects null bytes, path separators, absolute paths, and `..` — [backend/routers/be_resizer.py](backend/routers/be_resizer.py#L723-L755); magic-byte content/extension agreement via `_validate_magic_bytes` — [backend/routers/be_resizer.py](backend/routers/be_resizer.py#L757-L777); plus a `commonpath` containment check ensuring the destination stays inside the album folder — [backend/routers/be_resizer.py](backend/routers/be_resizer.py#L821-L826). These run inside `_integrer_fichier_tus`, so they are effective regardless of middleware wiring.
- FAIL (served media): the `nosniff` + sandbox-CSP + forced `Content-Disposition: attachment` for `/images` and `/thumbnails` (incl. SVG/HTML) live in `SecurityHeadersMiddleware` — [utils/security.py](utils/security.py#L163-L177) — which is **not wired**. So served-media hardening is **not active**.
- Note: the enabled upload tests target the legacy `POST /be_resizer/upload_images/{id}` XHR path — [tests/test_upload.py](tests/test_upload.py#L48-L131) — not the hardened TUS `_integrer_fichier_tus` move, so the new magic-byte/path-traversal logic is not covered by an enabled test.

## Defects (must-fix before Phase 1 is done)

### Critical

- **C-1 — Security middleware never wired; app hardening inert.** `configure_cors(app)` / `configure_security(app)` are imported but never called in `AlbumsAventures-BE.py` (import at [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L40); no invocation). Ruff confirms both as unused imports (F401 ×2 at L40). Consequence: no CSP, no security headers, no HSTS, no HTTPS redirect, no TrustedHost, no CORS tightening on the running app. This alone fails conditions 4 and 5 and the transport halves of 3 and 7.
- **C-2 — Production app cannot start (NameError).** The `CORSMiddleware` import was removed but the original block still references it — [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L104). Ruff: `F821 Undefined name 'CORSMiddleware'` at L104. Verified by loading the module: `NameError: name 'CORSMiddleware' is not defined` at line 104. The app fails at import before serving. (Unit tests still pass because they import `AlbumsAventures_BE_test.py`, a separate app that was not touched.)

### High

- **H-1 — Required JWT wrong-alg/`none` test missing** (condition 2). No test asserts a `alg:none`/wrong-alg token is rejected. Add one against `decode_token`/`get_current_user`.
- **H-2 — is_superuser enforcement test still skipped** (condition 1). Un-skip and green `test_upload_superuser_bypasses_access_check` — [tests/test_upload.py](tests/test_upload.py#L58) — now that the claim is populated, or add an equivalent enabled authz test.
- **H-3 — Test app not hardened; security headers unverifiable.** `AlbumsAventures_BE_test.py` still uses wildcard CORS and no `configure_security` — [AlbumsAventures_BE_test.py](AlbumsAventures_BE_test.py#L40-L46). Because the harness never exercises the middleware, there is no regression test proving CSP/nosniff/HSTS/media headers. After fixing C-1, wire `configure_security` into the test app and add header assertions.

### Medium

- **M-1 — CORS origins not config-driven in the live path** (condition 5): even after wiring, ensure the app uses `app_config.cors_allowed_origins()` rather than the hardcoded `origins` literal at [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L100-L102).
- **M-2 — Durable-rate-limit test missing** (condition 6 acceptance): no test asserts lockout after N attempts / persistence via `RateLimitEntry`. Add a DB-backed test.
- **M-3 — Prod deployment prerequisite undocumented**: `rate_limit_entries` must be created via `0001_rate_limit_entries.sql` before first prod boot or all auth attempts error. Add to the deploy runbook / Phase handoff.

### Low

- **L-1 — Lint fails on changed files**: `ruff check` reports 4 errors (F401 ×2, F821, plus `I001` unsorted imports at [backend/routers/be_resizer.py](backend/routers/be_resizer.py#L668)). Phase 1 validation requires green ruff.
- **L-2 — Format fails**: `black --check` would reformat `backend/routers/be_resizer.py`.

## Validation commands

| Command | Result |
|---|---|
| `pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py` | 41 passed, 1 skipped (superuser authz test) |
| load `AlbumsAventures-BE.py` (import) | **FAIL** — `NameError: CORSMiddleware` at L104 |
| `ruff check` (9 changed/new files) | **FAIL** — 4 errors (F401 ×2 @ BE:40, F821 @ BE:104, I001 @ be_resizer:668) |
| `black --check` (9 files) | **FAIL** — `be_resizer.py` would reformat |
| e2e Playwright | Not run — assessment below |

### e2e assessment (not run, per instruction)

Treating the reported Playwright failures as environmental (no live server) is **reasonable**: the specs need a running instance, and — independently — the prod app currently fails to import (C-2), so a live e2e run would fail at startup rather than on assertions. This does **not** indicate a Phase-1 regression in test logic. However, because the middleware is unwired, the e2e acceptance items in the plan (no CSP console violations, `Set-Cookie` `Secure` under prod config) are **currently unverifiable** and remain open until C-1/C-2 are fixed.

## What is genuinely good (keep)

- `utils/security.py`: single, well-documented CSP with explicit forward-allowances and a tracked `unsafe-inline` exception; correct Starlette middleware ordering; media sandbox policy. Sound design — it just needs to be *called*.
- `utils/rate_limit.py` + `RateLimitEntry` + flagged SQL migration: clean, durable, no new infra, no plaintext keys. Condition 6 fully met.
- `decode_token` hardening and its application across all three decode sites; `is_superuser` claim plumbing. Correct — needs tests.
- Upload move hardening (sanitize + magic bytes + containment). Correct and always-on.

## Recommendation

Do **not** close Phase 1. Route back to `developer` for a focused fix:

1. Wire the app: call `configure_cors(app)` + `configure_security(app)` and remove the dead wildcard `CORSMiddleware` block (resolves C-1, C-2, conditions 4/5 and transport halves of 3/7); use `app_config.cors_allowed_origins()` (M-1).
2. Harden the test app + add header assertions (H-3).
3. Add the missing tests: JWT wrong-alg/none (H-1), un-skip superuser authz (H-2), durable rate-limit lockout (M-2).
4. Green ruff + black on changed files (L-1, L-2).
5. Document the prod migration prerequisite (M-3).

Re-review after fixes; conditions 1–5 and 7 flip to PASS only once the middleware is wired and the named tests exist.

---

## Re-validation (cycle 1)

> Re-validated by squad `tester` role (member Delta) on 2026-07-07 against the working tree and the developer change record `.copilot-tracking/changes/2026-07-07/albumsaventures-phase1-security-changes.md` after developer fix cycle 1. This section supersedes the Request-changes verdict above.

### Final verdict

**✅ Approve.** Every defect from the initial review (C-1, C-2, H-1, H-2, H-3, M-1, M-2, M-3, L-1, L-2) is resolved in the working tree and independently re-verified. The production app now imports cleanly and the security/CORS layer reaches the running application. No new defects introduced. No follow-ups block Phase 1 closure.

### Defect resolution (re-verified)

| Defect | Prior verdict | Re-validation evidence | Status |
|---|---|---|---|
| **C-2** app non-importable (`NameError: CORSMiddleware`) | 🚫 Critical | Dead wildcard `CORSMiddleware` block gone from [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L99-L109). Module imports without error; grep confirms no stale `CORSMiddleware` reference in app entrypoint. | ✅ Resolved |
| **C-1** `configure_cors`/`configure_security` never called | 🚫 Critical | Both invoked right after `app = FastAPI(...)` in [AlbumsAventures-BE.py](AlbumsAventures-BE.py#L105-L106). Import log shows `SecurityHeadersMiddleware` + `CORSMiddleware` registered. Ruff no longer flags F401. | ✅ Resolved |
| **H-1** JWT wrong-alg/`none` test missing | ⚠️ High | `TestJWTAlgorithmConfinement` in [tests/test_auth.py](tests/test_auth.py#L315-L370): `alg:none` and HS512 rejected by `decode_token` (raises `JWTError`), plus 401 on `/be_auth/me`. All pass. | ✅ Resolved |
| **H-2** superuser authz test skipped | ⚠️ High | `test_upload_superuser_bypasses_access_check` un-skipped and enabled in [tests/test_upload.py](tests/test_upload.py#L57-L79); asserts non-403 for a superuser token carrying `is_superuser`. Passes. | ✅ Resolved |
| **H-3** test app not hardened; headers unverifiable | ⚠️ High | Test app calls `configure_cors`/`configure_security` [AlbumsAventures_BE_test.py](AlbumsAventures_BE_test.py#L40-L41); `TestSecurityHeaders` asserts CSP (`default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'`) + nosniff + `X-Frame-Options: DENY` + Referrer-Policy + Permissions-Policy [tests/test_auth.py](tests/test_auth.py#L373-L394). Passes. | ✅ Resolved |
| **M-1** CORS origins hardcoded literal | Medium | `configure_cors` reads `app_config.cors_allowed_origins()` [utils/security.py](utils/security.py#L192); hardcoded literals removed from both apps. Import log: `CORS configuré pour 1 origine(s)` from config. | ✅ Resolved |
| **M-2** durable-rate-limit lockout test missing | Medium | `TestDurableRateLimit` [tests/test_auth.py](tests/test_auth.py#L397-L460): lockout after `max_attempts` persists in `rate_limit_entries` with hashed key (no plaintext), 429 on `check_rate_limit`, durability via `expire_all()` + DB re-read. Passes. | ✅ Resolved |
| **M-3** prod migration prerequisite undocumented | Medium | [backend/db/migrations/README.md](backend/db/migrations/README.md) documents `0001_rate_limit_entries.sql` as a **bloquant** deploy prerequisite with apply/rollback and explicit no-auto-apply. | ✅ Resolved |
| **L-1** ruff fails on changed files | Low | `ruff check` on all 12 Phase 1 files: **All checks passed.** | ✅ Resolved |
| **L-2** black fails on `be_resizer.py` | Low | `black --check` on all 12 Phase 1 files: **12 files would be left unchanged.** | ✅ Resolved |

### Developer deviations — assessment

Both documented deviations are **acceptable**:

- **H-1 — manual `alg:none` forge** (base64url header/payload + empty signature instead of `jose.jwt.encode(algorithm="none")`). Acceptable and in fact preferable: the installed `python-jose` refuses to encode an unsigned token, and the manual forge is a dependency-independent negative test that exercises the exact attacker-controlled wire format. It still asserts rejection via `decode_token` and the protected endpoint.
- **M-2 — `expire_all()` + DB re-read** instead of a second `TestingSessionLocal()`. Acceptable: the in-memory SQLite `StaticPool` fixture yields a spurious `no such table` under a second session (a pooling artifact, not a durability issue). `expire_all()` clears the SQLAlchemy identity map so the subsequent read comes from the durable store, which proves the lockout is persisted rather than session-cached. Durability intent is preserved.

### Validation commands (re-run in venv)

| Command | Result |
|---|---|
| `.\Scripts\python.exe -m pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **48 passed** (was 41 passed + 1 skipped) |
| import `AlbumsAventures-BE.py` | **OK** — `SecurityHeadersMiddleware` + `CORSMiddleware` registered; CORS from config (1 origin); dev headers active, HTTPS/HSTS off in dev |
| `ruff check` (12 Phase 1 files) | **All checks passed** |
| `black --check` (12 Phase 1 files) | **12 files unchanged** |

Out-of-scope note: `ruff check .` at repo scope still reports pre-existing I001/F401 in bundled `.agents/skills/**` hve-core template files, which are not part of this application and were not modified in Phase 1. Excluded from Phase 1 scope per instruction; all Phase 1 changed files are clean.

### Severity counts (post-fix)

| Severity | Open |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |

All council conditions 1–7 now reach PASS: the security/CORS/header/CSP/HSTS layer is wired into the running app, JWT confinement and superuser authz have enabled tests, durable rate limiting has a persistence test, and lint/format are green. **Phase 1 may proceed to closure** (human confirmation still recommended before deploy, and the `0001_rate_limit_entries.sql` migration remains a manual, blocking prod prerequisite).
