"""
Utilitaires d'authentification pour le frontend
Fonctions réutilisables pour vérifier l'authentification via cookies
"""

import logging

from fastapi import HTTPException, Request

# Configuration du logger
logger = logging.getLogger(__name__)


async def verify_authentication(request: Request) -> dict | None:
    """Vérifie si l'utilisateur est authentifié via le cookie JWT

    Résolution en processus (C-8) : plutôt que de refaire un aller-retour HTTP
    en boucle locale vers ``GET /be_auth/me`` (httpx → localhost, latence
    doublée + surface d'échec d'un self-timeout de 10 s), on décode le token du
    cookie/header et on charge l'utilisateur directement depuis la base, dans le
    même processus. La décision d'authentification est identique à celle de
    l'endpoint ``/me`` (mêmes règles de décodage via ``get_current_user`` puis
    ``crud.get_user_info_by_id``) et la forme renvoyée reflète le schéma
    ``UserAdmin`` — seul le saut réseau en boucle locale est supprimé.

    :param request: Requête FastAPI contenant les cookies
    :return: Données utilisateur si authentifié, None sinon
    """
    # Imports différés : évite tout cycle d'import au chargement du module
    # (``utils.auth`` est importé par ``be_media_bridge``) et ne charge le routeur
    # backend que lorsque la garde est effectivement appelée.
    from backend.db import crud
    from backend.db.db_connect import SessionLocal
    from backend.routers.be_auth import get_current_user

    # Décodage du token (cookie HttpOnly ou header Authorization). Un token
    # absent/invalide lève une HTTPException 401 — on la convertit en None pour
    # conserver le contrat historique (auth échouée → None), comme le faisait la
    # réponse non-200 de ``/me``.
    try:
        user_data = await get_current_user(request)
    except HTTPException:
        logger.debug(f"Authentification échouée (token absent ou invalide) pour {request.url.path}")
        return None

    # Chargement de l'utilisateur en base, dans une session dédiée et fermée
    # explicitement (on n'est pas dans le graphe d'injection de dépendances de
    # FastAPI ici).
    db = SessionLocal()
    try:
        user = crud.get_user_info_by_id(db, user_id=user_data["id"])
        if not user:
            logger.debug(f"Utilisateur introuvable en base pour {request.url.path}")
            return None

        # Forme identique à ``schemas.UserAdmin`` renvoyée par ``/me`` : les
        # appelants (``require_auth``, garde média du bridge) lisent ``id``/
        # ``is_superuser`` et les infos de profil.
        return {
            "id": user.id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "email": user.email,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la vérification d'authentification: {type(e).__name__}: {e}")
        return None
    finally:
        db.close()


async def require_auth(request: Request) -> tuple[bool, dict | None]:
    """Vérifie que l'utilisateur est authentifié

    :param request: Requête FastAPI
    :return: Tuple (is_authenticated, user_data)
    """
    user = await verify_authentication(request)
    return (user is not None, user)
