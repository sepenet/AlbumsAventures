import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy import URL, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.config import database_config

# postgreUrl de la forme, on utilise la fonction URL.Create de SQLAlchmy pour la créer
# postgresql+psycopg2://user:password@host:port/database
postgreUrl = URL.create(
    drivername=database_config.drivername,
    username=database_config.user,
    password=database_config.password,
    host=database_config.host,
    port=database_config.port,
    database=database_config.name,
)


# Pour une base de données SQLite, on peut utiliser le code suivant à la place
# pour le développement local
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# on utilise le type d'OS pour savoir si on est sur windows ou linux et en fonction de ça on choisit le bon moteur de base de données
if os.name == "nt":
    # Windows
    engine = create_engine(sqlite_url)
else:
    # Linux or MacOS
    engine = create_engine(postgreUrl, future=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[SessionLocal, Depends(get_db)]
