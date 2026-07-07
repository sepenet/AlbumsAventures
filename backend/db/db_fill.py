from datetime import date

from sqlalchemy.orm import Session

from .db_connect import engine
from .models import Album, Category, Group, User, UserAlbum, UserGroup


def db_users_fill():
    """Remplissage de la table des Users"""

    db = Session(bind=engine)
    user_sebastien = User(
        firstname="Sebastien",
        lastname="Penet",
        email="sebastien@pe-net.fr",
        password="$scrypt$ln=16,r=8,p=1$qPV+r7X2/h/jHONc6x0jZA$CD3ulpiZFxSgweFBcEtn0guI//7jR/NC1fH9uLOnzt0",
        is_active=True,
        is_superuser=True,
    )
    user_sabina = User(
        firstname="Sabina",
        lastname="Penet",
        email="sabina@pe-net.fr",
        password="fake",
        is_active=True,
        is_superuser=False,
    )
    db.add_all([user_sebastien, user_sabina])
    db.commit()


def db_categories_fill():
    """Remplissage de la table des categories"""

    db = Session(bind=engine)
    category_Montagne = Category(category="Montagne")
    category_Rando = Category(category="Randonnée")
    category_VeloRoute = Category(category="Vélo de route")
    category_VTT = Category(category="VTT")
    category_SkiRando = Category(category="Ski de Rando")
    category_Ski = Category(category="Ski")
    category_tri = Category(category="Triathlon")
    category_FêteFamille = Category(category="Fêtes de famille")
    category_Amis = Category(category="Amis")
    db.add_all(
        [
            category_Ski,
            category_SkiRando,
            category_Montagne,
            category_Rando,
            category_VeloRoute,
            category_VTT,
            category_tri,
            category_FêteFamille,
            category_Amis,
        ]
    )
    db.commit()


def db_albums_fill():
    """Remplissage de la table des albums"""

    db = Session(bind=engine)
    album_ChamZermatt = Album(
        title="Chamonix Zermatt",
        description="Traversée des Alpes",
        date=date(2024, 4, 3),
        participants="Janick|Thierry|Patrick|François|Hervé",
        location="Chamonix, Zermatt",
        tags="Ski de Rando, Chamonix, Zermatt, 2024",
        image_cover="2024-ChamonixZermatt-JanickThierryFrancoisPatrickHerve_07.jpg",
        # la definition de la categorie est faite ici grace a la classe Categorie definit comme model,
        # mais cela ne fonctionne pas car cela cree une nouvelle categorie et ne renvoie pas l'id de la categorie existante meme si celle ci existe deja.
        # un moyen de réaliser cela est de faire une requete pour recuperer l'id de la categorie et de l'ajouter a la classe album_ChamZermatt
        # categorie = Categorie(categorie = "Ski de Rando")
        category_id=2,
    )
    album_Tri_PontenRoyan = Album(
        title="Vercorsman",
        description="Triathlon du Vercors",
        date=date(2024, 8, 6),
        participants="Margaux|Eléna|Guilhem|Antoine",
        location="Pont en Royan",
        tags="Thriathlon, Pont en Royan, 2024",
        image_cover="2024-TriathlonVercorsMan-MargauxElenaGuilhemAntoine_03.jpg",
        category_id=7,
    )
    album_Rando_chaletMiage = Album(
        title="Bivouac Chalet de Miage",
        description="Weekend au Chalet de Miage",
        date=date(2024, 7, 30),
        participants="Sabina|Pascale|Julie|Etienne|Fred|Manu",
        location="Chalet de Miage",
        tags="Weekend, Bivouac, Chalet de Miage, 2024",
        image_cover="Miage.jpg",
        category_id=4,
    )
    db.add_all([album_ChamZermatt, album_Tri_PontenRoyan, album_Rando_chaletMiage])
    db.commit()


def db_user_albums_fill():
    """Remplissage de la table des relations entre utilisateurs et albums"""
    db = Session(bind=engine)
    user1_album1 = UserAlbum(user_id=1, album_id=1)
    user1_album2 = UserAlbum(user_id=1, album_id=2)
    user1_album3 = UserAlbum(user_id=1, album_id=3)
    db.add_all([user1_album1, user1_album2, user1_album3])
    db.commit()


def db_group_fill():
    """Remplissage de la table des groupes"""
    db = Session(bind=engine)
    skiderando = Group(name="Ski de Rando", description="Groupe pour les utilisateurs et Albums de Ski de Rando")
    randonnee = Group(name="Randonnée", description="Groupe pour les utilisateurs et Albums de randonnée")
    allAlbums = Group(name="Tous les Albums", description="Groupe pour tous les Albums")
    db.add_all([skiderando, randonnee, allAlbums])
    db.commit()


def db_users_groups_fill():
    """Remplissage de la table des relations entre utilisateurs et groupes"""
    db = Session(bind=engine)
    user1_group1 = UserGroup(user_id=1, group_id=1)
    user2_group1 = UserGroup(user_id=2, group_id=1)
    user2_group2 = UserGroup(user_id=2, group_id=2)
    db.add_all([user1_group1, user2_group1, user2_group2])
    db.commit()


def db_albums_groups_fill():
    """Remplissage de la table des relations entre albums et groupes"""
    from .models import AlbumGroup

    db = Session(bind=engine)
    # Album 1 (Chamonix Zermatt) dans groupe 1 (Ski de Rando) et groupe 3 (Tous les Albums)
    album1_group1 = AlbumGroup(album_id=1, group_id=1)
    album1_group3 = AlbumGroup(album_id=1, group_id=3)
    # Album 2 (Vercorsman) dans groupe 3 (Tous les Albums)
    album2_group3 = AlbumGroup(album_id=2, group_id=3)
    # Album 3 (Bivouac Miage) dans groupe 2 (Randonnée) et groupe 3 (Tous les Albums)
    album3_group2 = AlbumGroup(album_id=3, group_id=2)
    album3_group3 = AlbumGroup(album_id=3, group_id=3)
    db.add_all([album1_group1, album1_group3, album2_group3, album3_group2, album3_group3])
    db.commit()
