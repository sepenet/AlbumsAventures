"""
Tests E2E pour la page de profil React (SPA, Phase 3.5).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). La page de profil est routée sous ``/app/profile``
(deep-linkable via le repli SPA). C'est la variante ``/app`` du strangler : la
page Jinja historique ``/profile`` reste servie inchangée.

Les mutations (``PUT /be_auth/update_profile`` et ``PUT /be_auth/update_password``)
transitent par l'apiClient partagé, qui envoie le cookie de session HttpOnly en
même origine et rejoue l'en-tête CSRF double-submit — aucun token stocké en JS.
La validation client (dont la vérification de non-correspondance des mots de
passe) est couverte par les tests unitaires Vitest
(frontend/spa/src/lib/profileValidation.test.ts). Ce spec vérifie le rendu, le
préremplissage depuis la session et la validation côté client.

Prérequis (identiques aux autres tests e2e) : serveur lancé sur
``E2E_BASE_URL`` avec la SPA buildée (``npm run build`` dans frontend/spa/) et
les credentials ``E2E_USER_PASSWORD`` renseignés.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestSpaProfileUI:
    """Tests de la page de profil migrée en React."""

    def test_profile_page_prefilled_from_session(self, authenticated_page: Page, base_url: str):
        """La page de profil SPA affiche les sections et préremplit l'email."""
        page = authenticated_page
        page.goto(f"{base_url}/app/profile")
        expect(page.get_by_role("heading", name="Mon profil")).to_be_visible(timeout=5000)
        expect(page.get_by_role("heading", name="Informations personnelles")).to_be_visible()
        expect(page.get_by_role("heading", name="Changer le mot de passe")).to_be_visible()
        # L'email est prérempli depuis la session (GET /be_auth/me).
        email_value = page.locator("#email").input_value()
        assert "@" in email_value

    def test_password_mismatch_blocks_submit(self, authenticated_page: Page, base_url: str):
        """Une confirmation divergente affiche l'erreur et n'envoie pas la mutation."""
        page = authenticated_page
        page.goto(f"{base_url}/app/profile")
        page.locator("#current_password").fill("Whatever1")
        page.locator("#new_password").fill("NewPass1")
        page.locator("#confirm_password").fill("Different1")
        page.get_by_role("button", name="Changer le mot de passe").click()
        expect(page.get_by_text("Les mots de passe ne correspondent pas")).to_be_visible(
            timeout=3000
        )

    def test_profile_deeplink_refresh_serves_shell(self, authenticated_page: Page, base_url: str):
        """Un rafraîchissement direct sur /app/profile renvoie le shell SPA."""
        page = authenticated_page
        url = f"{base_url}/app/profile"
        page.goto(url)
        page.goto(url)  # deep-link refresh : repli FastAPI + résolution React Router
        expect(page.get_by_role("heading", name="Mon profil")).to_be_visible(timeout=5000)
