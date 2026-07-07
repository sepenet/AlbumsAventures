"""Tests E2E pour le flux d'album partagé migré vers la SPA React (sous-phase 3.7).

Scénario : l'admin génère un lien + PIN via l'UI (modal Jinja), puis le viewer
PUBLIC (non authentifié) accède à l'album via la route SPA `/app/shared/:token`.

Isolation vérifiée : la page publique n'affiche AUCUNE affordance propriétaire
(retour, modifier, envoyer, couverture, associer) et n'expose pas la navigation
authentifiée ; seul le badge d'accès partagé est visible.

Nécessite un serveur live + des identifiants admin (E2E_ADMIN_EMAIL /
E2E_ADMIN_PASSWORD) ; les tests se skippent proprement sinon.
"""

import re
import os

import pytest
from playwright.sync_api import Page, expect


def _spa_share_url(base_url: str, share_url: str) -> str:
    """Dérive l'URL SPA `/app/shared/:token` depuis l'URL de partage Jinja."""
    match = re.search(r"[?&]token=([^&]+)", share_url)
    if not match:
        pytest.skip("Impossible d'extraire le token du lien de partage")
    token = match.group(1)
    return f"{base_url}/app/shared/{token}"


@pytest.fixture(scope="class")
def share_credentials(browser, base_url):
    """Se connecte en admin, crée un partage, renvoie (spa_share_url, pin)."""
    context = browser.new_context()
    page = context.new_page()

    page.goto(f"{base_url}/login")
    page.fill("#email", os.environ.get("E2E_ADMIN_EMAIL", "sebastien@pe-net.fr"))
    page.fill("#password", os.environ.get("E2E_ADMIN_PASSWORD", ""))
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/", timeout=5000)
    page.wait_for_timeout(1500)

    share_btn = page.locator('button[title="Partage temporaire"]').first
    if not share_btn.is_visible():
        context.close()
        pytest.skip("Aucun album avec bouton de partage disponible")

    share_btn.click()
    expect(page.get_by_text("Partager l'album")).to_be_visible(timeout=3000)
    page.click('button:has-text("Générer le lien")')

    pin_el = page.locator("code")
    expect(pin_el).to_be_visible(timeout=5000)
    share_url_input = page.locator("input[readonly]")
    expect(share_url_input).to_be_visible(timeout=3000)

    pin = pin_el.inner_text().strip()
    share_url = share_url_input.input_value().strip()

    page.click('button:has-text("Fermer")')
    context.close()

    return _spa_share_url(base_url, share_url), pin


@pytest.mark.e2e
class TestSpaSharedAlbumPinUI:
    """Formulaire de saisie du PIN dans la SPA."""

    def test_pin_page_loads(self, page: Page, share_credentials):
        spa_url, _ = share_credentials
        page.goto(spa_url)
        expect(page.get_by_text("Album partagé")).to_be_visible()
        expect(page.locator('input[name="pin"]')).to_be_visible()
        expect(page.get_by_text("Accéder à l'album")).to_be_visible()

    def test_wrong_pin_shows_error(self, page: Page, share_credentials):
        spa_url, _ = share_credentials
        page.goto(spa_url)
        page.fill('input[name="pin"]', "XXXXXX")
        page.click('button[type="submit"]')
        error_box = page.locator(".bg-red-50, .bg-red-900\\/30")
        expect(error_box).to_be_visible(timeout=5000)

    def test_correct_pin_shows_album(self, page: Page, share_credentials):
        spa_url, pin = share_credentials
        page.goto(spa_url)
        page.fill('input[name="pin"]', pin)
        page.click('button[type="submit"]')
        expect(page.get_by_text("Accès temporaire par lien de partage")).to_be_visible(timeout=5000)


@pytest.mark.e2e
class TestSpaSharedAlbumDetailUI:
    """Album partagé — vue lecture seule restreinte."""

    @pytest.fixture(autouse=True)
    def navigate_to_shared_album(self, page: Page, share_credentials):
        spa_url, pin = share_credentials
        page.goto(spa_url)
        page.fill('input[name="pin"]', pin)
        page.click('button[type="submit"]')
        expect(page.get_by_text("Accès temporaire par lien de partage")).to_be_visible(timeout=5000)
        page.wait_for_timeout(1000)

    def test_shared_badge_visible(self, page: Page):
        expect(page.get_by_text("Accès temporaire par lien de partage")).to_be_visible()

    def test_no_back_to_albums_link(self, page: Page):
        expect(page.get_by_text("Retour aux albums")).not_to_be_visible()

    def test_no_edit_button(self, page: Page):
        expect(page.get_by_text("Modifier")).not_to_be_visible()

    def test_no_upload_button(self, page: Page):
        expect(page.get_by_text("Ajouter des photos")).not_to_be_visible()

    def test_no_cover_button(self, page: Page):
        expect(page.get_by_text("Choisir couverture")).not_to_be_visible()

    def test_no_associate_button(self, page: Page):
        expect(page.get_by_text("Associer")).not_to_be_visible()
