-- ============================================================================
-- Migration 0001 — Table de rate limiting durable (SEC-06)
-- ============================================================================
--
-- ⚠️  APPROBATION REQUISE AVANT APPLICATION EN BASE RÉELLE ⚠️
--
-- Cette migration crée la table `rate_limit_entries` utilisée par le rate
-- limiting durable (voir utils/rate_limit.py et backend/db/models.py).
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
-- opérateur autorisé (condition : pas d'opération DB destructive/auto en prod).
--
-- Application manuelle (après approbation) :
--   psql "$DATABASE_URL" -f backend/db/migrations/0001_rate_limit_entries.sql
--
-- Rollback :
--   DROP TABLE IF EXISTS rate_limit_entries;
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limit_entries (
    key_hash      VARCHAR(64)      PRIMARY KEY,   -- SHA-256 hex de la clé logique
    attempts      INTEGER          NOT NULL DEFAULT 0,
    first_attempt DOUBLE PRECISION NOT NULL DEFAULT 0,  -- epoch (secondes)
    blocked_until DOUBLE PRECISION NOT NULL DEFAULT 0   -- epoch (secondes), 0 = non bloqué
);

-- Index pour purge périodique des entrées expirées (optionnel).
CREATE INDEX IF NOT EXISTS idx_rate_limit_blocked_until
    ON rate_limit_entries (blocked_until);
