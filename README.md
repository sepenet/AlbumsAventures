# AlbumsAventures

> **Note développeur** : les conventions de codage, règles de sécurité et patterns sont décrits dans [`.github/copilot-instructions.md`](.github/copilot-instructions.md). Ce README est dédié au contexte fonctionnel et au démarrage.

## Description

Application de gestion d'albums photos et vidéos.
Système multi-utilisateurs avec groupes et catégories.

Titre et sous-titre par la partie aventure de l'application :

- Aventures planquées dans les cartes
  - Parce que ton canapé n'a pas besoin de toi tous les week-ends !!!

## Objectifs de l'application

- Gestion d'albums photo et vidéos.
- Les albums, photos et vidéos ne sont pas en libre accès. L'application utilise un mécanisme d'authentification.
- Multi-utilisateurs et groupes d'albums.
- Relations **many-to-many** entre :
  - utilisateurs et groupes
  - groupes et albums
  - utilisateurs et albums
- Ces relations définissent quels albums sont accessibles par quels utilisateurs.
- Toutes les images et vidéos d'un album sont contenues dans 2 répertoires :
  - 1 répertoire pour les images et vidéos originales
  - 1 répertoire pour les miniatures (thumbnails)
- Les répertoires des albums sont organisés hiérarchiquement par catégories.
- Le nom du répertoire d'un album suit une nomenclature précise : `Année-Mois-jour_titre_participants`. Voir [`docs/GESTION_FORMATS.md`](docs/GESTION_FORMATS.md).
- Le format des titres et participants dans le nom du répertoire est normalisé. Voir [`docs/GESTION_FORMATS.md`](docs/GESTION_FORMATS.md).
- Partage temporaire d'albums via lien public sécurisé par token JWT et code PIN :
  - **Token JWT** avec expiration 1h par défaut
  - **Code PIN** : 6 caractères alphanumériques (A-Z, 0-9)
  - **Rate limiting** : max 5 tentatives en 15 minutes (protection brute-force)

## Pages HTML

### Style et composants UI

Voir [`docs/GUIDELINES_UI.md`](docs/GUIDELINES_UI.md) pour la palette Tailwind, les composants et les patterns responsives.

### Page principale d'albums

- Barre de recherche permettant de rechercher un titre, un participant, une date, un tag, un lieu.
- Affichage en grille : 4 colonnes sur tablette/PC, 1 colonne sur téléphone.
- Albums classés par ordre décroissant de date (le plus récent en haut à gauche, remplissage par ligne de gauche à droite).
- Pour chaque album sont affichés :
  - image de couverture
  - titre
  - date
  - participants
  - lieu (caché)
  - tags (cachés)
  - liste d'icônes :
    - télécharger toutes les photos
    - uploader de nouvelles photos
    - éditer les informations (super-utilisateur)
    - partage temporaire (super-utilisateur)
    - génération des vignettes (super-utilisateur)
    - effacer l'album (super-utilisateur)
    - associer l'album à un ou plusieurs groupes ou utilisateurs (super-utilisateur) : modal avec 2 onglets (utilisateurs / albums), multisélection possible

## Dependencies & setup

- Python 3.12
- Virtual environment Python : `python3 -m venv AlbumsAventuresBE`
- Install : `pip install -r requirements.txt`

## Démarrage de l'application

- `AlbumsAventures-BE.py` : point d'entrée FastAPI avec lifespan events.

### Comportement selon l'environnement

- **Windows (dev)** :
  - SQLite avec reset DB au démarrage
  - Remplissage données de test automatique
  - Suppression DB à l'arrêt
- **Linux/Mac (prod)** :
  - PostgreSQL persistante
  - Pas de reset automatique

## Technologies utilisées

### Backend

- **Framework** : FastAPI + uvicorn
- **Base de données** : PostgreSQL (production), SQLite (développement Windows / tests)
- **ORM** : SQLAlchemy + SQLModel avec `Mapped` types
- **Authentification** : JWT en cookie HttpOnly via python-jose
- **Sécurité** : passlib (hash mots de passe)
- **Images** : Pillow + PyExifTool pour les métadonnées EXIF, OpenCV pour les vignettes vidéo
- **Secrets** : Azure Key Vault (prod) / `.env` (dev)

### Frontend (variant hybride)

- **Templates** : Jinja2 pour le rendu HTML côté serveur
- **Styles** : Tailwind CSS — CDN acceptable en prototype ; en production, utiliser la toolchain npm (`tailwindcss`) et copier le CSS buildé dans `static/` pour purger les classes inutilisées
- **Interactivité** : Alpine.js
- **Static files** : servis via `StaticFiles` de FastAPI
- **Upload images + vidéos** : uppy.io via CDN

## Modèle de données

- **User** : utilisateurs avec email unique, rôles (`is_active`, `is_superuser`)
- **Album** : titre, description, date, participants, location, tags, image_cover
- **Category** : catégories d'albums (relation many-to-one avec Album)
- **Group** : groupes d'utilisateurs avec nom unique
- **UserGroup** : table de liaison users ↔ groups (many-to-many)
- **AlbumGroup** : table de liaison albums ↔ groups (many-to-many)

## Gestion des images

Tout est décrit dans [`docs/GESTION_IMAGES.md`](docs/GESTION_IMAGES.md).

## Structure du projet

Tout est décrit dans [`docs/GESTION_REPERTOIRES.md`](docs/GESTION_REPERTOIRES.md).

### Cas de mise à jour des informations d'un album

Mettre à jour les informations d'un album peut avoir un impact sur les répertoires de stockage des thumbnails et images. Liste des cas :

1. Changement de la catégorie.
2. Changement du titre → renommage des répertoires contenant les thumbnails et les images.
3. Changement de la date → renommage des répertoires contenant les thumbnails et les images.
4. Changement de la liste des participants → renommage des répertoires contenant les thumbnails et les images.

- Pour le cas 1 : déplacer les répertoires dans le répertoire de la nouvelle catégorie sélectionnée.
- Pour les cas 2, 3 ou 4 : renommer les répertoires en suivant les règles de nommage décrites dans [`docs/GESTION_FORMATS.md`](docs/GESTION_FORMATS.md).
- Pour le cas 1 combiné avec 2, 3 ou 4 : renommer **et** déplacer les répertoires dans le répertoire de la nouvelle catégorie sélectionnée.

## Documentation complémentaire

| Sujet | Fichier |
|---|---|
| Conventions de codage et règles pour Copilot | [`.github/copilot-instructions.md`](.github/copilot-instructions.md) |
| Plan agent qualité | [`docs/agent.md`](docs/agent.md) |
| Guidelines UI Tailwind | [`docs/GUIDELINES_UI.md`](docs/GUIDELINES_UI.md) |
| Format des titres, dates, participants | [`docs/GESTION_FORMATS.md`](docs/GESTION_FORMATS.md) |
| Pipeline images / vidéos / thumbnails | [`docs/GESTION_IMAGES.md`](docs/GESTION_IMAGES.md) |
| Structure des répertoires d'albums | [`docs/GESTION_REPERTOIRES.md`](docs/GESTION_REPERTOIRES.md) |
| Upload en masse | [`docs/Bulk-upload.md`](docs/Bulk-upload.md) |
| Backlog et TODO | [`docs/TODO.md`](docs/TODO.md) |
# AlbumsAventures

## Description

C'est une application pour gérer des albums photos et vidéos.
Système de gestion multi-utilisateurs avec groupes et catégories.

titre et sous-titre par la partie aventure de l'application

- Aventures planquées dans les cartes
  - Parce que ton canapé n’a pas besoin de toi tous les week-ends !!!


## Objectifs de l'application

- C'est une application de gestion d'albums photo et vidéos.
- Les albums, photos et vidéos ne sont pas en libre accès. L'application utilise un mécanisme d'authentification.
- L'application gère plusieurs utilisateurs.
- L'application gère des groupes d'albums.
- La relation entre utilisateurs et groupes est une relation **many to many**.
- La relation entre groupes et albums est une relation **many to many**.
- La relation entre utilisateurs et albums est une relation **many to many**.
- Ces relations permettent de définir quels albums sont accessibles par quels utilisateurs.
- Toutes les images et vidéos d'un album sont contenues dans 2 répertoires.
  - 1 répertoire pour les images et vidéos originales.
  - 1 répertoire pour les miniatures (thumbnails) des images et vidéos.
- Les répertoires des albums sont organisés hierarchiquement par catégories.
- le nom du repertoire d'un album suit une nomenclature précise: Année-Mois-jour_titre_participants. confère la doc  "GESTION_FORMATS.md". pour plus de détails.
- Le format des titres et participants dans le nom du repertoire d'un album est normalisé. Confère la doc "GESTION_FORMATS.md".
- Le partage temporaire d'albums via un lien public sécurisé par token JWT et code PIN est implémenté.
  - **Token JWT** avec expiration 1h par défaut
  - **Code PIN** : 6 caractères alphanumériques (A-Z, 0-9)
  - **Rate limiting** : Max 5 tentatives en 15 minutes (protection bruteforce)

## descriptions des pages html

### Guidelines de style UI

Toutes les pages héritent de `base.html` qui fournit le style de base. Voici les conventions Tailwind à suivre pour garantir la cohérence visuelle :

#### Structure de page
| Élément | Classes Tailwind |
|---------|-----------------|
| Conteneur page | `py-6` ou `py-8` |
| Titre page | `text-3xl font-bold bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-transparent mb-2` |
| Sous-titre/description | `text-gray-600 dark:text-gray-400` |

#### Composants
| Élément | Classes Tailwind |
|---------|-----------------|
| Cartes | `bg-white dark:bg-gray-800 rounded-lg shadow-md` |
| Cartes avec bordure | `bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700` |
| Boutons primaires | `bg-sky-600 hover:bg-sky-700 text-white px-4 py-2 rounded-lg transition-colors` |
| Boutons secondaires | `bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700` |
| Boutons danger | `text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700` |
| Inputs/Recherche | `bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:ring-2 focus:ring-sky-500 focus:border-transparent` |

#### Grilles responsives
| Type | Classes Tailwind |
|------|-----------------|
| Albums (4 cols) | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4` |
| Formulaires (2 cols) | `grid grid-cols-1 md:grid-cols-2 gap-4` |

#### Tableaux (mobile-friendly)
| Élément | Classes Tailwind |
|---------|-----------------|
| Conteneur scroll | `overflow-x-auto` (permet le scroll horizontal sur mobile) |
| Table | `min-w-full divide-y divide-gray-200 dark:divide-gray-700` |
| Header | `bg-gray-50 dark:bg-gray-900` |
| Cells | `px-6 py-4 whitespace-nowrap` |

#### Badges/Tags
| Type | Classes Tailwind |
|------|-----------------|
| Succès | `bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300` |
| Attente | `bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-300` |
| Admin | `bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-300` |

#### Icônes d'action
| Action | Couleur hover |
|--------|--------------|
| Télécharger | `hover:text-sky-600 dark:hover:text-sky-400` |
| Uploader/Ajouter | `hover:text-green-600 dark:hover:text-green-400` |
| Éditer | `hover:text-blue-600 dark:hover:text-blue-400` |
| Partager | `hover:text-green-600 dark:hover:text-green-400` |
| Vignettes | `hover:text-purple-600 dark:hover:text-purple-400` |
| Supprimer | `hover:text-red-600 dark:hover:text-red-400` |

### la page principal d'albums

- la page principal des albums contient une barre de recherche qui permet de rechercher un titre, un participant, une date, un tag, un lieu.
- sur cette page principal, pour une écran de tablette ou de PC, en dessous de la barre de recherche, les albums seront affichés avec une grid de 4 colonnes, qui se reduira à 1 pour un téléphone.
- les albums seront classés par ordre décroissant de date, sur grand écran : le plus récent en haut à gauche et le plus vieux en bas à droite, avec un remplissage par ligne des colonnes de gauche à droite. Sur une téléphone de haut en bas
- Pour chaque album sera affiché dans l'ordre :
  - l'image de couverture de l'album
  - le titre
  - la date
  - les participants
  - le lieu (caché)
  - les tags (caché)
  - un liste d'icone :
    - telecharger toutes les photos de l'album.
    - telecharger de nouvelles photos dans l'album.
    - editer les informations de l'album: super-utilisateur
    - partage temporaire : super-utilisateur
    - generation des vignettes : super-utilisateur
    - effacer l'album : super-utilisateur
    - associer l'album à un ou plusieurs groupes ou utilisateurs : super-utilisateur. le click sur l'icone ouvre un modal avec 2 onglets : liste des utilisateurs , liste des albums, la multiselection sera possible.



## Dependencies & setup

- Python 3.1x
- Virtual environment Python: python3 -m venv AlbumsAventuresBE
- Install: pip install -r requirements.txt

## Démarrage de l'application

- `AlbumsAventures-BE.py` : Point d'entrée FastAPI avec lifespan events

### Comportement selon l'environnement

- **Windows (dev)** :
  - SQLite avec reset DB au démarrage
  - Remplissage données de test automatique
  - Suppression DB à l'arrêt
- **Linux/Mac (prod)** :
  - PostgreSQL persistante
  - Pas de reset automatique

## Technologies utilisées

### backend

- **Framework** : FastAPI avec uvicorn
- **Base de données** : PostgreSQL (production), SQLite (développement Windows)
- **ORM** : SQLAlchemy + SQLModel avec Mapped types

### Frontend (variant hybride)

- **Templates** : Jinja2 pour le rendu HTML côté serveur
- **Styles** : Tailwind CSS pour prototype, CDN est acceptable; pour la production, utilisez la toolchain npm (tailwindcss) et copiez le CSS buildé dans `static/` pour purger les classes inutilisées.
- **Interactivité** : Alpine.js pour des interactions légères côté client
- **Static files** : Servis via StaticFiles de FastAPI
- **upload images + videos** : uppy.io via CDN
- **Authentification** : JWT bearer token via python-jose
- **Images** : Pillow + PyExifTool pour métadonnées EXIF
- **Sécurité** : passlib pour le hachage des mots de passe

### Modèle de données

- **User** : Utilisateurs avec email unique, roles (is_active, is_superuser)
- **Album** : Titre, description, date, participants, location, tags, image_cover
- **Category** : Catégories d'albums (relation many-to-one avec Album)
- **Group** : Groupes d'utilisateurs avec nom unique
- **UserGroup** : Table de liaison users ↔ groups (many-to-many)
- **AlbumGroup** : Table de liaison albums ↔ groups (many-to-many)

### Sécurité et authentification

- Tous les endpoints protégés par `Depends(get_current_user)`
- Tokens JWT pour l'authentification
- Hachage des mots de passe avec passlib
- CORS configuré pour `http://localhost:5003`

### Gestion des images

Tous est décrit dans le fichier `docs/GESTION_IMAGES.md`

## Conventions de codage

- **Langage** : Tout en français (noms de variables, endpoints, commentaires)
- **Nommage** : snake_case pour fonctions et variables
- tous ce qui est relatif au frontend est dans le dossier frontend/
- tous ce qui est relatif au backend est dans le dossier backend/
- tous ce qui est relatif aux configurations et utilitaires communs est dans le dossier utils/
- **Endpoints routers** : Préfixés `/be_` (ex: `/be_album`, `/be_user`) pour le backend, `/fe_` pour le frontend
- **Modèles** : Utiliser SQLAlchemy avec `Mapped` types et `mapped_column`
- **Relations** : Utiliser `relationship` avec `back_populates`
- **Réponses API** : Utiliser `response_model` avec les schemas Pydantic
- **Variables/constantes** : Charger depuis `config.py` disponible dans le repertoire `utils`
- **Structure des dossiers** : confère la section "Architecture" plus bas.
- **gestion des erreurs et exceptions pour les appels API** : Utiliser les HTTPException de FastAPI avec codes d'erreurs appropriés (400, 401, 403, 404, 500, etc.)
- **Commentaires et docstrings** : Utiliser des docstrings pour toutes les fonctions et classes; commenter les sections complexes du code.
- **gestions des erreurs pour le code python** : Utiliser des blocs try/except pour capturer et gérer les exceptions potentielles.
- **gestion des logs** : Utiliser le module logging de Python pour enregistrer les événements importants, erreurs et informations de débogage. La configuration centralisée du logging se trouve dans `utils/config.py` (classe `logging_config`). Les logs sont écrits dans `logs/albums_aventures.log` avec rotation automatique.
- **separation backend/frontend** : garder une séparation claire entre le code backend (FastAPI, logique métier, accès aux données) et le code frontend (templates Jinja2, static files, interactivité client). Toutes les manipulations de données doivent être effectuées via des appels API au backend. Toutes les manipulations des albums, images et vidéos, repertoires associés doivent être effectuées via des endpoints API définis dans les routers backend.
- **frontend dynamique** : Utiliser Jinja2 pour le rendu dynamique côté serveur. Éviter le code JavaScript complexe côté client; privilégier Alpine.js pour des interactions légères.
- **frontend remplacable** : Concevoir le frontend de manière à pouvoir être remplacé facilement par une SPA ou une application mobile à l'avenir. Toute la logique métier et l'accès aux données doivent résider dans le backend, exposé via des endpoints API RESTful.
- **frontend responsive** : Utiliser les classes utilitaires de Tailwind CSS pour créer un design responsive qui fonctionne bien sur les appareils mobiles et de bureau.
- **gitignore** : le fichier existant à la racine doit être toujours utilisé et mis à jour, aucun fichier dans des sous répertoires ne sera créé.
- **fonction** : l'usage de fonctions pour éviter la duplication de code est à systématiser.
- **commits réguliers** : effectuer des commits fréquents après chaque fonctionnalité ou correction testée et fonctionnelle. Cela permet de revenir facilement à un état stable en cas de problème et évite de perdre du travail.

## Structure du projet

Tous est décrit dans le fichier `docs/GESTION_REPERTOIRES.md`

### cas mise à jour des informations d'un album

Mettre à jour les informations d'un album peut avoir un impact sur les répertoires de stockages des thumbnails et images.
liste des différents cas:

1. Changement de la catégorie.
2. Changement du titre -> le nom des répertoires contenant les thumbnails et des images.
3. Changement de la date -> le nom des répertoires contenant les thumbnails et des images.
4. Changement de la liste des participants -> le nom des répertoires contenant les thumbnails et des images.

Pour 1 il faut déplacer les répertoires dans le répertoire de la nouvelle catégorie sélectionnée.
Pour 2, 3 ou 4 il faut renommer les répertoires en suivant les regles de nomage décrit dans GESTION_FORMATS.md

Pour 1 + 2 ou 3 ou 4 il faut renommer et déplacer les répertoires dans le répertoire de la nouvelle catégorie sélectionnée.
