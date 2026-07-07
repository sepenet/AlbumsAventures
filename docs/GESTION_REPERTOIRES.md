# Gestion des répertoires 

## répertoires utilisés

- backend/ : tout ce qui est relatif au backend
- frontend/ : tout ce qui est relatif au frontend
- utils/ : utilitaires communs backend/frontend, (helpers, fonctions communes, wrappers, scripts de build, etc.).
- docs/ : documentation du projet
- tests/ : tests unitaires et d'intégration (pas encore implémenté)

## backend

`backend` tout ce qui est relatif au backend

`backend\db` tous les fichiers relatifs à la gestion de la base de données, définitions des schémas et modèles, des opérations CRUD, de la connexion…,  
`backend\albums` contient tous les fichiers relatifs à la gestion des répertoires des albums
`backend\routers` contient tous les fichiers des endpoints API

## Frontend

`frontend` tout ce qui est relatif au frontend

`frontend\routers` contient tous les fichiers des routes
`frontend\static` contient tous les fichiers static genre css, js, et les images et videos
`frontend\templates` contient tous les fichiers html jinja2 des pages web

## docs

Tous les fichiers de documentions.
`docs/TODO.md` : Tâches et backlog principal du projet catégorisé par frontend, backend, tests, documentation, déploiement.

## utils

Tous les fichiers communs entre le backend et le frontend.
`utils/config.py` : Configuration globale (chemins images, dimensions thumbnails, ...)


## Images et Vidéos

### Arborescence des répertoires

- Tous les répertoires sont stockés dans `frontend\static`.
- 2 sous-répertoires sont créés :
  - images : pour stocker les images et vidéos taille originale
  - thumbnails : pour stocker les images et vidéos des vignettes.
- Dans chacun des sous répertoires la structure sera la suivante :
  - Un sous-répertoire par catégorie.
  - Dans chaque répertoire de catégorie les répertoires des albums

Exemple : 
```
static/
├── images/
│   └── Ski-de-Rando/
│       └── 2025-12-01_Roche-Parstire_Sabina-Janick-Stéphane/
└── thumbnails/
    └── Ski-de-Rando/
        └── 2025-12-01_Roche-Parstire_Sabina-Janick-Stéphane/
```

### Règles de nommage des répertoires

- Le nom d'un répertoire ne peut pas avoir d'espace.
- Les caractères accentués sont autorisés.
- Les caractères spéciaux ne sont pas autorisés.
- Le nom du répertoire correspondant à un album est constitué de section :
  - Première section : YYYY-MM-DD, objectif lister les répertoires de façon chronologique.
  - Deuxième section : Titre
  - Troisième section : les participants
- les sections sont séparés par des "_"
- pour le format à l'intérieur de chaque section confère le fichier GESTION_FORMATS.md

