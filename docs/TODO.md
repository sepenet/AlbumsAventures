# TODO - AlbumsAventures

Ce fichier regroupe les tâches et le backlog principal du projet. Placez ici les tâches haute-priorité et leurs statuts.

> **Légende** : `[x]` terminé | `[ ]` à faire | `[~]` abandonné/non pertinent | `→ #N` dépend de la tâche N

---

## Frontend (hybride)

### UI/UX - Design

- [x] 010. Choisir stack frontend — Jinja2 + Tailwind + Alpine.js (variante hybride choisie)
- [x] 020. Scaffold projet frontend (templates Jinja2 et router d'exemple)
- [x] 030. Design moderne page de login avec gradient et card élégante
- [x] 040. Design moderne page d'accueil (index) avec grille d'albums responsive
- [x] 050. Implémenter dark mode fonctionnel avec localStorage
- [x] 060. Harmoniser le design entre toutes les pages (gradients, typographie, spacing)
- [x] 070. Nettoyer les URLs frontend (supprimer le prefix /fe_router)

### Authentification & Sécurité (Frontend)

- [x] 080. Stocker le token JWT dans un cookie HttpOnly sécurisé
- [x] 090. Implémenter la persistance de session (vérifier token au chargement)
- [x] 100. Ajouter page d'inscription (/signup) avec validation frontend
- [x] 110. Ajouter page "Mot de passe oublié" (/forgot-password)
- [x] 115. Page admin de validation des nouveaux utilisateurs (activer compte + attribuer rôle superuser)
- [x] 120. Implémenter le flux de réinitialisation de mot de passe (email + token)
- [x] 130. Ajouter protection CSRF sur les formulaires (login, signup)
- [x] 140. Implémenter le logout côté frontend (supprimer cookie + redirection)

### Pages & Fonctionnalités (Frontend)

- [~] 150. ~~Générer client API (OpenAPI -> types/clients)~~ — *Non pertinent : architecture Jinja2+Alpine.js côté serveur*
- [x] 160. Remplacer données mockées par appels réels CRUD (liste albums)
- [x] 170. Page détail d'un album (images + thumbnails avec lazy-loading)
- [x] 175. Ouverture de l'image en grand, possibilité de zoomer, navigation entre images
- [x] 180. Filtres par catégorie sur la page d'accueil (au-dessus du bandeau de recherche),  il ne faut afficher un bouton de catégorie que si cette catégorie est utilisée par un album affiché
- [x] 190. Page d'upload d'images/vidéos (avec uppy.io) → *dépend de #320*
- [x] 200. Page de partage d'album (génération lien + PIN) — *Modal de partage dans index.html + page shared_album.html + route /album/shared*
- [x] 210. Page de profil utilisateur (modifier infos, changer mot de passe)
- [x] 220. Navbar avec menu utilisateur (profil, déconnexion)
- [ ] 230. Gestion des erreurs 404 et 500 avec pages dédiées
- [x] 240. Notifications email (nouvel accès groupe/album, reset password) via SMTP Nuxit
- [x] 250. Page admin : gestion des accès (Utilisateurs ↔ Groupes, Albums ↔ Groupes, Utilisateurs <-> Albums) → `/admin/groups`
- [x] 251. Page principal des albums: en mode admin, possibilité d'affecter un ou plusieurs groupes ou utilisateurs.
- [x] 260. *(fusionné avec #250)* — Vue centrée sur le groupe pour gérer les 2 types de liens
- [x] 270. Page admin : gestion (CRUD) d'un groupe
- [x] 280. Page principal albums, affichage nombre utilisateurs non activé grace à une puce ronde rouge avec le nombre en blanc.

### Albums - CRUD (Frontend + Backend liés)

> Ces tâches frontend/backend sont couplées et doivent être implémentées ensemble.

| Frontend (UI) | Backend (API) | Description |
|---------------|---------------|-------------|
| [x] 280. Page formulaire création/édition album | [x] 285. Endpoints CRUD album de base | Formulaire admin + endpoints POST/PUT/DELETE |
| [x] 290. Upload images dans formulaire album | [x] 295. Endpoint upload images avec traitement | Upload via uppy.io + stockage + thumbnails |
| [x] 300. Affichage/suppression images existantes | [x] 305. Endpoint gestion images d'un album | Liste, suppression, réorganisation images |
| [x] 310. Sélection image couverture depuis album_detail | — | Clic sur vignette pour définir la couverture de l'album |

### Performance & Optimisation (Frontend)

- [x] 350. Lazy-loading des images dans la grille d'albums
- [x] 360. Pagination ou infinite scroll pour la liste d'albums
- [ ] 370. Optimiser les requêtes API (mise en cache, debounce sur recherche)
- [ ] 380. Compression et optimisation des images uploadées côté client

### Fiabilisation des uploads (réseau de mauvaise qualité)

> Contexte : sur réseau faible (3G, Wi-Fi instable), une coupure pendant l'upload XHR oblige à renvoyer le fichier depuis 0. Solution implémentée = protocole TUS (chunked + resumable) côté backend (`tuspyserver`) et frontend (`Uppy.Tus`).

- [x] 391. **[Backend]** Endpoint TUS resumable dans `backend/routers/be_resizer.py` (préfixe `/be_resizer/tus/`) — *implémenté avec `tuspyserver` (`create_tus_router`). Hooks `pre_create_dep` (validation `album_id` + droits `verify_album_access`) et `upload_complete_dep` (intégration via `_process_tus_uploaded_file` : déplacement vers le dossier album, génération thumbnail image/vidéo). Auth via cookie JWT (`get_current_user`). Dossier temporaire : `image.tus_files_dir` (hors `frontend/static`).*
- [x] 392. **[Frontend]** Plugin `Uppy.Tus` dans `frontend/templates/album_upload.html` — *`endpoint=/be_resizer/tus/`, `chunkSize=5MB`, `retryDelays=[0,1s,3s,5s,10s,20s]`, `removeFingerprintOnSuccess=true`, `withCredentials=true`, `limit=1`. `setMeta({album_id})` transmis dans la metadata TUS.*
- [ ] 393. **[Frontend]** Migrer Uppy v3.27 → v5.x. Breaking changes :
  - Plus de bundle UMD `uppy.min.js` : passer aux modules ESM (`@uppy/core`, `@uppy/dashboard`, `@uppy/tus`) via CDN ESM (`https://esm.sh/@uppy/...@5`) ou introduire un bundler (esbuild/vite) côté `frontend/static/`
  - `new Uppy.Uppy(...)` → `new Uppy(...)` importé de `@uppy/core`
  - Charger les locales via `@uppy/locales/lib/fr_FR` au lieu d'inliner les `strings`
  - Vérifier la CSP du `base.html` pour autoriser le nouveau CDN
- [ ] 394. **[Frontend]** Activer `@uppy/golden-retriever` pour reprendre les uploads après rechargement de page (à faire en même temps que #393, le plugin est dans le bundle UMD v3 mais bénéficie surtout des améliorations v5)
- [ ] 395. **[Backend]** Décider du sort de l'endpoint legacy `POST /be_resizer/upload_images/{album_id}` (XHR multipart) : à supprimer une fois TUS validé en production, ou à garder comme fallback temporaire

---

## Backend / API

### Infrastructure & Intégration

- [x] 400. Stabiliser API backend (routers be_*)
- [x] 410. Déplacer la configuration globale dans `utils/config.py`
- [x] 420. Monter les fichiers statiques via `app.mount('/static', StaticFiles(...))`
- [x] 430. Remplacer les données d'exemple dans `fe_router.py` par appels réels à `crud`
- [x] 440. Vérifier que toutes les routes CRUD albums/users/categories sont fonctionnelles

### Authentification & Sécurité (Backend)

- [x] 450. Endpoint reset password (génération token + email)
- [x] 455. Module email SMTP (utils/email.py) — fournisseur Nuxit
- [x] 460. Endpoint validation token reset password
- [~] 470. Rate limiting sur les endpoints sensibles (login, reset password, partage) — *Partage : implémenté (5 tentatives / 15 min). Login + forgot-password : implémentés (SEC-21). Reset-password (avec token) : non couvert mais le token est déjà à usage limité (10 min) → SEC-29.*
- [x] 480. **[FAIT]** Migrer les secrets vers Azure Key Vault ou variables d'environnement — *`utils/secret_store.py` + `utils/config.py` : SecretStore gère .env (dev) et Azure Key Vault (prod via KEY_VAULT_URL)* :
  - **Auth JWT** (`utils/config.py` → `auth_config`) :
    - `secret_key` — clé secrète JWT
    - `algorithm` — algorithme de hashage
    - `access_token_expire_minutes` — durée de vie du token
    - `cookie_name` — nom du cookie HTTP
  - **Base de données** (`utils/config.py` → `database_config`) :
    - `user`, `password`, `host`, `port`, `name` — credentials PostgreSQL
  - **Email / SMTP** (`utils/config.py` → `email_config`) :
    - `enabled` — activation envoi email
    - `smtp_host`, `smtp_port` — serveur SMTP
    - `smtp_user`, `smtp_password` — identifiants SMTP
    - `sender`, `sender_name` — expéditeur
  - Cookie CSRF `secure=True` en production (`csrf.py`)
- [x] 482. Configurer les URLs de production (`backend_api.base_url` et `password_reset.frontend_url` dans `utils/config.py`) via variables d'environnement
- [ ] 485. **[BUG]** Inclure `is_superuser` dans le token JWT et `get_current_user()` :
  - `create_access_token()` n'encode que `sub` et `id`, pas `is_superuser`
  - `get_current_user()` retourne seulement `email` et `id`
  - Impact : les vérifications `is_superuser` dans be_resizer.py sont toujours False
- [ ] 490. Implémenter refresh tokens (alternative aux tokens longue durée)

### Fonctionnalités Albums (Backend)

- [x] 320. Endpoint upload images avec stockage et génération thumbnails → *utilisé par #190, #290*
- [x] 325. Extraction métadonnées EXIF automatique à l'upload — *`img_get_exif_data()` dans `be_resizer.py` via ExifTool*
- [x] 330. Endpoint partage d'album (génération token JWT + PIN) → *`POST /be_album/create_share_token/{album_id}` implémenté*
- [x] 335. Endpoint validation partage (vérification PIN + rate limiting) → *`verify_share_token()` dans `be_auth.py` + `GET /be_album/shared` implémenté*
- [~] 340. Gestion des permissions (qui peut voir/modifier quel album) — *Tables UserAlbum/AlbumGroup/UserGroup + `verify_album_access()` dans be_resizer.py existent. Manque : vérification sur les endpoints GET/PATCH album.*

---

## Base de données

- [ ] 500. Valider le schéma PostgreSQL en production
- [~] 510. Ajouter indexes sur les colonnes fréquemment requêtées — *Index définis dans `models.py` via SQLAlchemy (email, nom, prénom, groupe). Valider en prod.*
- [ ] 520. Implémenter les migrations avec Alembic — *Aucun fichier Alembic. `drop_all/create_all` utilisé en dev Windows.*
- [~] 530. Ajouter contraintes de validation au niveau DB — *PK, FK, UNIQUE (email) définis. Contraintes métier absentes.*
- [ ] 540. Vérifier les cascades de suppression (user → albums → images)

---

## Tests & Qualité

- [~] 600. Tests unitaires backend (pytest) pour les endpoints critiques — *`tests/test_auth.py`, `test_albums.py`, `test_upload.py` existent. Manquent : partage, rate limiting, admin.*
- [~] 610. Tests d'intégration (login, création album, upload) — *Couverts partiellement dans les fichiers de tests existants.*
- [ ] 620. Tests frontend (si nécessaire, avec Playwright)
- [x] 625. Tests E2E partage d'album — *`tests/e2e/test_shared_album_ui.py` : formulaire PIN, mode lecture seule (pas de boutons admin), galerie Masonry, PhotoSwipe, vidéos*
- [ ] 630. Tests de sécurité (injection SQL, XSS, CSRF)
- [ ] 640. Tests de performance (load testing avec locust)
- [ ] 650. Pipeline CI: build + tests (lint, format, sécurité)

---

## Documentation

- [~] 700. Documenter variables d'environnement (API_URL, SECRET_KEY, DB credentials) — *`.env.example` présent avec toutes les clés. README à compléter.*
- [ ] 710. Guide de contribution (CONTRIBUTING.md)
- [~] 720. Documentation API avec Swagger/Redoc (déjà disponible via FastAPI) — *Disponible automatiquement à `/docs` via FastAPI.*
- [ ] 730. Guide d'installation et de démarrage rapide
- [~] 740. Documentation des conventions de code et architecture — *`docs/` contient GESTION_FORMATS.md, GESTION_IMAGES.md, GESTION_REPERTOIRES.md, Bulk-upload.md.*

---

## Déploiement & Production

- [ ] 800. Préparer build Tailwind pour production (npm + purge CSS inutilisé)
- [ ] 810. Configuration Caddy/Nginx + reverse-proxy
- [ ] 820. Setup Docker/Docker Compose pour faciliter déploiement
- [ ] 830. Configuration SSL/TLS pour HTTPS
- [ ] 840. Monitoring et logs (sentry, prometheus, grafana)
- [ ] 850. Backup automatique de la base de données
- [ ] 860. Plan de reprise après sinistre (disaster recovery)

---

## Améliorations futures (Nice to have)

- [ ] 900. Recherche full-text sur albums (titre, participants, tags)
- [ ] 910. Filtres avancés (par catégorie, date, participants)
- [ ] 920. Timeline chronologique des albums
- [ ] 930. Galerie en mode lightbox/carrousel amélioré
- [ ] 940. Commentaires sur les photos
- [ ] 950. Géolocalisation des albums (carte interactive)
- [ ] 960. Export d'albums (ZIP, PDF)
- [ ] 970. Intégration stockage cloud (S3, Azure Blob)
- [ ] 980. PWA (Progressive Web App) pour accès offline
- [ ] 990. Application mobile native (React Native, Flutter)
- [ ] 995. Génération automatique de tags IA sur les photos via GPT-4o mini Vision
  - Analyser chaque photo (thumbnail) à l'upload pour générer des tags (scène, activité, saison, météo, lieu...)
  - Coût négligeable : ~$0.05 pour 1 000 photos avec GPT-4o mini
  - Déclencher uniquement à l'upload (pas de retraitement du catalogue existant)
  - Stocker les tags générés dans le champ `tags` de l'album ou dans un champ dédié par photo
  - Intégration via Azure AI Foundry ou Azure OpenAI directement

---

## Sécurité & Performance — Audit fusionné (15-16 avril 2026)

> **Sources** : Audit manuel (15/04) + Audit CLI Copilot Claude Opus 4.6 (16/04)
>
> **Légende gravité** : 🔴 CRITIQUE | 🟠 ÉLEVÉ | 🟡 MOYEN | 🟢 BAS
>
> **Légende source** : `[MAN]` audit manuel | `[CLI]` audit CLI | `[MAN+CLI]` identifié par les deux

### 🔴 Vulnérabilités critiques

- [x] **SEC-01** 🔴 `[MAN]` **[PRIVILEGE ESCALATION]** `POST /be_auth/activate/{user_id}/` et `POST /be_auth/admin/{user_id}/` vérifient seulement `is_authenticated`, pas `is_superuser` → n'importe quel utilisateur connecté peut activer des comptes ou se promouvoir admin
  - *Fichier* : `backend/routers/be_auth.py` — fonctions `activate_user()` et `admin_user()`
  - *Correction* : ajouter vérification `is_superuser` via requête DB (comme dans `update_user_rights`)

- [x] **SEC-02** 🔴 `[MAN+CLI]` **[BROKEN ACCESS CONTROL]** `DELETE /be_auth/delete/{user_id}/` accessible à tout utilisateur authentifié — TODO laissé en commentaire dans le code
  - *Fichier* : `backend/routers/be_auth.py` — fonction `delete_user()`
  - *Correction* : vérifier `is_superuser` + interdire auto-suppression

- [x] **SEC-03** 🔴 `[MAN+CLI]` **[MASS ASSIGNMENT / PRIVILEGE ESCALATION]** `POST /be_auth/create/` est public (sans auth) et accepte `is_superuser: true` dans le corps JSON → n'importe qui peut créer un compte admin via API directe
  - *Fichier* : `backend/routers/be_auth.py` — ligne `def create_user()`
  - *Correction* : forcer `is_active=False` et `is_superuser=False` côté serveur, indépendamment du body reçu

- [x] **SEC-04** 🔴 `[MAN+CLI]` **[INFORMATION DISCLOSURE — TOKEN EN CLAIR DANS LES LOGS]** Le token de réinitialisation de mot de passe (JWT valide 10 min) est loggé en clair dans le fichier `logs/albums_aventures.log`
  - *Fichier* : `backend/routers/be_auth.py` ligne 710 — `logger.info(f"   {reset_url}")`
  - *Correction* : supprimer ce log en production, ou masquer le token (`...{reset_token[:8]}...`)

- [x] **SEC-05** 🔴 `[MAN+CLI]` **[BROKEN SECRET / PIN EXPOSÉ]** Le PIN de partage d'album est stocké **en clair dans le payload JWT** (base64 non chiffré). Quiconque a le token peut décoder le PIN sans connaître la clé secrète, ce qui annule sa valeur en tant que second facteur
  - *Fichier* : `backend/routers/be_auth.py` — `create_album_share_token()` et `verify_share_token()`
  - *Correction appliquée* : le PIN est hashé avec SHA-256 avant stockage dans le JWT, comparaison par hash lors de la validation

- [~] **SEC-06** 🔴 `[MAN+CLI]` **[RATE LIMITING CONTOURNABLE]** Le cache rate-limiting (`failed_attempts_cache`) est un `defaultdict` en mémoire du processus — réinitialisé à chaque redémarrage et non partagé entre workers (gunicorn multi-process = N × 5 tentatives possibles)
  - *Fichier* : `backend/routers/be_auth.py` — `failed_attempts_cache`
  - *Mitigation acceptée* : déploiement en mono-worker (`gunicorn -w 1 -k uvicorn.workers.UvicornWorker`) ou Uvicorn standalone — le cache mémoire est alors cohérent. Risque résiduel uniquement contre mots de passe triviaux ; PIN de partage statistiquement incassable (~31 000 ans même avec 4 workers).
  - *Action requise sur le serveur* : vérifier `AlbumsPhotos-BE.service` (systemd) — forcer `--workers 1` dans la commande `ExecStart` si Gunicorn multi-process. Si Uvicorn direct, rien à faire.
  - *Correction définitive ultérieure* (si trafic justifie multi-worker) : table PostgreSQL `rate_limit_attempts` (DB déjà présente) ou Redis

- [ ] **SEC-07** 🔴 `[CLI]` **[PATH TRAVERSAL — SUPPRESSION]** `filename` extrait de l'URL non sanitisé dans l'endpoint de suppression d'images → `../../etc/passwd` permettrait de supprimer des fichiers arbitraires
  - *Fichier* : `backend/routers/be_resizer.py` lignes 609-637
  - *Correction* : `os.path.basename(filename)` + vérifier absence de `..` dans le chemin résolu

### 🟠 Vulnérabilités élevées

- [ ] **SEC-10** 🟠 `[MAN+CLI]` **[INFORMATION DISCLOSURE]** `GET /be_user/get_all_users_info/` et `GET /be_user/get_user_info_by_email/{email}` retournent tous les profils (email, is_superuser, is_active) à tout utilisateur authentifié, sans vérification `is_superuser`
  - *Fichier* : `backend/routers/be_user.py`
  - *Correction* : limiter ces endpoints aux admins, ou n'exposer que les champs strictement nécessaires

- [ ] **SEC-11** 🟠 `[MAN+CLI]` **[INSECURE DIRECT OBJECT REFERENCE]** `GET /be_user/get_user_info_by_id/{user_id}` expose le profil de n'importe quel utilisateur à tout authentifié
  - *Fichier* : `backend/routers/be_user.py`
  - *Correction* : soit réserver aux admins, soit n'autoriser que `user_id == current_user.id`

- [ ] **SEC-12** 🟠 `[MAN+CLI]` **[COOKIES NON SÉCURISÉS EN PRODUCTION]** `secure=False` hardcodé sur le cookie JWT et le cookie CSRF — les cookies seront transmis en clair si HTTPS n'est pas forcé
  - *Fichiers* : `backend/routers/be_auth.py` ligne 535, `utils/csrf.py` ligne 43
  - *Correction* : lire `ENVIRONMENT` depuis les variables d'env, passer `secure=True` en production

- [ ] **SEC-13** 🟠 `[MAN+CLI]` **[PATH TRAVERSAL — UPLOAD]** `safe_filename = file.filename.replace(" ", "_")` ne sanitise pas `../`, `/`, chemins absolus ni caractères spéciaux — un fichier nommé `../../etc/cron.d/malicious` serait écrit hors du répertoire album
  - *Fichier* : `backend/routers/be_resizer.py` ligne 488
  - *Correction* : utiliser `os.path.basename(filename)` puis vérifier que le chemin final est bien sous `img_path` avec `os.path.realpath()`

- [ ] **SEC-14** 🟠 `[MAN+CLI]` **[VALIDATION EMAIL ABSENTE CÔTÉ BACKEND]** Format email validé uniquement par regex JS côté client — `UserBase.email` est un `str` simple sans `EmailStr` (pydantic-email-validator)
  - *Fichier* : `backend/db/schemas.py` — classe `UserBase`
  - *Correction* : ajouter `pydantic[email]` et utiliser `EmailStr` pour les champs email

- [x] **SEC-15** 🟠 `[MAN]` **[URL DE PARTAGE HARDCODÉE]** `share_url` générée avec `http://localhost:5003` en dur dans le code — les liens de partage seront invalides en production
  - *Fichier* : `backend/routers/be_album.py` ligne ~237
  - *Correction appliquée* : utilise `password_reset.frontend_url` depuis `config.py`

- [ ] **SEC-16** 🟠 `[MAN]` **[UTILISATEUR DÉSACTIVÉ PEUT UTILISER SON TOKEN]** `get_current_user()` vérifie la validité du JWT mais pas `user.is_active == True` — un compte désactivé avec un token encore valide reste opérationnel
  - *Fichier* : `backend/routers/be_auth.py` — `get_current_user()`
  - *Correction* : après décodage JWT, charger l'utilisateur depuis DB et vérifier `is_active`

- [ ] **SEC-17** 🟠 `[CLI]` **[BROKEN ACCESS CONTROL — PARTAGE ALBUM]** Tout utilisateur authentifié peut créer un lien de partage pour n'importe quel album, sans vérification d'accès
  - *Fichier* : `backend/routers/be_album.py` lignes 201-242
  - *Correction* : appeler `verify_album_access()` avant la création du token de partage

- [ ] **SEC-18** 🟠 `[CLI]` **[XSS DANS LES EMAILS HTML]** Variables insérées dans le contenu HTML des emails via f-string sans `html.escape()` → injection HTML/JS possible via nom d'utilisateur ou titre d'album
  - *Fichier* : `utils/email.py` lignes 108-131
  - *Correction* : `html.escape()` sur toutes les données utilisateur injectées dans le HTML

### 🟡 Vulnérabilités moyennes

- [ ] **SEC-20** 🟡 `[MAN]` **[ABSENCE DE HEADERS DE SÉCURITÉ HTTP]** Aucun middleware ne positionne les headers `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`
  - *Correction* : ajouter `starlette-middleware` ou middleware FastAPI custom avec ces headers

- [x] **SEC-21** 🟡 `[MAN]` **[PAS DE RATE LIMITING SUR LE LOGIN]** Endpoint `POST /be_auth/login` sans limitation — bruteforce illimité sur les mots de passe
  - *Fichier* : `backend/routers/be_auth.py`
  - *Correction appliquée* : `check_rate_limit` / `record_failed_attempt` / `clear_failed_attempts` ajoutés sur `/login` (clé `login:<email>`) et `/forgot-password` (clé `forgot:<email>`). 5 tentatives / 15 min, même logique que le partage album. Tentative enregistrée même si user inexistant (anti-énumération). Couvre aussi #470.

- [ ] **SEC-22** 🟡 `[CLI]` **[HASH PASSWORD EXPOSABLE]** Le schéma `User` peut exposer le hash du mot de passe dans les réponses API si utilisé comme `response_model`
  - *Fichier* : `backend/db/schemas.py` ligne 16
  - *Correction* : utiliser `UserAdmin` (sans password) comme `response_model` sur les endpoints

- [ ] **SEC-23** 🟡 `[CLI]` **[CORS PERMISSIF]** Configuration CORS avec origines, méthodes et headers trop larges (`allow_methods=["*"]`, `allow_headers=["*"]`) ; la liste `origins` n'est pas paramétrable par variable d'env (dev vs prod)
  - *Fichier* : `AlbumsAventures-BE.py` lignes 74-83
  - *Correction* : charger les origines depuis variables d'env, restreindre `allow_methods=["GET","POST","PUT","PATCH","DELETE"]` et headers stricts

- [ ] **SEC-24** 🟡 `[CLI]` **[CHEMINS SERVEUR EXPOSÉS]** Les réponses API contiennent des chemins absolus du serveur (ex. `/home/user/app/static/...`)
  - *Fichier* : `backend/routers/be_resizer.py` lignes 367-370
  - *Correction* : retourner uniquement l'URL relative

- [ ] **SEC-25** 🟡 `[CLI]` **[MDP NON HASHÉ DANS DONNÉES DE TEST]** Les mots de passe des utilisateurs de test sont stockés en clair dans le script de remplissage
  - *Fichier* : `backend/db/db_fill.py` ligne 11
  - *Correction* : utiliser `get_password_hash("fake")` pour tous les users de test

- [x] **SEC-26** 🟡 `[CLI]` **[CODE MORT — DOUBLE EXCEPT]** Double bloc `except JWTError` inaccessible dans `verify_share_token()` (avec un `return album_id` mort après un `raise`)
  - *Fichier* : `backend/routers/be_auth.py` lignes ~260-276
  - *Correction appliquée* : bloc inaccessible et `return` mort supprimés (commit `595474c`)

- [ ] **SEC-27** 🟠 `[MAN]` **[STATIC FILES PUBLICS — ACCÈS IMAGES SANS AUTH]** Les montages `StaticFiles` (`/images/`, `/thumbnails/`) sont publics et accessibles sans aucune authentification. Toute personne connaissant le pattern de nommage (`catégorie/date_titre_participants/fichier`) peut accéder directement à n'importe quelle image
  - *Fichiers* : `AlbumsAventures-BE.py` — `app.mount('/images', ...)` et `app.mount('/thumbnails', ...)`
  - *Correction* : remplacer les montages StaticFiles par des endpoints authentifiés (ex. `@router.get("/images/{path:path}")`) qui vérifient `get_current_user()` ou un token de partage valide avant de servir le fichier via `FileResponse`

- [ ] **SEC-28** 🟡 `[CLI]` **[VALIDATION DE CONTENU FICHIER ABSENTE]** `allowed_file()` vérifie seulement l'extension du nom — un fichier malveillant renommé `.jpg` est accepté
  - *Fichier* : `backend/routers/be_resizer.py` — `allowed_file()`
  - *Correction* : valider le magic number / MIME type réel avec `python-magic` ou `imghdr`

- [ ] **SEC-29** 🟡 `[CLI]` **[TOKEN RESET PASSWORD NON INVALIDÉ APRÈS USAGE]** Le token JWT de reset est valide jusqu'à expiration — s'il est intercepté, il peut être réutilisé plusieurs fois dans la fenêtre de 10 min
  - *Correction* : stocker en DB un flag `used=True` ou un `jti` (JWT ID) invalidé à la première utilisation

- [ ] **SEC-30** 🟡 `[CLI]` **[LOGS CONTENANT DES DONNÉES PERSONNELLES]** Emails utilisateurs loggés en clair dans les logs applicatifs (login, admin) — problème RGPD potentiel
  - *Correction* : hasher ou tronquer les emails dans les logs (`user@...` ou `sha256[:8]`)

- [ ] **SEC-31** 🟡 `[CLI]` **[VALIDATION MOT DE PASSE INSUFFISANTE]** Seulement 8 caractères minimum vérifiés — aucune règle de complexité (majuscule, chiffre, caractère spécial). Non vérifié dans `update_password()` (seulement dans reset et signup)
  - *Fichier* : `backend/routers/be_auth.py` — `update_password()` et `reset_password()`

### 🟢 Vulnérabilités basses

- [ ] **SEC-40** 🟢 `[CLI]` **[COOKIE JWT : PREFIX "Bearer " NON STANDARD]** La valeur du cookie est `"Bearer <token>"` (non standard pour un cookie) — fonctionne mais à normaliser
  - *Fichier* : `backend/routers/be_auth.py` — `login()` et `get_token_from_cookie_or_header()`

### 🟡 XSS — Templates Jinja2

- [ ] **XSS-01** 🟡 `[CLI]` **[FILENAME DANS ALPINE.JS SANS ÉCHAPPEMENT]** Un filename contenant `'` ou `"` casse le binding Alpine.js et peut injecter du code
  - *Fichier* : `frontend/templates/album_detail.html` lignes 260, 282, 296
  - *Correction* : échapper les filenames ou utiliser des data attributes HTML

- [ ] **XSS-02** 🟡 `[CLI]` **[innerHTML AVEC HTML DYNAMIQUE]** `innerHTML` utilisé avec du HTML construit dynamiquement — `escapeHtml()` présent mais pattern dangereux
  - *Fichier* : `frontend/templates/album_detail.html` ligne 473
  - *Correction* : continuer à utiliser `escapeHtml()`, ajouter CSP `script-src` restrictive

- [ ] **XSS-03** 🟡 `[CLI]` **[`| tojson | safe` DANS TEMPLATES]** `tojson` encode en JSON (mitigation partielle) mais `safe` désactive l'échappement Jinja2
  - *Fichiers* : `frontend/templates/index.html` lignes 308-309, `frontend/templates/profile.html` ligne 217
  - *Correction* : vérifier que toutes les données sont nettoyées côté serveur avant injection

---

## Performance — Audit CLI Copilot (16 avril 2026)

> **Source** : Audit CLI Copilot Claude Opus 4.6

### 🔴 Performance — Haute

- [ ] **PERF-01** 🔴 **[REQUÊTES N+1]** `get_albums_by_user` exécute 1 requête SQL par album dans une boucle
  - *Fichier* : `backend/routers/be_album.py` lignes 60-86
  - *Correction* : `filter(Album.id.in_(all_album_ids))` en une seule requête batch

- [ ] **PERF-02** 🔴 **[UPLOAD FICHIER ENTIER EN RAM]** `await file.read()` charge tout le fichier en mémoire (vidéos 500 MB+)
  - *Fichier* : `backend/routers/be_resizer.py` lignes 498-500
  - *Correction* : `shutil.copyfileobj` avec streaming par chunks

- [ ] **PERF-03** 🔴 **[PIL OUVERT PAR IMAGE À L'AFFICHAGE]** Lecture disque + EXIF par image pour chaque page view
  - *Fichier* : `frontend/routers/fe_router.py` lignes 964-974
  - *Correction* : cache dimensions/EXIF en BDD ou fichier JSON

- [ ] **PERF-04** 🔴 **[FRONTEND HTTP VERS LUI-MÊME]** Requêtes `httpx` vers `localhost:8003` = boucle HTTP interne au lieu d'appels directs
  - *Fichier* : `frontend/routers/fe_router.py` (partout)
  - *Correction* : appeler directement les fonctions CRUD Python au lieu de passer par HTTP

### 🟡 Performance — Moyenne

- [ ] **PERF-05** 🟡 **[PAS DE CONNECTION POOLING POSTGRESQL]** Pas de configuration de pool de connexions
  - *Fichier* : `backend/db/db_connect.py` lignes 33-34
  - *Correction* : `pool_size=10, max_overflow=20, pool_recycle=3600`

- [ ] **PERF-06** 🟡 **[EMAILS SMTP SYNCHRONES]** Envoi d'email bloquant dans les handlers de requête
  - *Fichier* : `backend/routers/be_group.py` lignes 88-98
  - *Correction* : utiliser `BackgroundTasks` de FastAPI

- [ ] **PERF-07** 🟡 **[PAS D'INDEX COMPOSITE]** Tables de jointure sans index composite sur les paires FK
  - *Fichier* : `backend/db/models.py` lignes 70-92
  - *Correction* : ajouter `UniqueConstraint` ou `Index` sur les paires FK

- [ ] **PERF-08** 🟡 **[THUMBNAILS SYNCHRONES]** Génération de thumbnails bloquante dans le handler de requête
  - *Fichier* : `backend/routers/be_resizer.py` lignes 294-329
  - *Correction* : `BackgroundTasks` de FastAPI ou Celery

### 🟢 Performance — Basse

- [ ] **PERF-09** 🟢 **[GET ALL USERS RETOURNE TOUT]** `get_all_users_info` retourne tous les champs de tous les utilisateurs
  - *Fichier* : `backend/db/crud.py` lignes 107-108
  - *Correction* : sélectionner uniquement les colonnes nécessaires

- [ ] **PERF-10** 🟢 **[PAS DE PAGINATION API]** Endpoints de liste sans `skip`/`limit`
  - *Fichiers* : `backend/routers/be_album.py` lignes 25-27, `backend/routers/be_user.py` lignes 23-28
  - *Correction* : ajouter paramètres `skip`/`limit` avec valeurs par défaut

---

## 📊 Résumé des audits fusionnés

| Priorité | Sécurité | XSS | Performance | Total |
|----------|----------|-----|-------------|-------|
| 🔴 CRITIQUE | 7 (5 corrigés, 1 mitigé) | — | 4 | 11 |
| 🟠 ÉLEVÉ | 9 (1 corrigé) | — | — | 9 |
| 🟡 MOYEN | 11 (2 corrigés) | 3 | 4 | 18 |
| 🟢 BAS | 1 | — | 2 | 3 |
| **Total** | **28** | **3** | **10** | **41** |

### 🎯 TOP 5 CORRECTIONS URGENTES
1. 🔴 SEC-07/13 — Path traversal suppression + upload → `os.path.basename()` partout
2. 🔴 SEC-03 — Création admin sans auth → forcer `is_superuser=False` *(corrigé)*
3. 🔴 SEC-05 — PIN en clair dans JWT → hasher le PIN *(corrigé)*
4. 🔴 SEC-02 + #485 — Suppression sans auth + `is_superuser` absent du JWT → contrôles d'autorisation *(SEC-02 corrigé, #485 en attente)*
5. 🔴 PERF-01/04 — N+1 queries + boucle HTTP interne → requête batch + appels directs

---

## Agent Qualité — Phase 2 (plan détaillé dans `docs/agent.md`)

> Construction d'un agent de dev/qualité combinant outillage standard (`ruff`, `black`, `pre-commit`), CI/CD GitHub Actions, et un script custom `quality_agent.py` pour vérifier les conventions spécifiques au projet (nommage français, préfixes `/be_`/`/fe_`, docstrings, `response_model`, couverture endpoints/tests).

### Étape 2.1 — Outillage : `pyproject.toml` + pre-commit

- [x] **AGT-2.1.1** Créer `pyproject.toml` (config `ruff`, `black`, `pytest`, `coverage`)
- [x] **AGT-2.1.2** Créer `.pre-commit-config.yaml` (hooks `ruff`, `black`, `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `mixed-line-ending`, `detect-private-key`)
- [x] **AGT-2.1.3** Ajouter `ruff`, `black`, `pre-commit`, `pytest-cov` dans `requirements.txt`
- [x] **AGT-2.1.4** Installer le hook (`pre-commit install`)
- [x] **AGT-2.1.5** Auto-fix global du projet (`ruff check . --fix --unsafe-fixes` + `black .`) — commit `6963ad4`
- [ ] **AGT-2.1.6** 🟢 Activer `detect-secrets` (créer `.secrets.baseline` puis décommenter dans `.pre-commit-config.yaml`)
- [ ] **AGT-2.1.7** 🟡 Réactiver progressivement les règles ruff temporairement ignorées dans `pyproject.toml` :
  - `E402` : imports pas en haut de fichier (`be_auth.py`, `be_resizer.py`, `conftest.py`)
  - `B904` : `raise X from err` manquant (`be_auth.py`, `be_resizer.py`)
  - `B007` : variable de boucle non utilisée (`be_resizer.py`)
  - `E712` : `== False` vs `not x` (`be_auth.py` ligne 459)

### Étape 2.2 — CI/CD GitHub Actions

- [ ] **AGT-2.2.1** 🔴 Créer `.github/workflows/test.yml` :
  - Job `lint` : `ruff check .` + `black --check .`
  - Job `test` (avec `needs: [lint]`) : `pytest --cov=backend --cov=utils`
  - Déclenchement sur `push` (master/main) et `pull_request`
- [ ] **AGT-2.2.2** 🔴 Modifier `.github/workflows/deploy.yml` : ajouter `needs: [test]` au job `deploy` pour bloquer le déploiement si les tests échouent
- [ ] **AGT-2.2.3** 🟢 Ajouter un badge CI dans le `README.md`

### Étape 2.3 — Script custom `scripts/quality_agent.py`

- [ ] **AGT-2.3.1** 🟡 Créer `scripts/quality_agent.py` avec utilisation de `ast` pour scanner le code, et implémenter les 5 vérifications :
  1. **Conventions françaises** : détecter les noms de fonctions/variables en anglais (liste de mots-clés `get_`, `delete_`, `update_`, `user`, `album`, etc.)
  2. **Préfixes endpoints** : `/be_*` pour `backend/routers/`, `/fe_*` pour `frontend/routers/`
  3. **Docstrings** : présentes sur toutes les fonctions décorées par `@router.xxx`
  4. **`response_model`** : défini sur tous les endpoints GET/POST
  5. **Couverture endpoints/tests** : croiser endpoints (extraits via AST) avec noms de tests dans `tests/`, lister les endpoints sans test
- [ ] **AGT-2.3.2** 🟡 Output : rapport markdown (stdout + fichier `quality_report.md`)
- [ ] **AGT-2.3.3** 🟢 Intégrer le script comme étape dans `.github/workflows/test.yml` (warning ou bloquant selon sévérité)

### Étape 2.4 — Instructions Copilot enrichies

- [x] **AGT-2.4.1** Réécrire `.github/copilot-instructions.md` avec conventions complètes (10 sections)
- [x] **AGT-2.4.2** Extraire guidelines UI dans `docs/GUIDELINES_UI.md`
- [x] **AGT-2.4.3** Nettoyer doublons dans `README.md` (Option B : single source of truth)

### Étape 2.5 — Consolidation des tests + Makefile

- [ ] **AGT-2.5.1** 🟡 Déplacer/consolider les tests éparpillés vers `tests/` :
  - `run_test_login.py` → intégrer dans `tests/test_auth.py` ou supprimer (doublon)
  - `test_frontend_login.py` → `tests/test_frontend_login.py`
  - `test_share_album.py` → `tests/test_share_album.py` (à convertir en pytest, fixe le `F841` restant)
  - `Scripts/test_formatter.py` → `tests/test_formatter.py` (sinon perdu si recréation venv)
- [ ] **AGT-2.5.2** 🟡 Créer un `Makefile` avec cibles :
  - `make install` — `pip install -r requirements.txt && pre-commit install`
  - `make test` — `pytest --cov=backend --cov=utils -v`
  - `make lint` — `ruff check . && black --check .`
  - `make format` — `ruff check --fix . && black .`
  - `make quality` — `python scripts/quality_agent.py`
- [ ] **AGT-2.5.3** 🟢 Créer un `make.ps1` PowerShell équivalent (Windows sans `make` natif)

---

## Notes

- **Priorité haute** : Finaliser CRUD albums (#280-305) + upload images (#320)
- **Priorité sécurité CRITIQUE** : SEC-01, SEC-02, SEC-03, SEC-04, SEC-05 à corriger avant mise en production
- **Priorité moyenne** : Partage d'albums (#330-335, #200) + gestion permissions (#340)
- Utiliser GitHub Issues / Projects pour transformer ces items en tickets assignables
- Ce fichier est évolutif; pour le suivi fin utiliser des issues ou un project board
