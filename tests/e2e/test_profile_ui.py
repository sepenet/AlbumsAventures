"""
Tests E2E pour la page de profil utilisateur.

Page testée : profile.html
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestProfilePageUI:
    """Tests de la page profil"""

    def test_profile_page_loads(self, authenticated_page: Page, base_url: str):
        """La page de profil affiche les informations personnelles"""
        page = authenticated_page
        page.goto(f"{base_url}/profile")

        expect(page.locator("#firstname")).to_be_visible()
        expect(page.locator("#lastname")).to_be_visible()
        expect(page.locator("#email")).to_be_visible()

    def test_profile_fields_prefilled(self, authenticated_page: Page, base_url: str):
        """Les champs du profil sont pré-remplis avec les données utilisateur"""
        page = authenticated_page
        page.goto(f"{base_url}/profile")

        # Les champs ne doivent pas être vides
        expect(page.locator("#firstname")).not_to_have_value("")
        expect(page.locator("#lastname")).not_to_have_value("")
        expect(page.locator("#email")).not_to_have_value("")

    def test_profile_password_section_visible(self, authenticated_page: Page, base_url: str):
        """La section changement de mot de passe est présente"""
        page = authenticated_page
        page.goto(f"{base_url}/profile")

        expect(page.locator("#current_password")).to_be_visible()
        expect(page.locator("#new_password")).to_be_visible()
        expect(page.locator("#confirm_password")).to_be_visible()

    def test_profile_update_shows_success(self, authenticated_page: Page, base_url: str):
        """Modifier le profil affiche un message de succès"""
        page = authenticated_page
        page.goto(f"{base_url}/profile")

        # Lire la valeur actuelle du prénom pour la restaurer
        current_firstname = page.locator("#firstname").input_value()

        # Modifier le prénom (ajout d'un espace pour tester sans casser)
        page.fill("#firstname", current_firstname.strip())

        # Cliquer sur le bouton de sauvegarde du profil
        save_buttons = page.locator('button[type="submit"]')
        save_buttons.first.click()

        # Un message de succès doit apparaître (template x-if)
        success = page.locator('[x-text="successMessage"]')
        expect(success).to_be_visible(timeout=5000)

    def test_profile_password_mismatch(self, authenticated_page: Page, base_url: str):
        """Mots de passe différents dans le formulaire de changement"""
        page = authenticated_page
        page.goto(f"{base_url}/profile")

        page.fill("#current_password", "CurrentPass123")
        page.fill("#new_password", "NewPassword123")
        page.fill("#confirm_password", "DifferentPassword456")

        # Cliquer sur le bouton de changement de mot de passe (second submit)
        save_buttons = page.locator('button[type="submit"]')
        save_buttons.last.click()

        # Un message d'erreur doit apparaître (template x-if)
        error = page.locator('[x-text="errorMessage"], [x-text="passwordErrors.confirm_password"]')
        expect(error.first).to_be_visible(timeout=3000)


@pytest.mark.e2e
class TestProfileNavigation:
    """Tests de navigation vers le profil"""

    def test_profile_link_in_navbar(self, authenticated_page: Page, base_url: str):
        """Le lien profil est accessible dans le menu utilisateur"""
        page = authenticated_page
        page.goto(f"{base_url}/")

        # Ouvrir le menu utilisateur
        user_menu = page.locator('button:has(svg path[d*="M16 7a4 4 0"])').first
        if user_menu.is_visible():
            user_menu.click()

            # Le lien profil doit être visible
            profile_link = page.locator('a[href="/profile"]')
            expect(profile_link).to_be_visible(timeout=2000)
