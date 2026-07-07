-- ============================================================================
-- Migration 0002 — Statut durable de traitement post-upload (UPL-01)
-- ============================================================================
--
-- ⚠️  APPROBATION REQUISE AVANT APPLICATION EN BASE RÉELLE ⚠️
--
-- Cette migration crée la table `image_processing_status` utilisée par le
-- pipeline d'upload TUS (voir backend/routers/be_resizer.py et le modèle
-- backend/db/models.py::ImageProcessingStatus).
--
-- Contexte :
--   • En développement Windows/SQLite et dans les tests, la table est créée
--     automatiquement par SQLAlchemy `Base.metadata.create_all()`.
--   • En production PostgreSQL, `create_all()` n'est PAS exécuté au démarrage.
--     Cette table doit donc être créée explicitement.
--
-- Ce projet n'utilise PAS Alembic : ce fichier .sql est fourni comme migration
-- manuelle. NE PAS l'appliquer automatiquement à une base non-dev. L'exécution
-- sur une base de production doit être validée puis lancée manuellement par un
-- opérateur autorisé.
--
-- Sans cette table en production, la génération de vignette continue de
-- fonctionner mais le statut par fichier n'est plus persisté : l'endpoint
-- `GET /be_resizer/processing_status/{album_id}` échouera (table absente) et
-- l'UI ne pourra plus signaler les vignettes en échec.
-- ============================================================================

CREATE TABLE IF NOT EXISTS image_processing_status (
    id            SERIAL PRIMARY KEY,
    album_id      INTEGER NOT NULL REFERENCES albums (id),
    filename      VARCHAR NOT NULL,
    media_type    VARCHAR NOT NULL DEFAULT 'unknown',
    status        VARCHAR NOT NULL DEFAULT 'pending',
    detail        VARCHAR,
    created_at    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    updated_at    DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    CONSTRAINT uq_ips_album_filename UNIQUE (album_id, filename)
);

CREATE INDEX IF NOT EXISTS ix_image_processing_status_album_id ON image_processing_status (album_id);
CREATE INDEX IF NOT EXISTS ix_image_processing_status_filename ON image_processing_status (filename);
CREATE INDEX IF NOT EXISTS ix_image_processing_status_status ON image_processing_status (status);

-- Rollback :
--   DROP TABLE IF EXISTS image_processing_status;
