import logging
import os
import re

from fastapi import APIRouter, Depends, HTTPException

from utils.config import image

from .be_auth import get_current_user

# Configuration du logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/be_formatter", tags=["backend_formatter"], dependencies=[Depends(get_current_user)])


##################################################################
# formatter section
# format une chaine de caractères venant de la db
@router.get("/format_from_db/")
def format_from_db(strfromdb: str, format: str = "db"):
    """Format une chaîne issue de la DB.
    format de destination: `web` (alias `list`), `folder`, `db` (no-op)
    Le format de la DB est: Sabina|Margaux|Élena|Guilhem|Jean-Pierre

    - DB -> web: remplace `|` par `, ` et les `-` internes aux prénoms par un espace
    - DB -> folder: remplace `|` par `-` et supprime les `-` internes aux prénoms (Jean-Pierre -> JeanPierre)
    - DB -> DB: retourne la valeur inchangée
    """
    target = format.lower()
    if target in ("web", "list"):  # DB -> web/list
        parts = [p.replace("-", " ").replace("'", "").strip() for p in strfromdb.split("|") if p.strip()]
        result = ", ".join(parts)
    elif target == "folder":  # DB -> folder
        parts = [p.replace("-", "").replace("'", "").strip() for p in strfromdb.split("|") if p.strip()]
        result = "-".join(parts)
    elif target == "db":
        result = strfromdb
    else:
        raise HTTPException(status_code=400, detail="Le format de destination n'est pas correct")
    return result


#  formatter une chaine de caractères pour la db
@router.get("/format_to_db/")
def format_to_db(strfromweb: str, srcformat: str = "list"):
    """Format une chaîne pour la DB.
    format de destination: DB
    formats sources supportés:
    - `list`: éléments séparés par des virgules (avec ou sans espaces)
    - `folder`: éléments séparés par des tirets; les prénoms composés peuvent être en CamelCase (JeanPierre)

    Règles:
    - remplace les séparateurs par `|`
    - remplace les espaces internes d'un prénom par `-` (Jean Pierre -> Jean-Pierre)
    - pour `folder`, détecte les prénoms CamelCase et insère un `-` avant chaque majuscule interne
    """
    source = srcformat.lower()
    if source == "list":
        # séparer sur les virgules, nettoyer, remplacer les espaces internes par '-'
        items = [i.strip() for i in re.split(r",\s*", strfromweb.strip()) if i.strip()]
        processed = [itm.replace("'", "").replace(" ", "-") for itm in items]
        result = "|".join(processed)
    elif source == "folder":
        parts = [p.strip() for p in strfromweb.split("-") if p.strip()]
        processed = []
        for p in parts:
            p_clean = p.replace("'", "")
            # si CamelCase (plus d'une majuscule) on insère un '-' avant chaque majuscule interne
            if sum(1 for c in p_clean if c.isupper()) > 1:
                p_clean = re.sub(r"(?<!^)(?=[A-Z])", "-", p_clean)
            processed.append(p_clean)
        result = "|".join(processed)
    else:
        raise HTTPException(status_code=400, detail="Le format source n'est pas connu")
    return result


# formatter pour les titres d'album
@router.get("/format_from_db_title/")
def format_from_db_title(strfromdb: str, format: str = "db"):
    """Format un titre issu de la DB.
    format de destination: `web`, `folder`, `db` (no-op)

    - DB -> web: retourne le titre tel quel (orthographe française)
    - DB -> folder: remplace espaces et apostrophes par des tirets
    - DB -> db: retourne la valeur inchangée
    """
    target = format.lower()
    if target == "web":
        result = strfromdb
    elif target == "folder":
        result = strfromdb.replace(" ", "-").replace("'", "-")
    elif target == "db":
        result = strfromdb
    else:
        raise HTTPException(status_code=400, detail="Le format de destination n'est pas correct")
    return result


# formatter pour les catégories
@router.get("/format_from_db_category/")
def format_from_db_category(strfromdb: str, format: str = "db"):
    """Format une catégorie issue de la DB.
    format de destination: `web`, `folder`, `db` (no-op)

    - DB -> web: retourne la catégorie telle quelle (orthographe française)
    - DB -> folder: remplace espaces et apostrophes par des tirets
    - DB -> db: retourne la valeur inchangée
    """
    target = format.lower()
    if target == "web":
        result = strfromdb
    elif target == "folder":
        result = strfromdb.replace(" ", "-").replace("'", "-")
    elif target == "db":
        result = strfromdb
    else:
        raise HTTPException(status_code=400, detail="Le format de destination n'est pas correct")
    return result


##################################################################
# Fonctions utilitaires (non-endpoints) pour construire les chemins
##################################################################


def _format_participants_folder(participants_db: str) -> str:
    """Convertit les participants format DB vers format folder.
    DB: Sabina|Jean-Pierre|François
    Folder: Sabina-JeanPierre-François (tirets supprimés dans prénoms composés)
    """
    if not participants_db:
        return ""
    parts = [p.replace("-", "").replace("'", "").strip() for p in participants_db.split("|") if p.strip()]
    return "-".join(parts)


def _format_title_folder(title: str) -> str:
    """Convertit un titre format DB vers format folder.
    Espaces et apostrophes → tirets
    """
    if not title:
        return ""
    return title.replace(" ", "-").replace("'", "-")


def _format_category_folder(category: str) -> str:
    """Convertit une catégorie format DB vers format folder.
    Espaces et apostrophes → tirets
    """
    if not category:
        return ""
    return category.replace(" ", "-").replace("'", "-")


def build_album_folder_name(date_str: str, title: str, participants: str) -> str:
    """Construit le nom du répertoire d'un album selon les règles de nommage.
    Format: {date}_{titre}_{participants}
    - date: YYYY-MM-DD
    - titre: espaces/apostrophes → tirets
    - participants: séparés par tirets, prénoms composés en CamelCase
    """
    title_folder = _format_title_folder(title)
    participants_folder = _format_participants_folder(participants)
    logger.info(f"le nom du répertoire de l'album: {date_str}_{title_folder}_{participants_folder}")
    return f"{date_str}_{title_folder}_{participants_folder}"


def build_cover_url(category: str, date_str: str, title: str, participants: str, image_cover: str) -> str | None:
    """Construit l'URL complète de l'image de couverture d'un album.
    Format: /thumbnails/{categorie_folder}/{album_folder}/{image_cover}
    """
    if not image_cover:
        return None

    from urllib.parse import quote

    category_folder = _format_category_folder(category)
    album_folder = build_album_folder_name(date_str, title, participants)

    # Log du chemin complet sur le système de fichiers
    full_path = os.path.join(image.thumbnails_path, category_folder, album_folder, image_cover)
    logger.info(f"Chemin complet de la vignette: {full_path}")

    logger.info(f"l'URL de l'image de couverture: /thumbnails/{category_folder}/{album_folder}/{image_cover}")

    # Encoder les caractères spéciaux pour l'URL (accents, etc.)
    return f"/thumbnails/{quote(category_folder)}/{quote(album_folder)}/{quote(image_cover)}"
