"""
Utilitaires d'authentification pour le frontend
Fonctions réutilisables pour vérifier l'authentification via cookies
"""

import logging

import httpx
from fastapi import Request

from utils.config import backend_api

# Configuration du logger
logger = logging.getLogger(__name__)


async def verify_authentication(request: Request) -> dict | None:
    """Vérifie si l'utilisateur est authentifié via le cookie JWT

    :param request: Requête FastAPI contenant les cookies
    :return: Données utilisateur si authentifié, None sinon
    """
    async with httpx.AsyncClient() as client:
        try:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.auth_url}/me",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                return resp.json()

            logger.debug(f"Authentification échouée: status {resp.status_code} pour {request.url.path}")
            return None

        except httpx.TimeoutException:
            logger.warning(f"Timeout lors de la vérification d'authentification pour {request.url.path}")
            return None
        except httpx.ConnectError:
            logger.error(f"Impossible de se connecter au backend {backend_api.auth_url}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la vérification d'authentification: {type(e).__name__}: {e}")
            return None


async def require_auth(request: Request) -> tuple[bool, dict | None]:
    """Vérifie que l'utilisateur est authentifié

    :param request: Requête FastAPI
    :return: Tuple (is_authenticated, user_data)
    """
    user = await verify_authentication(request)
    return (user is not None, user)


async def require_superuser(request: Request) -> tuple[bool, dict | None]:
    """Vérifie que l'utilisateur est authentifié ET superuser

    :param request: Requête FastAPI
    :return: Tuple (is_superuser, user_data)
    """
    user = await verify_authentication(request)

    if user is None:
        return (False, None)

    if not user.get("is_superuser", False):
        return (False, user)

    return (True, user)
