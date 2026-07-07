# Phase 2 : Agent de Dev/Qualité

L'objectif global de cette phase est de mettre en place un **agent de qualité** composé de plusieurs couches complémentaires : outils automatiques de vérification, intégration continue (CI), script personnalisé adapté aux conventions du projet, et instructions enrichies pour Copilot. Ensemble, ils garantissent que le code reste cohérent, sûr et testé à chaque modification.

---

## Étape 2.1 — Outillage : `pyproject.toml` + pre-commit

### Objectif

Mettre en place les **outils automatiques** qui vérifient et nettoient le code Python à chaque modification, pour garantir qu'il reste propre, lisible et cohérent.

### Les outils

#### `ruff` — Le linter

Un **linter** = outil qui analyse le code pour détecter des problèmes **sans l'exécuter**.

`ruff` détecte :
- **Imports inutilisés** : `import os` mais jamais utilisé
- **Variables non utilisées** : `x = 5` jamais lu
- **Erreurs de syntaxe** ou patterns suspects (ex: `if x == None` au lieu de `if x is None`)
- **Code mort** : conditions toujours vraies/fausses
- **Mauvaises pratiques** : `except:` sans préciser l'exception
- **Ordre des imports** incorrect

**Pourquoi `ruff` ?** C'est le linter Python le plus rapide (écrit en Rust, ~100x plus rapide que `flake8` ou `pylint`). Il remplace à lui seul `flake8`, `isort`, `pyupgrade` et plus.

**Exemple** :
```python
import os, sys           # ❌ ruff: deux imports sur une ligne
from typing import List  # ❌ ruff: List non utilisé

def login(email = None): # ⚠️ ruff: utilise Optional[str]
    if email == None:    # ❌ ruff: utilise `is None`
        pass
```

#### `black` — Le formateur

Un **formateur** = outil qui réécrit le code avec un **style uniforme** (espaces, indentation, retours à la ligne). `black` n'a quasi pas d'options : il impose **un seul style**, ce qui élimine les débats de style.

**Exemple avant `black`** :
```python
def create_album(  title:str,date:str  ,participants = [] ):
    return {'title':title,
        'date':date,'participants':participants}
```

**Après `black`** :
```python
def create_album(title: str, date: str, participants=[]):
    return {"title": title, "date": date, "participants": participants}
```

**Différence avec `ruff`** : `ruff` détecte des **erreurs** (qualité), `black` corrige le **style** (mise en forme). Ils sont complémentaires.

#### `pre-commit` — L'orchestrateur

Un système de **hooks Git** qui déclenche automatiquement des outils **avant chaque commit**.

**Comment ça marche** :
1. `git commit` est lancé
2. `pre-commit` intercepte le commit
3. Il lance ruff, black, etc. sur les fichiers modifiés
4. Si un outil détecte un problème → le commit est **bloqué**
5. Si black a reformaté du code → `git add` puis commit à nouveau

**Conséquence** : impossible de commiter du code mal formaté ou avec des erreurs basiques.

Le fichier `.pre-commit-config.yaml` liste les hooks à exécuter :
- `ruff` → vérifier le code
- `black` → formater
- `detect-secrets` → empêcher de commiter accidentellement des mots de passe ou clés API
- `trailing-whitespace` → enlever les espaces en fin de ligne
- `end-of-file-fixer` → garantir un retour à la ligne en fin de fichier

#### `pytest-cov` — La couverture de tests

Une extension de `pytest` qui mesure **quel pourcentage du code est testé**.

**Exemple de rapport** :
```
Name                              Stmts   Miss  Cover
-----------------------------------------------------
backend/routers/be_auth.py         320    180    44%
backend/routers/be_album.py        180     90    50%
backend/routers/be_group.py        150    150     0%   ❌ aucun test
-----------------------------------------------------
TOTAL                             1500   1200    20%
```

#### `pyproject.toml` — Le fichier de config central

C'est le **standard moderne** pour configurer un projet Python. Au lieu d'avoir 5 fichiers (`.flake8`, `setup.cfg`, `pytest.ini`, `mypy.ini`, etc.), tout est dans un seul `pyproject.toml`.

**Exemple de contenu** :
```toml
[tool.ruff]
line-length = 120
select = ["E", "W", "F", "I"]  # quelles règles activer

[tool.black]
line-length = 120
target-version = ["py312"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short --cov=backend --cov=utils"
```

### Workflow

```
Tu écris du code
       ↓
"git commit"
       ↓
pre-commit s'active
       ↓
   ┌───┴───┬─────────┬──────────────┐
   ↓       ↓         ↓              ↓
 ruff    black   detect-secrets  trailing-ws
(check)  (fix)   (check)         (fix)
   ↓       ↓         ↓              ↓
   └───┬───┴─────────┴──────────────┘
       ↓
   Tout OK ? → commit accepté ✅
   Problème ? → commit bloqué ❌
```

### Actions concrètes

- Créer `pyproject.toml` avec config :
  - `ruff` (lint)
  - `black` (format)
  - `pytest`
- Créer `.pre-commit-config.yaml` avec hooks :
  - `ruff`
  - `black`
  - `detect-secrets`
  - `trailing-whitespace`
- Ajouter dans `requirements.txt` :
  - `ruff`
  - `black`
  - `pre-commit`
  - `pytest-cov`

---

## Étape 2.2 — CI/CD GitHub Actions *(parallèle avec 2.1)*

### Objectif

Garantir que **chaque push et chaque pull request** déclenche automatiquement les vérifications qualité et l'exécution des tests sur les serveurs GitHub. C'est une **double sécurité** au cas où quelqu'un aurait contourné les hooks locaux (`git commit --no-verify`).

### Concept : CI/CD

- **CI** (Continuous Integration) : à chaque modification du code, on lance automatiquement les tests pour s'assurer que rien n'est cassé.
- **CD** (Continuous Deployment) : si les tests passent, on déploie automatiquement.

GitHub Actions exécute tout cela sur les serveurs GitHub, dans des machines virtuelles éphémères, à chaque push.

### Pourquoi c'est important pour AlbumsAventures

Aujourd'hui, le workflow `deploy.yml` déploie **sans aucun test préalable**. Si du code cassé est poussé sur `master`, il part directement en production. La CI résout ce problème.

### Comment ça fonctionne

Un fichier YAML `.github/workflows/test.yml` décrit les étapes :

```yaml
name: Tests

on:
  push:
    branches: [master, main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff black
      - run: ruff check .
      - run: black --check .

  test:
    needs: [lint]   # ne lance les tests que si le lint passe
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest --cov=backend --cov=utils
```

À chaque push, GitHub :
1. Crée une VM Ubuntu
2. Installe Python et les dépendances
3. Lance ruff + black (job `lint`)
4. Si OK, lance pytest (job `test`)
5. Affiche un ✅ ou ❌ sur le commit / la PR

### Lien avec le déploiement

Le workflow `deploy.yml` actuel est modifié pour **dépendre du job `test`** :

```yaml
jobs:
  deploy:
    needs: [test]   # n'exécute le déploiement que si les tests passent
    runs-on: ubuntu-latest
    steps:
      - ...
```

Si les tests échouent → **pas de déploiement**. Le code cassé ne peut plus arriver en production.

### Actions concrètes

- Créer `.github/workflows/test.yml` : lint → tests avec coverage sur push/PR.
- Modifier `.github/workflows/deploy.yml` : ajouter `needs: [test]` pour bloquer le deploy si les tests échouent.

---

## Étape 2.3 — Script `scripts/quality_agent.py` — le cœur de l'agent

### Objectif

Créer un **agent personnalisé** qui vérifie les **conventions spécifiques au projet AlbumsAventures**, que `ruff` et `black` ne peuvent pas vérifier (ils sont génériques).

### Pourquoi un script custom ?

Les outils standards (`ruff`, `black`) ne connaissent pas les règles **propres au projet**, comme :
- Les noms de variables doivent être en français
- Les endpoints doivent commencer par `/be_` ou `/fe_`
- Les routers backend doivent avoir un `response_model` Pydantic
- Chaque endpoint devrait avoir au moins un test associé

Le script `quality_agent.py` comble ce manque.

### Comment ça fonctionne — `ast`

`ast` (Abstract Syntax Tree) est un module standard Python qui permet de **lire le code Python comme une structure de données**, sans l'exécuter.

**Exemple** : pour vérifier que toutes les fonctions ont une docstring :

```python
import ast

with open("backend/routers/be_album.py") as f:
    tree = ast.parse(f.read())

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        docstring = ast.get_docstring(node)
        if not docstring:
            print(f"❌ Fonction `{node.name}` (ligne {node.lineno}) sans docstring")
```

C'est rapide, fiable, et ne nécessite **aucun LLM**.

### Les 5 vérifications

1. **Conventions françaises**
   Détecter les noms de fonctions/variables en anglais (`get_user`, `delete_album`...) avec une liste de mots-clés anglais courants.

2. **Préfixes `/be_` et `/fe_` sur les endpoints**
   Lire les décorateurs `@router.get("/...")`, `@router.post("/...")` et vérifier le préfixe selon le dossier (`backend/` → `/be_`, `frontend/` → `/fe_`).

3. **Docstrings sur les fonctions publiques des routers**
   Toute fonction décorée par `@router.xxx` doit avoir une docstring expliquant ce qu'elle fait.

4. **`response_model` défini sur les endpoints GET/POST**
   Vérifier que le décorateur contient `response_model=...` pour garantir une réponse typée Pydantic.

5. **Rapport de couverture des tests**
   Croiser la liste des endpoints (extraits des routers) avec les noms de tests dans `tests/` pour lister ceux qui n'ont aucun test.

### Format de sortie

Un rapport Markdown structuré, par exemple :

```markdown
# Rapport Quality Agent — 2026-04-21

## ❌ Endpoints sans docstring (3)
- `backend/routers/be_album.py:45` → `update_album`
- `backend/routers/be_group.py:12` → `list_groups`
- ...

## ⚠️ Endpoints sans response_model (5)
- ...

## 📊 Couverture endpoints/tests : 23/67 (34%)
Endpoints sans test :
- POST /be_group/create
- DELETE /be_group/{id}
- ...
```

### Intégration

- **Local** : `python scripts/quality_agent.py` ou via le `Makefile` (`make quality`)
- **CI** : ajouté comme step dans `.github/workflows/test.yml` — bloque la PR si des violations critiques sont détectées

### Actions concrètes

Créer `scripts/quality_agent.py` qui utilise `ast` pour scanner le code et vérifier :

1. Conventions françaises (noms de fonctions/variables).
2. Préfixes `/be_` et `/fe_` sur les endpoints.
3. Docstrings présentes sur toutes les fonctions publiques des routers.
4. `response_model` défini sur les endpoints GET/POST.
5. Rapport de couverture : liste les endpoints sans test correspondant.

**Output** : rapport markdown (stdout ou fichier).
**Intégration** : ajouté comme step dans la CI.

---

## Étape 2.4 — Instructions Copilot enrichies

### Objectif

Aider GitHub Copilot (et tout autre assistant IA) à **générer du code conforme** aux conventions du projet **dès la première suggestion**, sans qu'on ait à corriger systématiquement.

### Le fichier `.github/copilot-instructions.md`

C'est un fichier spécial **lu automatiquement** par GitHub Copilot dans VS Code à chaque interaction. Tout son contenu est ajouté en contexte aux requêtes envoyées au modèle.

**État actuel** : le fichier ne contient que 3 lignes pointant vers `docs/README.md`. C'est insuffisant — Copilot ne lit pas spontanément les documents externes à chaque requête.

### Ce qu'on va y mettre

1. **Conventions de codage complètes** (extraites du `README.md`) :
   - Tout en français (variables, endpoints, commentaires)
   - `snake_case` pour fonctions et variables
   - Endpoints préfixés `/be_` (backend) ou `/fe_` (frontend)
   - Modèles SQLAlchemy avec `Mapped` types et `mapped_column`
   - Réponses API avec `response_model` Pydantic

2. **Patterns de code à suivre** :
   - Comment écrire un nouveau test (utiliser les fixtures `client`, `auth_headers`, etc.)
   - Comment ajouter un nouvel endpoint (structure des routers existants)
   - Comment gérer les erreurs (HTTPException avec codes appropriés)

3. **Règles de sécurité spécifiques** :
   - Tous les endpoints protégés par `Depends(get_current_user)`
   - Rate limiting via `check_rate_limit()` / `record_failed_attempt()`
   - Validation systématique de `is_active` et `is_superuser`

4. **Références aux docs** :
   - Mentionner explicitement `GESTION_FORMATS.md`, `GESTION_IMAGES.md`, `GESTION_REPERTOIRES.md`
   - Indiquer quand consulter chacun

### Bénéfice

Quand on demande à Copilot d'ajouter une fonctionnalité, il :
- Génère du code en français
- Utilise les bons préfixes d'endpoints
- Ajoute automatiquement les `response_model`
- Inclut la dépendance `get_current_user`
- Suit les patterns existants

→ moins de retouches, code plus cohérent.

### Actions concrètes

- Réécrire `.github/copilot-instructions.md` avec :
  - Les conventions complètes du projet.
  - Les patterns de code à suivre.
  - Les références aux fichiers de documentation (`GESTION_FORMATS.md`, `GESTION_IMAGES.md`, etc.).

---

## Étape 2.5 — Consolidation des tests *(dépend de 2.1)*

### Objectif

Regrouper **tous les tests dans un seul endroit** (`tests/`) pour qu'ils soient découverts automatiquement par pytest et exécutés en CI, et automatiser les commandes courantes via un `Makefile`.

### Le problème actuel

Les tests sont éparpillés à plusieurs endroits :
- `tests/` → les tests pytest officiels (couverture ~10%)
- `run_test_login.py` (racine) → script standalone, **non lancé par pytest**
- `test_frontend_login.py` (racine) → test pytest mais hors dossier `tests/`
- `test_share_album.py` (racine) → script de test manuel avec `requests`, **non lancé par pytest**
- `Scripts/test_formatter.py` → test isolé dans le dossier de venv

**Conséquences** :
- La CI ne lance qu'une partie des tests
- Difficile de savoir lesquels sont à jour
- `Scripts/` est généré par le venv, donc le test sera **perdu** si on recrée l'environnement

### Le `Makefile`

Un `Makefile` est un fichier qui définit des **commandes raccourcies** (cibles) pour automatiser les tâches courantes. Au lieu de retenir :
```bash
ruff check . && black --check . && python scripts/quality_agent.py
```
On tape simplement :
```bash
make quality
```

**Exemple de Makefile pour le projet** :
```makefile
.PHONY: test lint format quality install

install:
	pip install -r requirements.txt
	pre-commit install

test:
	pytest --cov=backend --cov=utils -v

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

quality:
	python scripts/quality_agent.py
```

**Note Windows** : `make` n'est pas natif sur Windows. Il existe deux solutions :
- Installer `make` via `choco install make` ou WSL
- Créer en parallèle un `make.ps1` PowerShell équivalent

### Actions concrètes

- Déplacer les tests éparpillés vers `tests/` :
  - `run_test_login.py` → intégrer dans `tests/test_auth.py` ou supprimer (doublon)
  - `test_frontend_login.py` → `tests/test_frontend_login.py`
  - `test_share_album.py` → `tests/test_share_album.py` (à convertir en pytest)
  - `Scripts/test_formatter.py` → `tests/test_formatter.py`
- Créer un `Makefile` avec les commandes :
  - `make test` — lance tous les tests avec coverage
  - `make lint` — vérifie le code (ruff + black)
  - `make format` — corrige automatiquement le formatage
  - `make quality` — lance le script `quality_agent.py`
# Phase 2 : Agent de Dev/Qualité

## Étape 2.1 — Outillage : `pyproject.toml` + pre-commit

- Créer `pyproject.toml` avec config :
  - `ruff` (lint)
  - `black` (format)
  - `pytest`
- Créer `.pre-commit-config.yaml` avec hooks :
  - `ruff`
  - `black`
  - `detect-secrets`
  - `trailing-whitespace`
- Ajouter dans `requirements.txt` :
  - `ruff`
  - `black`
  - `pre-commit`
  - `pytest-cov`

## Étape 2.2 — CI/CD GitHub Actions *(parallèle avec 2.1)*

- Créer `.github/workflows/test.yml` : lint → tests avec coverage sur push/PR.
- Modifier `.github/workflows/deploy.yml` : ajouter `needs: [test]` pour bloquer le deploy si les tests échouent.

## Étape 2.3 — Script `scripts/quality_agent.py` — le cœur de l'agent

Un script Python CLI qui utilise `ast` pour scanner le code et vérifier :

1. Conventions françaises (noms de fonctions/variables).
2. Préfixes `/be_` et `/fe_` sur les endpoints.
3. Docstrings présentes sur toutes les fonctions publiques des routers.
4. `response_model` défini sur les endpoints GET/POST.
5. Rapport de couverture : liste les endpoints sans test correspondant.

**Output** : rapport markdown (stdout ou fichier).

**Intégration** : ajouté comme step dans la CI.

## Étape 2.4 — Instructions Copilot enrichies

- Réécrire `.github/copilot-instructions.md` avec :
  - Les conventions complètes du projet.
  - Les patterns de code à suivre.
  - Les références aux fichiers de documentation (`GESTION_FORMATS.md`, `GESTION_IMAGES.md`, etc.).

## Étape 2.5 — Consolidation des tests *(dépend de 2.1)*

- Déplacer les tests éparpillés vers `tests/` :
  - `run_test_login.py`
  - `test_share_album.py`
  - `Scripts/test_formatter.py`
- Créer un `Makefile` avec les commandes :
  - `make test`
  - `make lint`
  - `make format`
  - `make quality`
