import runpy

from fastapi.testclient import TestClient

# Charger le module depuis le fichier (nom de fichier avec tiret n'est pas un module Python valide)
mod = runpy.run_path("AlbumsAventures-BE.py")
app = mod.get("app")


def test_login_page_renders():
    client = TestClient(app)
    response = client.get("/fe_router/login")
    assert response.status_code == 200
    content = response.text
    assert "Bienvenue — Connectez-vous" in content
    assert "Mot de passe oublié" in content
