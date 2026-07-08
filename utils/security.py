"""
Middlewares de sécurité HTTP (transport + en-têtes).

Regroupe la configuration CORS et les en-têtes de sécurité afin qu'elle soit
identique entre l'application de production (``AlbumsAventures-BE.py``) et
l'application de test (``AlbumsAventures_BE_test.py``).

Contenu :
  • CORS piloté par config (jamais wildcard avec ``allow_credentials``)
  • TrustedHostMiddleware + redirection HTTPS + HSTS (production uniquement)
  • En-têtes de sécurité sur toutes les réponses : CSP, X-Content-Type-Options,
    X-Frame-Options, Referrer-Policy, Permissions-Policy
  • Durcissement des mounts média (/images, /thumbnails) : nosniff + CSP bac à
    sable pour neutraliser un éventuel SVG/HTML porteur de script.

Références :
  • CSP niveau 3 : https://www.w3.org/TR/CSP3/
  • HSTS (RFC 6797) : https://datatracker.ietf.org/doc/html/rfc6797
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from utils.config import app_config

logger = logging.getLogger(__name__)

# En-têtes TUS exposés au client (requis pour @uppy/tus, voir TODO #391/#392).
TUS_EXPOSE_HEADERS = [
    "Location",
    "Upload-Offset",
    "Upload-Length",
    "Upload-Expires",
    "Tus-Resumable",
    "Tus-Version",
    "Tus-Extension",
    "Tus-Max-Size",
]

# Méthodes/headers CORS réellement utilisés par l'application (double-submit CSRF,
# JSON API, TUS). On resserre volontairement depuis "*" (condition sécurité conseil).
CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
CORS_ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-CSRF-Token",
    "X-Requested-With",
    # En-têtes TUS envoyés par @uppy/tus lors des PATCH resumables.
    "Tus-Resumable",
    "Upload-Length",
    "Upload-Offset",
    "Upload-Metadata",
    "Upload-Concat",
    "Upload-Defer-Length",
]

# ──────────────────────────────────────────────────────────────────────────────
# Content Security Policy — politique UNIQUE durcie (Jinja décommissionné).
#
# La couche de repli Jinja2 (base.html + CDN + <script> inline) a été entièrement
# retirée : toutes les pages sont servies par la SPA React same-origin sous /app
# (assets bundlés hachés, aucun <script>/<style> inline). Une seule politique
# applicative durcie s'applique donc à toute la surface HTTP (SPA + API) :
#
#   • script-src 'self' UNIQUEMENT — aucun CDN, aucun 'unsafe-inline'/'unsafe-eval'.
#   • style-src 'self' 'unsafe-inline' — 'unsafe-inline' RÉSIDUEL, conservé pour
#     les styles injectés au runtime par des libs bundlées (ex. tableau de bord
#     Uppy). Retrait différé (hash/nonce des styles runtime).
#
# INVARIANTS (vérifiés par tests/test_auth.py::TestSecurityHeaders) :
#   • aucun 'unsafe-eval' ; aucune source large '*' ; aucun CDN.
#
# Les ressources média servies statiquement (/images, /thumbnails) gardent leur
# politique bac à sable distincte (_MEDIA_CSP), inchangée.
# ──────────────────────────────────────────────────────────────────────────────

# Directives partagées (indépendantes de script/style).
_CSP_SHARED: dict[str, list[str]] = {
    "default-src": ["'self'"],
    # Images/vignettes servies en local + previews Uppy (blob:) + data: (icônes).
    "img-src": ["'self'", "data:", "blob:"],
    "media-src": ["'self'", "blob:"],
    "font-src": ["'self'", "data:"],
    # XHR/fetch/TUS restent same-origin (le frontend appelle la même origine).
    "connect-src": ["'self'"],
    # Service worker Phase 4 : autoriser 'self' + blob: dès maintenant.
    "worker-src": ["'self'", "blob:"],
    "manifest-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
    # Force la mise à niveau des ressources http:// vers https:// en production.
    "upgrade-insecure-requests": [],
}

# Politique applicative UNIQUE (durcie) : same-origin, aucun CDN, aucun script
# inline. 'unsafe-inline' n'est conservé que sur ``style-src`` (styles runtime des
# libs bundlées ; retrait futur via hash/nonce).
_CSP_DIRECTIVES: dict[str, list[str]] = {
    **_CSP_SHARED,
    # Shell buildé = uniquement des <script>/<link> same-origin hachés -> 'self'.
    "script-src": ["'self'"],
    # 'unsafe-inline' RÉSIDUEL, uniquement pour les styles injectés au runtime.
    "style-src": ["'self'", "'unsafe-inline'"],
}

# CSP restrictive « bac à sable » pour les ressources média servies statiquement
# (/images, /thumbnails). Neutralise l'exécution de script d'un SVG/HTML hostile
# tout en laissant le rendu <img>/<video>.
_MEDIA_CSP = "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox"

# Extensions média « actives » à ne jamais servir en inline (SVG/HTML scriptables).
_MEDIA_ACTIVE_EXTENSIONS = (".svg", ".svgz", ".html", ".htm", ".xhtml", ".xml")

# Préfixes de chemins servis en fichiers statiques média.
_MEDIA_PATH_PREFIXES = ("/images", "/thumbnails")


def _build_csp(directives: dict[str, list[str]], include_upgrade_insecure: bool) -> str:
    """Construit la chaîne CSP à partir d'un jeu de directives.

    :param directives: politique à sérialiser (``_CSP_DIRECTIVES``).
    :param include_upgrade_insecure: ajoute ``upgrade-insecure-requests`` (prod HTTPS).
    """
    parties: list[str] = []
    for directive, sources in directives.items():
        if directive == "upgrade-insecure-requests":
            if include_upgrade_insecure:
                parties.append(directive)
            continue
        parties.append(f"{directive} {' '.join(sources)}".strip())
    return "; ".join(parties)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les en-têtes de sécurité sur toutes les réponses.

    Applique une CSP, ``X-Content-Type-Options: nosniff``, ``X-Frame-Options``,
    ``Referrer-Policy`` et ``Permissions-Policy``. Une politique CSP UNIQUE durcie
    (``script-src 'self'``, aucun CDN) s'applique à toute la surface applicative
    (SPA ``/app`` + API) depuis le décommissionnement de la couche Jinja. En
    production, ajoute HSTS et ``upgrade-insecure-requests``. Pour les mounts
    média, remplace la CSP par une politique bac à sable et force
    ``Content-Disposition: attachment`` sur les fichiers scriptables.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        is_prod = app_config.is_production()
        chemin = request.url.path

        # En-têtes communs à toutes les réponses.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )

        # HSTS uniquement en production (HTTPS requis, sinon dangereux en HTTP local).
        if is_prod:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={app_config.hsts_max_age}; includeSubDomains",
            )

        # Durcissement spécifique des ressources média servies statiquement.
        est_media = any(chemin.startswith(prefixe) for prefixe in _MEDIA_PATH_PREFIXES)
        if est_media:
            response.headers["Content-Security-Policy"] = _MEDIA_CSP
            if chemin.lower().endswith(_MEDIA_ACTIVE_EXTENSIONS):
                # SVG/HTML : jamais rendus en top-level -> téléchargement forcé.
                response.headers["Content-Disposition"] = "attachment"
        else:
            # CSP applicative UNIQUE (durcie) : même politique same-origin pour la
            # SPA (/app) et l'API. La couche Jinja (CDN + inline) est retirée.
            response.headers.setdefault(
                "Content-Security-Policy",
                _build_csp(_CSP_DIRECTIVES, include_upgrade_insecure=is_prod),
            )

        return response


def configure_cors(app: FastAPI) -> None:
    """Configure CORS à partir de la liste blanche d'origines (jamais wildcard).

    Les méthodes et en-têtes sont resserrés à ceux réellement utilisés.
    """
    origins = app_config.cors_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
        expose_headers=TUS_EXPOSE_HEADERS,
    )
    logger.info(f"CORS configuré pour {len(origins)} origine(s) : {origins}")


def configure_security(app: FastAPI) -> None:
    """Ajoute les middlewares de sécurité transport + en-têtes.

    En production : TrustedHostMiddleware + redirection HTTPS + HSTS.
    Toujours : middleware d'en-têtes de sécurité (CSP, nosniff, frame options...).

    Note ordre Starlette : le dernier middleware ajouté est le plus externe.
    On ajoute d'abord les en-têtes, puis (prod) HTTPS redirect et TrustedHost,
    afin que la validation d'hôte et la redirection s'exécutent en premier.
    """
    # En-têtes de sécurité (toutes réponses, tous environnements).
    app.add_middleware(SecurityHeadersMiddleware)

    if app_config.is_production():
        # Redirige http:// -> https:// avant tout traitement applicatif.
        app.add_middleware(HTTPSRedirectMiddleware)
        # Rejette les requêtes dont l'en-tête Host n'est pas dans la liste blanche.
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_config.trusted_hosts())
        logger.info("Middlewares production activés : HTTPS redirect + TrustedHost + HSTS")
    else:
        logger.info("Mode développement : en-têtes de sécurité actifs, HTTPS/HSTS désactivés")
