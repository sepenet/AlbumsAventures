"""
SecretStore — Accès unifié et sécurisé aux secrets.

Stratégie :
  • Si KEY_VAULT_URL est défini (prod) → lecture directe depuis Azure Key Vault
  • Sinon (dev) → lecture depuis fichier .env via python-dotenv

Les secrets ne transitent JAMAIS par os.environ.
Ils sont stockés dans un cache mémoire interne avec TTL configurable.
L'application sort en erreur si un secret obligatoire est introuvable.

Usage dans config.py :
    from utils.secret_store import SecretStore
    secret_key = SecretStore.get("SECRET_KEY")          # obligatoire — lève une erreur si absent
    algorithm  = SecretStore.get("JWT_ALGORITHM", "HS256")  # avec valeur par défaut

Initialisation (dans AlbumsAventures-BE.py, AVANT tout import de config) :
    from utils.secret_store import SecretStore
    SecretStore.init()
"""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Sentinel pour distinguer "pas de défaut" de "None comme défaut"
_MISSING = object()

# Mapping : nom de variable d'environnement → nom du secret dans Key Vault
# Les noms KV utilisent des tirets (convention Azure), les env vars des underscores
_ENV_TO_KV = {
    "SECRET_KEY": "SECRET-KEY",
    "JWT_ALGORITHM": "JWT-ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "ACCESS-TOKEN-EXPIRE-MINUTES",
    "COOKIE_NAME": "COOKIE-NAME",
    "DB_DRIVERNAME": "DB-DRIVERNAME",
    "DB_USER": "DB-USER",
    "DB_PASSWORD": "DB-PASSWORD",
    "DB_HOST": "DB-HOST",
    "DB_PORT": "DB-PORT",
    "DB_NAME": "DB-NAME",
    "EMAIL_ENABLED": "EMAIL-ENABLED",
    "SMTP_HOST": "SMTP-HOST",
    "SMTP_PORT": "SMTP-PORT",
    "SMTP_USER": "SMTP-USER",
    "SMTP_PASSWORD": "SMTP-PASSWORD",
    "SMTP_SENDER": "SMTP-SENDER",
    "SMTP_SENDER_NAME": "SMTP-SENDER-NAME",
    "BACKEND_BASE_URL": "BACKEND-BASE-URL",
    "FRONTEND_URL": "FRONTEND-URL",
}


class SecretStoreError(Exception):
    """Erreur levée quand un secret obligatoire est introuvable."""

    pass


class SecretStore:
    """Accès unifié aux secrets — Key Vault en prod, .env en dev.

    Les secrets sont cachés en mémoire avec TTL (jamais dans os.environ).
    Appeler SecretStore.init() au démarrage de l'application.
    """

    # --- État interne ---
    _initialized: bool = False
    _mode: str = "none"  # "keyvault" ou "dotenv"
    _cache: dict = {}  # {key: (value, timestamp)}
    _ttl: int = 300  # Cache TTL en secondes (5 min) — prod uniquement
    _kv_client = None  # SecretClient Azure (lazy)
    _dotenv_values: dict = {}  # Valeurs chargées depuis .env

    @classmethod
    def init(cls, ttl: int = 300):
        """Initialise le SecretStore. À appeler UNE FOIS au démarrage.

        Args:
            ttl: Durée de vie du cache en secondes (prod KV uniquement). Défaut : 300s.
        """
        cls._ttl = ttl
        cls._cache = {}
        vault_url = os.getenv("KEY_VAULT_URL")

        if vault_url:
            cls._init_keyvault(vault_url)
        else:
            cls._init_dotenv()

        cls._initialized = True
        logger.info(f"SecretStore initialisé en mode '{cls._mode}'")

    @classmethod
    def _init_keyvault(cls, vault_url: str):
        """Initialise le client Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError:
            logger.critical(
                "KEY_VAULT_URL est défini mais les packages Azure ne sont pas installés. "
                "Installez : pip install azure-identity azure-keyvault-secrets"
            )
            sys.exit(1)

        # Tentative Managed Identity en premier (VM Azure), fallback DefaultAzureCredential
        try:
            credential = ManagedIdentityCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            # Test rapide d'authentification
            client.list_properties_of_secrets(max_page_size=1)
            logger.info("Authentification Key Vault via Managed Identity réussie")
        except Exception as e:
            logger.info(f"Managed Identity indisponible ({e}), fallback DefaultAzureCredential")
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)

        cls._kv_client = client
        cls._mode = "keyvault"

        # Pré-charger tous les secrets au démarrage pour détecter les erreurs tôt
        cls._preload_keyvault_secrets()

    @classmethod
    def _preload_keyvault_secrets(cls):
        """Charge tous les secrets KV mappés dans le cache au démarrage."""
        errors = []
        for env_name, kv_name in _ENV_TO_KV.items():
            try:
                secret = cls._kv_client.get_secret(kv_name)
                if secret.value:
                    cls._cache[env_name] = (secret.value, time.time())
                else:
                    errors.append(kv_name)
            except Exception as e:
                errors.append(f"{kv_name} ({e})")

        loaded = len(_ENV_TO_KV) - len(errors)
        logger.info(f"Key Vault : {loaded}/{len(_ENV_TO_KV)} secrets pré-chargés")

        if errors:
            logger.warning(f"Secrets manquants ou vides dans le Key Vault : {', '.join(errors)}")

    @classmethod
    def _init_dotenv(cls):
        """Charge les variables depuis le fichier .env (développement local)."""
        cls._mode = "dotenv"

        try:
            from dotenv import dotenv_values
        except ImportError:
            logger.critical("python-dotenv n'est pas installé. " "Installez : pip install python-dotenv")
            sys.exit(1)

        # Chercher le fichier .env à la racine du projet
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        env_path = os.path.normpath(env_path)

        if not os.path.exists(env_path):
            logger.critical(
                f"Fichier .env introuvable : {env_path}\n"
                "Copiez .env.example vers .env et renseignez vos valeurs.\n"
                "L'application ne peut pas démarrer sans configuration."
            )
            sys.exit(1)

        # Charger les valeurs SANS les injecter dans os.environ
        cls._dotenv_values = dotenv_values(env_path)
        loaded = len([v for v in cls._dotenv_values.values() if v])
        logger.info(f"Fichier .env chargé : {loaded} variables depuis {env_path}")

    @classmethod
    def get(cls, key: str, default=_MISSING) -> str:
        """Récupère un secret par son nom de variable d'environnement.

        Args:
            key: Nom de la variable (ex: "SECRET_KEY", "DB_PASSWORD").
            default: Valeur par défaut. Si omis et que le secret est introuvable,
                     lève SecretStoreError et arrête l'application.

        Returns:
            La valeur du secret (str).

        Raises:
            SecretStoreError: Si le secret est obligatoire et introuvable.
        """
        if not cls._initialized:
            raise SecretStoreError(
                "SecretStore.init() n'a pas été appelé. "
                "Appelez-le dans AlbumsAventures-BE.py AVANT d'importer config."
            )

        if cls._mode == "keyvault":
            return cls._get_from_keyvault(key, default)
        else:
            return cls._get_from_dotenv(key, default)

    @classmethod
    def _get_from_keyvault(cls, key: str, default) -> str:
        """Lecture depuis Key Vault avec cache TTL."""
        # Vérifier le cache
        if key in cls._cache:
            value, timestamp = cls._cache[key]
            if time.time() - timestamp < cls._ttl:
                return value
            # TTL expiré — recharger

        # Nom du secret dans le KV
        kv_name = _ENV_TO_KV.get(key)
        if kv_name is None:
            # Clé non mappée dans le KV → utiliser le défaut ou erreur
            return cls._resolve_default(key, default)

        try:
            secret = cls._kv_client.get_secret(kv_name)
            if secret.value:
                cls._cache[key] = (secret.value, time.time())
                return secret.value
        except Exception as e:
            logger.error(f"Erreur lecture Key Vault pour '{kv_name}': {e}")

        # Le secret n'a pas pu être lu — utiliser le cache expiré si disponible
        if key in cls._cache:
            logger.warning(f"Utilisation du cache expiré pour '{key}' (KV inaccessible)")
            return cls._cache[key][0]

        return cls._resolve_default(key, default)

    @classmethod
    def _get_from_dotenv(cls, key: str, default) -> str:
        """Lecture depuis les valeurs chargées du .env."""
        value = cls._dotenv_values.get(key)
        if value is not None and value != "":
            return value
        return cls._resolve_default(key, default)

    @classmethod
    def _resolve_default(cls, key: str, default) -> str:
        """Retourne la valeur par défaut ou lève une erreur fatale."""
        if default is not _MISSING:
            return default

        # Pas de défaut fourni → secret OBLIGATOIRE manquant → erreur fatale
        msg = f"SECRET OBLIGATOIRE MANQUANT : '{key}'\n" f"  Mode : {cls._mode}\n"
        if cls._mode == "keyvault":
            kv_name = _ENV_TO_KV.get(key, "?")
            msg += f"  Secret KV attendu : '{kv_name}'\n"
            msg += "  Vérifiez que le secret existe dans le Key Vault et que la Managed Identity a les droits."
        else:
            msg += f"  Vérifiez que '{key}' est défini dans le fichier .env"

        logger.critical(msg)
        raise SecretStoreError(msg)

    @classmethod
    def get_mode(cls) -> str:
        """Retourne le mode actif : 'keyvault', 'dotenv' ou 'none'."""
        return cls._mode

    @classmethod
    def is_production(cls) -> bool:
        """Retourne True si le SecretStore utilise Key Vault (prod)."""
        return cls._mode == "keyvault"
