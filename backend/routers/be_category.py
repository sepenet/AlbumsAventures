from fastapi import APIRouter, Depends, HTTPException

from ..db import crud, schemas

# from sqlalchemy.orm import Session
from ..db.db_connect import db_dependency
from .be_auth import get_current_user, require_superuser

router = APIRouter(prefix="/be_category", tags=["backend_category"], dependencies=[Depends(get_current_user)])


##################################################################
# category section
# get all categories
@router.get("/get_all_categories/", response_model=list[schemas.Category])
def get_all_categories(db: db_dependency):
    """
    Fonction pour récupérer toutes les catégories.
    """
    categories = crud.get_all_categories(db)
    if not categories:
        raise HTTPException(status_code=404, detail="Aucune catégorie trouvée")
    return categories


# get category_id info by category
@router.get("/get_category_id_by_category/{category}", response_model=schemas.Category)
def get_category_id_by_category(category: str, db: db_dependency):
    category = crud.get_category_id_by_category(db, category=category)
    if category is None:
        raise HTTPException(status_code=404, detail="La catégorie n'existe pas")
    return category


# créer une nouvelle catégorie
# Réservé aux superusers (parité avec l'ancien gate Jinja require_superuser).
@router.post("/create_category/", response_model=schemas.Category, dependencies=[Depends(require_superuser)])
def create_category(db: db_dependency, category: schemas.CategoryCreate):
    """
    Fonction pour créer une nouvelle catégorie.
    """
    # Vérification si la catégorie existe déjà
    existing_category = crud.get_category_id_by_category(db, category=category.category)
    if existing_category:
        raise HTTPException(status_code=400, detail="La catégorie existe déjà")
    return crud.create_category(db, category)
