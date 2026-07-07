import runpy

from fastapi.testclient import TestClient

mod = runpy.run_path("AlbumsAventures-BE.py")
app = mod.get("app")

client = TestClient(app)
resp = client.get("/fe_router/login")
print("STATUS", resp.status_code)
text = resp.text
print("Contains title?", "Bienvenue" in text)
print("Contains forgot?", "Mot de passe oublié" in text)
if resp.status_code == 200 and "Bienvenue" in text:
    print("TEST PASSED")
else:
    print("TEST FAILED")
    raise SystemExit(2)
