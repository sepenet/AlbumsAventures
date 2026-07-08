"""
Version de l'application FastAPI pour les tests.
N'initialise pas de données de test et n'efface pas la base au démarrage.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Initialiser le SecretStore AVANT tout import de config (idem que dans AlbumsAventures-BE.py)
from utils.secret_store import SecretStore

SecretStore.init()

from backend.routers import (
    be_album,
    be_auth,
    be_category,
    be_formatter,
    be_group,
    be_media_bridge,
    be_resizer,
    be_user,
)
from frontend.routers import fe_redirects
from frontend.spa_serving import configure_spa
from utils.security import configure_cors, configure_security

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan simplifié pour les tests - pas d'initialisation de données"""
    logger.info("Démarrage de l'application de test")
    yield
    logger.info("Arrêt de l'application de test")


# Créer l'application
app = FastAPI(lifespan=lifespan, title="AlbumsAventures Test")

# Sécurité HTTP identique à l'app de production (utils/security.py) afin que la
# CSP et les en-têtes de sécurité soient vérifiables par la suite de tests.
configure_cors(app)
configure_security(app)

# Inclure les routers
app.include_router(be_album.router)
app.include_router(be_album.public_router)
app.include_router(be_user.router)
app.include_router(be_auth.router)
app.include_router(be_category.router)
app.include_router(be_formatter.router)
app.include_router(be_group.router)
app.include_router(be_resizer.router)
# Seam de préservation d'URL (identique à la prod) : /album/{id}/images +
# /album/shared/images à leurs URLs bare.
app.include_router(be_media_bridge.router)
# Shims 302 des routes Jinja retirées -> SPA /app (couche Jinja décommissionnée).
app.include_router(fe_redirects.router)

# Monter les fichiers statiques seulement s'ils existent
if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# SPA React servie same-origin sous /app (identique à l'app de prod) : garantit
# que la CSP et le contrat de service SPA sont vérifiables côté tests.
configure_spa(app)
