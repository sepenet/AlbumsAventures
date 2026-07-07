# Migrations SQL manuelles

Ce projet n'utilise pas Alembic. Les fichiers `.sql` de ce dossier sont des
migrations **manuelles**, à appliquer explicitement et après approbation sur une
base de données réelle.

## Contexte environnement

- **Développement (Windows / SQLite) et tests** : les tables sont créées
  automatiquement par `Base.metadata.create_all()` au démarrage. Aucune action
  manuelle requise.
- **Production (PostgreSQL)** : `create_all()` n'est **pas** exécuté au
  démarrage. Toute nouvelle table doit être créée explicitement via la migration
  correspondante.

## Migrations

| Fichier | Objet créé | Prérequis de déploiement |
|---|---|---|
| `0001_rate_limit_entries.sql` | Table `rate_limit_entries` | **Oui — bloquant** |
| `0002_image_processing_status.sql` | Table `image_processing_status` | **Oui — bloquant pour le suivi de traitement** |

### 0001 — `rate_limit_entries` (rate limiting durable, SEC-06)

Le rate limiting durable (`utils/rate_limit.py`, modèle
`backend/db/models.py::RateLimitEntry`) lit et écrit dans la table
`rate_limit_entries`.

> ⚠️ **Prérequis de déploiement bloquant.** Tant que cette table n'existe pas en
> production, **chaque** tentative de login, de mot de passe oublié et de
> vérification de PIN de partage échouera (accès à une table absente). La
> migration **doit** être appliquée **avant le premier démarrage** de la version
> intégrant Phase 1 en production.

Application manuelle (après approbation d'un opérateur autorisé) :

```bash
psql "$DATABASE_URL" -f backend/db/migrations/0001_rate_limit_entries.sql
```

Rollback :

```sql
DROP TABLE IF EXISTS rate_limit_entries;
```

Ne pas appliquer automatiquement à une base non-dev : l'exécution sur une base de
production est validée puis lancée manuellement (aucune opération DB automatique
ou destructive en production).

### 0002 — `image_processing_status` (statut durable post-upload, UPL-01)

Le pipeline d'upload TUS (`backend/routers/be_resizer.py`, modèle
`backend/db/models.py::ImageProcessingStatus`) persiste l'état de traitement de
chaque fichier (déplacement + génération de vignette) dans la table
`image_processing_status`. Le traitement s'exécute dans un pool de threads borné
APRÈS le renvoi du `204` au client.

> ⚠️ **Prérequis de déploiement bloquant (pour le suivi de traitement).** Sans
> cette table en production, la génération de vignette continue de fonctionner,
> mais le statut par fichier n'est plus persisté : l'endpoint
> `GET /be_resizer/processing_status/{album_id}` échoue (table absente) et l'UI
> ne peut plus signaler à l'utilisateur les vignettes en cours ou en échec. Un
> redémarrage du process pendant un traitement ne laisse alors aucune trace
> durable. Appliquer cette migration **avant le premier démarrage** de la
> version intégrant Phase 2 en production.

Application manuelle (après approbation d'un opérateur autorisé) :

```bash
psql "$DATABASE_URL" -f backend/db/migrations/0002_image_processing_status.sql
```

Rollback :

```sql
DROP TABLE IF EXISTS image_processing_status;
```

Ne pas appliquer automatiquement à une base non-dev.
