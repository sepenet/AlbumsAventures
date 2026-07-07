"""
Utilitaires pour le hashing de mots de passe.
Séparé de be_auth.py pour éviter les imports circulaires.
"""

from passlib.context import CryptContext

# Context pour le hashage des mots de passe
# Utilise scrypt qui est plus sécurisé que bcrypt
pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash un mot de passe avec scrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash"""
    return pwd_context.verify(plain_password, hashed_password)
