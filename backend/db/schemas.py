from datetime import date as date_type

from pydantic import BaseModel, Field


# Pydantic model for group, la base du groupe ne contient pas l'ID parce ce qu'a la creation l'id n'existe pas encore
# le group base peut être utiliser pour la creation ou la lecture il est commun
#####################################################################
# les models pour les tables principales
# utilisateurs
class UserBase(BaseModel):
    __tablename__ = "users"

    firstname: str = Field(min_length=1, max_length=128)
    lastname: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=128)
    is_active: bool = False
    is_superuser: bool = False


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


# Schema pour l'affichage admin (sans mot de passe)
class UserAdmin(BaseModel):
    """Schema utilisateur pour la page admin (sans mot de passe)"""

    id: int
    firstname: str
    lastname: str
    email: str
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


# Schema pour la mise à jour des droits utilisateur
class UserRightsUpdate(BaseModel):
    """Schema pour activer/désactiver un utilisateur ou changer son rôle admin"""

    is_active: bool | None = None
    is_superuser: bool | None = None


# Schema pour la mise à jour du profil utilisateur (Tâche 210)
class UserProfileUpdate(BaseModel):
    """Schema pour la mise à jour du profil (prénom, nom, email)"""

    firstname: str = Field(min_length=1, max_length=128)
    lastname: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=1, max_length=128)


# Model Categorie
class CategoryBase(BaseModel):
    category: str = Field(min_length=1, max_length=128)


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True


#  Album model
class AlbumBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str | None = None
    category_id: int
    date: date_type
    participants: str | None = Field(min_length=0, max_length=512)
    location: str | None = Field(min_length=0, max_length=512)
    tags: str | None = Field(min_length=0, max_length=512)
    image_cover: str | None = Field(min_length=0, max_length=512)


class AlbumCreate(AlbumBase):
    pass


class Album(AlbumBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


class Album_Category(Album):
    category: str = Field(min_length=1, max_length=128)

    class Config:
        from_attributes = True


# Album avec URL de couverture calculée (pour l'affichage frontend)
class Album_Category_WithCoverUrl(Album_Category):
    """Album avec l'URL de l'image de couverture calculée pour le frontend"""

    image_cover_url: str | None = None

    class Config:
        from_attributes = True


# Model AlbumUpdate = champs optionnels pour mise à jour partielle (PATCH)
# Ne pas hériter de AlbumBase pour éviter les contraintes de validation
class AlbumUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    date: date_type | None = None
    participants: str | None = None
    location: str | None = None
    tags: str | None = None
    image_cover: str | None = None


# Model Groupe
class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class GroupCreate(GroupBase):
    pass


class Group(GroupBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


# Schema pour la mise à jour d'un groupe (Tâche 270)
class GroupUpdate(BaseModel):
    """Schema pour la mise à jour d'un groupe (nom et description)"""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


#####################################################################
# les models pour les relations entre les tables
# la relation se définit comme suit Utilisteur_groupe = Utilisateur dans groupe
# utilisateur1 -> groupe1
# utilisateur1 -> groupe2
# utilisateur2 -> groupe1
# ...
# Model Utilisateur_groupe
class User_GroupBase(BaseModel):
    user_id: int
    group_id: int


class User_GroupCreate(User_GroupBase):
    pass


class User_Group(User_GroupBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


# Multi-sélection bulk : plusieurs utilisateurs vers un groupe
class User_GroupBulkCreate(BaseModel):
    user_ids: list[int]
    group_id: int


# Model Album_groupe
class Album_GroupBase(BaseModel):
    album_id: int
    group_id: int


class Album_GroupCreate(Album_GroupBase):
    pass


class Album_Group(Album_GroupBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


# Multi-sélection bulk : plusieurs albums vers un groupe
class Album_GroupBulkCreate(BaseModel):
    album_ids: list[int]
    group_id: int


# Bulk: associer plusieurs groupes à un album
class Album_GroupsBulkCreate(BaseModel):
    album_id: int
    group_ids: list[int]


# model Utilisateur_Album
class User_AlbumBase(BaseModel):
    user_id: int
    album_id: int


class User_AlbumCreate(User_AlbumBase):
    pass


class User_Album(User_AlbumBase):
    id: int = Field(primary_key=True)

    class Config:
        from_attributes = True


# Multi-sélection bulk : plusieurs utilisateurs vers un album (accès direct)
class User_AlbumBulkCreate(BaseModel):
    user_ids: list[int]
    album_id: int
