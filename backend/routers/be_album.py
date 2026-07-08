import json
import logging
import os
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

from utils.config import image, password_reset

from ..albums import folder
from ..db import crud, schemas
from ..db.db_connect import db_dependency
from .be_auth import (
    ShareTokenCreate,
    ShareTokenResponse,
    create_album_share_token,
    generate_pin,
    get_current_user,
    require_superuser,
    verify_share_token,
)
from .be_formatter import build_cover_url

logger = logging.getLogger(__name__)

# check user.py for more comments on the following line
router = APIRouter(prefix="/be_album", tags=["backend_album"], dependencies=[Depends(get_current_user)])

# Router séparé pour les endpoints publics (sans authentification)
public_router = APIRouter(prefix="/be_album", tags=["backend_album_public"])


##################################################################
# album section
# get all albums
@router.get("/get_all_albums/", response_model=list[schemas.Album_Category])
def get_all_albums(db: db_dependency):
    return crud.get_all_albums_with_category(db)


# get albums pour un utilisateur
@router.get("/get_albums_by_user/{user_id}", response_model=list[schemas.Album_Category_WithCoverUrl])
def get_albums_by_user(user_id: int, db: db_dependency):
    """
    Récupération de tous les albums d'un utilisateur : albums associés directement à l'utilisateur
    + albums associés aux groupes dont il est membre.
    """
    # Albums liés directement à l'utilisateur
    user_album_links = crud.get_albums_by_user(db, user_id=user_id)
    user_album_ids = [ua.album_id for ua in user_album_links]

    # Groupes de l'utilisateur
    user_groups = crud.get_groups_id_by_user(db, user_id=user_id)
    group_ids = [ug.group_id for ug in user_groups]

    # Albums liés aux groupes
    group_album_links = crud.get_albums_id_by_groups(db, group_ids)
    group_album_ids = [ga.album_id for ga in group_album_links]

    # Fusionner et supprimer les doublons tout en conservant l'ordre
    all_album_ids = []
    seen = set()
    for aid in user_album_ids + group_album_ids:
        if aid not in seen:
            all_album_ids.append(aid)
            seen.add(aid)

    if not all_album_ids:
        raise HTTPException(status_code=404, detail="Aucun album trouvé pour cet utilisateur")

    # Récupérer les infos détaillées pour chaque album et construire l'URL de couverture
    result = []
    for album_id in all_album_ids:
        db_album = crud.get_album_by_id_with_category(db, album_id=album_id)
        if db_album is not None:
            cover_url = build_cover_url(
                category=db_album.category,
                date_str=str(db_album.date),
                title=db_album.title,
                participants=db_album.participants or "",
                image_cover=db_album.image_cover,
            )
            logger.debug(f"Album ID {album_id} - image_cover_url: {cover_url}")
            album_dict = {
                "id": db_album.id,
                "title": db_album.title,
                "description": db_album.description,
                "category_id": db_album.category_id,
                "date": db_album.date,
                "participants": db_album.participants,
                "location": db_album.location,
                "tags": db_album.tags,
                "image_cover": db_album.image_cover,
                "category": db_album.category,
                "image_cover_url": cover_url,
            }
            result.append(album_dict)
    result.sort(key=lambda a: a["date"], reverse=True)
    return result


# get album by id
@router.get("/get_album_by_id/{album_id}", response_model=schemas.Album_Category)
def get_album_by_id(album_id: int, db: db_dependency):
    db_album = crud.get_album_by_id_with_category(db, album_id=album_id)
    if db_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")
    return db_album


# create album
# Réservé aux superusers (SEC — parité avec l'ancien gate Jinja require_superuser).
@router.post("/create_album/", response_model=schemas.Album, dependencies=[Depends(require_superuser)])
def create_album(album: schemas.AlbumCreate, db: db_dependency):
    db_album = crud.create_album(db, album)

    # Associer automatiquement au groupe "all_albums" s'il existe
    all_albums_group = crud.get_group_by_name(db, "all_albums")
    if all_albums_group:
        crud.create_album_group(db, schemas.Album_GroupCreate(album_id=db_album.id, group_id=all_albums_group.id))
        logger.info(f"Album {db_album.id} associé automatiquement au groupe 'all_albums' (id={all_albums_group.id})")
    else:
        logger.warning("Groupe 'all_albums' introuvable — association automatique ignorée")

    return db_album


# update album
# Réservé aux superusers (SEC — parité avec l'ancien gate Jinja require_superuser).
@router.patch(
    "/update_album/{album_id}", response_model=schemas.Album, dependencies=[Depends(require_superuser)]
)
def update_album(album_id: int, album: schemas.AlbumUpdate, db: db_dependency):
    """
    Met à jour un album et renomme/déplace les répertoires si nécessaire.

    Les répertoires sont impactés par les changements de:
    - Catégorie (déplacement)
    - Titre, date, participants (renommage)
    """
    # Récupérer l'album AVANT modification (Row immuable pour conserver les anciennes valeurs)
    old_album = crud.get_album_by_id_with_category(db, album_id=album_id)
    if old_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # Effectuer la mise à jour en base
    updated_album = crud.update_album(db, album_id, album)

    # Récupérer l'album APRÈS modification (Row immuable pour les nouvelles valeurs)
    new_album = crud.get_album_by_id_with_category(db, album_id=album_id)

    # Renommer/déplacer les répertoires si nécessaire
    if new_album:
        success = folder.rename_album_folder(old_album, new_album)
        if not success:
            logger.warning(f"Le renommage des répertoires a échoué pour l'album {album_id}")

    return updated_album


# creation du repertoire relatif à l'album
# POST car état-modifiant (crée des répertoires sur disque) : un GxSRF via GET
# n'est PAS protégé par le cookie SameSite=lax. Réservé aux superusers.
# Idempotent : folder.create_album_folder utilise makedirs(exist_ok=True).
@router.post("/create_album_folder/{album_id}", dependencies=[Depends(require_superuser)])
def create_album_folder(album_id: int, db: db_dependency):
    db_album = crud.get_album_by_id(db, album_id=album_id)
    if db_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")
    folder.create_album_folder(db_album)


# export album to json
# Opération d'administration/maintenance (écrit album.json dans le dossier de
# l'album) — réservé aux superusers (triage authz turn 17).
@router.post("/export_album_json/{album_id}", dependencies=[Depends(require_superuser)])
def export_album_json(album_id: int, db: db_dependency):
    """
    Exporte les informations d'un album dans un fichier album.json dans le dossier de l'album.
    """
    db_album = crud.get_album_by_id(db, album_id=album_id)
    if db_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # Sérialisation via Pydantic
    from ..db import schemas

    album_schema = schemas.Album.model_validate(db_album)
    album_data = album_schema.model_dump()

    # Récupérer le chemin du dossier de l'album
    album_folder = folder.get_album_folder_path(db_album)  # à adapter selon ta logique
    if not os.path.exists(album_folder):
        os.makedirs(album_folder)
    json_path = os.path.join(album_folder, "album.json")

    # Sauvegarder le JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(album_data, f, ensure_ascii=False, indent=4)

    return JSONResponse(content={"message": f"album.json créé dans {album_folder}"})


##################################################################
# cover image section

# Extensions autorisées pour l'image de couverture — allowlist stricte, vérifiée
# AVANT toute écriture disque (durcissement path-traversal / arbitrary-write).
_COVER_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
# Taille maximale d'une image de couverture (10 Mo) — cohérent avec la copie UI.
_COVER_MAX_BYTES = 10 * 1024 * 1024


def _sanitize_path_component(component: str) -> str:
    """Neutralise un composant de chemin dérivé des données de l'album.

    Retire les séparateurs et séquences de remontée (``..``) pour empêcher toute
    évasion hors du répertoire de l'album lors du ``os.path.join``. Défense en
    profondeur : les données proviennent de la DB et sont déjà formatées côté
    ``folder``, mais on re-sanitize avant l'écriture.
    """
    cleaned = (component or "").replace("\\", "").replace("/", "").replace("..", "")
    return cleaned.strip()


# upload de l'image de couverture (multipart) — réservé aux superusers.
@router.post("/upload_cover/{album_id}", dependencies=[Depends(require_superuser)])
async def upload_cover(album_id: int, db: db_dependency, image_cover: UploadFile = File(...)):
    """Téléverse l'image de couverture d'un album (superusers uniquement).

    Durcissement (correctif live path-traversal / arbitrary-write) :
    - le nom de fichier est réduit à son ``basename`` puis rejeté s'il est vide, ``.`` ou ``..`` ;
    - l'extension doit appartenir à une allowlist stricte AVANT toute écriture ;
    - la taille est bornée (lecture capée) ;
    - les octets sont vérifiés comme image valide via PIL (magic bytes) ;
    - les composants de dossier (catégorie/album) sont re-sanitizés contre ``..``.

    L'image est écrite dans ``images/{cat}/{album}/{filename}`` et une vignette est
    générée dans ``thumbnails/{cat}/{album}/{filename}`` (parité avec l'ancien flux
    Jinja ``_save_cover_image``). ``album.image_cover`` est mis à jour dans le même
    handler (pas de PATCH update_album additionnel : évite un renommage de dossier
    et un point de défaillance supplémentaire). Idempotent (makedirs exist_ok=True).
    """
    db_album = crud.get_album_by_id_with_category(db, album_id=album_id)
    if db_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # 1. Nom de fichier : basename uniquement, rejet des valeurs dangereuses/vides.
    filename = os.path.basename(image_cover.filename or "")
    if filename in ("", ".", ".."):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide")

    # 2. Allowlist d'extension (AVANT toute écriture).
    _, ext = os.path.splitext(filename)
    if ext.lower() not in _COVER_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Extension non autorisée (formats acceptés : jpg, jpeg, png, webp, gif)",
        )

    # 3. Borne de taille : lecture capée à la limite + 1 octet pour détecter le dépassement.
    contents = await image_cover.read(_COVER_MAX_BYTES + 1)
    if len(contents) > _COVER_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image trop volumineuse (max 10 Mo)")
    if not contents:
        raise HTTPException(status_code=400, detail="Fichier vide")

    # 4. Vérification magic bytes : le contenu doit être une image réellement valide.
    try:
        PILImage.open(BytesIO(contents)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Le fichier n'est pas une image valide")

    # 5. Chemins de dossier sanitizés (défense en profondeur contre `..`/séparateurs).
    category_folder = _sanitize_path_component(folder.get_category_folder_name(db_album))
    album_folder = _sanitize_path_component(folder.get_album_folder_name(db_album))
    if not category_folder or not album_folder:
        raise HTTPException(status_code=400, detail="Chemin d'album invalide")

    images_dir = os.path.join(image.image_path, category_folder, album_folder)
    thumbnails_dir = os.path.join(image.thumbnails_path, category_folder, album_folder)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(thumbnails_dir, exist_ok=True)

    # Défense finale : le chemin résolu doit rester CONFINÉ sous images_dir.
    image_path_full = os.path.join(images_dir, filename)
    if os.path.commonpath([os.path.abspath(images_dir), os.path.abspath(image_path_full)]) != os.path.abspath(
        images_dir
    ):
        raise HTTPException(status_code=400, detail="Chemin de fichier invalide")

    with open(image_path_full, "wb") as f:
        f.write(contents)

    # Génération de la vignette avec correction d'orientation EXIF (parité _save_cover_image).
    thumbnail_path_full = os.path.join(thumbnails_dir, filename)
    try:
        img = PILImage.open(BytesIO(contents))
        img.thumbnail((image.thumbnail_width, image.thumbnail_height), PILImage.Resampling.LANCZOS)
        try:
            exif = img._getexif()
            if exif:
                orientation_tag = next((k for k, v in TAGS.items() if v == "Orientation"), None)
                if orientation_tag and orientation_tag in exif:
                    orientation = exif[orientation_tag]
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
        except Exception:
            pass
        img.save(thumbnail_path_full, quality=85, optimize=True)
        logger.info(f"Thumbnail de couverture créé: {thumbnail_path_full}")
    except Exception as e:
        logger.error(f"Erreur création thumbnail de couverture: {e}")
        with open(thumbnail_path_full, "wb") as f:
            f.write(contents)

    # Met à jour image_cover dans le même handler (pas de rename_album_folder déclenché).
    crud.update_album(db, album_id, schemas.AlbumUpdate(image_cover=filename))

    return {"image_cover": filename}


##################################################################
# categories section
# get all categories
@router.get("/get_categories/", response_model=list[schemas.Category])
def get_categories(db: db_dependency):
    return crud.get_categories(db)


# create a new category
# Réservé aux superusers (deuxième endpoint create_category masqué — parité authz
# avec be_category.create_category ; évite la création anarchique de catégories).
@router.post("/create_category/", response_model=schemas.Category, dependencies=[Depends(require_superuser)])
def create_category(category: schemas.CategoryCreate, db: db_dependency):
    # Vérification si la catégorie existe déjà
    existing_category = crud.get_category_by_name(db, category)
    if existing_category:
        raise HTTPException(status_code=400, detail="La catégorie existe déjà")
    return crud.create_category(db, category=schemas.CategoryCreate)


##################################################################
# Partage d'albums (endpoints avec authentification)
##################################################################


@router.post("/create_share_token/{album_id}", response_model=ShareTokenResponse)
async def create_share_token(
    album_id: int,
    db: db_dependency,
    current_user: Annotated[dict, Depends(get_current_user)],
    share_data: ShareTokenCreate = ShareTokenCreate(),
):
    """
    Crée un token de partage temporaire pour un album.
    L'utilisateur doit être authentifié et avoir accès à l'album.

    Authorité (triage authz turn 17) : opération orientée UTILISATEUR (tout
    utilisateur authentifié ayant accès à l'album peut le partager) — PAS une
    opération réservée aux administrateurs. Reste donc sous get_current_user.
    Suivi : audit IDOR du contrôle d'accès album (TODO ci-dessous).
    """
    # Vérifier que l'album existe
    db_album = crud.get_album_by_id(db, album_id)
    if not db_album:
        raise HTTPException(status_code=404, detail="Album introuvable")

    # TODO: Vérifier que l'utilisateur a accès à cet album
    # (vérifier via UserAlbum ou AlbumGroup)

    # Générer ou utiliser le PIN fourni
    pin = share_data.pin if share_data.pin else generate_pin(6)

    # Valider le format du PIN (6 caractères alphanumériques)
    if len(pin) != 6 or not pin.isalnum():
        raise HTTPException(
            status_code=400,
            detail="Le code PIN doit contenir exactement 6 caractères alphanumériques (lettres et chiffres uniquement)",
        )

    # Créer le token
    token, expires_at = create_album_share_token(
        album_id=album_id, pin=pin.upper(), expiration_hours=share_data.expiration_hours  # Stocker en majuscules
    )

    return ShareTokenResponse(
        share_token=token,
        share_url=f"{password_reset.frontend_url}/album/shared?token={token}",
        pin=pin.upper(),
        expires_at=expires_at,
    )


##################################################################
# Accès public aux albums partagés (SANS authentification)
##################################################################


@public_router.get("/shared", response_model=schemas.Album_Category)
async def get_shared_album(
    db: db_dependency,
    token: str = Query(..., description="Token de partage JWT"),
    pin: str = Query(..., description="Code PIN à 6 caractères", min_length=6, max_length=6),
):
    """
    Accède à un album partagé via token et code PIN.
    Aucune authentification utilisateur requise.
    """
    # Vérifier le token et le PIN
    album_id = verify_share_token(db, token, pin.upper())

    # Récupérer l'album
    db_album = crud.get_album_by_id_with_category(db, album_id)
    if not db_album:
        raise HTTPException(status_code=404, detail="Album introuvable")

    return db_album
