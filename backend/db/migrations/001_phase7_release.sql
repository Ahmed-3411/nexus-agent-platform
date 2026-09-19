-- Phase 7 release alignment for databases created from an earlier schema.sql.
-- Safe to re-run. Unique-index creation deliberately fails if legacy data
-- already contains duplicate logical steps or verifications; reconcile those
-- rows before retrying instead of silently deleting audit-relevant data.

BEGIN;

ALTER TABLE workflows ADD COLUMN IF NOT EXISTS role TEXT;
UPDATE workflows SET role = 'analyst' WHERE role IS NULL;
ALTER TABLE workflows ALTER COLUMN role SET NOT NULL;

ALTER TABLE workflow_steps ADD COLUMN IF NOT EXISTS latency_ms INT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_step_index
    ON workflow_steps (workflow_id, step_index);

CREATE UNIQUE INDEX IF NOT EXISTS uq_verification_workflow_step
    ON verifications (workflow_step_id);

COMMIT;
