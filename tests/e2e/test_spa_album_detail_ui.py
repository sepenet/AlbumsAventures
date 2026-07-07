"""
Tests E2E pour la page de détail d'album React (SPA, Phase 3.3).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). La page de détail est deep-linkable via
``/app/albums/:albumId`` (le repli SPA sert index.html au rafraîchissement).
Les données proviennent de ``be_album`` (métadonnées) et de l'endpoint JSON
``/album/{id}/images`` (médias) — pas de rendu Jinja pour cette route.

La page Jinja historique ``/album/{id}`` reste servie inchangée (strangler).

Prérequis (identiques aux autres tests e2e) : serveur lancé sur
``E2E_BASE_URL`` avec la SPA buildée (``npm run build`` dans frontend/spa/) et
les credentials ``E2E_USER_PASSWORD`` renseignés.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestSpaAlbumDetailUI:
    """Tests de la page de détail d'album migrée en React."""

    def _open_first_album(self, page: Page, base_url: str) -> bool:
        """Ouvre le premier album de la grille SPA. Retourne False si vide."""
        page.goto(f"{base_url}/app")
        page.wait_for_timeout(1500)
        card = page.locator('.grid a[href*="/albums/"]').first
        if not card.is_visible():
            return False
        card.click()
        page.wait_for_url("**/app/albums/**", timeout=5000)
        return True

    def test_grid_card_navigates_to_spa_detail(self, authenticated_page: Page, base_url: str):
        """Cliquer une carte ouvre la page de détail SPA (React Router)."""
        page = authenticated_page
        if not self._open_first_album(page, base_url):
            pytest.skip("Aucun album disponible")

        # Le lien de retour React est présent sur la page de détail.
        expect(page.get_by_text("Retour aux albums")).to_be_visible(timeout=5000)

    def test_detail_deeplink_refresh_serves_shell(self, authenticated_page: Page, base_url: str):
        """Un rafraîchissement direct sur /app/albums/:id renvoie le shell SPA."""
        page = authenticated_page
        if not self._open_first_album(page, base_url):
            pytest.skip("Aucun album disponible")

        # Deep-link : recharger l'URL courante doit re-servir la page de détail
        # (repli FastAPI index.html + résolution React Router), pas un 404.
        current_url = page.url
        page.goto(current_url)
        expect(page.get_by_text("Retour aux albums")).to_be_visible(timeout=5000)

    def test_detail_shows_photo_count(self, authenticated_page: Page, base_url: str):
        """L'en-tête affiche le compteur de photos (parité UI Jinja)."""
        page = authenticated_page
        if not self._open_first_album(page, base_url):
            pytest.skip("Aucun album disponible")

        expect(page.get_by_text("photo(s)")).to_be_visible(timeout=5000)

    def test_jinja_detail_still_served(self, authenticated_page: Page, base_url: str):
        """La page de détail Jinja historique reste servie (strangler)."""
        page = authenticated_page
        page.goto(f"{base_url}/app")
        page.wait_for_timeout(1500)
        card = page.locator('.grid a[href*="/albums/"]').first
        if not card.is_visible():
            pytest.skip("Aucun album disponible")

        href = card.get_attribute("href")
        assert href is not None
        album_id = href.rstrip("/").split("/")[-1]

        # La route Jinja /album/{id} (non migrée) répond toujours en HTML.
        response = page.goto(f"{base_url}/album/{album_id}")
        assert response is not None and response.status == 200
