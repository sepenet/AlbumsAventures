"""Same-origin serving of the built React SPA (Phase 3.1).

The SPA (Vite + React 18 + TypeScript, source in ``frontend/spa/``) is built to
``frontend/spa/dist`` and served by THIS FastAPI process under the ``/app`` URL
prefix. No separate Node runtime or cross-origin surface is introduced: the
browser sends the existing HttpOnly session cookie automatically on same-origin
requests, so there is no CORS and no token in JS storage.

Asset-manifest contract
-----------------------
Vite rewrites ``dist/index.html`` on every build to reference content-hashed
JS/CSS under ``/app/assets/<name>-<hash>.js`` (because ``base = "/app/"``).
FastAPI serves that generated ``index.html`` verbatim and mounts
``dist/assets`` at ``/app/assets``; the Python side therefore NEVER hardcodes a
hashed filename. Vite also emits ``dist/.vite/manifest.json``
(``build.manifest = true``) for programmatic resolution if a later increment
needs it.

Route-shadowing guarantee
-------------------------
Serving is scoped to the ``/app`` prefix and is registered AFTER every
``be_*``/``fe_redirects`` include and after the ``/static``, ``/images`` and
``/thumbnails`` mounts. It therefore CANNOT intercept ``/be_*`` API calls,
``/be_resizer/tus/`` uploads, or the media mounts — those live outside ``/app``.
The legacy Jinja2 view layer has been fully decommissioned; bare legacy paths
now 302-redirect into ``/app`` via ``frontend/routers/fe_redirects.py``.

PWA build artifacts (Phase 4)
-----------------------------
``vite-plugin-pwa`` emits root-level files into ``dist/`` — the service worker
(``sw.js``), the Workbox runtime (``workbox-<hash>.js``), the registration
script (``registerSW.js``), the web app manifest (``manifest.webmanifest``) and
the icon set (``icons/``). The SPA fallback below serves any REAL file found in
``dist/`` at ``/app/<path>`` (with a path-traversal guard) BEFORE falling back
to ``index.html``. This is what lets the browser fetch ``/app/sw.js`` as a
script (so the SW registers with control scope ``/app/``) and ``/app/manifest
.webmanifest`` as the manifest, instead of receiving the HTML shell. Because
every one of these paths is under ``/app``, none can shadow ``/be_*``,
``/be_resizer/tus/`` or the media mounts.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# URL prefix under which the SPA is served. Distinct from every API/media path,
# so it cannot shadow them.
SPA_URL_PREFIX = "/app"

# Build output produced by `npm run build` in frontend/spa (Vite `outDir`).
SPA_DIST_DIR = Path("frontend/spa/dist")
SPA_ASSETS_DIR = SPA_DIST_DIR / "assets"
SPA_INDEX_FILE = SPA_DIST_DIR / "index.html"

# Explicit media types for PWA artifacts that Python's ``mimetypes`` does not
# resolve correctly (``.webmanifest``) or resolves inconsistently across
# versions (``.js``).
_PWA_MEDIA_TYPES = {
    ".webmanifest": "application/manifest+json",
    ".js": "text/javascript",
}

# PWA lifecycle files that must always be revalidated so a redeploy propagates
# (the browser can then detect a new service worker / manifest immediately).
_PWA_NO_CACHE_FILES = {"sw.js", "registerSW.js", "manifest.webmanifest"}


def _safe_dist_file(full_path: str) -> Path | None:
    """Resolve ``full_path`` to a real file inside ``dist/`` or return ``None``.

    Guards against path traversal: the resolved candidate MUST stay within the
    resolved ``dist/`` directory, so a crafted ``/app/../../etc/passwd`` cannot
    escape the build output. Returns ``None`` for the SPA shell itself
    (``index.html``) and for anything that is not an existing regular file, so
    those fall through to the client-side-routing fallback.
    """
    if not full_path or full_path in ("index.html", "index.htm"):
        return None
    try:
        dist_root = SPA_DIST_DIR.resolve()
        candidate = (SPA_DIST_DIR / full_path).resolve()
    except (OSError, ValueError):
        return None
    if dist_root not in candidate.parents:
        return None
    if not candidate.is_file():
        return None
    return candidate


def _dist_file_response(candidate: Path) -> FileResponse:
    """Serve a ``dist/`` artifact with the right media type and cache policy."""
    media_type = _PWA_MEDIA_TYPES.get(candidate.suffix.lower())
    headers: dict[str, str] = {}
    if candidate.name in _PWA_NO_CACHE_FILES:
        headers["Cache-Control"] = "no-cache"
    return FileResponse(candidate, media_type=media_type, headers=headers)


def configure_spa(app: FastAPI) -> None:
    """Mount the built SPA assets and register the SPA fallback route.

    Call this AFTER all API/frontend routers and media mounts are registered.

    Safe to call when the build output is absent (e.g. a fresh checkout before
    the first ``npm run build``): the fallback then returns a 404 hint instead
    of raising, so the app still imports and starts cleanly.
    """
    if SPA_ASSETS_DIR.is_dir():
        # Registered BEFORE the catch-all route below so hashed asset requests
        # are served as static files rather than rewritten to index.html.
        app.mount(
            f"{SPA_URL_PREFIX}/assets",
            StaticFiles(directory=str(SPA_ASSETS_DIR)),
            name="spa_assets",
        )
        logger.info("SPA : assets montés sur %s/assets", SPA_URL_PREFIX)
    else:
        logger.warning(
            "SPA non buildé (%s absent) — exécuter `npm run build` dans frontend/spa/",
            SPA_ASSETS_DIR,
        )

    async def serve_spa(full_path: str = "") -> FileResponse | PlainTextResponse:
        """Return a real ``dist/`` artifact or the SPA shell for ``/app`` routes.

        Resolution order:

        1. If ``full_path`` names an existing file in ``dist/`` (the PWA
           ``sw.js`` / ``workbox-<hash>.js`` / ``registerSW.js`` /
           ``manifest.webmanifest`` / ``icons/*``), serve that file so the
           browser receives a script/manifest/icon rather than HTML — this is
           required for service-worker registration and installability.
        2. Otherwise return ``index.html`` so client-side (history) routing
           resolves the view: ``/app/anything`` -> shell -> React Router.

        Never matches ``/be_*``, ``/be_resizer/tus/``, ``/images``,
        ``/thumbnails`` or ``/static`` — those are registered outside the
        ``/app`` prefix. ``/app/assets/*`` is handled by the static mount above,
        before this handler.
        """
        # Serve a genuine build artifact (service worker, manifest, icons) when
        # the path resolves to one; the traversal guard keeps this inside dist/.
        candidate = _safe_dist_file(full_path)
        if candidate is not None:
            return _dist_file_response(candidate)

        if SPA_INDEX_FILE.is_file():
            # `no-store` on the HTML shell so a rebuild's new hashed asset refs
            # are always picked up; the hashed assets themselves are immutable
            # and cached by their filename.
            return FileResponse(
                SPA_INDEX_FILE,
                media_type="text/html",
                headers={"Cache-Control": "no-store"},
            )
        return PlainTextResponse(
            "SPA non buildé. Exécuter `npm run build` dans frontend/spa/.",
            status_code=404,
        )

    # Bind both the bare prefix and the catch-all so `/app`, `/app/` and any
    # nested client route resolve to the shell. `response_model=None` disables
    # FastAPI's response-model inference from the ``FileResponse |
    # PlainTextResponse`` return annotation (neither is a Pydantic type).
    app.add_api_route(SPA_URL_PREFIX, serve_spa, include_in_schema=False, response_model=None)
    app.add_api_route(
        f"{SPA_URL_PREFIX}/{{full_path:path}}",
        serve_spa,
        include_in_schema=False,
        response_model=None,
    )
    logger.info("SPA : route de repli enregistrée sur %s/{full_path}", SPA_URL_PREFIX)
