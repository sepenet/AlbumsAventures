# Gestion des images

- **Stockage** : `static/images/` et `static/thumbnails/`
- **Dimensions thumbnails** : configure dans `utils\config.py`
- **EXIF** : extraction métadonnées EXIF (date de prise, etc.)
- endpoint API pour le redimensionnement et l'extraction des métadonnées : `backend/routers/be_resizer.py`