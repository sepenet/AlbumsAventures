import logging
import os

from utils.config import image

from ..routers.be_formatter import format_from_db, format_from_db_category, format_from_db_title

logger = logging.getLogger(__name__)


def get_album_folder_name(album) -> str:
    """
    Calcule le nom du dossier de l'album à partir de ses données.
    Format: YYYY-MM-DD_titre_participants

    Args:
        album: Objet album avec attributs date, title, participants

    Returns:
        str: Nom du dossier formaté pour le filesystem
    """
    participants = format_from_db(str(album.participants or ""), "folder")
    title = format_from_db_title(str(album.title), "folder")
    return f"{album.date}_{title}_{participants}"


def get_category_folder_name(album) -> str:
    """
    Récupère le nom de la catégorie formaté pour le filesystem.

    Args:
        album: Objet album avec attribut category (ORM ou Row)

    Returns:
        str: Nom de catégorie formaté (espaces/apostrophes → tirets)
    """
    # Gérer les deux cas : objet ORM (album.category.category) ou Row (album.category string)
    cat = album.category
    if hasattr(cat, "category"):
        cat_name = str(cat.category)
    else:
        cat_name = str(cat)

    return format_from_db_category(cat_name, "folder")


# create_album_folder en fonction des informations de l'album
def create_album_folder(album: dict):
    """créer les répertoires (images et vignettes) pour un album"""
    folder_name = get_album_folder_name(album)
    category = get_category_folder_name(album)

    folderPathImages_Name = os.path.join(image.image_path, category, folder_name)
    folderPathThumbnails_Name = os.path.join(image.thumbnails_path, category, folder_name)

    try:
        os.makedirs(folderPathImages_Name, exist_ok=True)
        os.makedirs(folderPathThumbnails_Name, exist_ok=True)
        logger.info(f"Répertoires créés: {category}/{folder_name}")
    except OSError as e:
        logger.error(f"Erreur lors de la création des répertoires: {e}")
        raise


# get_album_folder_path en fonction de l'id de l'album
def get_album_folder_path(album: dict) -> str:
    """Renvoie le chemin du dossier images de l'album (rétrocompatibilité)"""
    img_path, _ = get_album_paths(album)
    return img_path


def get_album_paths(album) -> tuple[str, str]:
    """
    Renvoie les chemins des dossiers images et thumbnails de l'album.

    Args:
        album: Objet album SQLAlchemy avec les attributs date, title, participants, category

    Returns:
        tuple: (chemin_images, chemin_thumbnails)
    """
    folder_name = get_album_folder_name(album)
    category = get_category_folder_name(album)

    img_path = os.path.join(image.image_path, category, folder_name)
    tb_path = os.path.join(image.thumbnails_path, category, folder_name)

    return img_path, tb_path


def rename_album_folder(old_album, new_album) -> bool:
    """
    Renomme et/ou déplace les répertoires d'un album si nécessaire.

    Cas traités (cf README.md):
    1. Changement de catégorie -> déplacement des répertoires
    2. Changement de titre/date/participants -> renommage des répertoires
    3. Combinaison des deux -> renommage + déplacement

    Args:
        old_album: État de l'album AVANT modification (Row immuable de la DB)
        new_album: État de l'album APRÈS modification (Row immuable de la DB)

    Returns:
        bool: True si succès ou pas de changement nécessaire, False si erreur
    """
    old_folder_name = get_album_folder_name(old_album)
    new_folder_name = get_album_folder_name(new_album)
    old_category = get_category_folder_name(old_album)
    new_category = get_category_folder_name(new_album)

    # Aucun changement nécessaire
    if old_folder_name == new_folder_name and old_category == new_category:
        logger.debug(f"Album {new_album.id}: pas de renommage nécessaire")
        return True

    # Construire les chemins
    old_img_path = os.path.join(image.image_path, old_category, old_folder_name)
    old_tb_path = os.path.join(image.thumbnails_path, old_category, old_folder_name)
    new_img_path = os.path.join(image.image_path, new_category, new_folder_name)
    new_tb_path = os.path.join(image.thumbnails_path, new_category, new_folder_name)

    logger.info(f"Album {new_album.id}: renommage {old_category}/{old_folder_name} → {new_category}/{new_folder_name}")

    try:
        # Renommer/déplacer le dossier images
        if os.path.exists(old_img_path):
            # S'assurer que le répertoire parent existe (pour changement de catégorie)
            os.makedirs(os.path.dirname(new_img_path), exist_ok=True)
            os.rename(old_img_path, new_img_path)
            logger.info(f"Images: {old_img_path} → {new_img_path}")
        else:
            logger.warning(f"Dossier images introuvable: {old_img_path}")

        # Renommer/déplacer le dossier thumbnails
        if os.path.exists(old_tb_path):
            os.makedirs(os.path.dirname(new_tb_path), exist_ok=True)
            os.rename(old_tb_path, new_tb_path)
            logger.info(f"Thumbnails: {old_tb_path} → {new_tb_path}")
        else:
            logger.warning(f"Dossier thumbnails introuvable: {old_tb_path}")

        return True

    except OSError as e:
        logger.error(f"Erreur renommage album {new_album.id}: {e}")
        return False
