"""
Rate limiting durable, adossé à la base de données existante (SEC-06).

Remplace le cache mémoire process-local (``defaultdict``) qui était réinitialisé
à chaque redémarrage et non partagé entre workers. Réutilise l'ORM/DB déjà en
place (PostgreSQL en prod, SQLite en dev) — aucune nouvelle infrastructure, en
particulier pas de Redis managé (condition coût C-4).

Sémantique conservée à l'identique :
  • ``max_attempts`` tentatives échouées dans une fenêtre de ``window_seconds``
  • au-delà, blocage pendant ``window_seconds``
  • succès -> réinitialisation du compteur

Les clés logiques (``login:<email>``, ``forgot:<email>``, ou le token de partage)
sont hashées en SHA-256 avant stockage : aucun identifiant en clair en base.
"""

import hashlib
import logging
import time

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import RateLimitEntry
from utils.config import rate_limiting

logger = logging.getLogger(__name__)


def _hash_key(key: str) -> str:
    """Retourne un identifiant opaque (SHA-256) pour une clé logique."""
    return hashlib.sha256(key.encode()).hexdigest()


def check_rate_limit(db: Session, key: str) -> None:
    """Vérifie que la clé n'est pas actuellement bloquée.

    :param db: session de base de données
    :param key: clé logique (ex. ``login:user@example.com`` ou token de partage)
    :raises HTTPException: 429 si la clé est bloquée
    """
    key_hash = _hash_key(key)
    entry = db.get(RateLimitEntry, key_hash)
    if entry is None:
        return

    current_time = time.time()
    if entry.blocked_until and current_time < entry.blocked_until:
        remaining_seconds = int(entry.blocked_until - current_time)
        remaining_minutes = remaining_seconds // 60
        logger.warning(f"Accès bloqué par rate limiting. Clé: {key_hash[:16]}, Reste: {remaining_minutes}min")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "too_many_attempts",
                "message": f"Trop de tentatives échouées. Réessayez dans {remaining_minutes} minute(s).",
                "retry_after_seconds": remaining_seconds,
            },
        )

    # Le blocage a expiré : on nettoie l'entrée pour repartir de zéro.
    if entry.blocked_until and current_time >= entry.blocked_until:
        logger.info(f"Blocage rate limiting expiré pour clé {key_hash[:16]}")
        db.delete(entry)
        db.commit()


def record_failed_attempt(db: Session, key: str) -> None:
    """Enregistre une tentative échouée et bloque la clé si le seuil est atteint.

    :param db: session de base de données
    :param key: clé logique
    """
    key_hash = _hash_key(key)
    current_time = time.time()

    entry = db.get(RateLimitEntry, key_hash)
    if entry is None:
        entry = RateLimitEntry(
            key_hash=key_hash,
            attempts=1,
            first_attempt=current_time,
            blocked_until=0.0,
        )
        db.add(entry)
        logger.info(f"Première tentative échouée pour clé {key_hash[:16]}")
    elif (current_time - entry.first_attempt) > rate_limiting.window_seconds:
        # Fenêtre expirée : on réinitialise le compteur.
        entry.attempts = 1
        entry.first_attempt = current_time
        entry.blocked_until = 0.0
        logger.info(f"Fenêtre expirée, compteur réinitialisé pour clé {key_hash[:16]}")
    else:
        entry.attempts += 1
        logger.warning(f"Tentative échouée {entry.attempts}/{rate_limiting.max_attempts} pour clé {key_hash[:16]}")

    # Blocage si le seuil est atteint.
    if entry.attempts >= rate_limiting.max_attempts:
        entry.blocked_until = current_time + rate_limiting.window_seconds
        logger.error(
            f"Clé {key_hash[:16]} bloquée pour {rate_limiting.window_seconds // 60} minutes "
            f"après {rate_limiting.max_attempts} tentatives échouées"
        )

    db.commit()


def clear_failed_attempts(db: Session, key: str) -> None:
    """Réinitialise le compteur après un succès.

    :param db: session de base de données
    :param key: clé logique
    """
    key_hash = _hash_key(key)
    entry = db.get(RateLimitEntry, key_hash)
    if entry is not None:
        logger.info(f"Accès réussi pour clé {key_hash[:16]} (tentatives précédentes: {entry.attempts})")
        db.delete(entry)
        db.commit()


def get_attempts(db: Session, key: str) -> int:
    """Retourne le nombre de tentatives échouées enregistrées pour une clé.

    :param db: session de base de données
    :param key: clé logique
    :return: nombre de tentatives (0 si aucune entrée)
    """
    entry = db.get(RateLimitEntry, _hash_key(key))
    return entry.attempts if entry is not None else 0
