from fastapi import APIRouter, Depends, HTTPException

from ..db import crud, schemas

# from sqlalchemy.orm import Session
from ..db.db_connect import db_dependency
from .be_auth import get_current_user

router = APIRouter(prefix="/be_user", tags=["backend_user"], dependencies=[Depends(get_current_user)])


##################################################################
# User section
# create utilisateur
@router.post("/create_user/", response_model=schemas.UserAdmin)
def create_user(user: schemas.UserCreate, db: db_dependency):
    # check if the user already exists by his/her email
    db_user = crud.get_user_info_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email exit déjà")
    return crud.create_user(db=db, user=user)


# get all users info
@router.get("/get_all_users_info/", response_model=list[schemas.UserAdmin])
def get_all_users_info(db: db_dependency):
    db_users = crud.get_all_users_info(db)
    if db_users is None:
        raise HTTPException(status_code=404, detail="Aucun utilisateur trouvé")
    return db_users


# get user by email
@router.get("/get_user_info_by_email/{user_email}", response_model=schemas.UserAdmin)
def get_user_info_by_email(user_email: str, db: db_dependency):
    db_user = crud.get_user_info_by_email(db, email=user_email)
    if db_user is None:
        raise HTTPException(status_code=404, detail="L'utilisateur n'existe pas")
    return db_user


# get user info by id
@router.get("/get_user_info_by_id/{user_id}", response_model=list[schemas.User_Album])
def get_user_info_by_id(user_id: int, db: db_dependency):
    db_user = crud.get_user_info_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="L'utilisateur n'existe pas")
    return db_user


# get user profile by id (Tâche 210)
@router.get("/get_user_profile/{user_id}", response_model=schemas.UserAdmin)
def get_user_profile(user_id: int, db: db_dependency):
    """Récupère le profil complet d'un utilisateur pour la page profil"""
    db_user = crud.get_user_info_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="L'utilisateur n'existe pas")
    return db_user


##################################################################
# user album section
# create user album link
@router.post("/create_user_album/", response_model=schemas.User_Album)
def create_user_album(user_album: schemas.User_AlbumCreate, db: db_dependency):
    # on verifie si l'utilisateur est déjà lié à l'album
    userid_albumid_link = crud.get_usersid_albumid_link(db, user_album.user_id, user_album.album_id)
    if userid_albumid_link:
        raise HTTPException(status_code=404, detail="L'utilisateur est déjà lié à l'album")
    # on crée le lien entre l'utilisateur et l'album
    return crud.create_userid_albumid_link(db, user_album)
