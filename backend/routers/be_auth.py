import logging
import secrets
import string
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ..db import schemas

# Configuration du logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/be_auth", tags=["backend_auth"])

import hashlib

from utils.config import auth_config, password_reset, rate_limiting
from utils.email import send_password_reset_email

from ..db import crud
from ..db.db_connect import db_dependency

# configure le context pour le hashage des mots de passe et la durée de vie du token
SECRET_KEY = auth_config.secret_key
ALGORITHM = auth_config.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = auth_config.access_token_expire_minutes

# le bearar token se recupère dans le header de la requête et il est utilisé pour l'authentification
# pour le réucpérer on navigue /photos.marlenagui.com/token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="be_auth/login")

# context pour le hashage des mots de passe, utilisé plus loin dans le code pour le cryptage decryptage des mots de passe.
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")

# Nom du cookie utilisé pour stocker le token JWT
COOKIE_NAME = auth_config.cookie_name

# Cache en mémoire pour stocker les tentatives échouées
# Structure: {token_hash: {"attempts": count, "first_attempt": timestamp, "blocked_until": timestamp}}
failed_attempts_cache = defaultdict(dict)


# creation du model pour le token, on ne le fait pas dans models.py car un token n'est pas une table de la base de données
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None


class PasswordUpdateForm(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    """Demande de réinitialisation de mot de passe"""

    email: str


class ResetPasswordRequest(BaseModel):
    """Réinitialisation du mot de passe avec token"""

    token: str
    new_password: str


class ShareTokenCreate(BaseModel):
    expiration_hours: int = 24
    pin: str | None = None  # Si None, généré automatiquement


class ShareTokenResponse(BaseModel):
    share_token: str
    share_url: str
    pin: str
    expires_at: datetime


# fonction pour créer un token
def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    """fonction pour créer un token
    :param username: le nom de l'utilisateur
    :param user_id: l'id de l'utilisateur
    :param expires_delta: la durée de vie du token"""

    encode = {"sub": username, "id": user_id}
    expire = datetime.now(UTC) + expires_delta
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# fonction pour générer un code PIN alphanumérique
def generate_pin(length: int = 6) -> str:
    """Génère un code PIN de 6 caractères alphanumériques (chiffres et lettres)"""
    alphabet = string.ascii_uppercase + string.digits  # A-Z et 0-9
    return "".join(secrets.choice(alphabet) for _ in range(length))


# fonction pour créer un token de partage d'album
def create_album_share_token(album_id: int, pin: str, expiration_hours: int = 24) -> tuple[str, datetime]:
    """Crée un token JWT pour le partage d'album avec PIN
    :param album_id: l'id de l'album à partager
    :param pin: le code PIN à 6 caractères
    :param expiration_hours: durée de validité en heures
    :return: tuple (token, date_expiration)
    """
    expire = datetime.now(UTC) + timedelta(hours=expiration_hours)
    # SEC-05 : stocker un hash du PIN au lieu du PIN en clair
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    payload = {"album_id": album_id, "type": "album_share", "pin_hash": pin_hash, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire


# fonction pour vérifier les tentatives de rate limiting
def check_rate_limit(token: str) -> None:
    """Vérifie si le token n'est pas bloqué par rate limiting
    :param token: le token JWT
    :raises HTTPException: si trop de tentatives échouées
    """
    # Créer un hash du token pour la clé du cache (évite de stocker le token complet)
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]

    current_time = time.time()
    cache_entry = failed_attempts_cache.get(token_hash, {})

    # Vérifier si le token est bloqué
    if "blocked_until" in cache_entry:
        if current_time < cache_entry["blocked_until"]:
            remaining_seconds = int(cache_entry["blocked_until"] - current_time)
            remaining_minutes = remaining_seconds // 60

            logger.warning(
                f"Tentative d'accès bloquée par rate limiting. " f"Token: {token_hash}, Reste: {remaining_minutes}min"
            )

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "too_many_attempts",
                    "message": f"Trop de tentatives échouées. Réessayez dans {remaining_minutes} minute(s).",
                    "retry_after_seconds": remaining_seconds,
                },
            )
        else:
            # Le blocage a expiré, nettoyer le cache
            logger.info(f"Blocage rate limiting expiré pour token {token_hash}")
            del failed_attempts_cache[token_hash]


def record_failed_attempt(token: str) -> None:
    """Enregistre une tentative échouée et bloque si nécessaire
    :param token: le token JWT
    """
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]

    current_time = time.time()
    cache_entry = failed_attempts_cache[token_hash]

    # Première tentative ou fenêtre expirée
    if (
        "first_attempt" not in cache_entry
        or (current_time - cache_entry["first_attempt"]) > rate_limiting.window_seconds
    ):
        cache_entry["attempts"] = 1
        cache_entry["first_attempt"] = current_time
        logger.info(f"Première tentative échouée pour token {token_hash}")
    else:
        # Incrémenter le compteur
        cache_entry["attempts"] = cache_entry.get("attempts", 0) + 1
        logger.warning(
            f"Tentative échouée {cache_entry['attempts']}/{rate_limiting.max_attempts} " f"pour token {token_hash}"
        )

    # Bloquer si limite atteinte
    if cache_entry["attempts"] >= rate_limiting.max_attempts:
        cache_entry["blocked_until"] = current_time + rate_limiting.window_seconds
        logger.error(
            f"Token {token_hash} bloqué pour {rate_limiting.window_seconds // 60} minutes "
            f"après {rate_limiting.max_attempts} tentatives échouées"
        )


def clear_failed_attempts(token: str) -> None:
    """Nettoie les tentatives échouées après succès
    :param token: le token JWT
    """
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    if token_hash in failed_attempts_cache:
        attempts = failed_attempts_cache[token_hash].get("attempts", 0)
        logger.info(f"Accès réussi pour token {token_hash} " f"(tentatives précédentes: {attempts})")
        del failed_attempts_cache[token_hash]


# fonction pour vérifier un token de partage
def verify_share_token(token: str, pin: str) -> int:
    """Vérifie la validité du token de partage et du PIN
    :param token: le token JWT
    :param pin: le code PIN fourni par l'utilisateur
    :return: l'album_id si valide
    :raises HTTPException: si le token est invalide, expiré ou PIN incorrect
    """
    # Vérifier le rate limiting AVANT toute validation
    check_rate_limit(token)

    try:
        # Décode le token (vérifie automatiquement l'expiration)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Vérifier que c'est bien un token de partage
        if payload.get("type") != "album_share":
            logger.warning("Tentative d'utilisation d'un token non-partage")
            raise HTTPException(
                status_code=403,
                detail={"error": "invalid_token_type", "message": "Ce lien de partage n'est pas valide"},
            )

        # SEC-05 : comparer le hash du PIN fourni avec le hash stocké dans le token
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        if payload.get("pin_hash") != pin_hash:
            # Enregistrer la tentative échouée
            record_failed_attempt(token)

            # Calculer le nombre de tentatives restantes
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            attempts = failed_attempts_cache.get(token_hash, {}).get("attempts", 0)
            remaining = rate_limiting.max_attempts - attempts

            raise HTTPException(
                status_code=403,
                detail={
                    "error": "invalid_pin",
                    "message": "Code PIN incorrect",
                    "attempts_remaining": max(0, remaining),
                },
            )

        # Récupérer l'album_id
        album_id = payload.get("album_id")
        if album_id is None:
            logger.error("Token de partage sans album_id")
            raise HTTPException(
                status_code=403, detail={"error": "malformed_token", "message": "Le lien de partage est corrompu"}
            )

        # Succès : nettoyer les tentatives échouées
        clear_failed_attempts(token)
        logger.info(f"Accès réussi à l'album {album_id} via token de partage")

        return album_id

    except JWTError as e:
        logger.warning(f"Token JWT invalide ou expiré: {str(e)}")
        raise HTTPException(
            status_code=403,
            detail={"error": "token_expired", "message": "Ce lien de partage a expiré ou n'est plus valide"},
        )


# fonction pour extraire le token du cookie ou du header
def get_token_from_cookie_or_header(request: Request) -> str:
    """Extrait le token JWT soit du cookie HttpOnly, soit du header Authorization
    :param request: la requête FastAPI
    :return: le token JWT
    :raises HTTPException: si aucun token n'est trouvé
    """
    # D'abord, essayer de récupérer le token du cookie
    token = request.cookies.get(COOKIE_NAME)

    if token:
        logger.info(f"✅ Token récupéré depuis le COOKIE pour {request.url.path}")
        # Le cookie contient "Bearer <token>", on extrait juste le token
        if token.startswith("Bearer "):
            return token.replace("Bearer ", "")
        return token

    # Sinon, essayer de récupérer du header Authorization (compatibilité)
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        logger.info(f"⚠️ Token récupéré depuis le HEADER Authorization pour {request.url.path}")
        return authorization.replace("Bearer ", "")

    # Aucun token trouvé
    logger.warning(f"❌ Aucun token trouvé (ni cookie ni header) pour {request.url.path}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Non authentifié. Veuillez vous connecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# fonction pour récupérer l'utilisateur courant
async def get_current_user(request: Request):
    """fonction pour récupérer l'utilisateur courant depuis le cookie ou header
    :param request: la requête FastAPI contenant le cookie ou le header
    """
    token = get_token_from_cookie_or_header(request)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Le token d'accés n'a pas passé la vérification :( "
            )

        return {"email": username, "id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Le token d'accés n'a pas passé la vérification :( "
        )


# TODO : fonctions de hashage déplacées vers utils/password.py pour éviter imports circulaires
from utils.password import get_password_hash, verify_password


##################################################################
# User section
# create utilisateur
@router.post("/create/", response_model=schemas.UserAdmin)
def create_user(user: schemas.UserCreate, db: db_dependency):
    # def create_user(token: Annotated[str, Depends(oauth2_scheme)], user: schemas.UserCreate, db: db_dependency):
    # Forcer les droits côté serveur — inscription publique = compte inactif, non-admin (SEC-03)
    user.is_active = False
    user.is_superuser = False
    # check if the user already exists by his/her email
    db_user = crud.get_user_info_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="L'email exite déjà")
    return crud.create_user(db=db, user=user)


# update utilisateur by id, pour activer l'utilisateur
@router.post("/activate/{user_id}/")
async def activate_user(request: Request, user_id: int, db: db_dependency, is_active: bool = False):
    # Vérifier que l'utilisateur est authentifié ET superuser (SEC-01)
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    user = crud.get_user_info_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=400, detail="L'utilisateur n'existe pas")
    return crud.activate_user(db, user, is_active=is_active)


# update utilisateur by id, pour passer l'utilisateur en admin
@router.post("/admin/{user_id}/")
async def admin_user(request: Request, user_id: int, db: db_dependency, is_superuser: bool = True):
    # Vérifier que l'utilisateur est authentifié ET superuser (SEC-01)
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    user = crud.get_user_info_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=400, detail="L'utilisateur n'existe pas")
    return crud.admin_user(db, user, is_superuser=is_superuser)


##################################################################
# Section Admin - Gestion des utilisateurs (Tâche 111)


@router.get("/admin/users", response_model=list[schemas.UserAdmin])
async def get_all_users_admin(
    request: Request, db: db_dependency, filter_active: bool = None, filter_pending: bool = None
):
    """Récupère la liste des utilisateurs pour l'interface d'admin
    :param filter_active: si True, filtre les utilisateurs actifs; si False, les inactifs
    :param filter_pending: si True, retourne uniquement les utilisateurs en attente (is_active=False)
    """
    # Vérifier que l'utilisateur est authentifié et est admin
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])

    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")

    # Filtre: utilisateurs en attente de validation
    if filter_pending:
        users = crud.get_pending_users(db)
    elif filter_active is not None:
        users = crud.get_all_users_filtered(db, is_active=filter_active)
    else:
        users = crud.get_all_users_info(db)

    logger.info(f"Admin {current_user.email}: liste de {len(users)} utilisateur(s)")
    return users


@router.get("/admin/users/pending-count")
async def get_pending_users_count(request: Request, db: db_dependency):
    """Retourne le nombre d'utilisateurs en attente d'activation (Tâche 280)
    Utilisé pour afficher le badge dans le menu admin.
    """
    # Vérifier que l'utilisateur est authentifié et est admin
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])

    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")

    pending_users = crud.get_pending_users(db)
    return {"count": len(pending_users)}


@router.put("/admin/users/{user_id}/rights", response_model=schemas.UserAdmin)
async def update_user_rights(request: Request, user_id: int, rights: schemas.UserRightsUpdate, db: db_dependency):
    """Met à jour les droits d'un utilisateur (activation et/ou rôle admin)
    :param user_id: ID de l'utilisateur à modifier
    :param rights: nouveaux droits (is_active et/ou is_superuser)
    """
    # Vérifier que l'utilisateur est authentifié et est admin
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])

    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")

    # Récupérer l'utilisateur cible
    target_user = crud.get_user_info_by_id(db, user_id=user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur non trouvé")

    # Empêcher un admin de se retirer ses propres droits admin
    if target_user.id == current_user.id and rights.is_superuser == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous ne pouvez pas retirer vos propres droits administrateur",
        )

    # Mettre à jour les droits
    if rights.is_active is not None:
        crud.activate_user(db, target_user, is_active=rights.is_active)
        logger.info(f"Admin {current_user.email}: is_active de {target_user.email} → {rights.is_active}")

    if rights.is_superuser is not None:
        crud.admin_user(db, target_user, is_superuser=rights.is_superuser)
        logger.info(f"Admin {current_user.email}: is_superuser de {target_user.email} → {rights.is_superuser}")

    # Récupérer l'utilisateur mis à jour
    updated_user = crud.get_user_info_by_id(db, user_id=user_id)
    return updated_user


# récupere les info de l'utilisateur courant par son id (tâche 90: persistance de session)
@router.get("/me", response_model=schemas.UserAdmin)
async def get_me(request: Request, db: db_dependency):
    """Endpoint pour vérifier la session et récupérer les infos utilisateur
    Utilisé au chargement des pages pour la persistance de session
    """
    user_data = await get_current_user(request)
    user = crud.get_user_info_by_id(db, user_id=user_data["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user


# effacer un utilisateur par son id
# Réservé aux superusers, auto-suppression interdite (SEC-02)
@router.delete("/delete/{user_id}/")
async def delete_user(request: Request, user_id: int, db: db_dependency):
    # Vérifier que l'utilisateur est authentifié ET superuser (SEC-02)
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Impossible de supprimer votre propre compte"
        )
    user = crud.get_user_info_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    crud.delete_user(db, user_id=user_id)
    return {"message": "Utilisateur supprimé avec succès"}


##################################################################
# login section - Tâche 80 : stockage du token dans un cookie HttpOnly
@router.post("/login")
async def login(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    """Authentification utilisateur avec stockage du token dans un cookie HttpOnly sécurisé
    :param response: objet Response pour définir le cookie
    :param form_data: données du formulaire (username/password)
    :param db: session de base de données
    :return: message de succès
    """
    # SEC-21 : rate-limiting sur le login (clé par email pour limiter le bruteforce ciblant un compte)
    email_normalise = (form_data.username or "").lower().strip()
    cle_rate_limit = f"login:{email_normalise}"
    check_rate_limit(cle_rate_limit)

    # get the user from the DB by email, email vient de la form flask utiliser pour le login
    # TODO : changer form_data.username par form_data.email
    user = crud.get_user_info_by_email(db, email=form_data.username)
    if not user:
        # Enregistrer la tentative échouée même si l'utilisateur n'existe pas (anti-énumération)
        record_failed_attempt(cle_rate_limit)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="L'utilisateur n'existe pas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.password):
        record_failed_attempt(cle_rate_limit)
        raise HTTPException(status_code=400, detail="Es tu sur de ton mot de passe ?")

    # Connexion réussie : nettoyer les tentatives précédentes
    clear_failed_attempts(cle_rate_limit)

    # Créer le token JWT
    access_token = create_access_token(user.email, user.id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # Stocker le token dans un cookie HttpOnly sécurisé (Tâche 80)
    response.set_cookie(
        key=COOKIE_NAME,
        value=f"Bearer {access_token}",
        httponly=True,  # Protection XSS: pas accessible via JavaScript
        secure=False,  # TODO: mettre True en production (nécessite HTTPS)
        samesite="lax",  # Protection CSRF
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # En secondes
    )

    logger.info(f"Utilisateur {user.email} connecté avec succès (cookie HttpOnly)")

    return {"message": "Connexion réussie", "user": {"email": user.email, "id": user.id}}


##################################################################
# logout - supprimer le cookie
@router.post("/logout")
async def logout(response: Response):
    """Déconnexion utilisateur en supprimant le cookie HttpOnly
    :param response: objet Response pour supprimer le cookie
    :return: message de succès
    """
    response.delete_cookie(key=COOKIE_NAME)
    logger.info("Utilisateur déconnecté (cookie supprimé)")
    return {"message": "Déconnexion réussie"}


##################################################################
# update password
@router.put("/update_password")
async def update_password(request: Request, form_data: PasswordUpdateForm, db: db_dependency):
    """Mise à jour du mot de passe de l'utilisateur connecté
    :param request: requête contenant le token dans le cookie
    :param form_data: ancien et nouveau mot de passe
    :param db: session de base de données
    """
    # Récupérer l'utilisateur connecté depuis le cookie
    user_data = await get_current_user(request)
    user_id = user_data["id"]
    # On récupère les données de l'utilisateur pour faire des vérification
    user = crud.get_user_info_by_id(db, user_id=user_id)

    # if not user:
    #     raise HTTPException(status_code=400, detail="L'utilisateur n'existe pas")

    if not verify_password(form_data.current_password, user.password):
        raise HTTPException(status_code=400, detail="Es tu sur de ton mot de passe ?")

    # update the password
    crud.update_password_user(db, user, get_password_hash(form_data.new_password))
    return {"message": "Mot de passe mis à jour avec succès"}


##################################################################
# update profile (Tâche 210)
@router.put("/update_profile")
async def update_profile(request: Request, form_data: schemas.UserProfileUpdate, db: db_dependency):
    """Mise à jour du profil utilisateur (prénom, nom, email)
    :param request: requête contenant le token dans le cookie
    :param form_data: nouvelles informations du profil
    :param db: session de base de données
    """
    # Récupérer l'utilisateur connecté depuis le cookie
    user_data = await get_current_user(request)
    user_id = user_data["id"]

    # Vérifier si l'email n'est pas déjà utilisé par un autre utilisateur
    existing_user = crud.get_user_info_by_email(db, email=form_data.email)
    if existing_user and existing_user.id != user_id:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé par un autre compte")

    # Mettre à jour le profil
    updated_user = crud.update_user_profile(db, user_id, form_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    logger.info(f"Profil mis à jour pour l'utilisateur {user_id}")
    return {"message": "Profil mis à jour avec succès"}


##################################################################
# Réinitialisation de mot de passe (Tâches 110-120)


def create_password_reset_token(email: str, user_id: int) -> str:
    """Crée un token JWT pour la réinitialisation de mot de passe
    :param email: email de l'utilisateur
    :param user_id: id de l'utilisateur
    :return: token JWT
    """
    expire = datetime.now(UTC) + timedelta(minutes=password_reset.token_expire_minutes)
    payload = {"sub": email, "id": user_id, "type": "password_reset", "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> dict:
    """Vérifie et décode un token de réinitialisation de mot de passe
    :param token: le token JWT
    :return: payload décodé (email, user_id)
    :raises HTTPException: si le token est invalide ou expiré
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Vérifier que c'est bien un token de reset password
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalide")

        email = payload.get("sub")
        user_id = payload.get("id")

        if not email or not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token malformé")

        return {"email": email, "user_id": user_id}

    except JWTError as e:
        logger.warning(f"Token de reset password invalide ou expiré: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le lien de réinitialisation est invalide ou a expiré"
        )


@router.post("/forgot-password")
async def forgot_password(request_data: ForgotPasswordRequest, db: db_dependency):
    """Demande de réinitialisation de mot de passe
    Génère un token et log l'URL (en dev) ou envoie un email (en prod)

    Note: Toujours retourner succès même si l'email n'existe pas (sécurité)
    """
    email = request_data.email.lower().strip()

    # SEC-21 : rate-limiting sur la demande de reset (clé par email)
    # On enregistre toujours une tentative pour ne pas révéler si l'email existe
    cle_rate_limit = f"forgot:{email}"
    check_rate_limit(cle_rate_limit)
    record_failed_attempt(cle_rate_limit)

    # Chercher l'utilisateur
    user = crud.get_user_info_by_email(db, email=email)

    if user:
        # Générer le token
        reset_token = create_password_reset_token(email, user.id)

        # Construire l'URL de reset
        reset_url = f"{password_reset.frontend_url}/reset-password?token={reset_token}"

        # Envoyer l'email de réinitialisation
        send_password_reset_email(
            to=user.email,
            firstname=user.firstname,
            reset_url=reset_url,
            expire_minutes=password_reset.token_expire_minutes,
        )

        # Ne pas logger le token en production (SEC-04)
        logger.info(f"Demande de réinitialisation de mot de passe pour: {email}")
    else:
        # Ne pas révéler si l'email existe ou non (sécurité)
        logger.info(f"Demande de reset pour email inexistant: {email}")

    # Toujours retourner le même message (sécurité)
    return {"message": "Si cette adresse email est associée à un compte, vous recevrez un lien de réinitialisation."}


@router.get("/admin_reset_link/{user_id}")
async def admin_reset_link(request: Request, user_id: int, db: db_dependency):
    """Génère un lien de réinitialisation de mot de passe pour un utilisateur (réservé aux superusers).
    Flux de secours quand l'email ne fonctionne pas : l'admin transmet l'URL manuellement.
    """
    # Vérifier que l'utilisateur est authentifié ET superuser (SEC-04)
    current_user_data = await get_current_user(request)
    current_user = crud.get_user_info_by_id(db, user_id=current_user_data["id"])
    if not current_user or not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs")

    # Vérifier que l'utilisateur cible existe
    target_user = crud.get_user_info_by_id(db, user_id=user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    # Générer le token et l'URL
    reset_token = create_password_reset_token(target_user.email, target_user.id)
    reset_url = f"{password_reset.frontend_url}/reset-password?token={reset_token}"

    logger.info(f"Admin {current_user.email}: génération lien reset pour {target_user.email}")

    return {
        "reset_url": reset_url,
        "user_email": target_user.email,
        "expire_minutes": password_reset.token_expire_minutes,
    }


@router.post("/reset-password")
async def reset_password(request_data: ResetPasswordRequest, db: db_dependency):
    """Réinitialise le mot de passe avec un token valide"""
    # Vérifier le token
    token_data = verify_password_reset_token(request_data.token)

    # Récupérer l'utilisateur
    user = crud.get_user_info_by_id(db, user_id=token_data["user_id"])

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utilisateur non trouvé")

    # Vérifier que l'email correspond (double sécurité)
    if user.email.lower() != token_data["email"].lower():
        logger.error(f"Mismatch email dans token reset: {token_data['email']} vs {user.email}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalide")

    # Valider le nouveau mot de passe (min 8 caractères)
    if len(request_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le mot de passe doit contenir au moins 8 caractères"
        )

    # Mettre à jour le mot de passe
    hashed_password = get_password_hash(request_data.new_password)
    crud.update_password_user(db, user, hashed_password)

    logger.info(f"Mot de passe réinitialisé avec succès pour {user.email}")

    return {"message": "Votre mot de passe a été réinitialisé avec succès"}
