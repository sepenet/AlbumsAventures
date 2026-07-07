import os
import random
import re
from datetime import datetime

import cv2
import PIL
from exiftool import ExifToolHelper
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from utils.config import image as image_config

from ..albums.folder import get_album_paths
from ..db import crud, schemas
from ..db.db_connect import db_dependency
from .be_auth import get_current_user

# Créer le router avec les mêmes paramètres que les autres routers
router = APIRouter(prefix="/be_resizer", tags=["backend_resizer"], dependencies=[Depends(get_current_user)])

# Extensions supportées
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp")
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")

# Limites de taille de fichiers pour l'upload
MAX_IMAGE_SIZE = 30 * 1024 * 1024  # 30 MB par image
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB par vidéo
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB par requête

import logging

logger = logging.getLogger(__name__)


def verify_album_access(db, user_id: int, album_id: int) -> bool:
    """
    Vérifie si l'utilisateur a accès à l'album (directement ou via un groupe).

    Args:
        db: Session de base de données
        user_id: ID de l'utilisateur
        album_id: ID de l'album

    Returns:
        True si l'utilisateur a accès, False sinon
    """
    # Vérifier l'accès direct utilisateur-album
    direct_link = crud.get_usersid_albumid_link(db, album_id=album_id, user_id=user_id)
    if direct_link:
        return True

    # Vérifier l'accès via les groupes de l'utilisateur
    user_groups = crud.get_groups_id_by_user(db, user_id=user_id)
    if user_groups:
        group_albums = crud.get_albums_id_by_groups(db, user_groups)
        album_ids = [ga.album_id for ga in group_albums]
        if album_id in album_ids:
            return True

    return False


def video_create_thumbnail(
    video_path: str, thumbnail_path: str, size: tuple = (300, 200), frame_position: float = 1.0
) -> bool:
    """
    Génère une vignette à partir d'une vidéo en utilisant OpenCV.

    Args:
        video_path: Chemin vers le fichier vidéo source
        thumbnail_path: Chemin où sauvegarder la vignette (format jpg)
        size: Tuple (largeur, hauteur) de la vignette
        frame_position: Position en secondes dans la vidéo pour capturer la frame

    Returns:
        True si la vignette a été créée, False sinon
    """
    try:
        # Ouvrir la vidéo (OpenCV ne gère pas les accents, on utilise numpy pour lire)
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Impossible d'ouvrir la vidéo: {video_path}")
            return False

        # Obtenir le FPS et calculer le numéro de frame
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or total_frames <= 0:
            # Fallback: prendre la première frame
            frame_number = 0
        else:
            # Calculer la frame à la position demandée (en secondes)
            frame_number = int(frame_position * fps)
            # S'assurer qu'on ne dépasse pas le nombre total de frames
            frame_number = min(frame_number, total_frames - 1)

        # Se positionner à la frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

        # Lire la frame
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            print(f"Impossible de lire la frame {frame_number} de {video_path}")
            return False

        # Redimensionner en préservant le ratio
        height, width = frame.shape[:2]
        target_width, target_height = size

        # Calculer le ratio de redimensionnement
        scale = min(target_width / width, target_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        # Redimensionner
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Créer une image avec padding noir si nécessaire (pour centrer)
        thumbnail = cv2.copyMakeBorder(
            resized,
            top=(target_height - new_height) // 2,
            bottom=(target_height - new_height + 1) // 2,
            left=(target_width - new_width) // 2,
            right=(target_width - new_width + 1) // 2,
            borderType=cv2.BORDER_CONSTANT,
            value=[0, 0, 0],  # Noir
        )

        # Sauvegarder en JPEG - utiliser imencode + écriture Python
        # pour gérer les chemins avec caractères accentués (Windows)
        success, encoded_img = cv2.imencode(".jpg", thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if success:
            with open(thumbnail_path, "wb") as f:
                f.write(encoded_img.tobytes())

        if os.path.exists(thumbnail_path):
            return True
        else:
            return False

    except Exception as e:
        print(f"Erreur lors de la création de la vignette vidéo avec OpenCV: {e}")
        return False


# Définir les fonctions utilitaires qui seront appelées par les endpoints
def img_thumbnails(img_path, tb_path, size):
    """
    Crée des miniatures pour toutes les images dans le dossier img_path et les enregistre dans tb_path.
    Si la vignette existe déjà, on ne la recrée pas.
    Les images sont parcourues récursivement dans img_path.
    Si le fichier n'est pas une image supportée, il est ignoré.
    Les miniatures sont créées avec la taille spécifiée par size.
    """
    # on crée 3 variables pour compter les vignettes existantes, les vignettes créées et les images non supportées
    # c'est ce que la fonction retourne
    tbn_exist = 0
    img_not_supported = 0
    tbn_created = 0
    for dirpath, dirnames, filenames in os.walk(img_path):
        for filename in filenames:
            filename_lower = filename.lower()

            # Traitement des images
            if filename_lower.endswith(IMAGE_EXTENSIONS):
                # on verifie si la vignette existe déja
                if os.path.exists(os.path.join(tb_path, filename)):
                    print(f"La miniature {filename} existe déjà dans {tb_path}.")
                    tbn_exist += 1
                    continue
                img = Image.open(os.path.join(dirpath, filename))
                # Récupération des métadonnées EXIF pour corriger l'orientation
                # avant le redimensionnement (sinon les photos en portrait apparaissent
                # couchées dans les vignettes)
                exif_data = img_get_exif_data(os.path.join(dirpath, filename))
                orientation = exif_data.get("Orientation", 1)
                # Mapping orientation EXIF -> rotation PIL (degrés anti-horaires)
                rotation_map = {3: 180, 6: 270, 8: 90}
                if orientation in rotation_map:
                    img = img.rotate(rotation_map[orientation], expand=True)
                img.thumbnail(size, PIL.Image.Resampling.LANCZOS)
                img.save(os.path.join(tb_path, filename), quality=100, exif=img.info.get("exif"))
                tbn_created += 1

            # Traitement des vidéos
            elif filename_lower.endswith(VIDEO_EXTENSIONS):
                # Pour les vidéos, la vignette aura l'extension .jpg
                name, _ = os.path.splitext(filename)
                thumbnail_filename = f"{name}.jpg"
                thumbnail_path = os.path.join(tb_path, thumbnail_filename)

                if os.path.exists(thumbnail_path):
                    print(f"La miniature vidéo {thumbnail_filename} existe déjà dans {tb_path}.")
                    tbn_exist += 1
                    continue

                # Créer la vignette avec FFmpeg
                video_path = os.path.join(dirpath, filename)
                if video_create_thumbnail(video_path, thumbnail_path, size):
                    print(f"Vignette vidéo créée: {thumbnail_filename}")
                    tbn_created += 1
                else:
                    print(f"Impossible de créer la vignette pour la vidéo {filename}")
                    img_not_supported += 1
            else:
                print(f"Le fichier {filename} n'est pas un format supporté.")
                img_not_supported += 1

    return {"tbn_exist": tbn_exist, "tbn_created": tbn_created, "img_not_supported": img_not_supported}


def img_get_exif_data(img_file):
    exif_metadata = {}
    try:
        with ExifToolHelper() as eth:
            metadata = eth.get_tags(
                img_file, tags=["DateTimeOriginal", "ModifyDate", "FileModifyDate", "ModifyDatefile", "Orientation"]
            )
            for d in metadata:
                # si EXIF:DateTimeOriginal existe on le prend comme date de l'image
                if "EXIF:DateTimeOriginal" in d:
                    date_exif_str = d["EXIF:DateTimeOriginal"]
                    date_exif = datetime.strptime(date_exif_str, "%Y:%m:%d %H:%M:%S")
                # sinon si XMP:DateTimeOriginal existe on le prend comme date de l'image
                elif "XMP:DateTimeOriginal" in d:
                    date_exif_str = d["XMP:DateTimeOriginal"]
                    date_exif = datetime.strptime(date_exif_str, "%Y:%m:%d %H:%M:%S")
                # sinon on recupère les 3 valeures ModifyDate, FILE:FileModifyDate, File:ModifyDate
                # on prend la date la plus ancienne
                else:
                    if "ModifyDate" in d:
                        modify_date = datetime.strptime(d["ModifyDate"], "%Y:%m:%d %H:%M:%S")
                    else:
                        modify_date = datetime.strptime("9999:12:31 23:59:59", "%Y:%m:%d %H:%M:%S")
                    if "File:FileModifyDate" in d:
                        file_file_modify_date = datetime.strptime(d["File:FileModifyDate"], "%Y:%m:%d %H:%M:%S+00:00")
                    else:
                        file_file_modify_date = datetime.strptime("9999:12:31 23:59:59", "%Y:%m:%d %H:%M:%S")
                    if "File:ModifyDate" in d:
                        file_modify_date = datetime.strptime(d["File:ModifyDate"], "%Y:%m:%d %H:%M:%S")
                    else:
                        file_modify_date = datetime.strptime("9999:12:31 23:59:59", "%Y:%m:%d %H:%M:%S")
                    date_exif = min(modify_date, file_file_modify_date, file_modify_date)
                # on recupère l'orientation de l'image
                if "EXIF:Orientation" in d:
                    exif_metadata["Orientation"] = d["EXIF:Orientation"]
                else:
                    # on tente sa chance et on force le format à horizontal
                    exif_metadata["Orientation"] = 1
                # on format la date pour la rendre utilisable dans le nom du fichier YYYY:MM:DD HH:MM:SS -> YYYYMMDD_HHMMSS
                exif_metadata["DateTimeOriginal"] = date_exif.strftime("%Y%m%d_%H%M%S")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction des données EXIF: {str(e)}")
    return exif_metadata


# renommer les fichiers dans le dossier de l'album en fonction des données exif
def add_date_taken_to_image_file(album: dict):
    """renommer les fichiers dans le dossier de l'album en fonction des données exif de chaque fichier photo contenu dans le répertoire de l'album"""
    # on récupère le chemin complet des fichiers d'images
    folderPathImages_Name, folderPathThumbnails_Name = get_album_paths(album)
    if not os.path.exists(folderPathImages_Name):
        raise FileNotFoundError(f"Le dossier de l'album {album['title']} n'existe pas.")

    # On parcours tous les fichiers, on récupère les données exif pour construire le nouveau nom du fichier.
    for filename in os.listdir(folderPathImages_Name):
        # on construit le nom actual du fichier avec son chemin d'accés
        old_file_path = os.path.join(folderPathImages_Name, filename)
        # on extrait la date de prise de vue des données exif
        exif_data = img_get_exif_data(old_file_path)
        # on verifie si le nom actuel contient déjà la date de prise de vue "YYYYMMDD_HHMMSS" en début de nom et suivi par un underscore
        date_str = exif_data.get("DateTimeOriginal", "").replace(":", "").replace(" ", "_")
        if re.search(rf"^{date_str}_", filename):
            # continue  # Le nom contient déjà la date, on passe au suivant
            print(f"Le fichier {filename} contient déjà la date de prise de vue dans son nom.")
            continue
        # Renommer le fichier en exif_data_<old name>.extension
        date_taken = exif_data.get("DateTimeOriginal")
        new_file_name = f"{date_taken}_{filename}"
        new_file_path = os.path.join(folderPathImages_Name, new_file_name)
        os.rename(old_file_path, new_file_path)


# check the img file extension
ALLOWED_EXTENSIONS = set(["heic", "mp4", "avi", "png", "jpg", "jpeg", "gif"])


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# choose random file from folder album
def choose_random_file(album_path):
    files_list = os.listdir(album_path)
    random_file = random.choice(files_list)
    return random_file


# Note: get_album_paths() est maintenant importé depuis backend.albums.folder
# pour éviter la duplication de code

##################################################################
# Endpoints section


@router.get("/create_thumbnails/{album_id}")
async def create_thumbnails(
    album_id: int,
    db: db_dependency,
    width: int = image_config.thumbnail_width,
    height: int = image_config.thumbnail_height,
):
    """
    Créer des miniatures pour toutes les images d'un album en utilisant l'ID de l'album
    """
    try:
        # Obtenir les chemins des dossiers d'images et de miniatures
        # on récupère les infos de l'album dans la db
        album = crud.get_album_by_id(db, album_id=album_id)
        if album is None:
            raise HTTPException(status_code=404, detail="L'album n'existe pas")
        img_path, tb_path = get_album_paths(album)

        # Vérifier que les dossiers existent
        if not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail=f"Le dossier d'images pour l'album {album_id} n'existe pas")
        if not os.path.exists(tb_path):
            raise HTTPException(
                status_code=404, detail=f"Le dossier de miniatures pour l'album {album_id} n'existe pas"
            )

        # Définir la taille des miniatures
        size = (width, height)

        # Créer les miniatures
        status = img_thumbnails(img_path, tb_path, size)
        return JSONResponse(
            content={
                "status": "success",
                "message": f"Miniatures créées pour l'album {album.title}",
                "details": {
                    "tbn_created": status["tbn_created"],
                    "tbn_exist": status["tbn_exist"],
                    "img_not_supported": status["img_not_supported"],
                },
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création des miniatures: {str(e)}")


@router.get("/get_random_image/{album_id}")
async def get_random_image(album_id: int, db: db_dependency):
    """
    Obtenir une image aléatoire d'un album en utilisant l'ID de l'album
    et mettre à jour l'image de couverture de l'album avec cette image
    """
    try:
        album = crud.get_album_by_id(db, album_id=album_id)
        if album is None:
            raise HTTPException(status_code=404, detail="L'album n'existe pas")
        img_path, tb_path = get_album_paths(album)

        # Vérifier que les dossiers existent
        if not os.path.exists(img_path):
            raise HTTPException(status_code=404, detail=f"Le dossier d'images pour l'album {album_id} n'existe pas")

        # Obtenir un fichier aléatoire
        random_file = choose_random_file(img_path)

        # Mettre à jour l'image de couverture de l'album
        album_update = schemas.AlbumUpdate(
            title=None,
            description=None,
            category_id=None,
            date=None,
            participants=None,
            location=None,
            tags=None,
            image_cover=random_file,
        )

        # Appel de la fonction update_album pour mettre à jour l'image de couverture
        crud.update_album(db, album_id, album_update)

        return {
            "status": "success",
            "filename": random_file,
            "path": os.path.join(img_path, random_file),
            "album_id": album_id,
            "message": "Image de couverture mise à jour avec succès",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération d'une image aléatoire: {str(e)}")


# renomage des fichiers contenu dans le repertoire de l'album
@router.get("/rename_files_in_album_folder_with_exif_datetaken/{album_id}")
def rename_files_in_album_folder(album_id: int, db: db_dependency):
    """
    Renomme les fichiers dans le dossier de l'album en fonction des données exif de chaque fichier photo contenu dans le répertoire de l'album.
    """
    album = crud.get_album_by_id(db, album_id=album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")
    add_date_taken_to_image_file(album)
    return JSONResponse(content={"message": f"Fichiers renommés dans le dossier de l'album {album.title}"})


##################################################################
# Upload d'images dans un album (Tâche 295)
##################################################################


@router.post("/upload_images/{album_id}")
async def upload_images(
    album_id: int,
    db: db_dependency,
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload multiple images/videos dans un album.
    - Vérifie que l'utilisateur a accès à l'album
    - Valide la taille des fichiers (30 MB images, 500 MB vidéos, 2 GB total)
    - Sauvegarde les fichiers originaux dans le dossier images de l'album
    - Génère automatiquement les thumbnails
    - Retourne le nombre de fichiers uploadés avec succès

    Formats supportés : jpg, jpeg, png, gif, heic, webp, mp4, avi, mov, mkv, webm
    """
    # Vérifier que l'album existe
    album = crud.get_album_by_id(db, album_id=album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # Vérifier que l'utilisateur a accès à cet album (sauf superuser)
    user_id = current_user.get("id")
    is_superuser = current_user.get("is_superuser", False)

    if not is_superuser and not verify_album_access(db, user_id, album_id):
        logger.warning(f"Utilisateur {user_id} tentative upload non autorisé sur album {album_id}")
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cet album")

    # Validation des tailles de fichiers AVANT le traitement
    total_size = 0
    size_errors = []

    for file in files:
        # Lire la taille du fichier
        file.file.seek(0, 2)  # Aller à la fin
        file_size = file.file.tell()
        file.file.seek(0)  # Revenir au début

        # Déterminer la limite selon le type de fichier
        filename_lower = file.filename.lower() if file.filename else ""
        is_video = filename_lower.endswith(VIDEO_EXTENSIONS)
        max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
        max_size_label = "500 MB" if is_video else "30 MB"

        if file_size > max_size:
            size_errors.append(
                f"{file.filename}: trop volumineux ({file_size / (1024*1024):.1f} MB, max {max_size_label})"
            )
            continue

        total_size += file_size

    # Vérifier la taille totale
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=413, detail=f"Taille totale trop importante: {total_size / (1024*1024*1024):.2f} GB (max 2 GB)"
        )

    if size_errors:
        raise HTTPException(
            status_code=413, detail={"message": "Certains fichiers sont trop volumineux", "errors": size_errors}
        )

    # Obtenir les chemins des dossiers
    img_path, tb_path = get_album_paths(album)

    # Créer les dossiers s'ils n'existent pas
    os.makedirs(img_path, exist_ok=True)
    os.makedirs(tb_path, exist_ok=True)

    # Statistiques d'upload
    uploaded_count = 0
    skipped_count = 0
    error_count = 0
    uploaded_files = []
    errors = []

    for file in files:
        try:
            # Vérifier l'extension du fichier
            if not allowed_file(file.filename):
                skipped_count += 1
                errors.append(f"{file.filename}: format non supporté")
                continue

            # Sécuriser le nom du fichier
            safe_filename = file.filename.replace(" ", "_")
            file_path = os.path.join(img_path, safe_filename)

            # Vérifier si le fichier existe déjà
            if os.path.exists(file_path):
                skipped_count += 1
                errors.append(f"{file.filename}: fichier déjà existant")
                continue

            # Sauvegarder le fichier original
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)

            logger.info(f"Image uploadée: {safe_filename} dans {img_path}")

            # Générer la thumbnail
            filename_lower = safe_filename.lower()
            size = (image_config.thumbnail_width, image_config.thumbnail_height)

            # Thumbnail pour les images
            if filename_lower.endswith(IMAGE_EXTENSIONS):
                try:
                    thumbnail_path = os.path.join(tb_path, safe_filename)
                    img = Image.open(file_path)

                    # Préserver l'orientation EXIF
                    try:
                        exif = img.info.get("exif")
                    except Exception:
                        exif = None

                    # Créer la thumbnail
                    img.thumbnail(size, PIL.Image.Resampling.LANCZOS)

                    # Sauvegarder avec EXIF si disponible
                    if exif:
                        img.save(thumbnail_path, quality=85, exif=exif)
                    else:
                        img.save(thumbnail_path, quality=85)

                    logger.info(f"Thumbnail image créée: {safe_filename}")
                except Exception as e:
                    logger.warning(f"Erreur création thumbnail pour {safe_filename}: {e}")
                    # L'image est quand même uploadée, on continue

            # Thumbnail pour les vidéos (avec FFmpeg)
            elif filename_lower.endswith(VIDEO_EXTENSIONS):
                try:
                    name, _ = os.path.splitext(safe_filename)
                    thumbnail_filename = f"{name}.jpg"
                    thumbnail_path = os.path.join(tb_path, thumbnail_filename)

                    if video_create_thumbnail(file_path, thumbnail_path, size):
                        logger.info(f"Thumbnail vidéo créée: {thumbnail_filename}")
                    else:
                        logger.warning(f"FFmpeg n'a pas pu créer la vignette pour {safe_filename}")
                except Exception as e:
                    logger.warning(f"Erreur création thumbnail vidéo pour {safe_filename}: {e}")

            uploaded_count += 1
            uploaded_files.append(safe_filename)

        except Exception as e:
            error_count += 1
            errors.append(f"{file.filename}: {str(e)}")
            logger.error(f"Erreur upload {file.filename}: {e}")

    return JSONResponse(
        content={
            "status": "success" if uploaded_count > 0 else "error",
            "message": f"{uploaded_count} fichier(s) uploadé(s) avec succès",
            "details": {
                "uploaded": uploaded_count,
                "skipped": skipped_count,
                "errors": error_count,
                "uploaded_files": uploaded_files,
                "error_messages": errors if errors else None,
            },
        }
    )


@router.get("/get_album_images/{album_id}")
async def get_album_images(album_id: int, db: db_dependency):
    """
    Liste toutes les images d'un album avec leurs URLs.
    Retourne la liste des fichiers avec leurs URLs pour affichage.
    """
    # Vérifier que l'album existe
    album = crud.get_album_by_id(db, album_id=album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # Obtenir les chemins
    img_path, tb_path = get_album_paths(album)

    if not os.path.exists(img_path):
        return JSONResponse(content={"images": [], "count": 0})

    # Construire l'URL relative pour le frontend
    from .be_formatter import format_from_db, format_from_db_title

    participants_formatted = format_from_db(album.participants or "", "folder")
    title_formatted = format_from_db_title(album.title, "folder")
    date_str = album.date.strftime("%Y-%m-%d")
    folder_name = f"{date_str}_{title_formatted}_{participants_formatted}"
    category = album.category.category

    images = []
    for filename in sorted(os.listdir(img_path)):
        if allowed_file(filename):
            images.append(
                {
                    "filename": filename,
                    "full_url": f"/static/images/{category}/{folder_name}/{filename}",
                    "thumbnail_url": f"/static/thumbnails/{category}/{folder_name}/{filename}",
                }
            )

    return JSONResponse(content={"images": images, "count": len(images)})


@router.delete("/delete_image/{album_id}/{filename}")
async def delete_image(album_id: int, filename: str, db: db_dependency):
    """
    Supprime une image d'un album (original + thumbnail).
    """
    # Vérifier que l'album existe
    album = crud.get_album_by_id(db, album_id=album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="L'album n'existe pas")

    # Obtenir les chemins
    img_path, tb_path = get_album_paths(album)

    # Supprimer l'image originale
    original_file = os.path.join(img_path, filename)
    if os.path.exists(original_file):
        os.remove(original_file)
    else:
        raise HTTPException(status_code=404, detail="Image non trouvée")

    # Supprimer la thumbnail si elle existe
    thumbnail_file = os.path.join(tb_path, filename)
    if os.path.exists(thumbnail_file):
        os.remove(thumbnail_file)

    return JSONResponse(content={"status": "success", "message": f"Image {filename} supprimée"})


##################################################################
# Upload TUS resumable (Tâche 391)
# - Protocole TUS 1.0.0 fourni par tuspyserver
# - Compatible avec le plugin @uppy/tus côté frontend (cf TODO #392)
# - Reprise après coupure réseau, chunks de 5 Mo, retry automatique
##################################################################

import shutil
import threading
from collections.abc import Callable

from tuspyserver import create_tus_router


def _integrer_fichier_tus(album, chemin_source: str, nom_origine: str) -> dict:
    """Intègre un fichier uploadé via TUS dans le dossier de l'album.

    - Vérifie l'extension
    - Sécurise le nom (espaces -> underscores)
    - Refuse les doublons (fichier déjà présent)
    - Génère la vignette (image PIL ou vidéo OpenCV)
    - Déplace le fichier source du dossier temporaire TUS vers le dossier album

    Args:
        album: objet Album SQLAlchemy
        chemin_source: chemin du fichier temporaire produit par tuspyserver
        nom_origine: nom de fichier d'origine envoyé par le client

    Returns:
        dict {status: "success"|"skipped"|"error", filename, error?}
    """
    if not nom_origine:
        return {"status": "error", "filename": "", "error": "Nom de fichier manquant"}

    if not allowed_file(nom_origine):
        return {"status": "skipped", "filename": nom_origine, "error": "Format non supporté"}

    # Préparer les dossiers de l'album
    img_path, tb_path = get_album_paths(album)
    os.makedirs(img_path, exist_ok=True)
    os.makedirs(tb_path, exist_ok=True)

    nom_securise = nom_origine.replace(" ", "_")
    chemin_destination = os.path.join(img_path, nom_securise)

    if os.path.exists(chemin_destination):
        return {"status": "skipped", "filename": nom_origine, "error": "Fichier déjà existant"}

    try:
        shutil.move(chemin_source, chemin_destination)
    except OSError as exc:
        logger.error(f"Erreur déplacement fichier TUS {chemin_source} -> {chemin_destination}: {exc}")
        return {"status": "error", "filename": nom_origine, "error": str(exc)}

    logger.info(f"Image TUS intégrée: {nom_securise} dans {img_path}")

    # Génération de la vignette
    nom_lower = nom_securise.lower()
    taille = (image_config.thumbnail_width, image_config.thumbnail_height)

    try:
        if nom_lower.endswith(IMAGE_EXTENSIONS):
            chemin_vignette = os.path.join(tb_path, nom_securise)
            img = Image.open(chemin_destination)
            try:
                exif = img.info.get("exif")
            except Exception:
                exif = None
            img.thumbnail(taille, PIL.Image.Resampling.LANCZOS)
            if exif:
                img.save(chemin_vignette, quality=85, exif=exif)
            else:
                img.save(chemin_vignette, quality=85)
            logger.info(f"Vignette image créée (TUS): {nom_securise}")

        elif nom_lower.endswith(VIDEO_EXTENSIONS):
            base, _ = os.path.splitext(nom_securise)
            nom_vignette = f"{base}.jpg"
            chemin_vignette = os.path.join(tb_path, nom_vignette)
            if video_create_thumbnail(chemin_destination, chemin_vignette, taille):
                logger.info(f"Vignette vidéo créée (TUS): {nom_vignette}")
            else:
                logger.warning(f"OpenCV n'a pas pu créer la vignette pour {nom_securise}")
    except Exception as exc:
        # L'original est déjà en place : on ne fait pas échouer l'upload pour autant
        logger.warning(f"Erreur création vignette (TUS) pour {nom_securise}: {exc}")

    return {"status": "success", "filename": nom_securise}


def _tus_hook_pre_creation(
    db: db_dependency,
    current_user: dict = Depends(get_current_user),
) -> Callable[[dict, dict], None]:
    """Hook TUS exécuté AVANT la création d'un upload.

    Vérifie :
    - que la metadata ``album_id`` est présente et valide
    - que l'utilisateur a accès à l'album cible
    - que la taille annoncée respecte les limites (image 30 MB / vidéo 500 MB)
    """

    def _valider(metadata: dict, upload_info: dict) -> None:
        album_id_brut = metadata.get("album_id")
        if not album_id_brut:
            raise HTTPException(status_code=400, detail="Metadata 'album_id' manquante")
        try:
            album_id = int(album_id_brut)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Metadata 'album_id' invalide") from None

        album = crud.get_album_by_id(db, album_id=album_id)
        if album is None:
            raise HTTPException(status_code=404, detail="L'album n'existe pas")

        user_id = current_user.get("id")
        is_superuser = current_user.get("is_superuser", False)
        if not is_superuser and not verify_album_access(db, user_id, album_id):
            logger.warning(f"Utilisateur {user_id} tentative upload TUS non autorisé sur album {album_id}")
            raise HTTPException(status_code=403, detail="Vous n'avez pas accès à cet album")

        # Validation taille (image vs vidéo) selon le nom de fichier annoncé
        nom_fichier = (metadata.get("filename") or metadata.get("name") or "").lower()
        est_video = nom_fichier.endswith(VIDEO_EXTENSIONS)
        taille_max = MAX_VIDEO_SIZE if est_video else MAX_IMAGE_SIZE
        libelle_max = "500 MB" if est_video else "30 MB"
        taille = upload_info.get("size")
        if taille and taille > taille_max:
            raise HTTPException(
                status_code=413,
                detail=f"{nom_fichier or 'fichier'}: trop volumineux "
                f"({taille / (1024 * 1024):.1f} MB, max {libelle_max})",
            )

    return _valider


def _tus_hook_upload_complete(
    db: db_dependency,
    current_user: dict = Depends(get_current_user),  # noqa: ARG001 - garde l'auth active sur l'endpoint
) -> Callable[[str, dict], None]:
    """Hook TUS exécuté à la fin d'un upload.

    Déplace le fichier temporaire vers le dossier de l'album et génère la
    vignette. Nettoie les fichiers résiduels (le ``.info`` produit par tuspyserver).
    """

    def _finaliser(chemin_fichier: str, metadata: dict) -> None:
        try:
            album_id = int(metadata.get("album_id"))
        except (TypeError, ValueError):
            logger.error(f"TUS on_upload_complete: album_id invalide dans metadata={metadata}")
            return

        album = crud.get_album_by_id(db, album_id=album_id)
        if album is None:
            logger.error(f"TUS on_upload_complete: album {album_id} introuvable")
            return

        nom_origine = metadata.get("filename") or metadata.get("name") or os.path.basename(chemin_fichier)

        # IMPORTANT : on traite l'intégration (move + génération vignette) dans un
        # thread d'arrière-plan pour libérer immédiatement le worker FastAPI et
        # rendre le 204 No Content au client. Sans ça, sur réseau mobile le
        # navigateur voit la requête pendre pendant la création de la vignette PIL
        # (3-15 s par photo) et l'opérateur coupe la connexion TCP au bout de
        # ~10 s -> erreur Uppy "looks like a network error" sur les fichiers suivants.
        def _tache_arriere_plan() -> None:
            try:
                resultat = _integrer_fichier_tus(album, chemin_fichier, nom_origine)
                logger.info(f"TUS upload terminé pour album {album_id}: {resultat}")
            except Exception as exc:
                logger.error(f"TUS traitement arrière-plan échoué pour {nom_origine}: {exc}")
            finally:
                # Nettoyer les fichiers résiduels (.info produit par tuspyserver,
                # source si _integrer_fichier_tus a échoué avant le shutil.move)
                chemin_info = chemin_fichier + ".info"
                for chemin in (chemin_fichier, chemin_info):
                    if os.path.exists(chemin):
                        try:
                            os.remove(chemin)
                        except OSError as exc:
                            logger.warning(f"Impossible de supprimer {chemin}: {exc}")

        threading.Thread(
            target=_tache_arriere_plan,
            name=f"tus-finalize-{album_id}-{nom_origine}",
            daemon=True,
        ).start()

    return _finaliser


# Création du router TUS. S'expose sous le préfixe /be_resizer/tus.
# - auth=get_current_user : toutes les requêtes TUS doivent être authentifiées
#   (cookie JWT envoyé via withCredentials côté Uppy)
# - pre_create_dep : valide album_id + droits avant d'allouer un upload
# - upload_complete_dep : intègre le fichier dans l'album à la fin
os.makedirs(image_config.tus_files_dir, exist_ok=True)

tus_router = create_tus_router(
    prefix="be_resizer/tus",
    files_dir=image_config.tus_files_dir,
    max_size=MAX_VIDEO_SIZE,  # plafond global = limite vidéo
    auth=get_current_user,
    pre_create_dep=_tus_hook_pre_creation,
    upload_complete_dep=_tus_hook_upload_complete,
    days_to_keep=2,  # nettoyage des uploads abandonnés
)
