<!-- markdownlint-disable-file -->
# Release Changes: Phase 1 Security Hardening — Validator Fix Cycle 1

**Related Plan**: `.copilot-tracking/plans/albumsaventures-modernization.md` (Phase 1)
**Related Review**: `.copilot-tracking/reviews/2026-07-07/albumsaventures-phase1-security-review.md`
**Implementation Date**: 2026-07-07
**Role**: squad `developer` (member Gamma) — autopilot fix cycle 1

## Summary

The Phase 1 security helper logic (`utils/security.py`, `utils/rate_limit.py`) was
correct but had never been wired into the running applications, and the prod app was
left non-importable. This cycle wires the middleware into both the production and test
apps, removes the dead wildcard CORS block, adds the required security/JWT/superuser/
rate-limit tests, documents the production DB migration prerequisite, and makes ruff +
black green on all changed files. The production app now imports cleanly and the full
targeted suite passes (48 passed).

## Defect → Fix mapping

| Defect | Fix |
|---|---|
| **C-2** app cannot start (`NameError: CORSMiddleware`) | Removed the dead wildcard `CORSMiddleware` block in `AlbumsAventures-BE.py`; the stale reference no longer exists. App imports cleanly. |
| **C-1** `configure_cors`/`configure_security` imported but never called | Both now invoked on the prod app right after `app = FastAPI(...)`. Ruff no longer reports F401; startup logs confirm both middlewares register. |
| **H-1** missing JWT wrong-alg/`none` rejection test | Added `TestJWTAlgorithmConfinement` in `tests/test_auth.py`: `alg:none` (forged, unsigned) and HS512 (wrong-alg) tokens rejected by `decode_token`, plus 401 on `/be_auth/me` for an `alg:none` token. |
| **H-2** superuser authz test skipped | Un-skipped and implemented `test_upload_superuser_bypasses_access_check` in `tests/test_upload.py`; now green (token carries `is_superuser`). |
| **H-3** test app not hardened; headers unverifiable | `AlbumsAventures_BE_test.py` now calls `configure_cors`/`configure_security`; added `TestSecurityHeaders` asserting CSP + nosniff + frame + referrer-policy on a response. |
| **M-1** CORS origins hardcoded literal | Prod/test apps use `configure_cors`, which reads `app_config.cors_allowed_origins()` (config-driven). Hardcoded `origins = [...]` literals removed from both apps. |
| **M-2** durable-rate-limit lockout test missing | Added `TestDurableRateLimit` in `tests/test_auth.py`: lockout after `max_attempts` persists in `rate_limit_entries` (hashed key, no plaintext), 429 on `check_rate_limit`, and durability confirmed via identity-map flush + DB re-read. |
| **M-3** prod migration prerequisite undocumented | Documented in `backend/db/migrations/README.md` as a **bloquing deploy prerequisite**; not auto-applied to any DB. |
| **L-1** ruff fails on changed files | `ruff check` green on all changed files (fixed I001 import sorting in `be_resizer.py`; F401/F821 resolved by wiring). |
| **L-2** black fails on `be_resizer.py` | `black` applied; `black --check` green on all changed files. |

## Changes

### Added

* `backend/db/migrations/README.md` — Documents manual SQL migrations; flags `0001_rate_limit_entries.sql` as a blocking production deploy prerequisite (with apply/rollback commands, no auto-apply). Resolves M-3.
* `tests/test_auth.py::TestJWTAlgorithmConfinement` — JWT `alg:none`/wrong-alg rejection tests. Resolves H-1.
* `tests/test_auth.py::TestSecurityHeaders` — Asserts CSP + `X-Content-Type-Options` + `X-Frame-Options` + `Referrer-Policy` + `Permissions-Policy` on a response. Resolves H-3 (test half).
* `tests/test_auth.py::TestDurableRateLimit` — DB-backed lockout persistence tests. Resolves M-2.

### Modified

* `AlbumsAventures-BE.py` — Removed dead wildcard `CORSMiddleware` block (C-2); call `configure_cors(app)` + `configure_security(app)` (C-1, M-1). App imports cleanly; CSP/security headers/HSTS/HTTPS-redirect (prod-gated)/tightened CORS now reach the running app.
* `AlbumsAventures_BE_test.py` — Removed wildcard CORS + `CORSMiddleware` import; call `configure_cors(app)` + `configure_security(app)` so security headers/CSP are verifiable by the suite. Resolves H-3 (app half).
* `tests/test_upload.py` — Un-skipped and updated `test_upload_superuser_bypasses_access_check`; removed now-unused `import pytest`. Resolves H-2 and part of L-1.
* `backend/routers/be_resizer.py` — Import sorting fixed (ruff `--fix`, I001) and black formatting applied. Resolves L-1/L-2. No behavioral change.

### Removed

* (none — dead code removed inline within `AlbumsAventures-BE.py` and `AlbumsAventures_BE_test.py`, documented above.)

## Additional or Deviating Changes

* **M-2 second test uses identity-map flush instead of a second DB session.** The review suggested asserting persistence; an initial version opened a separate `TestingSessionLocal()` to simulate another worker, but the in-memory SQLite `StaticPool` test fixture caused a spurious `no such table` under a second session. Replaced with `db_session.expire_all()` + DB re-read, which proves the lockout is read from the durable store (not the session cache) without the SQLite pooling artifact. Durability intent preserved.
* **H-1 `alg:none` token is forged manually** (base64url header/payload with empty signature) rather than via `jose.jwt.encode(algorithm="none")`, because the installed `python-jose` raises on encoding an unsigned token. The manual forge is a stronger, dependency-independent negative test.
* **Out-of-scope ruff findings not touched.** `ruff check .` also reports I001/F401 in `.agents/skills/python-diagrams/templates/azure-webapp-lld.py` (a bundled hve-core skill template, not part of this app and not modified in Phase 1). Left untouched; all Phase 1 changed files are green.
* **No DB migration applied.** `0001_rate_limit_entries.sql` remains manual/approval-gated; dev/test create the table via `create_all`. No deploy/push/merge performed.

## Validation

| Command | Result |
|---|---|
| `pytest tests/test_auth.py tests/test_albums.py tests/test_upload.py -q` | **48 passed** (was 41 passed + 1 skipped) |
| import `AlbumsAventures-BE.py` (via importlib) | **OK** — `FastAPI`, 2 middlewares registered; `configure_cors`/`configure_security` logged |
| `ruff check` (changed files) | **All checks passed** |
| `black --check` (changed files) | **All files unchanged** (green) |

## Release Summary

Files affected: 4 modified (`AlbumsAventures-BE.py`, `AlbumsAventures_BE_test.py`,
`tests/test_upload.py`, `backend/routers/be_resizer.py`), 1 modified with net-new test
classes (`tests/test_auth.py`), 1 added (`backend/db/migrations/README.md`).

Conditions 3, 4, 5 and the transport halves of 3/7 now reach the running application;
conditions 1 and 2 gain their required enabled tests; condition 6 gains a durable-lockout
persistence test. Production deploy prerequisite (`rate_limit_entries` via
`0001_rate_limit_entries.sql`) is documented and must be applied manually before first
prod boot — no migration was applied here. No deploy/push/merge performed.
