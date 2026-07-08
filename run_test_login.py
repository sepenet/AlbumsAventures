import runpy

from fastapi.testclient import TestClient

mod = runpy.run_path("AlbumsAventures-BE.py")
app = mod.get("app")

client = TestClient(app)
# La couche Jinja est décommissionnée : la route bare /login redirige (302) vers
# la page de connexion SPA /app/login (voir frontend/routers/fe_redirects.py).
resp = client.get("/login", follow_redirects=False)
print("STATUS", resp.status_code)
location = resp.headers.get("location", "")
print("LOCATION", location)
if resp.status_code == 302 and location == "/app/login":
    print("TEST PASSED")
else:
    print("TEST FAILED")
    raise SystemExit(2)
