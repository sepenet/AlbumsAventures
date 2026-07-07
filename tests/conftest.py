"""
Configuration pytest et fixtures partagées pour les tests fonctionnels.
Utilise une base SQLite en mémoire pour l'isolation des tests.
"""

import os
import sys
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ajouter le répertoire racine au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Shim Windows pour fcntl (importé indirectement par tuspyserver via be_resizer)
from utils.win_fcntl_shim import install_if_windows as _install_fcntl_shim
from utils.win_fcntl_shim import patch_tuspyserver_for_windows as _patch_tus_windows

_install_fcntl_shim()

# Initialiser le SecretStore AVANT tout import de config
from utils.secret_store import SecretStore

SecretStore.init()

from backend.db.db_connect import get_db
from backend.db.models import Base
from utils.password import get_password_hash

# Une fois tuspyserver importé indirectement (via be_resizer dans l'app),
# patcher os.rename -> os.replace sur Windows.
_patch_tus_windows()

# ============================================================================
# Configuration de la base de données de test (SQLite en mémoire)
# ============================================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override de la dépendance get_db pour utiliser la DB de test"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Fixtures principales
# ============================================================================


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """
    Crée une session de base de données isolée pour chaque test.
    Les tables sont créées avant et supprimées après chaque test.
    """
    # Créer les tables
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Nettoyer après le test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """
    Client de test FastAPI avec la DB de test injectée.
    """
    # Import ici pour éviter les problèmes de circular import
    from AlbumsAventures_BE_test import app

    # Override la dépendance
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Nettoyer les overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session) -> dict:
    """
    Crée un utilisateur de test standard (non superuser).
    """
    from backend.db import models

    user = models.User(
        firstname="Test",
        lastname="User",
        email="test@example.com",
        password=get_password_hash("TestPassword123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "password": "TestPassword123",  # Mot de passe en clair pour les tests
        "firstname": user.firstname,
        "lastname": user.lastname,
        "is_superuser": user.is_superuser,
    }


@pytest.fixture(scope="function")
def test_superuser(db_session) -> dict:
    """
    Crée un utilisateur superuser de test.
    """
    from backend.db import models

    user = models.User(
        firstname="Admin",
        lastname="User",
        email="admin@example.com",
        password=get_password_hash("AdminPassword123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "password": "AdminPassword123",
        "firstname": user.firstname,
        "lastname": user.lastname,
        "is_superuser": user.is_superuser,
    }


@pytest.fixture(scope="function")
def test_category(db_session) -> dict:
    """
    Crée une catégorie de test.
    """
    from backend.db import models

    category = models.Category(category="Vacances")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    return {"id": category.id, "category": category.category}


@pytest.fixture(scope="function")
def test_album(db_session, test_category) -> dict:
    """
    Crée un album de test.
    """
    from datetime import date

    from backend.db import models

    album = models.Album(
        title="Album Test",
        description="Description de test",
        category_id=test_category["id"],
        date=date(2024, 6, 15),
        participants="Jean|Marie",
        location="Paris",
        tags="test,vacances",
        image_cover=None,
    )
    db_session.add(album)
    db_session.commit()
    db_session.refresh(album)

    return {"id": album.id, "title": album.title, "category_id": album.category_id, "date": str(album.date)}


@pytest.fixture(scope="function")
def test_group(db_session) -> dict:
    """
    Crée un groupe de test.
    """
    from backend.db import models

    group = models.Group(name="Famille", description="Groupe famille")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    return {"id": group.id, "name": group.name}


@pytest.fixture(scope="function")
def user_with_album_access(db_session, test_user, test_album) -> dict:
    """
    Crée un utilisateur avec accès direct à un album.
    """
    from backend.db import models

    # Créer le lien utilisateur-album
    user_album = models.UserAlbum(user_id=test_user["id"], album_id=test_album["id"])
    db_session.add(user_album)
    db_session.commit()

    return {**test_user, "album_id": test_album["id"]}


@pytest.fixture(scope="function")
def auth_headers(client, test_user) -> dict:
    """
    Retourne les headers d'authentification pour un utilisateur standard.
    """
    response = client.post("/be_auth/login", data={"username": test_user["email"], "password": test_user["password"]})
    assert response.status_code == 200

    # Récupérer le cookie d'authentification
    cookies = response.cookies
    return {"cookies": dict(cookies)}


@pytest.fixture(scope="function")
def superuser_auth_headers(client, test_superuser) -> dict:
    """
    Retourne les headers d'authentification pour un superuser.
    """
    response = client.post(
        "/be_auth/login", data={"username": test_superuser["email"], "password": test_superuser["password"]}
    )
    assert response.status_code == 200

    cookies = response.cookies
    return {"cookies": dict(cookies)}
