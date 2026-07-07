# Description: This file contains the main code for the FastAPI application.
from contextlib import asynccontextmanager

# ══════════════════════════════════════════════════════════════════════════════
# Shim Windows : fcntl n'existe pas sur Windows, mais tuspyserver l'importe.
# À installer AVANT tout import indirect de tuspyserver (via be_resizer).
# ══════════════════════════════════════════════════════════════════════════════
from utils.win_fcntl_shim import install_if_windows as _install_fcntl_shim

_install_fcntl_shim()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTANT : Initialiser le SecretStore AVANT tout import de config
# Cela garantit que les secrets sont disponibles quand config.py est chargé
# ══════════════════════════════════════════════════════════════════════════════
from utils.secret_store import SecretStore

SecretStore.init()

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.db import models
from backend.db.db_connect import engine
from backend.db.db_fill import (
    db_albums_fill,
    db_albums_groups_fill,
    db_categories_fill,
    db_group_fill,
    db_user_albums_fill,
    db_users_fill,
    db_users_groups_fill,
)
from backend.routers import be_album, be_auth, be_category, be_formatter, be_group, be_resizer, be_user
from frontend.routers import fe_router
from utils.config import image, logging_config

# Patch Windows tuspyserver (os.rename -> os.replace pour les fichiers .info)
# À faire après l'import de be_resizer (qui charge tuspyserver).
from utils.win_fcntl_shim import patch_tuspyserver_for_windows as _patch_tus_windows

_patch_tus_windows()

# Configuration du logging au tout début de l'application
logging_config.setup_logging()
logger = logging.getLogger(__name__)


# Mise en place de la gestion du cycle de vie de l'application
# https://fastapi.tiangolo.com/advanced/events/#lifespan-events ,
# au demarrage de l'application, on initialise la base de données
# à la fin (apres le yield), on ne fait rien()
@asynccontextmanager
async def lifespan(app: FastAPI):
    # initialisation de la base de données, creation des tables si pas existantes et connexion à la base de données
    logger.info("Démarrage de l'application AlbumsAventures")

    # si OS est windows, on utilise la base de données SQLite, et on la cré et efface à chaque fois
    if os.name == "nt":
        logger.info("Environnement Windows détecté - Mode développement avec SQLite")
        models.Base.metadata.drop_all(bind=engine)
        models.Base.metadata.create_all(bind=engine)
        logger.info("Base de données SQLite créée et initialisée")

        db_categories_fill()
        db_albums_fill()
        db_users_fill()
        db_user_albums_fill()
        db_group_fill()
        db_users_groups_fill()
        db_albums_groups_fill()
        logger.info("Données de test chargées avec succès")
    else:
        logger.info("Environnement Linux/Mac détecté - Mode production avec PostgreSQL")

    yield

    # ici on peut faire des actions de nettoyage, comme fermer les connexions à la base de données
    logger.info("Arrêt de l'application AlbumsAventures")
    engine.dispose()

    if os.name == "nt":
        models.Base.metadata.drop_all(bind=engine)
        # on arrete le moteur de la base de données SQLite et on supprime le fichier de la base de données
        engine.dispose()
        os.remove("database.db")
        logger.info("Base de données SQLite supprimée")
    pass


##################################################################
# create the app fastapi
app = FastAPI(lifespan=lifespan)

# on ajoute les origines autorisées pour les requêtes, pour eviter les CORS errors
origins = [
    "http://localhost:5003",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Headers TUS exposés au client (requis pour @uppy/tus, voir TODO #391/#392)
    expose_headers=[
        "Location",
        "Upload-Offset",
        "Upload-Length",
        "Upload-Expires",
        "Tus-Resumable",
        "Tus-Version",
        "Tus-Extension",
        "Tus-Max-Size",
    ],
)
# include the routers qui sont divisés en plusieurs fichiers pour plus de clarté
app.include_router(be_album.router)
app.include_router(be_album.public_router)  # Router public pour les albums partagés
app.include_router(be_user.router)
app.include_router(be_auth.router)
app.include_router(be_category.router)
app.include_router(be_formatter.router)
app.include_router(be_group.router)
app.include_router(be_resizer.router)
app.include_router(be_resizer.tus_router)  # endpoints TUS resumable (/be_resizer/tus)
app.include_router(fe_router.router)

# on monte le dossier static pour servir les fichiers statiques (images, css, js, etc.)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# on monte le dossier thumbnails externe pour servir les vignettes d'albums
app.mount("/thumbnails", StaticFiles(directory=image.thumbnails_path), name="thumbnails")

# on monte le dossier images externe pour servir les images full-size
app.mount("/images", StaticFiles(directory=image.image_path), name="images")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("AlbumsAventures-BE:app", host="localhost", port=8003)
