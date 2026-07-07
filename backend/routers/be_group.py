import logging

from fastapi import APIRouter, Depends, HTTPException

from utils.email import send_new_album_access_email, send_new_group_access_email

from ..db import crud, schemas
from ..db.db_connect import db_dependency
from .be_auth import get_current_user
from .be_formatter import build_cover_url

logger = logging.getLogger(__name__)

# check user.py for more comments on the following line
router = APIRouter(prefix="/be_group", tags=["backend_group"], dependencies=[Depends(get_current_user)])


##################################################################
# group section
# creation d'un groupe
@router.get("/get_all_groups/", response_model=list[schemas.Group])
def get_all_groups(db: db_dependency):
    """fonction pour récupérer tous les groupes"""
    groups = crud.get_all_groups(db)
    if not groups:
        raise HTTPException(status_code=404, detail="Aucun groupe trouvé")
    return groups


@router.get("/get_group_by_name/{group_name}", response_model=schemas.Group)
def get_group_by_name(group_name: str, db: db_dependency):
    """
    Fonction pour récupérer un groupe par son nom.
    """
    group = crud.get_group_by_name(db, group_name)
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    return group


@router.post("/create_group/", response_model=schemas.Group)
def create_group(db: db_dependency, group: schemas.GroupCreate):
    """
    Fonction pour créer un groupe.
    """
    # Vérification si le groupe existe déjà
    existing_group = crud.get_group_by_name(db, group.name)
    if existing_group:
        raise HTTPException(status_code=400, detail="Le groupe existe déjà")
    return crud.create_group(db, group)


@router.put("/update_group/{group_id}", response_model=schemas.Group)
def update_group(group_id: int, group_update: schemas.GroupUpdate, db: db_dependency):
    """
    Mise à jour d'un groupe (Tâche 270).
    Vérifie que le nouveau nom n'existe pas déjà pour un autre groupe.
    """
    # Vérifier que le groupe existe
    existing_group = crud.get_group_by_id(db, group_id)
    if not existing_group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")

    # Vérifier que le nouveau nom n'est pas déjà utilisé par un autre groupe
    group_with_name = crud.get_group_by_name(db, group_update.name)
    if group_with_name and group_with_name.id != group_id:
        raise HTTPException(status_code=400, detail="Un groupe avec ce nom existe déjà")

    updated_group = crud.update_group(db, group_id, group_update)
    return updated_group


@router.delete("/delete_group/{group_id}")
def delete_group(group_id: int, db: db_dependency):
    """
    Suppression d'un groupe (Tâche 270).
    Supprime également tous les liens utilisateurs et albums associés.
    """
    deleted_group = crud.delete_group(db, group_id)
    if not deleted_group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")
    return {"message": f"Groupe '{deleted_group.name}' supprimé avec succès", "id": group_id}


# creation d'un lien utilisateur-groupe
@router.post("/create_user_group/", response_model=schemas.User_Group)
def create_user_group(db: db_dependency, user_group: schemas.User_GroupCreate):
    """
    Fonction pour créer un lien entre un utilisateur et un groupe.
    """
    result = crud.create_user_group(db, user_group)

    # Notification email
    try:
        user = crud.get_user_info_by_id(db, user_group.user_id)
        group = crud.get_group_by_id(db, user_group.group_id)
        if user and group:
            albums_raw = crud.get_albums_in_group_with_details(db, user_group.group_id)
            album_titles = [a["title"] for a in albums_raw] if albums_raw else None
            send_new_group_access_email(user.email, user.firstname, group.name, album_titles)
    except Exception as e:
        logger.warning(f"Erreur envoi email notification groupe: {e}")

    return result


# creation de plusieurs liens utilisateurs-groupe (multi-sélection)
@router.post("/create_users_group_bulk/")
def create_users_group_bulk(db: db_dependency, request: schemas.User_GroupBulkCreate):
    """
    Crée plusieurs liens utilisateur-groupe en une seule requête.
    """
    created = 0
    skipped = 0
    created_user_ids = []
    for user_id in request.user_ids:
        try:
            crud.create_user_group(db, schemas.User_GroupCreate(user_id=user_id, group_id=request.group_id))
            created += 1
            created_user_ids.append(user_id)
        except Exception:
            skipped += 1

    # Notifications email pour les utilisateurs nouvellement ajoutés
    if created_user_ids:
        try:
            group = crud.get_group_by_id(db, request.group_id)
            albums_raw = crud.get_albums_in_group_with_details(db, request.group_id)
            album_titles = [a["title"] for a in albums_raw] if albums_raw else None
            for user_id in created_user_ids:
                user = crud.get_user_info_by_id(db, user_id)
                if user and group:
                    send_new_group_access_email(user.email, user.firstname, group.name, album_titles)
        except Exception as e:
            logger.warning(f"Erreur envoi emails notification groupe bulk: {e}")

    return {"group_id": request.group_id, "created": created, "skipped": skipped}


# creation d'un lien album-groupe
@router.post("/create_album_group/", response_model=schemas.Album_Group)
def create_album_group(db: db_dependency, album_group: schemas.Album_GroupCreate):
    """
    Fonction pour créer un lien entre un album et un groupe.
    """
    return crud.create_album_group(db, album_group)


@router.post("/create_album_groups_bulk/")
def create_album_groups_bulk(request: schemas.Album_GroupsBulkCreate, db: db_dependency):
    """
    Crée plusieurs liens (album_id -> group_ids) en une seule opération.
    Retourne le nombre de liens créés et ignorés.
    """
    result = crud.create_album_groups_bulk(db, album_id=request.album_id, group_ids=request.group_ids)
    return {"album_id": request.album_id, "created": result.get("created", 0), "skipped": result.get("skipped", 0)}


# creation de plusieurs liens albums-groupe (multi-sélection)
@router.post("/create_albums_group_bulk/")
def create_albums_group_bulk(db: db_dependency, request: schemas.Album_GroupBulkCreate):
    """
    Crée plusieurs liens album-groupe en une seule requête.
    """
    created = 0
    skipped = 0
    for album_id in request.album_ids:
        try:
            crud.create_album_group(db, schemas.Album_GroupCreate(album_id=album_id, group_id=request.group_id))
            created += 1
        except Exception:
            skipped += 1
    return {"group_id": request.group_id, "created": created, "skipped": skipped}


# récupération des liens utilisateurs groupes
@router.get("/get_users_and_group_names/")
def get_users_and_group_names(db: db_dependency):
    """
    Retourne la liste des groupes avec la liste des utilisateurs (firstname, lastname) pour chaque groupe.
    """
    result = crud.get_users_and_group_names(db)
    groups_dict = {}
    for firstname, lastname, group_name in result:
        if group_name not in groups_dict:
            groups_dict[group_name] = []
        groups_dict[group_name].append({"firstname": firstname, "lastname": lastname})
    # Construction du format demandé
    response = []
    for group_name, users in groups_dict.items():
        response.append({"group_name": group_name, "users": users})
    return response


# récupération des liens albums groupes
@router.get("/get_albums_and_group_names/")
def get_albums_and_group_names(db: db_dependency):
    """
    Retourne la liste des groupes avec la liste des albums (title) pour chaque groupe.
    """
    result = crud.get_albums_and_group_names(db)
    print(f"result : {result}")
    groups_dict = {}
    for title, description, group_name in result:
        if group_name not in groups_dict:
            groups_dict[group_name] = []
        groups_dict[group_name].append({"title": title, "description": description})
    # Construction du format demandé
    response = []
    for group_name, albums in groups_dict.items():
        response.append({"group_name": group_name, "albums": albums})
    return response


##################################################################
# Endpoints pour la page admin de gestion des groupes (Tâches 250, 260)


@router.get("/get_group_details/{group_id}")
def get_group_details(group_id: int, db: db_dependency):
    """
    Retourne les détails d'un groupe avec ses utilisateurs et albums (avec IDs).
    Format optimisé pour la page admin de gestion des accès.
    """
    # Récupérer le groupe
    group = crud.get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Groupe non trouvé")

    # Récupérer les utilisateurs du groupe avec leurs infos
    users_in_group = crud.get_users_in_group_with_details(db, group_id)

    # Récupérer les albums du groupe avec leurs infos
    albums_raw = crud.get_albums_in_group_with_details(db, group_id)

    # Ajouter les URLs de couverture aux albums
    albums_in_group = []
    for album in albums_raw:
        cover_url = (
            build_cover_url(
                category=album.get("category", ""),
                date_str=album.get("date", ""),
                title=album.get("title", ""),
                participants=album.get("participants", "") or "",
                image_cover=album.get("image_cover", ""),
            )
            if album.get("image_cover")
            else None
        )
        albums_in_group.append(
            {
                "id": album["id"],
                "title": album["title"],
                "date": album["date"],
                "image_cover": album["image_cover"],
                "image_cover_url": cover_url,
            }
        )

    return {
        "group": {"id": group.id, "name": group.name, "description": group.description},
        "users": users_in_group,
        "albums": albums_in_group,
    }


@router.get("/get_all_users_simple/")
def get_all_users_simple(db: db_dependency):
    """
    Retourne tous les utilisateurs actifs (id, firstname, lastname) pour les dropdowns.
    """
    users = crud.get_all_active_users_simple(db)
    return users


@router.get("/get_all_albums_simple/")
def get_all_albums_simple(db: db_dependency):
    """
    Retourne tous les albums (id, title, date, image_cover_url) pour les dropdowns.
    """
    albums = crud.get_all_albums_simple(db)
    # Ajouter l'URL complète de la vignette pour chaque album
    for album in albums:
        try:
            album["image_cover_url"] = build_cover_url(
                album.get("category"),
                album.get("date"),
                album.get("title"),
                album.get("participants"),
                album.get("image_cover"),
            )
        except Exception:
            album["image_cover_url"] = None
    return albums


@router.delete("/delete_user_group/{user_id}/{group_id}")
def delete_user_group_link(user_id: int, group_id: int, db: db_dependency):
    """
    Supprime le lien entre un utilisateur et un groupe.
    """
    link = crud.delete_user_group_link(db, user_id, group_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien utilisateur-groupe non trouvé")
    return {"message": "Lien supprimé avec succès", "user_id": user_id, "group_id": group_id}


@router.delete("/delete_album_group/{album_id}/{group_id}")
def delete_album_group_link(album_id: int, group_id: int, db: db_dependency):
    """
    Supprime le lien entre un album et un groupe.
    """
    link = crud.delete_album_group_link(db, album_id, group_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien album-groupe non trouvé")
    return {"message": "Lien supprimé avec succès", "album_id": album_id, "group_id": group_id}


##################################################################
# Endpoints pour les accès directs User ↔ Album (sans passer par les groupes)


@router.get("/get_users_albums_links/")
def get_users_albums_links(db: db_dependency):
    """
    Retourne tous les liens directs utilisateur-album, groupés par album.
    Format: [{ album: {id, title, date}, users: [{id, firstname, lastname}] }]
    """
    return crud.get_users_albums_grouped_by_album(db)


@router.get("/get_album_direct_users/{album_id}")
def get_album_direct_users(album_id: int, db: db_dependency):
    """
    Retourne les utilisateurs ayant un accès direct à un album spécifique.
    """
    album = crud.get_album_by_id_with_category(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    # Construire l'URL de la couverture
    cover_url = (
        build_cover_url(
            category=album.category,
            date_str=str(album.date),
            title=album.title,
            participants=album.participants or "",
            image_cover=album.image_cover,
        )
        if album.image_cover
        else None
    )

    users = crud.get_users_with_direct_album_access(db, album_id)
    return {
        "album": {
            "id": album.id,
            "title": album.title,
            "date": album.date,
            "image_cover": album.image_cover,
            "image_cover_url": cover_url,
        },
        "users": users,
    }


@router.get("/get_album_groups/{album_id}")
def get_album_groups(album_id: int, db: db_dependency):
    """
    Retourne les groupes associés à un album spécifique.
    """
    album = crud.get_album_by_id(db, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    groups = crud.get_groups_by_album(db, album_id)
    return groups


@router.post("/create_user_album/")
def create_user_album_link(db: db_dependency, user_album: schemas.User_AlbumCreate):
    """
    Crée un lien direct entre un utilisateur et un album.
    """
    # Vérifier si le lien existe déjà
    existing = crud.get_user_album_link(db, user_album.user_id, user_album.album_id)
    if existing:
        raise HTTPException(status_code=400, detail="L'utilisateur a déjà accès à cet album")

    result = crud.create_userid_albumid_link(db, user_album)

    # Notification email
    try:
        user = crud.get_user_info_by_id(db, user_album.user_id)
        album = crud.get_album_by_id(db, user_album.album_id)
        if user and album:
            send_new_album_access_email(user.email, user.firstname, album.title)
    except Exception as e:
        logger.warning(f"Erreur envoi email notification album direct: {e}")

    return result


# creation de plusieurs accès directs utilisateurs-album (multi-sélection)
@router.post("/create_users_album_bulk/")
def create_users_album_bulk(db: db_dependency, request: schemas.User_AlbumBulkCreate):
    """
    Crée plusieurs liens directs utilisateur-album en une seule requête.
    """
    created = 0
    skipped = 0
    created_user_ids = []
    for user_id in request.user_ids:
        existing = crud.get_user_album_link(db, user_id, request.album_id)
        if existing:
            skipped += 1
        else:
            try:
                crud.create_userid_albumid_link(
                    db, schemas.User_AlbumCreate(user_id=user_id, album_id=request.album_id)
                )
                created += 1
                created_user_ids.append(user_id)
            except Exception:
                skipped += 1

    # Notifications email pour les utilisateurs nouvellement ajoutés
    if created_user_ids:
        try:
            album = crud.get_album_by_id(db, request.album_id)
            for user_id in created_user_ids:
                user = crud.get_user_info_by_id(db, user_id)
                if user and album:
                    send_new_album_access_email(user.email, user.firstname, album.title)
        except Exception as e:
            logger.warning(f"Erreur envoi emails notification album bulk: {e}")

    return {"album_id": request.album_id, "created": created, "skipped": skipped}


@router.delete("/delete_user_album/{user_id}/{album_id}")
def delete_user_album_link(user_id: int, album_id: int, db: db_dependency):
    """
    Supprime le lien direct entre un utilisateur et un album.
    """
    link = crud.delete_userid_albumid_link(db, album_id, user_id)
    if not link:
        raise HTTPException(status_code=404, detail="Lien utilisateur-album non trouvé")
    return {"message": "Accès direct supprimé", "user_id": user_id, "album_id": album_id}
