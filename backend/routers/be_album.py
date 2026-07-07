import json
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from utils.config import password_reset

from ..albums import folder
from ..db import crud, schemas
from ..db.db_connect import db_dependency
from .be_auth import (
    ShareTokenCreate,
    ShareTokenResponse,
    create_album_share_token,
    generate_pin,
    get_current_user,
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
@router.post("/create_album/", response_model=schemas.Album)
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
@router.patch("/update_album/{album_id}", response_model=schemas.Album)
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
@router.get("/create_album_folder/{album_id}")
def create_album_folder(album_id: int, db: db_dependency):
    db_album = crud.get_album_by_id(db, album_id=album_id)
    if db_album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")
    folder.create_album_folder(db_album)


# export album to json
@router.post("/export_album_json/{album_id}")
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
# categories section
# get all categories
@router.get("/get_categories/", response_model=list[schemas.Category])
def get_categories(db: db_dependency):
    return crud.get_categories(db)


# create a new category
@router.post("/create_category/", response_model=schemas.Category)
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
