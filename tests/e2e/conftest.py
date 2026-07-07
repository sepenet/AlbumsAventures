"""
Fixtures Playwright pour les tests E2E.

Ces tests nécessitent que le serveur soit lancé :
    uvicorn AlbumsAventures-BE:app --reload --port 8003

Lancer uniquement les tests E2E :
    pytest tests/e2e -m e2e

Lancer sans les tests E2E :
    pytest -m "not e2e"

Variables d'environnement pour les credentials :
    E2E_BASE_URL         (défaut : http://localhost:8003)
    E2E_ADMIN_EMAIL      (défaut : sebastien@pe-net.fr)
    E2E_ADMIN_PASSWORD   (requis pour les tests nécessitant un admin connecté)
    E2E_USER_EMAIL       (défaut : sebastien@pe-net.fr)
    E2E_USER_PASSWORD    (requis pour les tests nécessitant un utilisateur connecté)
"""
import os
import pytest
from playwright.sync_api import Page, expect

# Credentials lus depuis les variables d'environnement
E2E_ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "sebastien@pe-net.fr")
E2E_ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "")
E2E_USER_EMAIL = os.environ.get("E2E_USER_EMAIL", "sebastien@pe-net.fr")
E2E_USER_PASSWORD = os.environ.get("E2E_USER_PASSWORD", "")

# URL de base du serveur (peut être overridée via variable d'environnement)
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8003")


@pytest.fixture(scope="session")
def base_url():
    """URL de base pour tous les tests E2E."""
    return BASE_URL


def _login(page: Page, base_url: str, email: str, password: str) -> Page:
    """Helper de login partagé entre fixtures."""
    page.goto(f"{base_url}/login")
    page.fill('#email', email)
    page.fill('#password', password)
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/", timeout=5000)
    return page


@pytest.fixture(scope="function")
def authenticated_page(page: Page, base_url: str):
    """Page avec un utilisateur connecté."""
    return _login(page, base_url, E2E_USER_EMAIL, E2E_USER_PASSWORD)


@pytest.fixture(scope="function")
def admin_page(page: Page, base_url: str):
    """Page avec un utilisateur admin/superuser connecté."""
    return _login(page, base_url, E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD)
