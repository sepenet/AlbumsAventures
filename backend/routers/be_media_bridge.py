"""Compatibility-seam router for the two SPA-facing media JSON endpoints.

URL-PRESERVATION SEAM — NOT the canonical home for album media.

The React SPA calls two media endpoints at BARE (prefix-less) paths:

* ``GET /album/{album_id}/images`` — authenticated progressive image loading,
  consumed by ``frontend/spa/src/pages/AlbumDetailPage.tsx``.
* ``GET /album/shared/images`` — public token+PIN shared-album loading,
  consumed by ``frontend/spa/src/pages/SharedAlbumPage.tsx``.

These endpoints previously lived in ``frontend/routers/fe_router.py`` alongside
the now-decommissioned Jinja view layer. ``be_album.router`` and
``be_album.public_router`` both carry a ``/be_album`` prefix, so relocating there
would change the URLs to ``/be_album/...`` and break the SPA, which calls the
bare paths. This module is a deliberate prefix-less compatibility seam that hosts
the two endpoints verbatim so the SPA keeps working with zero client change.

Behavior, authorization, and response shape are preserved exactly:

* ``/album/{album_id}/images`` requires authentication (401 when unauthenticated)
  and relays the ``access_token`` cookie to the backend.
* ``/album/shared/images`` stays public but validates the ``token`` + 6-char
  ``pin`` against the backend BEFORE returning any files.

A future consolidation (moving album media under ``be_album`` and repointing the
SPA) is tracked as deferred tech debt; until then this seam is the load-bearing
URL contract.
"""

import logging
import os
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from PIL import Image as PILImage

from utils.auth import require_auth
from utils.config import backend_api, image

logger = logging.getLogger(__name__)

# Prefix-LESS router: the two endpoints MUST resolve at their bare SPA URLs.
router = APIRouter(tags=["media-bridge"])

_PAGE_SIZE = 30
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic")
_VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")
_ALL_EXTENSIONS = _IMAGE_EXTENSIONS + _VIDEO_EXTENSIONS


def _album_folder_info(album: dict) -> dict:
    """Calcule les chemins de dossiers pour un album."""
    category_folder = album.get("category", "").replace(" ", "-").replace("'", "-")
    title_folder = album.get("title", "").replace(" ", "-").replace("'", "-")
    participants_db = album.get("participants", "") or ""
    participants_parts = [p.replace("-", "").replace("'", "").strip() for p in participants_db.split("|") if p.strip()]
    participants_folder = "-".join(participants_parts)
    album_folder = f"{album.get('date')}_{title_folder}_{participants_folder}"
    thumbnails_dir = os.path.join(image.thumbnails_path, category_folder, album_folder)
    images_dir = os.path.join(image.image_path, category_folder, album_folder)
    return {
        "category_folder": category_folder,
        "album_folder": album_folder,
        "thumbnails_dir": thumbnails_dir,
        "images_dir": images_dir,
    }


def _get_album_media_page(album: dict, offset: int = 0, limit: int = _PAGE_SIZE) -> dict:
    """
    Retourne une page de médias pour un album, triés par date de modification.
    Lit les données EXIF uniquement pour la page demandée.
    Retourne {"items": [...], "total": int, "has_more": bool}
    """
    info = _album_folder_info(album)
    images_dir = info["images_dir"]
    thumbnails_dir = info["thumbnails_dir"]
    category_folder = info["category_folder"]
    album_folder = info["album_folder"]

    if not os.path.isdir(images_dir):
        return {"items": [], "total": 0, "has_more": False}

    # Étape 1 : lister tous les fichiers et trier par date de modification (rapide, pas de décodage)
    all_files = [f for f in os.listdir(images_dir) if f.lower().endswith(_ALL_EXTENSIONS)]
    file_mtimes = []
    for filename in all_files:
        try:
            mtime = os.path.getmtime(os.path.join(images_dir, filename))
        except OSError:
            mtime = 0
        file_mtimes.append((filename, mtime))
    file_mtimes.sort(key=lambda x: x[1])
    total = len(file_mtimes)

    # Étape 2 : page demandée
    page_files = file_mtimes[offset : offset + limit]

    # Étape 3 : lire EXIF/dimensions uniquement pour cette page
    media_files = []
    for filename, _ in page_files:
        is_video = filename.lower().endswith(_VIDEO_EXTENSIONS)
        original_path = os.path.join(images_dir, filename)

        if is_video:
            name, _ = os.path.splitext(filename)
            thumbnail_filename = f"{name}.jpg"
        else:
            thumbnail_filename = filename
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)

        img_width = None
        img_height = None
        if not is_video and os.path.isfile(original_path):
            try:
                with PILImage.open(original_path) as img:
                    img_width, img_height = img.size
                    exif_data = img._getexif()
                    if exif_data:
                        orientation = exif_data.get(274)
                        if orientation in (5, 6, 7, 8):
                            img_width, img_height = img_height, img_width
            except Exception as e:
                logger.debug(f"Impossible de lire EXIF pour {filename}: {e}")

        has_thumbnail = os.path.isfile(thumbnail_path)
        if has_thumbnail:
            thumbnail_url = f"/thumbnails/{quote(category_folder)}/{quote(album_folder)}/{quote(thumbnail_filename)}"
        elif is_video:
            thumbnail_url = "/static/images/video-placeholder.svg"
        else:
            thumbnail_url = f"/images/{quote(category_folder)}/{quote(album_folder)}/{quote(filename)}"

        media_files.append(
            {
                "filename": filename,
                "thumbnail_url": thumbnail_url,
                "full_url": f"/images/{quote(category_folder)}/{quote(album_folder)}/{quote(filename)}",
                "is_video": is_video,
                "has_thumbnail": has_thumbnail,
                "width": img_width,
                "height": img_height,
            }
        )

    return {
        "items": media_files,
        "total": total,
        "has_more": (offset + limit) < total,
    }


# NOTE d'ordre de routes : ``/album/shared/images`` DOIT être déclaré AVANT
# ``/album/{album_id}/images`` sinon Starlette lie ``album_id="shared"`` et la
# route publique partagée devient inatteignable.
@router.get("/album/shared/images")
async def shared_album_images_api(
    request: Request,
    token: str = Query(...),
    pin: str = Query(..., min_length=6, max_length=6),
    offset: int = Query(0, ge=0),
    limit: int = Query(_PAGE_SIZE, ge=1, le=200),
):
    """Endpoint public pour charger les images d'un album partagé.
    Valide le token+PIN via le backend avant de retourner les fichiers.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{backend_api.album_url}/shared",
                params={"token": token, "pin": pin},
                timeout=backend_api.default_timeout,
            )
            if resp.status_code != 200:
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            album = resp.json()
    except Exception as e:
        logger.error(f"Erreur shared_album_images_api: {type(e).__name__}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur"})

    result = _get_album_media_page(album, offset=offset, limit=limit)
    return JSONResponse(content=result)


@router.get("/album/{album_id}/images")
async def album_images_api(
    album_id: int,
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(_PAGE_SIZE, ge=1, le=100),
):
    """Endpoint JSON pour le chargement progressif des images d'un album."""
    is_authenticated, _ = await require_auth(request)
    if not is_authenticated:
        return JSONResponse(status_code=401, content={"detail": "Non authentifié"})

    album = None
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_album_by_id/{album_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )
            if resp.status_code == 200:
                album = resp.json()
            else:
                return JSONResponse(status_code=404, content={"detail": "Album introuvable"})
    except Exception as e:
        logger.error(f"Erreur album_images_api album {album_id}: {type(e).__name__}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur"})

    result = _get_album_media_page(album, offset=offset, limit=limit)
    return JSONResponse(content=result)
