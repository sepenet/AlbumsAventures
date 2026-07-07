"""
Protection CSRF manuelle pour les formulaires.
Tâche 130 : Ajouter protection CSRF sur les formulaires

Principe du double-submit cookie :
1. Un token CSRF est généré et stocké dans un cookie
2. Le même token est inclus dans un champ caché du formulaire
3. À la soumission, on vérifie que les deux correspondent
"""

import logging
import secrets

from fastapi import HTTPException, Request, Response

logger = logging.getLogger(__name__)

# Nom du cookie et du champ de formulaire
CSRF_COOKIE_NAME = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_TOKEN_LENGTH = 32


def generate_csrf_token() -> str:
    """Génère un token CSRF aléatoire et sécurisé."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def get_csrf_token(request: Request) -> str:
    """
    Récupère le token CSRF existant depuis le cookie,
    ou en génère un nouveau s'il n'existe pas.
    """
    existing_token = request.cookies.get(CSRF_COOKIE_NAME)
    if existing_token:
        return existing_token
    return generate_csrf_token()


def set_csrf_cookie(response: Response, token: str) -> None:
    """
    Ajoute le cookie CSRF à la réponse.
    - httponly=False : le JS peut lire le token si nécessaire pour AJAX
    - samesite="strict" : protection contre les requêtes cross-site
    - secure=False en dev, à passer à True en production avec HTTPS
    """
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # Doit être lisible par le formulaire
        samesite="strict",
        secure=False,  # TODO: passer à True en production avec HTTPS
        max_age=3600,  # 1 heure
    )


def validate_csrf_token(request: Request, form_token: str | None) -> bool:
    """
    Valide que le token du formulaire correspond au token du cookie.
    Retourne True si valide, False sinon.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

    if not cookie_token or not form_token:
        logger.warning("Token CSRF manquant (cookie ou formulaire)")
        return False

    # Comparaison en temps constant pour éviter les timing attacks
    if not secrets.compare_digest(cookie_token, form_token):
        logger.warning("Token CSRF invalide - les tokens ne correspondent pas")
        return False

    return True


def require_csrf(request: Request, form_token: str | None) -> None:
    """
    Valide le token CSRF et lève une HTTPException si invalide.
    À utiliser dans les endpoints POST/PUT/DELETE.
    """
    if not validate_csrf_token(request, form_token):
        raise HTTPException(
            status_code=403, detail="Token CSRF invalide ou expiré. Veuillez recharger la page et réessayer."
        )
