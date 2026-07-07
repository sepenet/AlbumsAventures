from datetime import date

from sqlalchemy import ForeignKey
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
