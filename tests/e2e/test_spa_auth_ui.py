"""
Tests E2E pour les pages d'authentification React (SPA, Phase 3.8).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). Les pages d'authentification sont routées sous
``/app/login``, ``/app/signup``, ``/app/forgot-password`` et
``/app/reset-password``. Elles sont volontairement HORS de ``RequireAuth`` et du
``Layout`` authentifié : la connexion pose le cookie de session HttpOnly
existant via ``be_auth`` (cookie uniquement, aucun token en JS) puis redirige
vers ``/app``. C'est la variante ``/app`` du strangler : les pages Jinja
historiques (``/login``, ``/signup``, ...) restent servies inchangées.

La validation côté client (format email, politique de mot de passe,
non-correspondance) est couverte par les tests unitaires Vitest
(frontend/spa/src/lib/authValidation.test.ts). Ce spec vérifie le rendu des
pages et la navigation entre elles.

Prérequis (identiques aux autres tests e2e) : serveur lancé sur
``E2E_BASE_URL`` avec la SPA buildée (``npm run build`` dans frontend/spa/).
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestSpaAuthUI:
    """Tests des pages d'authentification migrées en React."""

    def test_login_page_renders(self, page: Page, base_url: str):
        """La page de login SPA affiche le formulaire de connexion."""
        page.goto(f"{base_url}/app/login")
        expect(page.get_by_role("button", name="Se connecter")).to_be_visible(timeout=5000)
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()

    def test_login_links_to_signup_and_forgot(self, page: Page, base_url: str):
        """La page de login propose l'inscription et le mot de passe oublié."""
        page.goto(f"{base_url}/app/login")
        expect(page.get_by_role("link", name="Créer un compte")).to_be_visible()
        expect(page.get_by_role("link", name="Mot de passe oublié ?")).to_be_visible()

    def test_signup_page_renders(self, page: Page, base_url: str):
        """La page d'inscription SPA affiche les champs attendus."""
        page.goto(f"{base_url}/app/signup")
        expect(page.get_by_role("button", name="Créer mon compte")).to_be_visible(timeout=5000)
        expect(page.locator("#firstname")).to_be_visible()
        expect(page.locator("#lastname")).to_be_visible()
        expect(page.locator("#confirmPassword")).to_be_visible()

    def test_forgot_password_page_renders(self, page: Page, base_url: str):
        """La page mot de passe oublié SPA affiche le champ email."""
        page.goto(f"{base_url}/app/forgot-password")
        expect(page.get_by_role("button", name="Envoyer le lien")).to_be_visible(timeout=5000)
        expect(page.locator("#email")).to_be_visible()

    def test_reset_password_without_token_shows_error(self, page: Page, base_url: str):
        """Sans token dans l'URL, la page reset affiche un message d'erreur."""
        page.goto(f"{base_url}/app/reset-password")
        expect(page.get_by_role("alert")).to_be_visible(timeout=5000)

    def test_reset_password_with_token_renders_form(self, page: Page, base_url: str):
        """Avec un token dans l'URL, la page reset affiche le formulaire."""
        page.goto(f"{base_url}/app/reset-password?token=dummy-token")
        expect(page.get_by_role("button", name="Réinitialiser le mot de passe")).to_be_visible(timeout=5000)
        expect(page.locator("#new_password")).to_be_visible()
        expect(page.locator("#confirm_password")).to_be_visible()
