"""Bare-path redirect shim for decommissioned Jinja routes.

When the legacy server-rendered Jinja pages were removed, their bare URLs (``/``,
``/login``, ``/reset-password?token=``, ``/album/shared?token=``, ...) would
otherwise 404. This router maps each such path to its React SPA equivalent under
the same-origin ``/app`` prefix so bookmarks, and — critically — the password
reset emails and share links that point at bare paths keep working.

Security invariants (open-redirect-safe by construction):

* Every target is a STATIC same-origin ``/app/...`` path. No user-supplied
  ``next``/``return`` parameter is ever reflected into the ``Location`` header.
* Only EXPLICIT bare paths are enumerated — there is deliberately no bare
  ``/{full_path:path}`` catch-all (the SPA fallback owns ``/app`` only).
* Redirects use HTTP 302 (temporary) so the mapping can evolve.
* The share token is inserted as a URL-ENCODED single path segment, so it cannot
  break out of the fixed ``/app/shared/`` prefix.

This router is registered BEFORE ``configure_spa`` and after the media bridge.
The legacy Jinja view layer is fully removed: album create/edit are now
SPA-native, so ``/album/new`` -> ``/app/album/new`` and
``/album/{id}/edit`` -> ``/app/album/{id}/edit`` are redirected here too (both
declared BEFORE the ``int``-typed ``/album/{album_id}`` detail route so the
literal ``new`` segment and the ``/edit`` suffix are not shadowed). The static
``/rando`` page redirect also lives here now that ``fe_router`` is gone.
"""

from urllib.parse import quote

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import RedirectResponse

# Prefix-LESS router so the bare paths resolve exactly.
router = APIRouter(tags=["frontend-redirects"])

_FOUND = status.HTTP_302_FOUND


def _with_query(path: str, request: Request) -> str:
    """Append the incoming query string to a static same-origin target."""
    query = request.url.query
    return f"{path}?{query}" if query else path


@router.get("/")
async def redirect_index(request: Request):
    """Bare root -> SPA grid."""
    return RedirectResponse(url="/app/", status_code=_FOUND)


@router.get("/login")
async def redirect_login(request: Request):
    """Bare login -> SPA login (carry ``?registered=true`` etc.)."""
    return RedirectResponse(url=_with_query("/app/login", request), status_code=_FOUND)


@router.get("/signup")
async def redirect_signup(request: Request):
    """Bare signup -> SPA signup."""
    return RedirectResponse(url=_with_query("/app/signup", request), status_code=_FOUND)


@router.get("/forgot-password")
async def redirect_forgot_password(request: Request):
    """Bare forgot-password -> SPA forgot-password."""
    return RedirectResponse(url=_with_query("/app/forgot-password", request), status_code=_FOUND)


@router.get("/reset-password")
async def redirect_reset_password(request: Request):
    """MANDATORY: password-reset emails point at ``/reset-password?token=``.

    The SPA ``ResetPasswordPage`` reads ``token`` from the query string, so the
    query is preserved verbatim onto the static ``/app/reset-password`` target.
    """
    return RedirectResponse(url=_with_query("/app/reset-password", request), status_code=_FOUND)


@router.get("/profile")
async def redirect_profile(request: Request):
    """Bare profile -> SPA profile."""
    return RedirectResponse(url="/app/profile", status_code=_FOUND)


# ``/album/shared`` MUST be declared BEFORE ``/album/{album_id}`` so it is not
# shadowed by the parameterized route.
@router.get("/album/shared")
async def redirect_shared_album(request: Request, token: str = Query("")):
    """MANDATORY: share links point at ``/album/shared?token=``.

    The SPA ``SharedAlbumPage`` reads ``token`` from a PATH param (``/shared/:token``),
    so the token is URL-encoded into a single path segment of the fixed
    ``/app/shared/`` prefix (open-redirect-safe).
    """
    if token:
        return RedirectResponse(url=f"/app/shared/{quote(token, safe='')}", status_code=_FOUND)
    return RedirectResponse(url="/app/shared", status_code=_FOUND)


# ``/album/new`` and ``/album/{id}/edit`` MUST be declared BEFORE the ``int``-typed
# ``/album/{album_id}`` detail route so the literal ``new`` segment and the
# ``/edit`` suffix are matched here and not shadowed by the parameterized route.
@router.get("/album/new")
async def redirect_album_new(request: Request):
    """Bare album-create -> SPA album-create (``/app/album/new``, superuser-only)."""
    return RedirectResponse(url="/app/album/new", status_code=_FOUND)


@router.get("/album/{album_id}/edit")
async def redirect_album_edit(album_id: int, request: Request):
    """Bare album-edit -> SPA album-edit (``/app/album/{id}/edit``, superuser-only).

    ``album_id`` is an ``int`` path param, so the target is a fixed same-origin
    ``/app/album/{int}/edit`` path (open-redirect-safe by construction).
    """
    return RedirectResponse(url=f"/app/album/{album_id}/edit", status_code=_FOUND)


@router.get("/album/{album_id}")
async def redirect_album_detail(album_id: int, request: Request):
    """Bare album detail -> SPA album detail (``/app/albums/{id}``)."""
    return RedirectResponse(url=f"/app/albums/{album_id}", status_code=_FOUND)


@router.get("/rando")
async def redirect_rando(request: Request):
    """Public randonnée proposals page — static same-origin file redirect."""
    return RedirectResponse(url="/static/rando/propositions-rando.html", status_code=_FOUND)
