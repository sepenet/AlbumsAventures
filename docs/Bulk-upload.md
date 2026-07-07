# Bulk Upload - Import massif d'albums

## Objectif

Permettre la création massive d'albums avec upload de photos via un fichier JSON de configuration.

---

## Approches possibles

### Option 1 : Fichier centralisé (recommandé)

Un seul fichier `bulk_import.json` à la racine du projet ou dans un répertoire dédié.

| Avantages | Inconvénients |
|-----------|---------------|
| Vue globale de l'import | Fichier potentiellement volumineux |
| Validation unique | Modification centralisée requise |
| Cohérence des données garantie | |
| Versionnable facilement (Git) | |

**Cas d'usage :** Import initial massif, migration de données, synchronisation entre environnements.

### Option 2 : Fichier par album

Un fichier `album.json` dans chaque répertoire source de photos.

| Avantages | Inconvénients |
|-----------|---------------|
| Autonomie par album | Pas de vue globale |
| Préparation distribuée | Validation multiple nécessaire |
| Modification locale facile | Risque d'incohérence entre albums |

**Cas d'usage :** Import progressif, préparation par différentes personnes.

### Option 3 : Hybride

Fichier centralisé avec possibilité de surcharge par des fichiers locaux `album.json`.

---

## Structure JSON proposée

### Fichier centralisé : `bulk_import.json`

```json
{
  "$schema": "./schemas/bulk_import_schema.json",
  "version": "1.0",
  "import_date": "2026-01-26",
  "options": {
    "generate_thumbnails": true,
    "resize_originals": false,
    "skip_duplicates": true,
    "dry_run": false
  },
  "categories": [
    { "name": "Ski-de-Rando" },
    { "name": "Randonnée" },
    { "name": "VTT" }
  ],
  "groups_to_create": [
    { "name": "famille", "description": "Albums accessibles à la famille" },
    { "name": "amis-ski", "description": "Groupe des amis de ski" }
  ],
  "albums": [
    {
      "title": "Roche Parstire",
      "description": "Sortie ski de rando avec vue sur le Mont Blanc",
      "category": "Ski-de-Rando",
      "date": "2025-12-01",
      "participants": "Sabina, Janick, Stéphane",
      "location": "Alpes, France",
      "tags": "ski, montagne, hiver",
      "image_cover": "DSC_0042.jpg",
      "source_folder": "C:/Photos/2025-12-01_Roche-Parstire",
      "groups": ["famille", "amis-ski"]
    },
    {
      "title": "Tour du Mont Blanc",
      "description": "Randonnée de 7 jours autour du massif",
      "category": "Randonnée",
      "date": "2025-07-15",
      "participants": "Sabina, Stéphane",
      "location": "Alpes, France-Italie-Suisse",
      "tags": "randonnée, montagne, été, trek",
      "image_cover": "IMG_1234.jpg",
      "source_folder": "C:/Photos/2025-07-TMB",
      "groups": ["famille"]
    }
  ]
}
```

### Fichier par album : `album.json`

À placer dans chaque répertoire source (ex: `C:/Photos/2025-12-01_Roche-Parstire/album.json`)

```json
{
  "$schema": "../schemas/album_schema.json",
  "title": "Roche Parstire",
  "description": "Sortie ski de rando avec vue sur le Mont Blanc",
  "category": "Ski-de-Rando",
  "date": "2025-12-01",
  "participants": "Sabina, Janick, Stéphane",
  "location": "Alpes, France",
  "tags": "ski, montagne, hiver",
  "image_cover": "DSC_0042.jpg",
  "groups": ["famille", "amis-ski"]
}
```

---

## Correspondance avec le modèle de données

| Champ JSON | Modèle `Album` | Type | Obligatoire | Remarques |
|------------|----------------|------|-------------|-----------|
| `title` | `title` | string | ✅ | Max 50 caractères |
| `description` | `description` | string | ❌ | |
| `category` | → `category_id` | string | ✅ | Résolu vers l'ID de la catégorie |
| `date` | `date` | date | ✅ | Format YYYY-MM-DD |
| `participants` | `participants` | string | ❌ | Max 512 caractères |
| `location` | `location` | string | ❌ | Max 512 caractères |
| `tags` | `tags` | string | ❌ | Max 512 caractères |
| `image_cover` | `image_cover` | string | ❌ | Nom du fichier de couverture |
| `source_folder` | - | string | ✅ | Chemin local des photos sources |
| `groups` | → `AlbumGroup` | array | ❌ | Noms des groupes à associer |

---

## Options de traitement

| Option | Type | Défaut | Description |
|--------|------|--------|-------------|
| `generate_thumbnails` | bool | `true` | Générer les vignettes automatiquement |
| `resize_originals` | bool | `false` | Redimensionner les images originales |
| `skip_duplicates` | bool | `true` | Ignorer les fichiers déjà présents |
| `dry_run` | bool | `false` | Simulation sans modification réelle |
| `overwrite_existing` | bool | `false` | Écraser les albums existants (même titre+date) |

---

## Workflow d'import

```
┌─────────────────────────────────────────────────────────────┐
│                    1. VALIDATION                            │
├─────────────────────────────────────────────────────────────┤
│  • Valider le JSON contre le schéma                         │
│  • Vérifier l'existence des source_folder                   │
│  • Vérifier que les catégories existent ou sont à créer     │
│  • Vérifier que les groupes existent ou sont à créer        │
│  • Détecter les doublons potentiels (titre + date)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    2. PRÉPARATION                           │
├─────────────────────────────────────────────────────────────┤
│  • Créer les catégories manquantes                          │
│  • Créer les groupes manquants                              │
│  • Résoudre les category_id et group_id                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    3. CRÉATION ALBUMS                       │
├─────────────────────────────────────────────────────────────┤
│  Pour chaque album :                                        │
│  • Créer l'entrée en base de données                        │
│  • Créer les répertoires (images/ et thumbnails/)           │
│  • Associer l'album aux groupes                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    4. UPLOAD PHOTOS                         │
├─────────────────────────────────────────────────────────────┤
│  Pour chaque album :                                        │
│  • Copier les fichiers depuis source_folder                 │
│  • Générer les thumbnails si option activée                 │
│  • Définir l'image de couverture                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    5. RAPPORT                               │
├─────────────────────────────────────────────────────────────┤
│  • Nombre d'albums créés                                    │
│  • Nombre de photos importées                               │
│  • Erreurs rencontrées                                      │
│  • Temps d'exécution                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implémentation proposée

### 1. Schéma JSON de validation

Créer `schemas/bulk_import_schema.json` pour la validation automatique.

### 2. Script Python CLI

```bash
# Simulation (dry-run)
python bulk_import.py --config bulk_import.json --dry-run

# Import réel
python bulk_import.py --config bulk_import.json

# Import avec options spécifiques
python bulk_import.py --config bulk_import.json --no-thumbnails --verbose
```

### 3. Endpoint API (optionnel)

```
POST /api/albums/bulk-import
Content-Type: application/json
Body: { ... contenu du JSON ... }
```

---

## Gestion des erreurs

| Erreur | Comportement |
|--------|--------------|
| Catégorie inexistante | Créer si dans `categories`, sinon erreur |
| Groupe inexistant | Créer si dans `groups_to_create`, sinon erreur |
| `source_folder` introuvable | Erreur, album ignoré |
| Album doublon (titre+date) | Ignorer ou écraser selon option |
| Fichier image corrompu | Log warning, continuer |
| Espace disque insuffisant | Arrêt de l'import |

---

## Exemple de rapport d'import

```
═══════════════════════════════════════════════════════════════
                    RAPPORT D'IMPORT BULK
═══════════════════════════════════════════════════════════════
Date d'exécution : 2026-01-26 14:30:00
Fichier config   : bulk_import.json
Mode             : RÉEL (dry_run=false)

RÉSUMÉ
───────────────────────────────────────────────────────────────
Catégories créées     : 2 / 2
Groupes créés         : 1 / 2 (1 existait déjà)
Albums créés          : 15 / 15
Photos importées      : 847
Thumbnails générés    : 847
Erreurs               : 0

DÉTAIL PAR ALBUM
───────────────────────────────────────────────────────────────
✅ Roche Parstire (2025-12-01) - 42 photos
✅ Tour du Mont Blanc (2025-07-15) - 156 photos
✅ VTT Ardèche (2025-06-10) - 38 photos
...

Temps d'exécution : 4m 32s
═══════════════════════════════════════════════════════════════
```

---

## Prochaines étapes

- [ ] Valider la structure JSON proposée
- [ ] Choisir l'approche (centralisée vs par album)
- [ ] Créer le schéma JSON de validation
- [ ] Implémenter le script Python de traitement
- [ ] (Optionnel) Créer l'endpoint API
- [ ] Écrire les tests unitaires
