import time

from sqlalchemy.orm import Session

from utils.password import get_password_hash

from . import models, schemas


##################################################################
# album section
# On récupère un album par son id
def get_album_by_id(db: Session, album_id: int):
    return db.query(models.Album).filter(models.Album.id == album_id).first()


# On récupère tous les albums
def get_all_albums_with_category(db: Session):
    response = (
        db.query(
            models.Album.id,
            models.Album.title,
            models.Album.description,
            models.Album.date,
            models.Album.participants,
            models.Album.location,
            models.Album.tags,
            models.Album.image_cover,
            models.Album.category_id,
            models.Category.category.label("category"),
        )
        .join(models.Category)
        .order_by(models.Album.date.desc())
        .all()
    )
    return response
    # TIPS garder comme ref dans le cas ou !!!
    # reponse est de la forme [(1, 'titre', 'description', 'date', 'participants', 'lieu', 'tags', 'image_couverture', 'categorie_id', 'categorie_name'), ...]
    # il faut le convertir en une liste de dictionnaire avec des {} et pas des () pour que le format de la reponse corresponde au modele de reponse attendu
    # Format the response to match the expected response model using json
    # albums_with_categories = [
    #     {
    #         'id': album.id,
    #         ...
    #         'categorie_id': album.categorie_id,
    #         'categorie': album.categorie_name,
    #         # il est possible de le faire de cette maniere aussi dans le cas d'une liste de groupe par ex
    #         # 'categorie': {
    #         #     'categorie': album.categorie_name
    #         # }
    #     }
    # TIPS     for album in response
    # ]

    # return albums_with_categories


# On récupère un album par son id
def get_album_by_id_with_category(db: Session, album_id: int):
    response = (
        db.query(
            models.Album.id,
            models.Album.title,
            models.Album.description,
            models.Album.date,
            models.Album.participants,
            models.Album.location,
            models.Album.tags,
            models.Album.image_cover,
            models.Album.category_id,
            models.Category.category.label("category"),
        )
        .join(models.Category)
        .filter(models.Album.id == album_id)
        .first()
    )
    return response


# création d'un album
def create_album(db: Session, album: schemas.AlbumCreate):
    db_album = models.Album(
        title=album.title,
        description=album.description,
        date=album.date,
        participants=album.participants,
        location=album.location,
        tags=album.tags,
        image_cover=album.image_cover,
        category_id=album.category_id,
    )
    db.add(db_album)
    db.commit()
    db.refresh(db_album)
    return db_album


# On met à jour un album
def update_album(db: Session, album_id: int, album: schemas.AlbumUpdate):
    db_album = get_album_by_id(db, album_id=album_id)
    if album.title is not None:
        db_album.title = album.title
    if album.description is not None:
        db_album.description = album.description
    if album.date is not None:
        db_album.date = album.date
    if album.participants is not None:
        db_album.participants = album.participants
    if album.location is not None:
        db_album.location = album.location
    if album.tags is not None:
        db_album.tags = album.tags
    if album.image_cover is not None:
        db_album.image_cover = album.image_cover
    if album.category_id is not None:
        db_album.category_id = album.category_id
    db.add(db_album)
    db.commit()
    db.refresh(db_album)
    return db_album


##################################################################
# Utilisateur section
# On récupère un utilisateur
def get_all_users_info(db: Session):
    return db.query(models.User).all()


# On récupère un utilisateur par son email
def get_user_info_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


# on récurpère un utilisateur par son id
def get_user_info_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


# On crée un utilisateur
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        firstname=user.firstname,
        lastname=user.lastname,
        email=user.email,
        password=hashed_password,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# On met à jour un utilisateur
def update_password_user(db: Session, user: schemas.User, password: str):
    db_user = get_user_info_by_id(db, user_id=user.id)
    db_user.password = password
    db.commit()
    db.refresh(db_user)
    return db_user


# On active un utilisateur
def activate_user(db: Session, user: schemas.User, is_active: bool):
    db_user = get_user_info_by_id(db, user_id=user.id)
    db_user.is_active = is_active
    db.commit()
    db.refresh(db_user)
    return db_user


# On passe un utilisateur en admin
def admin_user(db: Session, user: schemas.User, is_superuser: bool):
    db_user = get_user_info_by_id(db, user_id=user.id)
    db_user.is_superuser = is_superuser
    db.commit()
    db.refresh(db_user)
    return db_user


# Récupérer les utilisateurs en attente de validation (is_active = False)
def get_pending_users(db: Session):
    """Récupère tous les utilisateurs en attente d'activation"""
    return db.query(models.User).filter(models.User.is_active == False).all()


# Récupérer tous les utilisateurs avec filtres optionnels
def get_all_users_filtered(db: Session, is_active: bool = None, is_superuser: bool = None):
    """Récupère les utilisateurs avec filtres optionnels sur is_active et is_superuser"""
    query = db.query(models.User)
    if is_active is not None:
        query = query.filter(models.User.is_active == is_active)
    if is_superuser is not None:
        query = query.filter(models.User.is_superuser == is_superuser)
    return query.all()


# Suppression d'un utilisateur
def delete_user(db: Session, user_id: int):
    db_user = get_user_info_by_id(db, user_id=user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
    return db_user


# Mise à jour générale des informations utilisateur
def update_user_info(db: Session, user_id: int, user_update: schemas.UserCreate):
    db_user = get_user_info_by_id(db, user_id=user_id)
    if not db_user:
        return None
    if user_update.firstname is not None:
        db_user.firstname = user_update.firstname
    if user_update.lastname is not None:
        db_user.lastname = user_update.lastname
    if user_update.email is not None:
        db_user.email = user_update.email
    db.commit()
    db.refresh(db_user)
    return db_user


# Mise à jour du profil utilisateur (Tâche 210)
def update_user_profile(db: Session, user_id: int, profile_update: schemas.UserProfileUpdate):
    """Met à jour le profil utilisateur (prénom, nom, email)"""
    db_user = get_user_info_by_id(db, user_id=user_id)
    if not db_user:
        return None
    db_user.firstname = profile_update.firstname
    db_user.lastname = profile_update.lastname
    db_user.email = profile_update.email
    db.commit()
    db.refresh(db_user)
    return db_user


##################################################################
# section pour les tables de jointure
# on recupere les albums d'un utilisateur
def get_albums_by_user(db: Session, user_id: int):
    return db.query(models.UserAlbum).filter(models.UserAlbum.user_id == user_id).all()


# on recupère le lien entre un utilisateur et un album id
def get_usersid_albumid_link(db: Session, album_id: int, user_id: int):
    return (
        db.query(models.UserAlbum)
        .filter(models.UserAlbum.album_id == album_id, models.UserAlbum.user_id == user_id)
        .first()
    )


# on cree le lien entre un utilisateur et un album
def create_userid_albumid_link(db: Session, user_album: schemas.User_AlbumCreate):
    db_user_album = models.UserAlbum(user_id=user_album.user_id, album_id=user_album.album_id)
    db.add(db_user_album)
    db.commit()
    db.refresh(db_user_album)
    return db_user_album


# on recupere les utilisateurs d'un groupe
def get_users_by_group(db: Session, group_id: int):
    return db.query(models.UserGroup).filter(models.UserGroup.group_id == group_id).all()


# Récupérer les albums d'un groupe
def get_albums_by_group(db: Session, group_id: int):
    return db.query(models.AlbumGroup).filter(models.AlbumGroup.group_id == group_id).all()


# Récupérer les albums id d'une liste de groupes
# groupes_ids est une liste d'id de groupes, par exemple [1, 2, 3]
# pour que la requete fonctionne, il faut que cela soit une liste et qu'elle contienne plus d'un element.
def get_albums_id_by_groups(db: Session, groups_ids):
    """
    groups_ids peut être une liste d'objets UserGroup ou une liste d'entiers (group_id).
    Cette fonction extrait les IDs si besoin et retourne les AlbumGroup correspondants.
    """
    # Si la liste est vide
    if not groups_ids:
        return []
    # Si ce sont des objets UserGroup, on extrait les IDs
    if hasattr(groups_ids[0], "group_id"):
        ids = [g.group_id for g in groups_ids]
    else:
        ids = groups_ids
    return db.query(models.AlbumGroup).filter(models.AlbumGroup.group_id.in_(ids)).all()


# Récupérer les groupes d'un utilisateur
def get_groups_id_by_user(db: Session, user_id: int):
    return db.query(models.UserGroup).filter(models.UserGroup.user_id == user_id).all()


# Supprimer un lien utilisateur-album
def delete_userid_albumid_link(db: Session, album_id: int, user_id: int):
    link = (
        db.query(models.UserAlbum)
        .filter(models.UserAlbum.album_id == album_id, models.UserAlbum.user_id == user_id)
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
    return link


# Supprimer un lien utilisateur-groupe
def delete_user_group_link(db: Session, user_id: int, group_id: int):
    link = (
        db.query(models.UserGroup)
        .filter(models.UserGroup.user_id == user_id, models.UserGroup.group_id == group_id)
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
    return link


# Supprimer un lien album-groupe
def delete_album_group_link(db: Session, album_id: int, group_id: int):
    link = (
        db.query(models.AlbumGroup)
        .filter(models.AlbumGroup.album_id == album_id, models.AlbumGroup.group_id == group_id)
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
    return link


##################################################################
# Catégorie section
# On recupère les catégories
def get_categories(db: Session):
    return db.query(models.Category).all()


def get_all_categories(db: Session):
    """
    Retourne toutes les catégories.
    """
    return db.query(models.Category).all()


def get_category_id_by_category(db: Session, category: str):
    return db.query(models.Category).filter(models.Category.category == category).first()


def get_category_by_name(db: Session, category_name: str):
    return db.query(models.Category).filter(models.Category.category == category_name).first()


def create_category(db: Session, category: schemas.CategoryCreate):
    db_category = models.Category(
        category=category.category,
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


##################################################################
# section pour les groupes
# creation d'un groupe
def get_group_by_name(db: Session, group_name: str):
    return db.query(models.Group).filter(models.Group.name == group_name).first()


def get_all_groups(db: Session):
    return db.query(models.Group).all()


def create_group(db: Session, group: schemas.GroupCreate):
    db_group = models.Group(
        name=group.name,
        description=group.description,
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


# Mise à jour d'un groupe (Tâche 270)
def update_group(db: Session, group_id: int, group_update: schemas.GroupUpdate):
    """Met à jour le nom et la description d'un groupe"""
    db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not db_group:
        return None
    db_group.name = group_update.name
    db_group.description = group_update.description
    db.commit()
    db.refresh(db_group)
    return db_group


# Suppression d'un groupe (Tâche 270)
def delete_group(db: Session, group_id: int):
    """Supprime un groupe et tous ses liens (utilisateurs et albums)"""
    db_group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not db_group:
        return None
    # Supprimer d'abord les liens utilisateur-groupe
    db.query(models.UserGroup).filter(models.UserGroup.group_id == group_id).delete()
    # Supprimer les liens album-groupe
    db.query(models.AlbumGroup).filter(models.AlbumGroup.group_id == group_id).delete()
    # Supprimer le groupe
    db.delete(db_group)
    db.commit()
    return db_group


# creation d'un lien utilisateur-groupe
def create_user_group(db: Session, user_group: schemas.User_GroupCreate):
    # On verifie si le lien existe deja
    existing_link = (
        db.query(models.UserGroup)
        .filter(models.UserGroup.user_id == user_group.user_id, models.UserGroup.group_id == user_group.group_id)
        .first()
    )
    if existing_link:
        return existing_link
    db_user_group = models.UserGroup(user_id=user_group.user_id, group_id=user_group.group_id)
    db.add(db_user_group)
    db.commit()
    db.refresh(db_user_group)
    return db_user_group


# creation d'un lien album-groupe
def create_album_group(db: Session, album_group: schemas.Album_GroupCreate):
    db_album_group = models.AlbumGroup(album_id=album_group.album_id, group_id=album_group.group_id)
    db.add(db_album_group)
    db.commit()
    db.refresh(db_album_group)
    return db_album_group


def create_album_groups_bulk(db: Session, album_id: int, group_ids: list[int]):
    """
    Crée en bulk les liens album ↔ groupes pour un `album_id` et une liste de `group_ids`.
    Ignore les liens déjà existants et insère uniquement les nouveaux.
    Retourne un dict { created: n, skipped: m }.
    """
    if not group_ids:
        return {"created": 0, "skipped": 0}

    # Récupérer les group_id déjà liés à cet album
    existing = (
        db.query(models.AlbumGroup.group_id)
        .filter(models.AlbumGroup.album_id == album_id, models.AlbumGroup.group_id.in_(group_ids))
        .all()
    )
    existing_ids = {r.group_id for r in existing}

    to_create = [gid for gid in group_ids if gid not in existing_ids]
    created = 0
    skipped = len(group_ids) - len(to_create)

    if to_create:
        objects = [models.AlbumGroup(album_id=album_id, group_id=gid) for gid in to_create]
        try:
            db.bulk_save_objects(objects)
            db.commit()
            created = len(objects)
        except Exception:
            db.rollback()
            # fallback to individual inserts
            created = 0
            for obj in objects:
                try:
                    db.add(obj)
                    db.commit()
                    created += 1
                except Exception:
                    db.rollback()
    return {"created": created, "skipped": skipped}


# on recupere les liens utilisateurs groupes
def get_all_users_groups_links(db: Session):
    """
    Retourne tous les liens utilisateur-groupe.
    """
    return db.query(models.UserGroup).all()


def get_users_and_group_names(db: Session):
    """
    Retourne une liste de tuples (firstname,lastname, group_name) pour tous les liens utilisateur-groupe.
    """
    return (
        db.query(models.User.firstname, models.User.lastname, models.Group.name)
        .join(models.UserGroup, models.User.id == models.UserGroup.user_id)
        .join(models.Group, models.UserGroup.group_id == models.Group.id)
        .all()
    )


def get_albums_and_group_names(db: Session):
    """
    Retourne une liste de tuples (album_id, album_title, group_name) pour tous les liens album-groupe.
    """
    return (
        db.query(
            # models.Album.id,
            models.Album.title,
            models.Album.description,
            models.Group.name,
        )
        .join(models.AlbumGroup, models.Album.id == models.AlbumGroup.album_id)
        .join(models.Group, models.AlbumGroup.group_id == models.Group.id)
        .all()
    )


##################################################################
# Fonctions pour la page admin de gestion des groupes (Tâches 250, 260)


def get_group_by_id(db: Session, group_id: int):
    """Récupère un groupe par son ID"""
    return db.query(models.Group).filter(models.Group.id == group_id).first()


def get_users_in_group_with_details(db: Session, group_id: int):
    """
    Récupère les utilisateurs d'un groupe avec leurs infos détaillées.
    Retourne une liste de dictionnaires.
    """
    result = (
        db.query(models.User.id, models.User.firstname, models.User.lastname, models.User.email)
        .join(models.UserGroup, models.User.id == models.UserGroup.user_id)
        .filter(models.UserGroup.group_id == group_id)
        .all()
    )
    return [{"id": r.id, "firstname": r.firstname, "lastname": r.lastname, "email": r.email} for r in result]


def get_albums_in_group_with_details(db: Session, group_id: int):
    """
    Récupère les albums d'un groupe avec leurs infos détaillées.
    Retourne une liste de dictionnaires incluant les infos pour construire l'URL de couverture.
    """
    result = (
        db.query(
            models.Album.id,
            models.Album.title,
            models.Album.date,
            models.Album.image_cover,
            models.Album.participants,
            models.Category.category.label("category"),
        )
        .join(models.AlbumGroup, models.Album.id == models.AlbumGroup.album_id)
        .join(models.Category, models.Album.category_id == models.Category.id)
        .filter(models.AlbumGroup.group_id == group_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "date": str(r.date) if r.date else None,
            "image_cover": r.image_cover,
            "participants": r.participants,
            "category": r.category,
        }
        for r in result
    ]


def get_all_active_users_simple(db: Session):
    """
    Récupère tous les utilisateurs actifs (id, firstname, lastname).
    Pour les dropdowns de la page admin.
    """
    result = (
        db.query(models.User.id, models.User.firstname, models.User.lastname)
        .filter(models.User.is_active == True)
        .order_by(models.User.lastname, models.User.firstname)
        .all()
    )
    return [{"id": r.id, "firstname": r.firstname, "lastname": r.lastname} for r in result]


def get_all_albums_simple(db: Session):
    """
    Récupère tous les albums (id, title, date, category, participants, image_cover).
    Pour les dropdowns de la page admin avec vignettes.
    """
    result = (
        db.query(
            models.Album.id,
            models.Album.title,
            models.Album.date,
            models.Category.category.label("category_name"),
            models.Album.participants,
            models.Album.image_cover,
        )
        .join(models.Category, models.Album.category_id == models.Category.id)
        .order_by(models.Album.date.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "date": str(r.date) if r.date else None,
            "category": r.category_name,
            "participants": r.participants,
            "image_cover": r.image_cover,
        }
        for r in result
    ]


##################################################################
# Section pour les accès directs User ↔ Album


def get_user_album_link(db: Session, user_id: int, album_id: int):
    """
    Vérifie si un lien direct utilisateur-album existe.
    """
    return (
        db.query(models.UserAlbum)
        .filter(models.UserAlbum.user_id == user_id, models.UserAlbum.album_id == album_id)
        .first()
    )


def get_users_albums_grouped_by_album(db: Session):
    """
    Retourne tous les liens directs utilisateur-album, groupés par album.
    Format: [{ album: {id, title, date}, users: [{id, firstname, lastname}] }]
    """
    result = (
        db.query(
            models.Album.id.label("album_id"),
            models.Album.title,
            models.Album.date,
            models.Album.image_cover,
            models.User.id.label("user_id"),
            models.User.firstname,
            models.User.lastname,
        )
        .join(models.UserAlbum, models.Album.id == models.UserAlbum.album_id)
        .join(models.User, models.UserAlbum.user_id == models.User.id)
        .order_by(models.Album.date.desc(), models.User.lastname)
        .all()
    )

    albums_dict = {}
    for r in result:
        if r.album_id not in albums_dict:
            albums_dict[r.album_id] = {
                "album": {
                    "id": r.album_id,
                    "title": r.title,
                    "date": str(r.date) if r.date else None,
                    "image_cover": r.image_cover,
                },
                "users": [],
            }
        albums_dict[r.album_id]["users"].append({"id": r.user_id, "firstname": r.firstname, "lastname": r.lastname})

    return list(albums_dict.values())


def get_groups_by_album(db: Session, album_id: int):
    """
    Retourne les groupes associés à un album spécifique.
    """
    result = (
        db.query(models.Group.id, models.Group.name, models.Group.description)
        .join(models.AlbumGroup, models.Group.id == models.AlbumGroup.group_id)
        .filter(models.AlbumGroup.album_id == album_id)
        .order_by(models.Group.name)
        .all()
    )
    return [{"id": r.id, "name": r.name, "description": r.description} for r in result]


def get_users_with_direct_album_access(db: Session, album_id: int):
    """
    Retourne les utilisateurs ayant un accès direct à un album spécifique.
    """
    result = (
        db.query(models.User.id, models.User.firstname, models.User.lastname, models.User.email)
        .join(models.UserAlbum, models.User.id == models.UserAlbum.user_id)
        .filter(models.UserAlbum.album_id == album_id)
        .order_by(models.User.lastname, models.User.firstname)
        .all()
    )
    return [{"id": r.id, "firstname": r.firstname, "lastname": r.lastname, "email": r.email} for r in result]


##################################################################
# Statut durable de traitement post-upload (UPL-01)
# Réutilise la base existante — aucune infrastructure supplémentaire.


def upsert_image_processing_pending(db: Session, album_id: int, filename: str, media_type: str):
    """Crée (ou réinitialise) l'enregistrement de statut d'un fichier en ``pending``.

    Appelé de façon synchrone dans le chemin de la requête TUS, AVANT de confier
    la génération de vignette au pool de threads. La ligne est donc persistée
    durablement : un crash/redémarrage du process laisse une trace ``pending``
    plutôt qu'un original silencieusement orphelin.
    """
    now = time.time()
    entry = (
        db.query(models.ImageProcessingStatus)
        .filter(
            models.ImageProcessingStatus.album_id == album_id,
            models.ImageProcessingStatus.filename == filename,
        )
        .first()
    )
    if entry is None:
        entry = models.ImageProcessingStatus(
            album_id=album_id,
            filename=filename,
            media_type=media_type,
            status="pending",
            detail=None,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
    else:
        # Ré-upload après échec : on repart d'un état propre.
        entry.media_type = media_type
        entry.status = "pending"
        entry.detail = None
        entry.updated_at = now
    db.commit()
    db.refresh(entry)
    return entry


def set_image_processing_status(db: Session, album_id: int, filename: str, status: str, detail: str | None = None):
    """Met à jour le statut de traitement d'un fichier (``processing``/``success``/...).

    Idempotent : crée l'enregistrement s'il n'existe pas (robustesse en cas de
    perte de la ligne ``pending``).
    """
    now = time.time()
    entry = (
        db.query(models.ImageProcessingStatus)
        .filter(
            models.ImageProcessingStatus.album_id == album_id,
            models.ImageProcessingStatus.filename == filename,
        )
        .first()
    )
    if entry is None:
        entry = models.ImageProcessingStatus(
            album_id=album_id,
            filename=filename,
            media_type="unknown",
            status=status,
            detail=detail,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
    else:
        entry.status = status
        entry.detail = detail
        entry.updated_at = now
    db.commit()
    db.refresh(entry)
    return entry


def get_image_processing_status_by_album(db: Session, album_id: int):
    """Retourne tous les statuts de traitement d'un album (les plus récents d'abord)."""
    return (
        db.query(models.ImageProcessingStatus)
        .filter(models.ImageProcessingStatus.album_id == album_id)
        .order_by(models.ImageProcessingStatus.updated_at.desc())
        .all()
    )


def get_image_processing_entry(db: Session, album_id: int, filename: str):
    """Retourne l'enregistrement de statut d'un fichier précis, ou ``None``."""
    return (
        db.query(models.ImageProcessingStatus)
        .filter(
            models.ImageProcessingStatus.album_id == album_id,
            models.ImageProcessingStatus.filename == filename,
        )
        .first()
    )
