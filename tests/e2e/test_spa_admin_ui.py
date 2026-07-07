"""
Tests E2E pour la page d'administration React (SPA, Phase 3.6).

La SPA est servie same-origin par FastAPI sous le préfixe ``/app`` (voir
frontend/spa_serving.py). La page admin est routée sous ``/app/admin``, derrière
le garde ``RequireSuperuser`` : un superuser voit les panneaux Utilisateurs /
Groupes ; un utilisateur non-admin est redirigé vers la grille (``/app/``). La
garde client n'est qu'un filtre UX — les endpoints ``be_auth/admin/*`` re-vérifient
``is_superuser`` côté serveur (#485), et la régénération de vignettes est durcie
de la même façon (F-1). C'est la variante ``/app`` du strangler : les pages Jinja
``/admin/users`` et ``/admin/groups`` restent servies inchangées.

Toutes les mutations (activation, promotion, gestion de groupes) transitent par
l'apiClient partagé : cookie de session HttpOnly en même origine + en-tête CSRF
double-submit sur POST/PUT/DELETE — aucun token stocké en JS.

Prérequis : serveur lancé sur ``E2E_BASE_URL`` avec la SPA buildée
(``npm run build`` dans frontend/spa/), ``E2E_ADMIN_PASSWORD`` pour le compte
superuser et ``E2E_USER_PASSWORD`` pour un compte standard.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestSpaAdminUI:
    """Tests de la page d'administration migrée en React (superuser-only)."""

    def test_admin_page_visible_for_superuser(self, admin_page: Page, base_url: str):
        """Un superuser voit la page admin et ses panneaux."""
        page = admin_page
        page.goto(f"{base_url}/app/admin")
        expect(page.get_by_role("heading", name="Administration")).to_be_visible(timeout=5000)
        # Le panneau Utilisateurs est actif par défaut.
        expect(page.get_by_role("heading", name="Utilisateurs")).to_be_visible()
        # Bascule vers le panneau Groupes.
        page.get_by_role("button", name="Groupes").click()
        expect(page.get_by_role("heading", name="Groupes")).to_be_visible(timeout=5000)

    def test_admin_link_shown_for_superuser(self, admin_page: Page, base_url: str):
        """Le lien Admin apparaît dans l'en-tête pour un superuser."""
        page = admin_page
        page.goto(f"{base_url}/app/")
        expect(page.get_by_role("link", name="Admin")).to_be_visible(timeout=5000)

    def test_admin_page_redirects_non_superuser(self, authenticated_page: Page, base_url: str):
        """Un utilisateur non-admin est redirigé hors de /app/admin vers la grille."""
        page = authenticated_page
        page.goto(f"{base_url}/app/admin")
        # RequireSuperuser renvoie vers la grille ; le titre Administration ne
        # doit jamais s'afficher pour un non-admin.
        expect(page.get_by_role("heading", name="Administration")).to_have_count(0, timeout=5000)
        # Le lien Admin n'est pas proposé non plus.
        expect(page.get_by_role("link", name="Admin")).to_have_count(0)
