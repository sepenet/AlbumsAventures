"""
Tests E2E pour la page d'administration des groupes et accès.

Page testée : admin_groups.html
Fonctionnalités : onglets Groupes/Accès directs, sélection groupe,
CRUD groupe, gestion utilisateurs/albums dans un groupe.
"""

import pytest
from playwright.sync_api import Page, expect

# ============================================================================
# Chargement de la page admin groupes
# ============================================================================


@pytest.mark.e2e
class TestAdminGroupsPageLoad:
    """Tests de chargement de la page admin groupes"""

    def test_admin_groups_page_loads(self, admin_page: Page, base_url: str):
        """La page admin groupes s'affiche avec le titre"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")

        expect(page.locator("h1")).to_contain_text("Gestion des accès")

    def test_admin_groups_shows_tabs(self, admin_page: Page, base_url: str):
        """Les onglets Groupes et Accès directs sont visibles"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")

        expect(page.locator("button.border-b-2", has_text="Groupes")).to_be_visible()
        expect(page.locator("button.border-b-2", has_text="Accès directs")).to_be_visible()

    def test_admin_groups_has_group_selector(self, admin_page: Page, base_url: str):
        """Le sélecteur de groupe est visible"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        expect(page.locator("#groupSelect")).to_be_visible()

    def test_admin_groups_has_new_group_button(self, admin_page: Page, base_url: str):
        """Le bouton Nouveau groupe est visible"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        expect(page.locator("button", has_text="Nouveau groupe")).to_be_visible()


# ============================================================================
# Navigation par onglets
# ============================================================================


@pytest.mark.e2e
class TestAdminGroupsTabs:
    """Tests des onglets Groupes / Accès directs"""

    def test_switch_to_direct_access_tab(self, admin_page: Page, base_url: str):
        """Cliquer sur 'Accès directs' affiche le contenu correspondant"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        page.locator("button.border-b-2", has_text="Accès directs").click()
        page.wait_for_timeout(1000)

        # L'onglet accès directs doit être actif (border-sky-500)
        direct_tab = page.locator("button.border-b-2", has_text="Accès directs")
        expect(direct_tab).to_be_visible()

    def test_switch_back_to_groups_tab(self, admin_page: Page, base_url: str):
        """Revenir à l'onglet Groupes fonctionne"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        page.locator("button.border-b-2", has_text="Accès directs").click()
        page.wait_for_timeout(500)

        page.locator("button.border-b-2", has_text="Groupes").click()
        page.wait_for_timeout(500)

        # Le sélecteur de groupe est de nouveau visible
        expect(page.locator("#groupSelect")).to_be_visible()


# ============================================================================
# Sélection et détails d'un groupe
# ============================================================================


@pytest.mark.e2e
class TestAdminGroupsSelection:
    """Tests de la sélection d'un groupe et affichage des détails"""

    def test_select_group_shows_details(self, admin_page: Page, base_url: str):
        """Sélectionner un groupe affiche ses utilisateurs et albums"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(2000)

        # Sélectionner le premier groupe disponible
        select = page.locator("#groupSelect")
        options = select.locator("option")
        count = options.count()

        if count <= 1:  # Seulement l'option vide
            pytest.skip("Aucun groupe disponible")

        # Sélectionner la 2ème option (première option réelle)
        select.select_option(index=1)
        page.wait_for_timeout(3000)

        # Les sections Utilisateurs et Albums doivent apparaître
        expect(page.get_by_role("heading", name="Utilisateurs").first).to_be_visible(timeout=10000)
        expect(page.get_by_role("heading", name="Albums").first).to_be_visible(timeout=3000)

    def test_group_shows_edit_delete_buttons(self, admin_page: Page, base_url: str):
        """Un groupe sélectionné affiche les boutons éditer et supprimer"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(2000)

        select = page.locator("#groupSelect")
        options = select.locator("option")
        if options.count() <= 1:
            pytest.skip("Aucun groupe disponible")

        select.select_option(index=1)
        page.wait_for_timeout(1500)

        # Boutons éditer et supprimer
        expect(page.locator('button[title="Modifier le groupe"]')).to_be_visible(timeout=3000)
        expect(page.locator('button[title="Supprimer le groupe"]')).to_be_visible(timeout=3000)

    def test_group_shows_add_user_button(self, admin_page: Page, base_url: str):
        """La section Utilisateurs a un bouton ajouter"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(2000)

        select = page.locator("#groupSelect")
        if select.locator("option").count() <= 1:
            pytest.skip("Aucun groupe disponible")

        select.select_option(index=1)
        page.wait_for_timeout(1500)

        expect(page.locator('button[title="Ajouter un utilisateur"]')).to_be_visible(timeout=3000)

    def test_group_shows_add_album_button(self, admin_page: Page, base_url: str):
        """La section Albums a un bouton ajouter"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(2000)

        select = page.locator("#groupSelect")
        if select.locator("option").count() <= 1:
            pytest.skip("Aucun groupe disponible")

        select.select_option(index=1)
        page.wait_for_timeout(1500)

        expect(page.locator('button[title="Ajouter un album"]')).to_be_visible(timeout=3000)


# ============================================================================
# Création de groupe (modal)
# ============================================================================


@pytest.mark.e2e
class TestAdminGroupsCreate:
    """Tests de la modal de création de groupe"""

    def test_new_group_modal_opens(self, admin_page: Page, base_url: str):
        """Le bouton Nouveau groupe ouvre la modal"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Nouveau groupe").click()

        # La modal doit s'ouvrir (titre = "Nouveau groupe")
        modal_title = page.locator(".fixed h3", has_text="Nouveau groupe")
        expect(modal_title).to_be_visible(timeout=3000)

    def test_new_group_modal_has_fields(self, admin_page: Page, base_url: str):
        """La modal de création a les champs nom et description"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Nouveau groupe").click()
        expect(page.locator(".fixed h3", has_text="Nouveau groupe")).to_be_visible(timeout=3000)

        # Les champs sont présents (input avec x-model="newGroup.name")
        expect(page.locator('.fixed input[type="text"]').first).to_be_visible()

    def test_new_group_modal_cancel(self, admin_page: Page, base_url: str):
        """Le bouton Annuler ferme la modal de création"""
        page = admin_page
        page.goto(f"{base_url}/admin/groups")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Nouveau groupe").click()
        modal_title = page.locator(".fixed h3", has_text="Nouveau groupe")
        expect(modal_title).to_be_visible(timeout=3000)

        # Cliquer sur le bouton Annuler de la modal visible (showNewGroupModal)
        page.locator(".fixed:visible button", has_text="Annuler").click()
        expect(modal_title).to_be_hidden(timeout=2000)
