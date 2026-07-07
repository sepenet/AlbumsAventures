from datetime import date

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db_connect import Base

###########################################################
# les tables de la base de données qui sont des entites
# excellentes explications de relation entre les tables et back poulate ici : https://sqlmodel.tiangolo.com/tutorial/relationship-attributes/create-and-update-relationships/#create-a-team-with-heroes
# dans l'exemple ci-dessus, on a une relation many-to-one entre les tables Team et Hero. Cela signifie qu'un héros peut appartenir à une seule équipe, mais une équipe peut avoir plusieurs héros.
# dans notre cas, on a une relation many-to-one entre les tables Album et Categorie. Cela signifie qu'un album peut avoir à une seule catégorie, mais une catégorie peut appartenir à plusieurs albums.
# We said before that this is a many-to-one relationship, because there can be many albums that belong to one categorie.


#####################################################################
# Les classes pour les tables principales
# La table des categories
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    category: Mapped[str]

    albums: Mapped[list["Album"]] = relationship(back_populates="category")


# La table des albums
class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    date: Mapped[date]
    participants: Mapped[str | None]
    location: Mapped[str | None]
    tags: Mapped[str | None]
    image_cover: Mapped[str | None]

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped["Category"] = relationship(back_populates="albums")


# la table des utilisateurs
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    firstname: Mapped[str] = mapped_column(nullable=False, index=True)
    lastname: Mapped[str] = mapped_column(nullable=False, index=True)
    email: Mapped[str] = mapped_column(nullable=False, index=True, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)


# la table des groupes
class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True, unique=True)
    description: Mapped[str] = mapped_column(index=True)


#####################################################################
# Les classes pour les tables de relations
# Relation entre utilisateurs et groupes
class UserGroup(Base):
    __tablename__ = "users_groups"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))


# Relation entre albums et groupes
class AlbumGroup(Base):
    __tablename__ = "albums_groups"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))


# Relation entre utilisateurs et albums
class UserAlbum(Base):
    __tablename__ = "users_albums"

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id"))


# Table de rate limiting durable (SEC-06)
# Remplace le cache mémoire process-local par un stockage partagé/durable.
# Réutilise la base existante (PostgreSQL en prod, SQLite en dev) — aucune
# nouvelle infrastructure (condition coût C-4 : pas de Redis managé Azure).
# La clé est un hash de la clé logique (login:<email>, forgot:<email>, ou hash
# du token de partage) pour ne jamais stocker d'identifiant en clair.
class RateLimitEntry(Base):
    __tablename__ = "rate_limit_entries"

    # Hash SHA-256 de la clé logique (identifiant opaque, jamais l'email en clair).
    key_hash: Mapped[str] = mapped_column(primary_key=True)
    # Nombre de tentatives échouées dans la fenêtre courante.
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    # Horodatage epoch (secondes) de la première tentative de la fenêtre.
    first_attempt: Mapped[float] = mapped_column(default=0.0, nullable=False)
    # Horodatage epoch (secondes) jusqu'auquel la clé est bloquée (0 = non bloquée).
    blocked_until: Mapped[float] = mapped_column(default=0.0, nullable=False)


# Statut durable de traitement post-upload par fichier (UPL-01).
# Le pipeline TUS (backend/routers/be_resizer.py) génère la vignette dans un
# pool de threads borné APRÈS avoir renvoyé le 204 au client. Sans trace
# durable, un redémarrage du process pouvait laisser un original orphelin avec
# une vignette manquante/échouée, sans que l'utilisateur le sache jamais.
# Cette table persiste l'état par fichier (réutilise la base existante :
# PostgreSQL en prod, SQLite en dev — aucune nouvelle infrastructure, pas de
# Redis ni de file de tâches, conformément au périmètre du conseil).
class ImageProcessingStatus(Base):
    __tablename__ = "image_processing_status"
    # Un seul enregistrement de statut par (album, fichier) : permet l'upsert.
    __table_args__ = (UniqueConstraint("album_id", "filename", name="uq_ips_album_filename"),)

    id: Mapped[int] = mapped_column(default=None, nullable=False, primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id"), nullable=False, index=True)
    # Nom de fichier sécurisé (tel qu'intégré dans l'album).
    filename: Mapped[str] = mapped_column(nullable=False, index=True)
    # Type de média déduit de l'extension : "image", "video" ou "unknown".
    media_type: Mapped[str] = mapped_column(default="unknown", nullable=False)
    # Étape de traitement : pending | processing | success | failed | skipped.
    status: Mapped[str] = mapped_column(default="pending", nullable=False, index=True)
    # Message d'erreur ou détail (échec de vignette, doublon ignoré, ...).
    detail: Mapped[str | None]
    # Horodatage epoch (secondes) de création de l'enregistrement.
    created_at: Mapped[float] = mapped_column(default=0.0, nullable=False)
    # Horodatage epoch (secondes) de la dernière mise à jour de statut.
    updated_at: Mapped[float] = mapped_column(default=0.0, nullable=False)
