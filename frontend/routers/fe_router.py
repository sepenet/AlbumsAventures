import logging
import os
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from PIL import Image as PILImage
from PIL.ExifTags import TAGS

from utils.auth import require_auth, require_superuser
from utils.config import backend_api, image
from utils.csrf import get_csrf_token, set_csrf_cookie, validate_csrf_token

# Configuration du logger
logger = logging.getLogger(__name__)

router = APIRouter(tags=["frontend"])

templates = Jinja2Templates(directory="frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def frontend_index(request: Request):
    """Page d'accueil - Liste des albums
    Vérifie côté serveur que l'utilisateur est authentifié
    Tâche 160 : Récupération des albums réels via API backend
    Tâche 180 : Filtres par catégorie
    """
    is_authenticated, user = await require_auth(request)
    if not is_authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Récupération des albums via l'API backend (Tâche 160)
    # L'API retourne directement image_cover_url calculé côté backend
    albums = []
    try:
        user_id = user.get("id")
        logger.info(f"Récupération des albums pour l'utilisateur {user_id}")

        async with httpx.AsyncClient() as client:
            # Appel à l'API backend avec le cookie d'authentification
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_albums_by_user/{user_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                albums = resp.json()
                logger.info(f"{len(albums)} album(s) récupéré(s) pour l'utilisateur {user_id}")
            elif resp.status_code == 404:
                # Aucun album trouvé pour cet utilisateur
                logger.info(f"Aucun album trouvé pour l'utilisateur {user_id}")
                albums = []
            else:
                logger.warning(f"Erreur lors de la récupération des albums: status {resp.status_code}")
                albums = []

    except httpx.TimeoutException:
        logger.warning(f"Timeout lors de la récupération des albums pour l'utilisateur {user_id}")
        albums = []
    except httpx.ConnectError:
        logger.error(f"Impossible de se connecter au backend {backend_api.album_url}")
        albums = []
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des albums: {type(e).__name__}: {e}")
        albums = []

    # Récupération des catégories pour les filtres (Tâche 180)
    categories = await _get_categories(request)

    return templates.TemplateResponse("index.html", {"request": request, "albums": albums, "categories": categories})


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse("login.html", {"request": request, "error": None, "csrf_token": csrf_token})
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    """Login frontend qui transfère le cookie HttpOnly du backend au client
    Tâche 80 : Gestion du cookie JWT sécurisé
    Tâche 130 : Protection CSRF
    """
    # Validation du token CSRF
    if not validate_csrf_token(request, csrf_token):
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "login.html", {"request": request, "error": "Session expirée. Veuillez réessayer.", "csrf_token": new_csrf}
        )
        set_csrf_cookie(response, new_csrf)
        return response

    # Envoi des credentials au backend d'authentification
    async with httpx.AsyncClient() as client:
        try:
            # OAuth2PasswordRequestForm expects form-encoded fields 'username' and 'password'
            resp = await client.post(
                f"{backend_api.auth_url}/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=backend_api.default_timeout,
            )
        except httpx.TimeoutException:
            logger.warning(f"Timeout lors de la tentative de login pour {email}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Le serveur met trop de temps à répondre. Réessayez.",
                    "csrf_token": new_csrf,
                },
            )
            set_csrf_cookie(response, new_csrf)
            return response
        except httpx.ConnectError:
            logger.error(f"Impossible de se connecter au backend {backend_api.auth_url}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": "Impossible de contacter le serveur. Réessayez plus tard.",
                    "csrf_token": new_csrf,
                },
            )
            set_csrf_cookie(response, new_csrf)
            return response
        except Exception as e:
            logger.error(f"Erreur inattendue lors du login: {type(e).__name__}: {e}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "error": f"Erreur de connexion au serveur backend: {str(e)}",
                    "csrf_token": new_csrf,
                },
            )
            set_csrf_cookie(response, new_csrf)
            return response

    if resp.status_code == 200:
        # Créer une réponse de redirection
        redirect_response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

        # Transférer le cookie 'access_token' du backend au client (Tâche 80)
        # Le backend a déjà défini le cookie dans sa réponse, on le récupère et le transfère
        if "set-cookie" in resp.headers:
            # Récupérer tous les cookies Set-Cookie de la réponse backend
            cookies = resp.headers.get_list("set-cookie")
            for cookie in cookies:
                if cookie.startswith("access_token="):
                    # Parser le cookie pour extraire ses composants
                    redirect_response.headers.append("set-cookie", cookie)
                    break

        return redirect_response
    else:
        error_detail = "Identifiants invalides"
        try:
            error_data = resp.json()
            if "detail" in error_data:
                error_detail = error_data["detail"]
        except Exception:
            pass

        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "login.html", {"request": request, "error": error_detail, "csrf_token": new_csrf}
        )
        set_csrf_cookie(response, new_csrf)
        return response


##################################################################
# Réinitialisation de mot de passe (Tâches 110-120)
@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_get(request: Request):
    """Affiche la page de demande de réinitialisation de mot de passe"""
    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse("forgot_password.html", {"request": request, "csrf_token": csrf_token})
    set_csrf_cookie(response, csrf_token)
    return response


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_get(request: Request):
    """Affiche la page de réinitialisation de mot de passe
    Le token est passé en paramètre GET et géré côté client
    """
    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse("reset_password.html", {"request": request, "csrf_token": csrf_token})
    set_csrf_cookie(response, csrf_token)
    return response


##################################################################
# Signup routes (Tâche 100)
@router.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    """Affiche la page d'inscription"""
    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse("signup.html", {"request": request, "error": None, "csrf_token": csrf_token})
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/signup")
async def signup_post(
    request: Request,
    firstname: str = Form(...),
    lastname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirmPassword: str = Form(...),
    csrf_token: str = Form(...),
):
    """Traitement de l'inscription utilisateur avec validation côté serveur
    Tâche 100 : Page d'inscription avec validation
    Tâche 130 : Protection CSRF
    """
    # Validation du token CSRF
    if not validate_csrf_token(request, csrf_token):
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "signup.html", {"request": request, "error": "Session expirée. Veuillez réessayer.", "csrf_token": new_csrf}
        )
        set_csrf_cookie(response, new_csrf)
        return response

    # Validation côté serveur (double sécurité)
    errors = []

    if len(firstname.strip()) < 2:
        errors.append("Le prénom doit contenir au moins 2 caractères")

    if len(lastname.strip()) < 2:
        errors.append("Le nom doit contenir au moins 2 caractères")

    if len(password) < 8:
        errors.append("Le mot de passe doit contenir au moins 8 caractères")

    if password != confirmPassword:
        errors.append("Les mots de passe ne correspondent pas")

    if errors:
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "signup.html", {"request": request, "error": " • ".join(errors), "csrf_token": new_csrf}
        )
        set_csrf_cookie(response, new_csrf)
        return response

    # Appel au backend pour créer l'utilisateur
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{backend_api.auth_url}/create/",
                json={
                    "firstname": firstname,
                    "lastname": lastname,
                    "email": email,
                    "password": password,
                    "is_active": False,  # En attente de validation admin (Tâche 111)
                    "is_superuser": False,
                },
                timeout=backend_api.default_timeout,
            )
        except httpx.TimeoutException:
            logger.warning(f"Timeout lors de l'inscription pour {email}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "signup.html",
                {
                    "request": request,
                    "error": "Le serveur met trop de temps à répondre. Réessayez.",
                    "csrf_token": new_csrf,
                },
            )
            set_csrf_cookie(response, new_csrf)
            return response
        except httpx.ConnectError:
            logger.error(f"Impossible de se connecter au backend {backend_api.auth_url}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "signup.html",
                {
                    "request": request,
                    "error": "Impossible de contacter le serveur. Réessayez plus tard.",
                    "csrf_token": new_csrf,
                },
            )
            set_csrf_cookie(response, new_csrf)
            return response
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'inscription: {type(e).__name__}: {e}")
            new_csrf = get_csrf_token(request)
            response = templates.TemplateResponse(
                "signup.html",
                {"request": request, "error": f"Erreur de connexion au serveur: {str(e)}", "csrf_token": new_csrf},
            )
            set_csrf_cookie(response, new_csrf)
            return response

    if resp.status_code == 200:
        # Inscription réussie → redirection vers login avec message de succès
        # Note: on pourrait aussi connecter automatiquement l'utilisateur ici
        return RedirectResponse(url="/login?registered=true", status_code=status.HTTP_303_SEE_OTHER)
    else:
        # Erreur d'inscription (email déjà existant, etc.)
        try:
            error_data = resp.json()
            error_detail = error_data.get("detail", "Erreur lors de l'inscription")
        except Exception:
            error_detail = "Erreur lors de l'inscription"

        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "signup.html", {"request": request, "error": error_detail, "csrf_token": new_csrf}
        )
        set_csrf_cookie(response, new_csrf)
        return response


##################################################################
# Page de profil utilisateur (Tâche 210)
@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Page de profil utilisateur
    Permet de modifier ses informations personnelles et son mot de passe
    """
    is_authenticated, user = await require_auth(request)
    if not is_authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Récupérer les informations complètes de l'utilisateur
    user_data = {}
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.user_url}/get_user_profile/{user.get('id')}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )
            if resp.status_code == 200:
                user_data = resp.json()
            else:
                # Fallback avec les données du token
                user_data = {"id": user.get("id"), "email": user.get("email"), "firstname": "", "lastname": ""}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du profil: {e}")
        user_data = {"id": user.get("id"), "email": user.get("email"), "firstname": "", "lastname": ""}

    return templates.TemplateResponse("profile.html", {"request": request, "user": user_data})


##################################################################
# Admin routes (Tâche 111)
@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """Affiche la page d'administration des utilisateurs
    Vérifie côté serveur que l'utilisateur est authentifié ET superuser
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        # Non authentifié → redirection vers login
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        # Authentifié mais non admin → redirection vers accueil
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("admin_users.html", {"request": request})


@router.get("/admin/groups", response_class=HTMLResponse)
async def admin_groups_page(request: Request):
    """Affiche la page d'administration des groupes et accès
    Tâches 250, 260 : Gestion des liens Utilisateurs ↔ Groupes, Albums ↔ Groupes
    Vérifie côté serveur que l'utilisateur est authentifié ET superuser
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        # Non authentifié → redirection vers login
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        # Authentifié mais non admin → redirection vers accueil
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("admin_groups.html", {"request": request})


##################################################################
# Création de catégorie via AJAX (réservé aux superusers)
@router.post("/category/create")
async def category_create_ajax(request: Request):
    """Création d'une nouvelle catégorie via AJAX
    Réservé aux superusers uniquement pour éviter la création anarchique
    """
    from fastapi.responses import JSONResponse

    is_superuser, user = await require_superuser(request)

    if user is None:
        return JSONResponse(status_code=401, content={"detail": "Non authentifié"})

    if not is_superuser:
        return JSONResponse(status_code=403, content={"detail": "Réservé aux administrateurs"})

    try:
        body = await request.json()
        category_name = body.get("category", "").strip()
        csrf_token = body.get("csrf_token", "")

        # Validation CSRF
        if not validate_csrf_token(request, csrf_token):
            return JSONResponse(status_code=403, content={"detail": "Session expirée. Veuillez rafraîchir la page."})

        # Validation du nom
        if len(category_name) < 3:
            return JSONResponse(status_code=400, content={"detail": "Le nom doit contenir au moins 3 caractères"})

        if len(category_name) > 128:
            return JSONResponse(status_code=400, content={"detail": "Le nom ne peut pas dépasser 128 caractères"})

        # Création via l'API backend
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.post(
                f"{backend_api.category_url}/create_category/",
                json={"category": category_name},
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                category = resp.json()
                logger.info(f"Catégorie créée: {category_name} (id={category.get('id')})")
                return JSONResponse(content=category)
            elif resp.status_code == 400:
                return JSONResponse(status_code=400, content={"detail": "Cette catégorie existe déjà"})
            else:
                logger.error(f"Erreur création catégorie: {resp.status_code} - {resp.text}")
                return JSONResponse(status_code=500, content={"detail": "Erreur lors de la création"})

    except Exception as e:
        logger.error(f"Erreur création catégorie: {type(e).__name__}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur"})


##################################################################
# Album CRUD routes (Tâche 260) - DOIT être avant /album/{album_id}
@router.get("/album/new", response_class=HTMLResponse)
async def album_create_page(request: Request):
    """Page de création d'un nouvel album
    Tâche 260 : Formulaire CRUD pour nouvel album (superusers seulement)
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    categories = await _get_categories(request)

    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse(
        "album_form.html", {"request": request, "categories": categories, "csrf_token": csrf_token, "error": None}
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/album/new")
async def album_create_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category_id: int = Form(...),
    date: str = Form(...),
    participants: str = Form(""),
    location: str = Form(""),
    tags: str = Form(""),
    csrf_token: str = Form(...),
):
    """Traitement du formulaire de création d'album
    Tâche 260 : Création album + upload image de couverture
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    if not validate_csrf_token(request, csrf_token):
        categories = await _get_categories(request)
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "album_form.html",
            {
                "request": request,
                "categories": categories,
                "csrf_token": new_csrf,
                "error": "Session expirée. Veuillez réessayer.",
            },
        )
        set_csrf_cookie(response, new_csrf)
        return response

    form = await request.form()
    image_file = form.get("image_cover")
    image_cover_filename = ""

    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}

            album_data = {
                "title": title,
                "description": description if description else None,
                "category_id": category_id,
                "date": date,
                "participants": participants if participants else None,
                "location": location if location else None,
                "tags": tags if tags else None,
                "image_cover": image_cover_filename if image_cover_filename else None,
            }

            resp = await client.post(
                f"{backend_api.album_url}/create_album/",
                json=album_data,
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                album = resp.json()
                album_id = album.get("id")
                logger.info(f"Album créé avec succès: id={album_id}, title={title}")

                # Récupérer l'album complet avec la catégorie pour avoir le nom de catégorie
                try:
                    album_resp = await client.get(
                        f"{backend_api.album_url}/get_album_by_id/{album_id}",
                        cookies=cookies,
                        timeout=backend_api.default_timeout,
                    )
                    if album_resp.status_code == 200:
                        album = album_resp.json()  # Contient maintenant 'category'
                except Exception as e:
                    logger.warning(f"Impossible de récupérer l'album complet: {e}")

                # Créer les répertoires images et thumbnails via l'API backend
                try:
                    folder_resp = await client.get(
                        f"{backend_api.album_url}/create_album_folder/{album_id}",
                        cookies=cookies,
                        timeout=backend_api.default_timeout,
                    )
                    if folder_resp.status_code == 200:
                        logger.info(f"Répertoires images/thumbnails créés pour l'album {album_id}")
                    else:
                        logger.warning(f"Erreur création répertoires: status {folder_resp.status_code}")
                except Exception as e:
                    logger.error(f"Erreur création répertoires album: {e}")

                # Lier l'album au groupe "Tous les Albums"
                try:
                    # Récupérer l'ID du groupe "Tous les Albums"
                    group_resp = await client.get(
                        f"{backend_api.group_url}/get_group_by_name/{backend_api.default_group_name}",
                        cookies=cookies,
                        timeout=backend_api.default_timeout,
                    )
                    if group_resp.status_code == 200:
                        group = group_resp.json()
                        group_id = group.get("id")

                        # Créer le lien album-groupe
                        link_resp = await client.post(
                            f"{backend_api.group_url}/create_album_group/",
                            json={"album_id": album_id, "group_id": group_id},
                            cookies=cookies,
                            timeout=backend_api.default_timeout,
                        )
                        if link_resp.status_code == 200:
                            logger.info(f"Album {album_id} lié au groupe '{backend_api.default_group_name}'")
                        else:
                            logger.warning(f"Erreur liaison album-groupe: status {link_resp.status_code}")
                    else:
                        logger.warning(f"Groupe '{backend_api.default_group_name}' non trouvé")
                except Exception as e:
                    logger.error(f"Erreur lors de la liaison album-groupe: {e}")

                if image_file and hasattr(image_file, "filename") and image_file.filename:
                    try:
                        await _save_cover_image(album, image_file)

                        await client.patch(
                            f"{backend_api.album_url}/update_album/{album_id}",
                            json={"image_cover": image_file.filename},
                            cookies=cookies,
                            timeout=backend_api.default_timeout,
                        )
                        logger.info(f"Image de couverture sauvegardée: {image_file.filename}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la sauvegarde de l'image: {e}")

                # Redirection vers page admin groupes pour configurer les associations
                return RedirectResponse(url="/admin/groups", status_code=status.HTTP_303_SEE_OTHER)

            else:
                try:
                    error_data = resp.json()
                    error_detail = error_data.get("detail", "Erreur lors de la création de l'album")
                except Exception:
                    error_detail = f"Erreur serveur (code {resp.status_code})"

                categories = await _get_categories(request)
                new_csrf = get_csrf_token(request)
                response = templates.TemplateResponse(
                    "album_form.html",
                    {"request": request, "categories": categories, "csrf_token": new_csrf, "error": error_detail},
                )
                set_csrf_cookie(response, new_csrf)
                return response

    except httpx.TimeoutException:
        logger.warning(f"Timeout lors de la création de l'album {title}")
        categories = await _get_categories(request)
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "album_form.html",
            {
                "request": request,
                "categories": categories,
                "csrf_token": new_csrf,
                "error": "Le serveur met trop de temps à répondre. Réessayez.",
            },
        )
        set_csrf_cookie(response, new_csrf)
        return response

    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de l'album: {type(e).__name__}: {e}")
        categories = await _get_categories(request)
        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "album_form.html",
            {
                "request": request,
                "categories": categories,
                "csrf_token": new_csrf,
                "error": f"Erreur inattendue: {str(e)}",
            },
        )
        set_csrf_cookie(response, new_csrf)
        return response


##################################################################
# Album Edit routes (Tâche 280)
@router.get("/album/{album_id}/edit", response_class=HTMLResponse)
async def album_edit_page(album_id: int, request: Request):
    """Page de modification d'un album existant
    Tâche 280 : Formulaire d'édition pour album existant (superusers seulement)
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Récupérer l'album existant
    album = None
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_album_by_id/{album_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                album = resp.json()
            else:
                logger.warning(f"Album {album_id} non trouvé pour édition")
                return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(f"Erreur récupération album {album_id}: {e}")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    categories = await _get_categories(request)

    # Convertir participants et tags du format DB (|) au format Web (, )
    participants_db = album.get("participants") or ""
    tags_db = album.get("tags") or ""
    participants_web = ", ".join([p.strip() for p in participants_db.split("|") if p.strip()])
    tags_web = ", ".join([t.strip() for t in tags_db.split("|") if t.strip()])

    csrf_token = get_csrf_token(request)
    response = templates.TemplateResponse(
        "album_edit.html",
        {
            "request": request,
            "album": album,
            "categories": categories,
            "participants_web": participants_web,
            "tags_web": tags_web,
            "csrf_token": csrf_token,
            "error": None,
        },
    )
    set_csrf_cookie(response, csrf_token)
    return response


@router.post("/album/{album_id}/edit")
async def album_edit_post(
    album_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category_id: int = Form(...),
    date: str = Form(...),
    participants: str = Form(""),
    location: str = Form(""),
    tags: str = Form(""),
    csrf_token: str = Form(...),
):
    """Traitement du formulaire de modification d'album
    Tâche 280 : Modification album + renommage répertoire si nécessaire
    """
    is_superuser, user = await require_superuser(request)

    if user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    if not is_superuser:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Helper pour afficher les erreurs
    async def _render_error(error_msg: str):
        album = None
        try:
            async with httpx.AsyncClient() as client:
                cookies = {"access_token": request.cookies.get("access_token", "")}
                resp = await client.get(
                    f"{backend_api.album_url}/get_album_by_id/{album_id}",
                    cookies=cookies,
                    timeout=backend_api.default_timeout,
                )
                if resp.status_code == 200:
                    album = resp.json()
        except Exception:
            pass

        if album is None:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

        categories = await _get_categories(request)
        participants_web = ", ".join([p.strip() for p in (album.get("participants") or "").split("|") if p.strip()])
        tags_web = ", ".join([t.strip() for t in (album.get("tags") or "").split("|") if t.strip()])

        new_csrf = get_csrf_token(request)
        response = templates.TemplateResponse(
            "album_edit.html",
            {
                "request": request,
                "album": album,
                "categories": categories,
                "participants_web": participants_web,
                "tags_web": tags_web,
                "csrf_token": new_csrf,
                "error": error_msg,
            },
        )
        set_csrf_cookie(response, new_csrf)
        return response

    # Validation CSRF
    if not validate_csrf_token(request, csrf_token):
        return await _render_error("Session expirée. Veuillez réessayer.")

    # Convertir participants et tags du format Web (, ) au format DB (|)
    participants_db = "|".join([p.strip() for p in participants.split(",") if p.strip()])
    tags_db = "|".join([t.strip() for t in tags.split(",") if t.strip()])

    form = await request.form()
    image_file = form.get("image_cover")

    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}

            # Données de mise à jour
            album_data = {
                "title": title,
                "description": description if description else None,
                "category_id": category_id,
                "date": date,
                "participants": participants_db if participants_db else None,
                "location": location if location else None,
                "tags": tags_db if tags_db else None,
            }

            # Appeler l'API de mise à jour
            resp = await client.patch(
                f"{backend_api.album_url}/update_album/{album_id}",
                json=album_data,
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                logger.info(f"Album {album_id} mis à jour: {title}")

                # Si nouvelle image de couverture uploadée
                if image_file and hasattr(image_file, "filename") and image_file.filename:
                    try:
                        # Récupérer l'album mis à jour pour avoir les bons chemins
                        album_resp = await client.get(
                            f"{backend_api.album_url}/get_album_by_id/{album_id}",
                            cookies=cookies,
                            timeout=backend_api.default_timeout,
                        )
                        if album_resp.status_code == 200:
                            album_full = album_resp.json()
                            await _save_cover_image(album_full, image_file)

                            await client.patch(
                                f"{backend_api.album_url}/update_album/{album_id}",
                                json={"image_cover": image_file.filename},
                                cookies=cookies,
                                timeout=backend_api.default_timeout,
                            )
                            logger.info(f"Image de couverture mise à jour: {image_file.filename}")
                    except Exception as e:
                        logger.error(f"Erreur sauvegarde image: {e}")

                return RedirectResponse(url=f"/album/{album_id}", status_code=status.HTTP_303_SEE_OTHER)

            else:
                try:
                    error_data = resp.json()
                    error_detail = error_data.get("detail", "Erreur lors de la modification")
                except Exception:
                    error_detail = f"Erreur serveur (code {resp.status_code})"

                return await _render_error(error_detail)

    except httpx.TimeoutException:
        logger.warning(f"Timeout modification album {album_id}")
        return await _render_error("Le serveur met trop de temps à répondre. Réessayez.")

    except Exception as e:
        logger.error(f"Erreur modification album {album_id}: {type(e).__name__}: {e}")
        return await _render_error(f"Erreur inattendue: {str(e)}")


##################################################################
# Album detail routes (Tâche 170)

_PAGE_SIZE = 30
_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic")
_VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")
_ALL_EXTENSIONS = _IMAGE_EXTENSIONS + _VIDEO_EXTENSIONS


def _album_folder_info(album: dict) -> dict:
    """Calcule les chemins de dossiers pour un album."""
    category_folder = album.get("category", "").replace(" ", "-").replace("'", "-")
    title_folder = album.get("title", "").replace(" ", "-").replace("'", "-")
    participants_db = album.get("participants", "") or ""
    participants_parts = [p.replace("-", "").replace("'", "").strip() for p in participants_db.split("|") if p.strip()]
    participants_folder = "-".join(participants_parts)
    album_folder = f"{album.get('date')}_{title_folder}_{participants_folder}"
    thumbnails_dir = os.path.join(image.thumbnails_path, category_folder, album_folder)
    images_dir = os.path.join(image.image_path, category_folder, album_folder)
    return {
        "category_folder": category_folder,
        "album_folder": album_folder,
        "thumbnails_dir": thumbnails_dir,
        "images_dir": images_dir,
    }


def _get_album_media_page(album: dict, offset: int = 0, limit: int = _PAGE_SIZE) -> dict:
    """
    Retourne une page de médias pour un album, triés par date de modification.
    Lit les données EXIF uniquement pour la page demandée.
    Retourne {"items": [...], "total": int, "has_more": bool}
    """
    info = _album_folder_info(album)
    images_dir = info["images_dir"]
    thumbnails_dir = info["thumbnails_dir"]
    category_folder = info["category_folder"]
    album_folder = info["album_folder"]

    if not os.path.isdir(images_dir):
        return {"items": [], "total": 0, "has_more": False}

    # Étape 1 : lister tous les fichiers et trier par date de modification (rapide, pas de décodage)
    all_files = [f for f in os.listdir(images_dir) if f.lower().endswith(_ALL_EXTENSIONS)]
    file_mtimes = []
    for filename in all_files:
        try:
            mtime = os.path.getmtime(os.path.join(images_dir, filename))
        except OSError:
            mtime = 0
        file_mtimes.append((filename, mtime))
    file_mtimes.sort(key=lambda x: x[1])
    total = len(file_mtimes)

    # Étape 2 : page demandée
    page_files = file_mtimes[offset : offset + limit]

    # Étape 3 : lire EXIF/dimensions uniquement pour cette page
    media_files = []
    for filename, _ in page_files:
        is_video = filename.lower().endswith(_VIDEO_EXTENSIONS)
        original_path = os.path.join(images_dir, filename)

        if is_video:
            name, _ = os.path.splitext(filename)
            thumbnail_filename = f"{name}.jpg"
        else:
            thumbnail_filename = filename
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)

        img_width = None
        img_height = None
        if not is_video and os.path.isfile(original_path):
            try:
                with PILImage.open(original_path) as img:
                    img_width, img_height = img.size
                    exif_data = img._getexif()
                    if exif_data:
                        orientation = exif_data.get(274)
                        if orientation in (5, 6, 7, 8):
                            img_width, img_height = img_height, img_width
            except Exception as e:
                logger.debug(f"Impossible de lire EXIF pour {filename}: {e}")

        has_thumbnail = os.path.isfile(thumbnail_path)
        if has_thumbnail:
            thumbnail_url = f"/thumbnails/{quote(category_folder)}/{quote(album_folder)}/{quote(thumbnail_filename)}"
        elif is_video:
            thumbnail_url = "/static/images/video-placeholder.svg"
        else:
            thumbnail_url = f"/images/{quote(category_folder)}/{quote(album_folder)}/{quote(filename)}"

        media_files.append(
            {
                "filename": filename,
                "thumbnail_url": thumbnail_url,
                "full_url": f"/images/{quote(category_folder)}/{quote(album_folder)}/{quote(filename)}",
                "is_video": is_video,
                "has_thumbnail": has_thumbnail,
                "width": img_width,
                "height": img_height,
            }
        )

    return {
        "items": media_files,
        "total": total,
        "has_more": (offset + limit) < total,
    }


##################################################################
# Album partagé — page publique (Tâche 200)
@router.get("/album/shared", response_class=HTMLResponse)
async def shared_album_page(request: Request):
    """Page d'accès à un album partagé via lien + PIN.
    Le token est dans le query string, le PIN est saisi via formulaire.
    Aucune authentification requise.
    """
    token = request.query_params.get("token", "")
    if not token:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "shared_album.html",
        {
            "request": request,
            "token": token,
            "error": None,
        },
    )


@router.post("/album/shared", response_class=HTMLResponse)
async def shared_album_verify(
    request: Request,
    pin: str = Form(...),
    token: str = Form(...),
):
    """Valide le PIN côté serveur puis rend album_detail.html en mode partagé."""
    pin_upper = pin.strip().upper()

    # Valider token + PIN via le backend
    error_message = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{backend_api.album_url}/shared",
                params={"token": token, "pin": pin_upper},
                timeout=backend_api.default_timeout,
            )
            if resp.status_code == 200:
                album = resp.json()
            else:
                # Mapper les erreurs backend vers un message utilisateur
                try:
                    detail = resp.json().get("detail", {})
                    if isinstance(detail, dict):
                        err_code = detail.get("error", "")
                        if err_code == "invalid_pin":
                            remaining = detail.get("attempts_remaining", 0)
                            error_message = (
                                f"Code PIN incorrect. {remaining} tentative(s) restante(s)."
                                if remaining > 0
                                else "Accès bloqué temporairement."
                            )
                        elif err_code == "too_many_attempts":
                            error_message = detail.get("message", "Trop de tentatives.")
                        elif err_code == "token_expired":
                            error_message = "Ce lien de partage a expiré."
                        else:
                            error_message = detail.get("message", "Erreur lors de la vérification.")
                    else:
                        error_message = str(detail) if detail else "Erreur lors de la vérification."
                except Exception:
                    error_message = "Erreur lors de la vérification."

                return templates.TemplateResponse(
                    "shared_album.html",
                    {
                        "request": request,
                        "token": token,
                        "error": error_message,
                    },
                )
    except Exception as e:
        logger.error(f"Erreur shared_album_verify: {type(e).__name__}: {e}")
        return templates.TemplateResponse(
            "shared_album.html",
            {
                "request": request,
                "token": token,
                "error": "Erreur de connexion au serveur.",
            },
        )

    # Charger la première page de médias
    page_result = _get_album_media_page(album, offset=0, limit=_PAGE_SIZE)

    return templates.TemplateResponse(
        "album_detail.html",
        {
            "request": request,
            "album": album,
            "images": page_result["items"],
            "total_images": page_result["total"],
            "has_more": page_result["has_more"],
            "page_size": _PAGE_SIZE,
            "is_superuser": False,
            "is_shared": True,
            "share_token": token,
            "share_pin": pin_upper,
        },
    )


@router.get("/album/shared/images")
async def shared_album_images_api(
    request: Request,
    token: str = Query(...),
    pin: str = Query(..., min_length=6, max_length=6),
    offset: int = Query(0, ge=0),
    limit: int = Query(_PAGE_SIZE, ge=1, le=200),
):
    """Endpoint public pour charger les images d'un album partagé.
    Valide le token+PIN via le backend avant de retourner les fichiers.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{backend_api.album_url}/shared",
                params={"token": token, "pin": pin},
                timeout=backend_api.default_timeout,
            )
            if resp.status_code != 200:
                return JSONResponse(status_code=resp.status_code, content=resp.json())
            album = resp.json()
    except Exception as e:
        logger.error(f"Erreur shared_album_images_api: {type(e).__name__}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur"})

    result = _get_album_media_page(album, offset=offset, limit=limit)
    return JSONResponse(content=result)


@router.get("/album/{album_id}", response_class=HTMLResponse)
async def album_detail(album_id: int, request: Request):
    """Page de détail d'un album avec liste des images
    Tâche 170 : Affichage des images avec thumbnails et chargement progressif
    """
    is_authenticated, user = await require_auth(request)
    if not is_authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Récupérer les infos de l'album via l'API backend
    album = None
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_album_by_id/{album_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                album = resp.json()
                logger.info(f"Album {album_id} récupéré: {album.get('title')}")
            else:
                logger.warning(f"Album {album_id} non trouvé: status {resp.status_code}")
                return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'album {album_id}: {type(e).__name__}: {e}")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    # Charger uniquement la première page de médias
    page_result = _get_album_media_page(album, offset=0, limit=_PAGE_SIZE)

    logger.info(
        f"{page_result['total']} fichier(s) dans l'album {album_id}, "
        f"{len(page_result['items'])} chargés initialement"
    )

    # Vérifier si l'utilisateur est superuser pour afficher le bouton upload
    is_superuser, _ = await require_superuser(request)

    return templates.TemplateResponse(
        "album_detail.html",
        {
            "request": request,
            "album": album,
            "images": page_result["items"],
            "total_images": page_result["total"],
            "has_more": page_result["has_more"],
            "page_size": _PAGE_SIZE,
            "is_superuser": is_superuser,
            "is_shared": False,
        },
    )


##################################################################
# Album images API (chargement progressif)
@router.get("/album/{album_id}/images")
async def album_images_api(
    album_id: int,
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(_PAGE_SIZE, ge=1, le=100),
):
    """Endpoint JSON pour le chargement progressif des images d'un album."""
    is_authenticated, _ = await require_auth(request)
    if not is_authenticated:
        return JSONResponse(status_code=401, content={"detail": "Non authentifié"})

    album = None
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_album_by_id/{album_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )
            if resp.status_code == 200:
                album = resp.json()
            else:
                return JSONResponse(status_code=404, content={"detail": "Album introuvable"})
    except Exception as e:
        logger.error(f"Erreur album_images_api album {album_id}: {type(e).__name__}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Erreur serveur"})

    result = _get_album_media_page(album, offset=offset, limit=limit)
    return JSONResponse(content=result)


@router.get("/album/{album_id}/upload", response_class=HTMLResponse)
async def album_upload_page(album_id: int, request: Request):
    """Page d'upload d'images pour un album
    Tâche 290 : Upload images avec uppy.io
    Accessible à tous les utilisateurs authentifiés ayant accès à l'album
    """
    is_authenticated, user = await require_auth(request)

    if not is_authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # Récupérer les infos de l'album
    album = None
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.album_url}/get_album_by_id/{album_id}",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )

            if resp.status_code == 200:
                album = resp.json()
            else:
                return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'album {album_id}: {e}")
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse("album_upload.html", {"request": request, "album": album})


@router.get("/rando", response_class=HTMLResponse)
async def rando_page(request: Request):
    """Page publique - Propositions de randonnée (fichier statique)"""
    return RedirectResponse(url="/static/rando/propositions-rando.html", status_code=status.HTTP_302_FOUND)


async def _get_categories(request: Request) -> list:
    """Fonction utilitaire pour récupérer les catégories"""
    categories = []
    try:
        async with httpx.AsyncClient() as client:
            cookies = {"access_token": request.cookies.get("access_token", "")}
            resp = await client.get(
                f"{backend_api.category_url}/get_all_categories/",
                cookies=cookies,
                timeout=backend_api.default_timeout,
            )
            if resp.status_code == 200:
                categories = resp.json()
    except Exception:
        pass
    return categories


def _get_album_folder_path(album: dict) -> tuple[str, str]:
    """Construit le chemin du dossier album à partir des infos de l'album

    Retourne: (category_folder, album_folder)
    """
    category_folder = album.get("category", "").replace(" ", "-").replace("'", "-")
    if not category_folder:
        category_folder = "Uncategorized"

    title_folder = album.get("title", "").replace(" ", "-").replace("'", "-")

    participants_db = album.get("participants", "") or ""
    participants_parts = [p.replace("-", "").replace("'", "").strip() for p in participants_db.split("|") if p.strip()]
    participants_folder = "-".join(participants_parts)

    album_folder = f"{album.get('date')}_{title_folder}_{participants_folder}"

    return category_folder, album_folder


async def _save_cover_image(album: dict, image_file) -> None:
    """Sauvegarde l'image de couverture dans le répertoire de l'album

    L'image est sauvegardée dans:
    - images/{category}/{date}_{title}_{participants}/{filename}
    - thumbnails/{category}/{date}_{title}_{participants}/{filename}
    """
    category_folder, album_folder = _get_album_folder_path(album)

    images_dir = os.path.join(image.image_path, category_folder, album_folder)
    thumbnails_dir = os.path.join(image.thumbnails_path, category_folder, album_folder)

    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(thumbnails_dir, exist_ok=True)

    contents = await image_file.read()

    image_path_full = os.path.join(images_dir, image_file.filename)
    with open(image_path_full, "wb") as f:
        f.write(contents)

    thumbnail_path_full = os.path.join(thumbnails_dir, image_file.filename)
    try:
        from io import BytesIO

        img = PILImage.open(BytesIO(contents))
        img.thumbnail((image.thumbnail_width, image.thumbnail_height), PILImage.Resampling.LANCZOS)

        try:
            exif = img._getexif()
            if exif:
                orientation_tag = next((k for k, v in TAGS.items() if v == "Orientation"), None)
                if orientation_tag and orientation_tag in exif:
                    orientation = exif[orientation_tag]
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
        except Exception:
            pass

        img.save(thumbnail_path_full, quality=85, optimize=True)
        logger.info(f"Thumbnail créé: {thumbnail_path_full}")
    except Exception as e:
        logger.error(f"Erreur création thumbnail: {e}")
        with open(thumbnail_path_full, "wb") as f:
            f.write(contents)
