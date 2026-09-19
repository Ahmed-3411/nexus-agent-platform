-- Enterprise Agentic Workflow Platform — base schema (Phase 0)
-- Applied automatically by docker-compose on first postgres init,
-- or manually via: psql -f schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- Organizations (kept minimal now; not enforced until multi-tenancy phase)
-- =========================================================
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========================================================
-- Identity & RBAC
-- =========================================================
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,        -- admin / manager / analyst / support_agent
    description TEXT
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    email           TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name       TEXT,
    role_id         UUID REFERENCES roles(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A permission is a capability string, e.g. "database.read", "email.send"
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code        TEXT NOT NULL UNIQUE,        -- e.g. "gmail.send"
    description TEXT
);

CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- =========================================================
-- Tools & Risk classification
-- =========================================================
CREATE TABLE tools (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,     -- e.g. "gmail.send", "database.query"
    mcp_server      TEXT NOT NULL,            -- e.g. "gmail", "postgres", "drive"
    risk_level      TEXT NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    description     TEXT,
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE
);

-- =========================================================
-- Workflows (agent runs)
-- =========================================================
CREATE TABLE workflows (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    user_request    TEXT NOT NULL,
    role            TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN (
                            'PENDING','PLANNING','RUNNING',
                            'AWAITING_APPROVAL','SUCCEEDED','FAILED','CANCELLED'
                        )),
    plan            JSONB,                    -- planner output
    final_result    JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE TABLE workflow_steps (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id     UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    step_index      INT NOT NULL,
    tool_id         UUID REFERENCES tools(id),
    tool_name       TEXT NOT NULL,
    arguments       JSONB,
    result          JSONB,
    status          TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN (
                            'PENDING','RUNNING','SUCCEEDED','FAILED',
                            'RETRYING','SKIPPED','AWAITING_APPROVAL'
                        )),
    risk_score      NUMERIC(4,2),
    risk_level      TEXT CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    attempt_count   INT NOT NULL DEFAULT 0,
    latency_ms      INT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    error           TEXT,
    UNIQUE (workflow_id, step_index)
);

-- Post-execution verification results (expected vs actual)
CREATE TABLE verifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_step_id UUID NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    expected        JSONB,
    actual          JSONB,
    passed          BOOLEAN NOT NULL,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (workflow_step_id)
);

-- Human-in-the-loop approvals
CREATE TABLE approvals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_step_id UUID NOT NULL REFERENCES workflow_steps(id) ON DELETE CASCADE,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at      TIMESTAMPTZ,
    decided_by      UUID REFERENCES users(id),
    decision        TEXT CHECK (decision IN ('APPROVED','REJECTED')),
    reason          TEXT
);

-- =========================================================
-- Audit log — append-only
-- =========================================================
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    organization_id UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    workflow_id     UUID REFERENCES workflows(id),
    workflow_step_id UUID REFERENCES workflow_steps(id),
    tool_name       TEXT,
    arguments       JSONB,
    permission_code TEXT,
    risk_level      TEXT,
    approval_id     UUID REFERENCES approvals(id),
    result          TEXT,          -- SUCCESS / FAILURE / DENIED
    latency_ms      INT,
    error           TEXT
);

CREATE INDEX idx_audit_logs_workflow ON audit_logs(workflow_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_workflow_steps_workflow ON workflow_steps(workflow_id);

-- =========================================================
-- Seed default roles + permissions
-- =========================================================
INSERT INTO roles (name, description) VALUES
    ('admin', 'Full access to all tools and settings'),
    ('manager', 'Can approve high-risk actions and view all workflows'),
    ('analyst', 'Read access to data, no write/send actions'),
    ('support_agent', 'Handles customer support workflows')
ON CONFLICT DO NOTHING;

INSERT INTO permissions (code, description) VALUES
    ('database.read', 'Read-only database queries'),
    ('database.write', 'Insert/update database records'),
    ('database.delete', 'Delete database records'),
    ('email.read', 'Search and read emails'),
    ('email.draft', 'Create email drafts'),
    ('email.send', 'Send emails to external recipients'),
    ('files.read', 'Search and read files'),
    ('crm.read', 'Read CRM records'),
    ('crm.update', 'Update CRM records')
ON CONFLICT DO NOTHING;

INSERT INTO tools (name, mcp_server, risk_level, description, requires_approval) VALUES
    ('database.query',  'postgres', 'LOW',      'Run a read-only SQL query', FALSE),
    ('gmail.search',    'gmail',    'LOW',       'Search mailbox', FALSE),
    ('gmail.read',      'gmail',    'MEDIUM',    'Read an email', FALSE),
    ('gmail.draft',     'gmail',    'MEDIUM',    'Create a draft email', FALSE),
    ('gmail.send',      'gmail',    'HIGH',      'Send an email', TRUE),
    ('drive.search',    'drive',    'LOW',       'Search files', FALSE),
    ('drive.read',      'drive',    'LOW',       'Read a file', FALSE)
ON CONFLICT DO NOTHING;

-- =========================================================
-- Seed default role -> permission grants (Phase 3 RBAC)
--
--                    admin  manager  analyst  support_agent
-- database.read        X       X        X          -
-- database.write       X       -        -          -
-- database.delete      X       -        -          -
-- email.read           X       X        X          X
-- email.draft          X       X        -          X
-- email.send           X       X        -          -
-- files.read           X       X        X          X
-- crm.read             X       X        X          X
-- crm.update           X       X        -          X
-- =========================================================
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'manager'
  AND p.code IN ('database.read', 'email.read', 'email.draft', 'email.send',
                 'files.read', 'crm.read', 'crm.update')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'analyst'
  AND p.code IN ('database.read', 'email.read', 'files.read', 'crm.read')
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'support_agent'
  AND p.code IN ('email.read', 'email.draft', 'files.read', 'crm.read', 'crm.update')
ON CONFLICT DO NOTHING;
