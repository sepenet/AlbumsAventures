"""
Tests E2E pour la page d'upload React (SPA, Phase 3.4 — Uppy v5 ESM).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). La page d'upload est routée sous
``/app/albums/:albumId/upload`` (deep-linkable via le repli SPA). Le tableau de
bord Uppy v5 est désormais *bundlé par Vite* (ESM, même origine) au lieu du
bundle UMD transloadit — mais la page Jinja historique ``/album/{id}/upload``
reste servie inchangée (strangler).

Les comportements de fiabilité Phase 2 (golden-retriever, compression #380,
chunk adaptatif avec plancher 256 KB via /upload_config, suivi durable du
post-traitement /processing_status, transport TUS vers /be_resizer/tus/) sont
portés sur Uppy v5 ; leur logique pure est couverte par les tests unitaires
Vitest (frontend/spa/src/lib/upload.test.ts). Ce spec vérifie le rendu et le
routage de la page.

Prérequis (identiques aux autres tests e2e) : serveur lancé sur
``E2E_BASE_URL`` avec la SPA buildée (``npm run build`` dans frontend/spa/) et
les credentials ``E2E_USER_PASSWORD`` renseignés.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestSpaUploadUI:
    """Tests de la page d'upload migrée en React + Uppy v5."""

    def _first_album_id(self, page: Page, base_url: str) -> str | None:
        """Retourne l'id du premier album de la grille SPA, ou None si vide."""
        page.goto(f"{base_url}/app")
        page.wait_for_timeout(1500)
        card = page.locator('.grid a[href*="/albums/"]').first
        if not card.is_visible():
            return None
        href = card.get_attribute("href")
        if not href:
            return None
        return href.rstrip("/").split("/")[-1]

    def test_upload_page_renders_dashboard(self, authenticated_page: Page, base_url: str):
        """La page d'upload SPA affiche l'en-tête et le tableau de bord Uppy."""
        page = authenticated_page
        album_id = self._first_album_id(page, base_url)
        if album_id is None:
            pytest.skip("Aucun album disponible")

        page.goto(f"{base_url}/app/albums/{album_id}/upload")
        expect(page.get_by_text("Ajouter des photos")).to_be_visible(timeout=5000)
        # Le tableau de bord Uppy (v5, bundlé) est monté dans le DOM.
        expect(page.locator(".uppy-Dashboard").first).to_be_visible(timeout=5000)

    def test_upload_deeplink_refresh_serves_shell(self, authenticated_page: Page, base_url: str):
        """Un rafraîchissement direct sur l'URL d'upload renvoie le shell SPA."""
        page = authenticated_page
        album_id = self._first_album_id(page, base_url)
        if album_id is None:
            pytest.skip("Aucun album disponible")

        url = f"{base_url}/app/albums/{album_id}/upload"
        page.goto(url)
        # Deep-link : recharger l'URL doit re-servir la page (repli FastAPI
        # index.html + résolution React Router), pas un 404.
        page.goto(url)
        expect(page.get_by_text("Retour à l'album")).to_be_visible(timeout=5000)

    def test_upload_back_link_returns_to_spa_detail(self, authenticated_page: Page, base_url: str):
        """Le lien de retour renvoie à la page de détail SPA (in-app router)."""
        page = authenticated_page
        album_id = self._first_album_id(page, base_url)
        if album_id is None:
            pytest.skip("Aucun album disponible")

        page.goto(f"{base_url}/app/albums/{album_id}/upload")
        page.get_by_text("Retour à l'album").first.click()
        page.wait_for_url(f"**/app/albums/{album_id}", timeout=5000)
        expect(page.get_by_text("Retour aux albums")).to_be_visible(timeout=5000)

    def test_jinja_upload_still_served(self, authenticated_page: Page, base_url: str):
        """La page d'upload Jinja historique reste servie (strangler)."""
        page = authenticated_page
        album_id = self._first_album_id(page, base_url)
        if album_id is None:
            pytest.skip("Aucun album disponible")

        # La route Jinja /album/{id}/upload (non migrée) répond toujours en HTML.
        response = page.goto(f"{base_url}/album/{album_id}/upload")
        assert response is not None and response.status == 200
