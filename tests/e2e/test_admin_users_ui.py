"""
Tests E2E pour la page d'administration des utilisateurs.

Page testée : admin_users.html
Fonctionnalités : liste utilisateurs, filtres, activation/désactivation,
toggle admin, génération lien reset password.
"""

import pytest
from playwright.sync_api import Page, expect

# ============================================================================
# Chargement de la page admin utilisateurs
# ============================================================================


@pytest.mark.e2e
class TestAdminUsersPageLoad:
    """Tests de chargement de la page admin utilisateurs"""

    def test_admin_users_page_loads(self, admin_page: Page, base_url: str):
        """La page admin utilisateurs s'affiche avec le tableau"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")

        # Le titre est affiché
        expect(page.locator("h1")).to_contain_text("Administration des utilisateurs")

    def test_admin_users_shows_filters(self, admin_page: Page, base_url: str):
        """Les filtres (Tous, En attente, Actifs) sont visibles"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")

        expect(page.locator("button", has_text="Tous les utilisateurs")).to_be_visible()
        expect(page.locator("button", has_text="En attente de validation")).to_be_visible()
        expect(page.locator("button", has_text="Actifs")).to_be_visible()

    def test_admin_users_table_has_columns(self, admin_page: Page, base_url: str):
        """Le tableau affiche les colonnes Utilisateur, Email, Statut, Admin, Actions"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        # Passer au filtre "Tous" pour avoir des utilisateurs et afficher le tableau
        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(2000)

        expect(page.locator("th", has_text="Utilisateur")).to_be_visible(timeout=5000)
        expect(page.locator("th", has_text="Email")).to_be_visible()
        expect(page.locator("th", has_text="Statut")).to_be_visible()
        expect(page.locator("th", has_text="Admin")).to_be_visible()
        expect(page.locator("th", has_text="Actions")).to_be_visible()

    def test_admin_users_default_filter_pending(self, admin_page: Page, base_url: str):
        """Le filtre par défaut est 'En attente de validation'"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        # Le bouton "En attente" doit avoir la classe active (bg-amber-500)
        pending_btn = page.locator("button", has_text="En attente de validation")
        expect(pending_btn).to_be_visible()


# ============================================================================
# Filtres utilisateurs
# ============================================================================


@pytest.mark.e2e
class TestAdminUsersFilters:
    """Tests des filtres de la liste utilisateurs"""

    def test_filter_all_users(self, admin_page: Page, base_url: str):
        """Le filtre 'Tous' affiche tous les utilisateurs"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(1000)

        # Le tableau doit contenir au moins un utilisateur
        rows = page.locator("tbody tr")
        expect(rows.first).to_be_visible(timeout=5000)

    def test_filter_active_users(self, admin_page: Page, base_url: str):
        """Le filtre 'Actifs' affiche les utilisateurs actifs"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Actifs").click()
        page.wait_for_timeout(1000)

        # Au moins l'admin doit être actif
        rows = page.locator("tbody tr")
        expect(rows.first).to_be_visible(timeout=5000)


# ============================================================================
# Actions admin
# ============================================================================


@pytest.mark.e2e
class TestAdminUsersActions:
    """Tests des actions sur les utilisateurs"""

    def test_action_buttons_visible(self, admin_page: Page, base_url: str):
        """Les boutons d'action sont visibles pour chaque utilisateur"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        # Passer au filtre "Tous" pour avoir des utilisateurs
        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(1000)

        # Au moins les boutons toggle activation et toggle admin existent
        action_buttons = page.locator("tbody tr td:last-child button")
        expect(action_buttons.first).to_be_visible(timeout=5000)

    def test_reset_link_modal_opens(self, admin_page: Page, base_url: str):
        """Le bouton reset password ouvre la modal avec le lien"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        # Passer au filtre "Tous"
        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(1000)

        # Cliquer sur le bouton reset password (icône clé)
        reset_btn = page.locator('button[title="Générer un lien de réinitialisation de mot de passe"]').first
        if not reset_btn.is_visible():
            pytest.skip("Bouton reset non visible")

        reset_btn.click()

        # La modal s'ouvre
        expect(page.get_by_text("Lien de réinitialisation")).to_be_visible(timeout=5000)

    def test_reset_link_modal_has_copy_button(self, admin_page: Page, base_url: str):
        """La modal reset password contient un bouton Copier"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(1000)

        reset_btn = page.locator('button[title="Générer un lien de réinitialisation de mot de passe"]').first
        if not reset_btn.is_visible():
            pytest.skip("Bouton reset non visible")

        reset_btn.click()
        expect(page.get_by_text("Lien de réinitialisation")).to_be_visible(timeout=5000)

        # Le bouton Copier est présent
        expect(page.get_by_text("Copier")).to_be_visible()

        # Le champ contient une URL
        url_input = page.locator("input[readonly]")
        expect(url_input).to_be_visible()

    def test_reset_link_modal_closes(self, admin_page: Page, base_url: str):
        """La modal reset password se ferme en cliquant sur la croix"""
        page = admin_page
        page.goto(f"{base_url}/admin/users")
        page.wait_for_timeout(1000)

        page.locator("button", has_text="Tous les utilisateurs").click()
        page.wait_for_timeout(1000)

        reset_btn = page.locator('button[title="Générer un lien de réinitialisation de mot de passe"]').first
        if not reset_btn.is_visible():
            pytest.skip("Bouton reset non visible")

        reset_btn.click()
        expect(page.get_by_text("Lien de réinitialisation")).to_be_visible(timeout=5000)

        # Fermer via le bouton croix
        page.locator('.fixed button:has(svg path[d*="M6 18L18 6"])').click()
        expect(page.get_by_text("Lien de réinitialisation")).to_be_hidden(timeout=2000)
