import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from utils.secret_store import SecretStore

##############################################
# Configuration globale
# Ce fichier contient les variables globales utilisées dans l'application
##############################################


# Configuration du logging
class logging_config:
    """Configuration centralisée du logging pour l'application"""

    # Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level = logging.INFO

    # Format des logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Dossier et fichier de logs
    log_directory = "logs"
    log_filename = "albums_aventures.log"

    # Rotation des fichiers de logs
    max_bytes = 10 * 1024 * 1024  # 10 MB par fichier
    backup_count = 5  # Garder 5 fichiers de backup

    @classmethod
    def setup_logging(cls):
        """Configure le système de logging pour toute l'application
        À appeler au démarrage de l'application dans AlbumsAventures-BE.py
        """
        # Créer le dossier de logs s'il n'existe pas
        if not os.path.exists(cls.log_directory):
            os.makedirs(cls.log_directory)

        # Chemin complet du fichier de log
        log_filepath = os.path.join(cls.log_directory, cls.log_filename)

        # Configuration du logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(cls.log_level)

        # Supprimer les handlers existants pour éviter les doublons
        root_logger.handlers.clear()

        # Formatter commun
        formatter = logging.Formatter(cls.log_format, cls.date_format)

        # Handler 1 : Console (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls.log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Handler 2 : Fichier avec rotation
        file_handler = RotatingFileHandler(
            log_filepath, maxBytes=cls.max_bytes, backupCount=cls.backup_count, encoding="utf-8"
        )
        file_handler.setLevel(cls.log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Log de démarrage
        root_logger.info("=" * 80)
        root_logger.info("Système de logging initialisé")
        root_logger.info(f"Niveau: {logging.getLevelName(cls.log_level)}")
        root_logger.info(f"Fichier: {log_filepath}")
        root_logger.info("=" * 80)


# classe image - tout ce qui concerne les images
class image:
    """définition des chemins pour les images"""

    # Chemin racine = répertoire frontend/static du projet
    # Utilise le chemin relatif au projet pour être portable
    import pathlib

    _project_root = pathlib.Path(__file__).parent.parent
    root_path = os.path.normpath(_project_root / "frontend" / "static")

    # Chemins relatifs pour images et thumbnails
    image_relative_path = "images" + os.path.sep
    thumbnail_relative_path = "thumbnails" + os.path.sep

    # Construire les chemins complets
    image_path = os.path.join(root_path, image_relative_path)
    thumbnails_path = os.path.join(root_path, thumbnail_relative_path)

    # Dossier temporaire pour les uploads TUS (resumable). Hors de frontend/static
    # pour éviter une exposition publique via le mount /static.
    tus_files_dir = os.path.normpath(_project_root / "uploads_tus")

    # Dimensions par défaut pour les miniatures
    thumbnail_width = 640
    thumbnail_height = 1080

    # Nombre maximum de threads simultanés pour la génération de vignettes TUS
    # (PIL/OpenCV). Borne le pool de workers du pipeline post-upload afin d'éviter
    # le spawn illimité de threads daemon sous forte charge (condition architecte
    # UPL-02). Réglable via THUMBNAIL_MAX_WORKERS ; défaut prudent = 2.
    max_thumbnail_workers = max(1, int(SecretStore.get("THUMBNAIL_MAX_WORKERS", "2")))

    @classmethod
    def log_paths(cls):
        """Log les chemins d'images — à appeler après l'initialisation du logging."""
        logger = logging.getLogger(__name__ + ".image")
        logger.info(f"Chemin racine des images: {cls.root_path}")
        logger.info(f"image_path: {cls.image_path}")
        logger.info(f"thumbnails_path: {cls.thumbnails_path}")


# Configuration du rate limiting pour le partage d'albums
class rate_limiting:
    """Configuration du rate limiting pour les tentatives de PIN"""

    max_attempts = 5  # Nombre max de tentatives échouées
    window_seconds = 900  # Fenêtre de temps en secondes (15 minutes)


# Configuration de l'authentification JWT
class auth_config:
    """Configuration JWT et cookies d'authentification"""

    # Clé secrète pour le hashage des tokens JWT
    # Générée via : openssl rand -hex 32
    secret_key = SecretStore.get("SECRET_KEY")  # OBLIGATOIRE — pas de défaut

    # Algorithme de hashage
    algorithm = SecretStore.get("JWT_ALGORITHM", "HS256")

    # Durée de vie du token d'authentification (en minutes)
    access_token_expire_minutes = int(SecretStore.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Nom du cookie HTTP pour stocker le token JWT
    cookie_name = SecretStore.get("COOKIE_NAME", "access_token")


# Configuration de sécurité applicative (transport, cookies, CORS, en-têtes)
class app_config:
    """Configuration de sécurité pilotée par l'environnement.

    Le drapeau ``ENVIRONMENT`` (development | production) commande le durcissement
    du transport : cookies ``Secure``, redirection HTTPS, HSTS et hôtes de confiance.
    En développement (défaut) tout reste compatible HTTP local (Windows/SQLite).
    """

    # Environnement d'exécution : "development" (défaut) ou "production"
    environment = SecretStore.get("ENVIRONMENT", "development").lower().strip()

    @classmethod
    def is_production(cls) -> bool:
        """Retourne True uniquement en production (durcissement transport actif)."""
        return cls.environment == "production"

    @classmethod
    def cookie_secure(cls) -> bool:
        """Cookies marqués ``Secure`` (HTTPS uniquement) en production."""
        # Permet un override explicite (ex. staging HTTP) via COOKIE_SECURE.
        override = SecretStore.get("COOKIE_SECURE", "").lower().strip()
        if override in ("true", "1", "yes"):
            return True
        if override in ("false", "0", "no"):
            return False
        return cls.is_production()

    @classmethod
    def cookie_samesite(cls) -> str:
        """Politique SameSite du cookie d'authentification (défaut : lax)."""
        return SecretStore.get("COOKIE_SAMESITE", "lax").lower().strip()

    @classmethod
    def cors_allowed_origins(cls) -> list[str]:
        """Liste blanche d'origines CORS, pilotée par config (jamais wildcard).

        ``CORS_ALLOWED_ORIGINS`` : liste séparée par des virgules. En développement,
        défaut sur l'origine locale historique.
        """
        raw = SecretStore.get("CORS_ALLOWED_ORIGINS", "http://localhost:5003")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @classmethod
    def trusted_hosts(cls) -> list[str]:
        """Hôtes autorisés pour TrustedHostMiddleware (défaut : tout en dev)."""
        raw = SecretStore.get("TRUSTED_HOSTS", "*")
        return [host.strip() for host in raw.split(",") if host.strip()]

    # Durée HSTS (secondes). 2 ans par défaut, appliqué uniquement en production.
    hsts_max_age = int(SecretStore.get("HSTS_MAX_AGE", "63072000"))

    @classmethod
    def legacy_xhr_upload_enabled(cls) -> bool:
        """Endpoint XHR multipart hérité (``POST /be_resizer/upload_images``).

        Le chemin d'upload par défaut est TUS resumable + golden-retriever
        (fiabilité mobile). L'ancien endpoint XHR est conservé UNIQUEMENT comme
        repli explicite, activable par configuration (condition architecte/sécurité
        UPL-06, TODO #395). Piloté par ``LEGACY_XHR_UPLOAD`` ; défaut activé pour
        préserver le repli et la compatibilité, à passer à ``false`` en production
        une fois TUS validé sur le terrain.
        """
        raw = SecretStore.get("LEGACY_XHR_UPLOAD", "true").lower().strip()
        return raw not in ("false", "0", "no", "off")


# Configuration du backend API
class backend_api:
    """Configuration centralisée des appels au backend API"""

    # URL de base du backend
    base_url = SecretStore.get("BACKEND_BASE_URL", "http://localhost:8003")

    # Endpoints d'authentification
    auth_url = f"{base_url}/be_auth"

    # Endpoints utilisateurs
    user_url = f"{base_url}/be_user"

    # Endpoints albums
    album_url = f"{base_url}/be_album"

    # Endpoints catégories
    category_url = f"{base_url}/be_category"

    # Endpoints groupes
    group_url = f"{base_url}/be_group"

    # Nom du groupe par défaut pour tous les albums
    default_group_name = "Tous les Albums"

    # Timeout par défaut pour les requêtes HTTP (en secondes)
    default_timeout = 10.0


# Configuration de la réinitialisation de mot de passe
class password_reset:
    """Configuration pour le flux de réinitialisation de mot de passe"""

    token_expire_minutes = 10  # Durée de validité du token (10 minutes)

    # URL du frontend pour le lien de reset
    frontend_url = SecretStore.get("FRONTEND_URL", "http://localhost:8003")


# Configuration base de données
class database_config:
    """Configuration de la connexion à la base de données"""

    # Driver SQLAlchemy
    drivername = SecretStore.get("DB_DRIVERNAME", "postgresql+psycopg2")

    # Identifiants et connexion — OBLIGATOIRES, pas de valeur par défaut
    user = SecretStore.get("DB_USER")
    password = SecretStore.get("DB_PASSWORD")
    host = SecretStore.get("DB_HOST")
    port = int(SecretStore.get("DB_PORT", "5432"))
    name = SecretStore.get("DB_NAME")


# Configuration email (SMTP Nuxit)
class email_config:
    """Configuration pour l'envoi d'emails via SMTP (fournisseur : Nuxit)"""

    # Activer/désactiver l'envoi réel d'emails
    # En développement : False → les emails sont uniquement loggés
    # En production : True → les emails sont envoyés via SMTP
    enabled = SecretStore.get("EMAIL_ENABLED", "true").lower() == "true"

    # Serveur SMTP — OBLIGATOIRES, pas de valeur par défaut
    smtp_host = SecretStore.get("SMTP_HOST")
    smtp_port = int(SecretStore.get("SMTP_PORT", "587"))

    # Mode de sécurité : "tls" (port 465, SSL/TLS implicite) ou "starttls" (port 587)
    # Par défaut : auto-détection basée sur le port (465 → tls, 587 → starttls)
    smtp_security = "auto"

    # Identifiants SMTP — OBLIGATOIRES
    smtp_user = SecretStore.get("SMTP_USER")
    smtp_password = SecretStore.get("SMTP_PASSWORD")

    # Expéditeur — OBLIGATOIRES
    sender = SecretStore.get("SMTP_SENDER")
    sender_name = SecretStore.get("SMTP_SENDER_NAME", "AlbumsAventures")
