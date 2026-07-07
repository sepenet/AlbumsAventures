"""
Tests E2E pour la grille d'albums React (SPA, Phase 3.2).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). Ces tests couvrent la première page migrée (grille
d'albums) tout en laissant les pages Jinja2 historiques (servies sur ``/``)
inchangées — migration strangler incrémentale.

Prérequis (identiques aux autres tests e2e) : serveur lancé sur
``E2E_BASE_URL`` avec la SPA buildée (``npm run build`` dans frontend/spa/) et
les credentials ``E2E_USER_PASSWORD`` renseignés.
"""

import re

import pytest
from playwright.sync_api import Page, expect

# ============================================================================
# Garde d'authentification (cookie-only)
# ============================================================================


@pytest.mark.e2e
class TestSpaAuthGuard:
    """La SPA redirige vers /login quand la session est absente."""

    def test_unauthenticated_spa_redirects_to_login(self, page: Page, base_url: str):
        """Accéder à /app sans session redirige vers la page de login Jinja."""
        # Aucune session : le garde RequireAuth (401 sur /be_auth/me) redirige.
        page.goto(f"{base_url}/app")
        page.wait_for_url("**/login", timeout=5000)
        expect(page).to_have_url(f"{base_url}/login")


# ============================================================================
# Grille d'albums React
# ============================================================================


@pytest.mark.e2e
class TestSpaAlbumGridUI:
    """Tests de la grille d'albums migrée en React."""

    def test_spa_grid_loads(self, authenticated_page: Page, base_url: str):
        """La grille React affiche la recherche et le filtre catégories."""
        page = authenticated_page
        page.goto(f"{base_url}/app")

        # La barre de recherche React est présente (parité avec la page Jinja).
        expect(page.locator('input[placeholder*="Rechercher"]')).to_be_visible(timeout=5000)
        # Le bouton "Toutes" (filtre catégories) est visible.
        expect(page.get_by_text("Toutes")).to_be_visible()

    def test_spa_search_shows_empty_state(self, authenticated_page: Page, base_url: str):
        """Une recherche improbable affiche l'état vide."""
        page = authenticated_page
        page.goto(f"{base_url}/app")
        page.wait_for_timeout(1500)

        page.fill('input[placeholder*="Rechercher"]', "xyznonexistent999")
        page.wait_for_timeout(500)

        expect(page.get_by_text("Aucun album trouvé")).to_be_visible(timeout=3000)

    def test_spa_deeplink_refresh_serves_shell(self, authenticated_page: Page, base_url: str):
        """Un rafraîchissement sur une route client SPA renvoie le shell (fallback)."""
        page = authenticated_page
        # Route client arbitraire : le repli FastAPI renvoie index.html, React
        # Router résout la vue et retombe sur la grille.
        page.goto(f"{base_url}/app/unknown-client-route")
        expect(page.locator('input[placeholder*="Rechercher"]')).to_be_visible(timeout=5000)

    def test_spa_album_card_links_to_detail(self, authenticated_page: Page, base_url: str):
        """Les cartes d'album pointent vers la page de détail (Jinja, non migrée)."""
        page = authenticated_page
        page.goto(f"{base_url}/app")
        page.wait_for_timeout(1500)

        album_link = page.locator('.grid a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible")

        # Le détail n'est pas encore migré (Phase 3.3) : lien vers la page Jinja.
        href = album_link.get_attribute("href")
        assert href is not None and re.search(r"/album/\d+", href)
