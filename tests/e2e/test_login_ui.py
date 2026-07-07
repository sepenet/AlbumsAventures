"""
Tests E2E pour l'authentification.

Pages testées : login.html, signup.html, forgot_password.html, reset_password.html
"""
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import E2E_USER_EMAIL, E2E_USER_PASSWORD


@pytest.mark.e2e
class TestLoginUI:
    """Tests de la page de login"""

    def test_login_page_loads(self, page: Page, base_url: str):
        """La page de login affiche le formulaire complet"""
        page.goto(f"{base_url}/login")

        expect(page.locator('#email')).to_be_visible()
        expect(page.locator('#password')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()
        expect(page.locator('a[href="/forgot-password"]')).to_be_visible()
        expect(page.locator('a[href="/signup"]')).to_be_visible()

    def test_login_with_valid_credentials(self, page: Page, base_url: str):
        """Login réussi redirige vers l'accueil"""
        page.goto(f"{base_url}/login")

        page.fill('#email', E2E_USER_EMAIL)
        page.fill('#password', E2E_USER_PASSWORD)
        page.click('button[type="submit"]')

        # Doit rediriger vers la page d'accueil
        page.wait_for_url(f"{base_url}/", timeout=5000)
        expect(page).to_have_url(f"{base_url}/")

    def test_login_with_invalid_credentials(self, page: Page, base_url: str):
        """Login échoué affiche un message d'erreur"""
        page.goto(f"{base_url}/login")

        page.fill('#email', "wrong@example.com")
        page.fill('#password', "WrongPassword123")
        page.click('button[type="submit"]')

        # Un message d'erreur doit apparaître
        error_alert = page.locator('[role="alert"]')
        expect(error_alert).to_be_visible(timeout=3000)

    def test_login_empty_fields_blocked(self, page: Page, base_url: str):
        """Soumettre le formulaire vide est bloqué par la validation HTML5"""
        page.goto(f"{base_url}/login")
        page.click('button[type="submit"]')

        # On reste sur la page de login (validation native bloque la soumission)
        expect(page).to_have_url(f"{base_url}/login")


@pytest.mark.e2e
class TestSignupUI:
    """Tests de la page d'inscription"""

    def test_signup_page_loads(self, page: Page, base_url: str):
        """La page d'inscription affiche tous les champs"""
        page.goto(f"{base_url}/signup")

        expect(page.locator('#firstname')).to_be_visible()
        expect(page.locator('#lastname')).to_be_visible()
        expect(page.locator('#email')).to_be_visible()
        expect(page.locator('#password')).to_be_visible()
        expect(page.locator('#confirmPassword')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_signup_link_from_login(self, page: Page, base_url: str):
        """Le lien vers inscription depuis login fonctionne"""
        page.goto(f"{base_url}/login")
        page.click('a[href="/signup"]')
        expect(page).to_have_url(f"{base_url}/signup")

    def test_signup_password_mismatch_shows_error(self, page: Page, base_url: str):
        """Mots de passe différents affiche une erreur de validation"""
        page.goto(f"{base_url}/signup")

        page.fill('#firstname', "Test")
        page.fill('#lastname', "User")
        page.fill('#email', "test@example.com")
        page.fill('#password', "Password123")
        page.fill('#confirmPassword', "Different456")
        page.click('button[type="submit"]')

        # L'erreur de confirmation doit apparaître
        error = page.locator('[x-show*="confirmPassword"]')
        expect(error).to_be_visible(timeout=2000)

    def test_signup_weak_password_shows_error(self, page: Page, base_url: str):
        """Un mot de passe trop court affiche une erreur"""
        page.goto(f"{base_url}/signup")

        page.fill('#firstname', "Test")
        page.fill('#lastname', "User")
        page.fill('#email', "test@example.com")
        page.fill('#password', "abc")
        page.fill('#confirmPassword', "abc")
        page.click('button[type="submit"]')

        # L'erreur de password doit apparaître
        error = page.locator('[x-show*="errors.password"]')
        expect(error).to_be_visible(timeout=2000)


@pytest.mark.e2e
class TestForgotPasswordUI:
    """Tests de la page mot de passe oublié"""

    def test_forgot_password_page_loads(self, page: Page, base_url: str):
        """La page mot de passe oublié affiche le formulaire"""
        page.goto(f"{base_url}/forgot-password")

        expect(page.locator('#email')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()
        expect(page.locator('a[href="/login"]')).to_be_visible()

    def test_forgot_password_link_from_login(self, page: Page, base_url: str):
        """Le lien mot de passe oublié depuis login fonctionne"""
        page.goto(f"{base_url}/login")
        page.click('a[href="/forgot-password"]')
        expect(page).to_have_url(f"{base_url}/forgot-password")

    def test_forgot_password_submit_shows_confirmation(self, page: Page, base_url: str):
        """Soumettre un email affiche un message de confirmation"""
        page.goto(f"{base_url}/forgot-password")

        page.fill('#email', "test@example.com")
        page.click('button[type="submit"]')

        # Un message de succès doit apparaître (même si l'email n'existe pas, par sécurité)
        success = page.locator('[x-show="success"]')
        expect(success).to_be_visible(timeout=5000)


@pytest.mark.e2e
class TestResetPasswordUI:
    """Tests de la page de réinitialisation de mot de passe"""

    def test_reset_password_page_loads(self, page: Page, base_url: str):
        """La page de reset s'affiche avec les champs"""
        page.goto(f"{base_url}/reset-password?token=fake-token")

        expect(page.locator('#password')).to_be_visible()
        expect(page.locator('#confirmPassword')).to_be_visible()
        expect(page.locator('button[type="submit"]')).to_be_visible()

    def test_reset_password_without_token_shows_error(self, page: Page, base_url: str):
        """Accéder à la page sans token affiche une erreur"""
        page.goto(f"{base_url}/reset-password")

        error = page.locator('[x-show="tokenError"]')
        expect(error).to_be_visible(timeout=3000)
