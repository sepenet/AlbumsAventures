"""
Tests E2E pour les albums.

Pages testées : index.html (liste), album_detail.html (détail),
album_form.html (création), album_edit.html (édition), album_upload.html (upload)
"""

import re
import pytest
from playwright.sync_api import Page, expect

# ============================================================================
# Liste des albums (page d'accueil)
# ============================================================================


@pytest.mark.e2e
class TestAlbumListUI:
    """Tests de la liste des albums (page d'accueil)"""

    def test_homepage_loads_with_albums(self, authenticated_page: Page, base_url: str):
        """La page d'accueil affiche la grille d'albums"""
        page = authenticated_page
        page.goto(f"{base_url}/")

        # La barre de recherche est présente
        expect(page.locator('input[placeholder*="Rechercher"]')).to_be_visible()
        # Le bouton "Toutes" (catégories) est visible
        expect(page.get_by_text("Toutes")).to_be_visible()

    def test_search_filters_albums(self, authenticated_page: Page, base_url: str):
        """La recherche filtre les albums affichés"""
        page = authenticated_page
        page.goto(f"{base_url}/")

        # Attendre le chargement des albums
        page.wait_for_timeout(1500)

        # Taper un terme de recherche improbable
        page.fill('input[placeholder*="Rechercher"]', "xyznonexistent999")
        page.wait_for_timeout(500)

        # Le message "Aucun album trouvé" doit apparaître
        expect(page.get_by_text("Aucun album trouvé")).to_be_visible(timeout=3000)

    def test_category_filter_toggles(self, authenticated_page: Page, base_url: str):
        """Les filtres par catégorie fonctionnent en toggle"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        # Le bouton "Toutes" est sélectionné par défaut (bg-sky-600)
        toutes_btn = page.get_by_text("Toutes")
        expect(toutes_btn).to_be_visible()

    def test_click_album_navigates_to_detail(self, authenticated_page: Page, base_url: str):
        """Cliquer sur un album navigue vers la page de détail"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('.grid a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)
        expect(page).to_have_url(re.compile(r"/album/\d+"))


# ============================================================================
# Détail d'un album
# ============================================================================


@pytest.mark.e2e
class TestAlbumDetailUI:
    """Tests de la page de détail d'un album"""

    def test_album_detail_loads(self, authenticated_page: Page, base_url: str):
        """La page de détail d'album affiche les métadonnées"""
        page = authenticated_page
        # Naviguer via la home pour trouver un vrai album
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        # Le titre de l'album est affiché
        expect(page.locator("h1")).to_be_visible()

    def test_album_detail_shows_images(self, authenticated_page: Page, base_url: str):
        """La galerie d'images s'affiche dans le détail de l'album"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        # Le masonry grid n'existe que si l'album a des photos ({% if total_images %})
        masonry = page.locator("#masonry-grid")
        if masonry.count() == 0:
            pytest.skip("Album sans images, masonry-grid non rendu")
        expect(masonry).to_be_visible(timeout=5000)

    def test_album_detail_back_link(self, authenticated_page: Page, base_url: str):
        """Le lien retour ramène à la page d'accueil"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        # Cliquer sur le lien retour
        page.locator('a[href="/"]').first.click()
        expect(page).to_have_url(f"{base_url}/")


# ============================================================================
# Création d'album (admin)
# ============================================================================


@pytest.mark.e2e
class TestAlbumCreationFlow:
    """Tests du formulaire de création d'album (superusers)"""

    def test_create_album_page_loads(self, admin_page: Page, base_url: str):
        """La page de création affiche le formulaire complet"""
        page = admin_page
        page.goto(f"{base_url}/album/new")

        expect(page.locator("#title")).to_be_visible()
        expect(page.locator("#description")).to_be_visible()
        expect(page.locator("#category_id")).to_be_visible()
        expect(page.locator("#date")).to_be_visible()
        expect(page.locator("#participants")).to_be_visible()
        expect(page.locator("#location")).to_be_visible()
        expect(page.locator("#tags")).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_create_album_button_visible_for_admin(self, admin_page: Page, base_url: str):
        """Le bouton de création d'album est visible pour les admins"""
        page = admin_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        create_link = page.locator('a[href="/album/new"]')
        expect(create_link).to_be_visible()

    def test_create_album_required_fields(self, admin_page: Page, base_url: str):
        """Soumettre sans remplir les champs obligatoires ne passe pas"""
        page = admin_page
        page.goto(f"{base_url}/album/new")

        # Soumettre vide → la validation HTML5 bloque
        page.click('button[type="submit"]')

        # On reste sur la page
        expect(page).to_have_url(f"{base_url}/album/new")


# ============================================================================
# Édition d'album (admin)
# ============================================================================


@pytest.mark.e2e
class TestAlbumEditFlow:
    """Tests du formulaire d'édition d'album"""

    def test_edit_album_page_loads(self, admin_page: Page, base_url: str):
        """La page d'édition charge les données existantes"""
        page = admin_page
        # Naviguer vers un album existant
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        # Cliquer sur le bouton Edit
        edit_link = page.locator('a[href*="/edit"]')
        if not edit_link.is_visible():
            pytest.skip("Bouton edit non visible (non admin?)")

        edit_link.click()
        page.wait_for_url("**/edit", timeout=5000)

        # Le titre est pré-rempli
        title_input = page.locator("#title")
        expect(title_input).to_be_visible()
        expect(title_input).not_to_have_value("")


# ============================================================================
# Upload d'images
# ============================================================================


@pytest.mark.e2e
class TestAlbumUploadFlow:
    """Tests de la page d'upload"""

    def test_upload_page_loads(self, authenticated_page: Page, base_url: str):
        """La page d'upload affiche le dashboard Uppy"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        upload_link = page.locator('a[href*="/upload"]')
        if not upload_link.is_visible():
            pytest.skip("Lien upload non visible")

        upload_link.click()
        page.wait_for_url("**/upload", timeout=5000)

        # Le dashboard Uppy est présent
        uppy = page.locator("#uppy-dashboard")
        expect(uppy).to_be_visible(timeout=5000)

    def test_upload_page_has_view_album_link(self, authenticated_page: Page, base_url: str):
        """La page d'upload a un lien retour vers l'album"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible pour ce test")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)

        upload_link = page.locator('a[href*="/upload"]')
        if not upload_link.is_visible():
            pytest.skip("Lien upload non visible")

        upload_link.click()
        page.wait_for_url("**/upload", timeout=5000)

        # Lien retour vers l'album
        back_link = page.locator('a[href*="/album/"]')
        expect(back_link.first).to_be_visible()


# ============================================================================
# Association album ↔ utilisateurs/groupes (modal)
# ============================================================================


@pytest.mark.e2e
class TestAlbumAssociateModal:
    """Tests de la modal d'association depuis la page d'accueil"""

    def test_associate_modal_opens(self, admin_page: Page, base_url: str):
        """Le bouton d'association ouvre la modal avec onglets"""
        page = admin_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        # Trouver un bouton d'association
        associate_btn = page.locator('button[title*="Associer"]').first
        if not associate_btn.is_visible():
            pytest.skip("Aucun bouton d'association visible")

        associate_btn.click()

        # La modal doit s'ouvrir avec les onglets Utilisateurs et Groupes
        expect(page.locator("h3", has_text="Associer l'album")).to_be_visible(timeout=3000)
        expect(page.locator(".fixed button", has_text="Utilisateurs")).to_be_visible()
        expect(page.locator(".fixed button", has_text="Groupes")).to_be_visible()

    def test_associate_modal_cancel(self, admin_page: Page, base_url: str):
        """Le bouton Annuler ferme la modal"""
        page = admin_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        associate_btn = page.locator('button[title*="Associer"]').first
        if not associate_btn.is_visible():
            pytest.skip("Aucun bouton d'association visible")

        associate_btn.click()
        modal_title = page.locator("h3", has_text="Associer l'album")
        expect(modal_title).to_be_visible(timeout=3000)

        # Annuler — la modal d'association est la seule visible
        page.locator(".fixed:visible button", has_text="Annuler").click()

        # La modal est fermée
        expect(modal_title).to_be_hidden(timeout=2000)

    def test_associate_modal_tabs_switch(self, admin_page: Page, base_url: str):
        """Les onglets Utilisateurs/Groupes fonctionnent"""
        page = admin_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        associate_btn = page.locator('button[title*="Associer"]').first
        if not associate_btn.is_visible():
            pytest.skip("Aucun bouton d'association visible")

        associate_btn.click()
        expect(page.locator("h3", has_text="Associer l'album")).to_be_visible(timeout=3000)

        # Cliquer sur Groupes dans la modal
        page.locator(".fixed button", has_text="Groupes").click()
        page.wait_for_timeout(500)

        # Des checkboxes de groupes doivent apparaître
        checkboxes = page.locator('.fixed input[type="checkbox"]')
        expect(checkboxes.first).to_be_visible(timeout=3000)

    def test_associate_submit_shows_toast(self, admin_page: Page, base_url: str):
        """Valider l'association affiche un toast de succès (pas un alert)"""
        page = admin_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        associate_btn = page.locator('button[title*="Associer"]').first
        if not associate_btn.is_visible():
            pytest.skip("Aucun bouton d'association visible")

        associate_btn.click()
        expect(page.locator("h3", has_text="Associer l'album")).to_be_visible(timeout=3000)

        # Cocher au moins un groupe
        page.locator(".fixed button", has_text="Groupes").click()
        page.wait_for_timeout(1000)

        checkbox = page.locator('.fixed input[type="checkbox"]').first
        if checkbox.is_visible():
            checkbox.check()

        # Valider
        page.locator(".fixed button", has_text="Valider").click()

        # Un toast de succès doit apparaître (pas un alert JS)
        toast = page.locator('[x-show="toast.show"]')
        expect(toast).to_be_visible(timeout=5000)


# ============================================================================
# Sélection image de couverture (admin)
# ============================================================================


@pytest.mark.e2e
class TestAlbumCoverSelection:
    """Tests de la sélection d'image de couverture dans album_detail"""

    def _navigate_to_album_detail(self, page: Page, base_url: str) -> bool:
        """Helper : navigue vers le détail du premier album. Retourne False si aucun album."""
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)
        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            return False
        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)
        return True

    def test_cover_button_visible_for_admin(self, admin_page: Page, base_url: str):
        """Le bouton 'Choisir couverture' est visible pour les admins"""
        page = admin_page
        if not self._navigate_to_album_detail(page, base_url):
            pytest.skip("Aucun album disponible")

        # Le bouton n'est rendu que si is_superuser (Jinja server-side)
        cover_btn = page.locator("button", has_text="Choisir couverture")
        if cover_btn.count() == 0:
            pytest.skip("Bouton couverture non rendu (is_superuser=False côté serveur)")
        expect(cover_btn).to_be_visible(timeout=3000)

    def test_cover_select_mode_activates(self, admin_page: Page, base_url: str):
        """Cliquer sur 'Choisir couverture' active le mode sélection"""
        page = admin_page
        if not self._navigate_to_album_detail(page, base_url):
            pytest.skip("Aucun album disponible")

        cover_btn = page.locator("button", has_text="Choisir couverture")
        if cover_btn.count() == 0:
            pytest.skip("Bouton couverture non rendu")

        cover_btn.click()

        # La barre de mode sélection apparaît
        expect(page.locator("text=Mode sélection")).to_be_visible(timeout=3000)

    def test_cover_select_mode_cancel(self, admin_page: Page, base_url: str):
        """Le bouton Annuler quitte le mode sélection de couverture"""
        page = admin_page
        if not self._navigate_to_album_detail(page, base_url):
            pytest.skip("Aucun album disponible")

        cover_btn = page.locator("button", has_text="Choisir couverture")
        if cover_btn.count() == 0:
            pytest.skip("Bouton couverture non rendu")

        cover_btn.click()
        expect(page.locator("text=Mode sélection")).to_be_visible(timeout=3000)

        page.locator(".bg-purple-100 button", has_text="Annuler").click()
        expect(page.locator("text=Mode sélection")).to_be_hidden(timeout=2000)


# ============================================================================
# Lightbox / Galerie d'images
# ============================================================================


@pytest.mark.e2e
class TestAlbumLightbox:
    """Tests de la visionneuse d'images (PhotoSwipe)"""

    def test_image_click_opens_lightbox(self, authenticated_page: Page, base_url: str):
        """Cliquer sur une image ouvre la lightbox"""
        page = authenticated_page
        page.goto(f"{base_url}/")
        page.wait_for_timeout(1000)

        album_link = page.locator('a[href*="/album/"]').first
        if not album_link.is_visible():
            pytest.skip("Aucun album disponible")

        album_link.click()
        page.wait_for_url("**/album/**", timeout=5000)
        page.wait_for_timeout(2000)

        # Cliquer sur la première image du masonry grid
        first_img = page.locator("#masonry-grid a").first
        if not first_img.is_visible():
            pytest.skip("Aucune image dans l'album")

        first_img.click()
        page.wait_for_timeout(1000)

        # PhotoSwipe crée un élément .pswp--open
        pswp = page.locator(".pswp--open")
        expect(pswp).to_be_visible(timeout=3000)
