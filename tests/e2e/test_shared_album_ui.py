"""
Tests E2E pour le partage d'album — flux complet et autonome.

Scénario : l'admin se connecte, ouvre la modal de partage sur un album,
génère un lien + PIN, puis vérifie l'accès partagé dans un contexte sans auth.

Pages testées : index.html (modal partage), shared_album.html (formulaire PIN),
album_detail.html (mode partagé)
"""

import re
import pytest
from playwright.sync_api import Page, BrowserContext, expect

# ============================================================================
# Fixture : génère un lien de partage via l'UI admin
# ============================================================================


@pytest.fixture(scope="class")
def share_credentials(browser, base_url):
    """Se connecte en admin, crée un partage, renvoie (share_url, pin)."""
    context = browser.new_context()
    page = context.new_page()

    # Login admin
    page.goto(f"{base_url}/login")
    page.fill("#email", __import__("os").environ.get("E2E_ADMIN_EMAIL", "sebastien@pe-net.fr"))
    page.fill("#password", __import__("os").environ.get("E2E_ADMIN_PASSWORD", ""))
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/", timeout=5000)

    # Attendre le chargement des albums
    page.wait_for_timeout(1500)

    # Cliquer sur le bouton partage du premier album
    share_btn = page.locator('button[title="Partage temporaire"]').first
    if not share_btn.is_visible():
        context.close()
        pytest.skip("Aucun album avec bouton de partage disponible")

    share_btn.click()

    # La modal de partage s'ouvre
    expect(page.get_by_text("Partager l'album")).to_be_visible(timeout=3000)

    # Cliquer sur "Générer le lien"
    page.click('button:has-text("Générer le lien")')

    # Attendre le résultat (le PIN et le lien s'affichent)
    pin_el = page.locator("code")
    expect(pin_el).to_be_visible(timeout=5000)

    share_url_input = page.locator("input[readonly]")
    expect(share_url_input).to_be_visible(timeout=3000)

    pin = pin_el.inner_text().strip()
    share_url = share_url_input.input_value().strip()

    # Fermer la modal et le contexte admin
    page.click('button:has-text("Fermer")')
    context.close()

    return share_url, pin


# ============================================================================
# Page de saisie du PIN
# ============================================================================


@pytest.mark.e2e
class TestSharedAlbumPinUI:
    """Tests du formulaire de saisie du PIN"""

    def test_pin_page_loads(self, page: Page, share_credentials):
        """La page de saisie du PIN s'affiche sans authentification"""
        share_url, _ = share_credentials
        page.goto(share_url)

        expect(page.get_by_text("Album partagé")).to_be_visible()
        expect(page.locator('input[name="pin"]')).to_be_visible()
        expect(page.get_by_text("Accéder à l'album")).to_be_visible()

    def test_pin_page_no_token_redirects(self, page: Page, base_url: str):
        """Sans token, la page redirige (vers / puis /login si non authentifié)"""
        page.goto(f"{base_url}/album/shared")
        # Redirige vers / qui redirige vers /login si pas de session
        expect(page).not_to_have_url(re.compile(r"/album/shared"))

    def test_wrong_pin_shows_error(self, page: Page, share_credentials):
        """Un PIN incorrect affiche un message d'erreur"""
        share_url, _ = share_credentials
        page.goto(share_url)

        page.fill('input[name="pin"]', "XXXXXX")
        page.click('button[type="submit"]')

        page.wait_for_timeout(1000)
        error_box = page.locator(".bg-red-50, .bg-red-900\\/30")
        expect(error_box).to_be_visible(timeout=5000)

    def test_correct_pin_shows_album(self, page: Page, share_credentials):
        """Le bon PIN affiche l'album dans album_detail.html"""
        share_url, pin = share_credentials
        page.goto(share_url)

        page.fill('input[name="pin"]', pin)
        page.click('button[type="submit"]')

        expect(page.locator("h1")).to_be_visible(timeout=5000)
        expect(page.get_by_text("Accès temporaire par lien de partage")).to_be_visible()


# ============================================================================
# Album partagé — mode lecture seule dans album_detail.html
# ============================================================================


@pytest.mark.e2e
class TestSharedAlbumDetailUI:
    """Tests de l'album affiché en mode partagé (lecture seule)"""

    @pytest.fixture(autouse=True)
    def navigate_to_shared_album(self, page: Page, share_credentials):
        """Accède à l'album partagé via PIN avant chaque test."""
        share_url, pin = share_credentials
        page.goto(share_url)
        page.fill('input[name="pin"]', pin)
        page.click('button[type="submit"]')
        expect(page.locator("h1")).to_be_visible(timeout=5000)
        # Attendre le chargement complet des images et de PhotoSwipe
        page.wait_for_timeout(2000)

    def test_shared_badge_visible(self, page: Page):
        """Le badge 'Accès temporaire' est affiché"""
        expect(page.get_by_text("Accès temporaire par lien de partage")).to_be_visible()

    def test_no_back_to_albums_link(self, page: Page):
        """Le lien 'Retour aux albums' n'est PAS affiché"""
        expect(page.get_by_text("Retour aux albums")).not_to_be_visible()

    def test_no_edit_button(self, page: Page):
        """Le bouton 'Modifier' n'est PAS affiché"""
        expect(page.get_by_text("Modifier")).not_to_be_visible()

    def test_no_upload_button(self, page: Page):
        """Le bouton 'Ajouter des photos' n'est PAS affiché"""
        expect(page.get_by_text("Ajouter des photos")).not_to_be_visible()

    def test_no_cover_button(self, page: Page):
        """Le bouton 'Choisir couverture' n'est PAS affiché"""
        expect(page.get_by_text("Choisir couverture")).not_to_be_visible()

    def test_no_associate_button(self, page: Page):
        """Le bouton 'Associer' n'est PAS affiché"""
        expect(page.get_by_text("Associer")).not_to_be_visible()

    def test_images_are_displayed(self, page: Page):
        """Les images/vidéos s'affichent dans la grille Masonry"""
        masonry = page.locator("#masonry-grid")
        if masonry.count() == 0:
            pytest.skip("Album partagé sans images")
        expect(masonry).to_be_visible(timeout=5000)
        items = page.locator(".masonry-item")
        expect(items.first).to_be_visible(timeout=5000)

    def test_photoswipe_opens_on_image_click(self, page: Page):
        """Cliquer sur une image ouvre la lightbox PhotoSwipe"""
        masonry = page.locator("#masonry-grid")
        if masonry.count() == 0:
            pytest.skip("Album partagé sans images")

        img_link = page.locator("#masonry-grid a:not([data-pswp-type='video'])").first
        if img_link.count() == 0:
            pytest.skip("Pas d'images (seulement des vidéos)")

        img_link.click()
        page.wait_for_timeout(1000)
        # PhotoSwipe 5 crée .pswp--open quand la lightbox est active
        expect(page.locator(".pswp--open")).to_be_visible(timeout=5000)

    def test_video_has_play_overlay(self, page: Page):
        """Les vidéos affichent l'icône play en overlay"""
        video_item = page.locator('#masonry-grid a[data-pswp-type="video"]').first
        if video_item.count() == 0:
            pytest.skip("Pas de vidéos dans cet album partagé")
        expect(video_item.locator("svg")).to_be_visible()
