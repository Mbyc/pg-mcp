-- Large DB: SaaS Observability + Billing + RBAC
-- Goal: many tables/views/types/indexes + enough synthetic data

DROP MATERIALIZED VIEW IF EXISTS mv_daily_usage;
DROP VIEW IF EXISTS v_recent_incidents;

DROP TABLE IF EXISTS audit_events;
DROP TABLE IF EXISTS incident_notes;
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS metric_points;
DROP TABLE IF EXISTS metrics;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS subscription_items;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS plans;
DROP TABLE IF EXISTS accounts;

DROP TYPE IF EXISTS incident_severity;
DROP TYPE IF EXISTS audit_action;
DROP DOMAIN IF EXISTS nonempty_text;

-- Domain
CREATE DOMAIN nonempty_text AS TEXT CHECK (length(trim(VALUE)) > 0);

-- Enum Types
CREATE TYPE incident_severity AS ENUM ('sev1', 'sev2', 'sev3', 'sev4');
CREATE TYPE audit_action AS ENUM ('create', 'update', 'delete', 'login', 'logout');

CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    name nonempty_text NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    email TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(account_id, email)
);

CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    name nonempty_text NOT NULL,
    UNIQUE(account_id, name)
);

CREATE TABLE permissions (
    id BIGSERIAL PRIMARY KEY,
    key nonempty_text NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE role_permissions (
    role_id BIGINT NOT NULL REFERENCES roles(id),
    permission_id BIGINT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY(role_id, permission_id)
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users(id),
    role_id BIGINT NOT NULL REFERENCES roles(id),
    PRIMARY KEY(user_id, role_id)
);

CREATE TABLE api_keys (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    user_id BIGINT REFERENCES users(id),
    key_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE TABLE plans (
    id BIGSERIAL PRIMARY KEY,
    name nonempty_text NOT NULL UNIQUE,
    monthly_price_cents INT NOT NULL,
    included_events BIGINT NOT NULL
);

CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    plan_id BIGINT NOT NULL REFERENCES plans(id),
    status TEXT NOT NULL DEFAULT 'active',
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE subscription_items (
    id BIGSERIAL PRIMARY KEY,
    subscription_id BIGINT NOT NULL REFERENCES subscriptions(id),
    item_key nonempty_text NOT NULL,
    quantity INT NOT NULL DEFAULT 1
);

CREATE TABLE invoices (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    subscription_id BIGINT REFERENCES subscriptions(id),
    amount_cents BIGINT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT now(),
    paid_at TIMESTAMPTZ
);

CREATE TABLE metrics (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    name nonempty_text NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(account_id, name)
);

CREATE TABLE metric_points (
    id BIGSERIAL PRIMARY KEY,
    metric_id BIGINT NOT NULL REFERENCES metrics(id),
    ts TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

CREATE TABLE alerts (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    metric_id BIGINT NOT NULL REFERENCES metrics(id),
    name nonempty_text NOT NULL,
    threshold DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE incidents (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    alert_id BIGINT REFERENCES alerts(id),
    severity incident_severity NOT NULL,
    title nonempty_text NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    opened_at TIMESTAMPTZ DEFAULT now(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE incident_notes (
    id BIGSERIAL PRIMARY KEY,
    incident_id BIGINT NOT NULL REFERENCES incidents(id),
    author_user_id BIGINT REFERENCES users(id),
    note TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_events (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    actor_user_id BIGINT REFERENCES users(id),
    action audit_action NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Views
CREATE VIEW v_recent_incidents AS
SELECT i.id, i.account_id, i.severity, i.title, i.status, i.opened_at
FROM incidents i
WHERE i.opened_at > now() - interval '7 days';

CREATE MATERIALIZED VIEW mv_daily_usage AS
SELECT
  a.id AS account_id,
  date_trunc('day', e.created_at) AS day,
  count(*) AS events
FROM audit_events e
JOIN accounts a ON a.id = e.account_id
GROUP BY a.id, date_trunc('day', e.created_at);

-- Indexes
CREATE INDEX idx_users_account_active ON users(account_id, is_active);
CREATE INDEX idx_api_keys_account_revoked ON api_keys(account_id, revoked_at);
CREATE INDEX idx_metrics_tags_gin ON metrics USING GIN (tags);
CREATE INDEX idx_metric_points_metric_ts ON metric_points(metric_id, ts DESC);
CREATE INDEX idx_incidents_account_status ON incidents(account_id, status);
CREATE INDEX idx_audit_events_account_created ON audit_events(account_id, created_at DESC);
CREATE INDEX idx_audit_events_metadata_gin ON audit_events USING GIN (metadata);

-- Data generation
INSERT INTO plans (name, monthly_price_cents, included_events) VALUES
('Starter', 0, 10000),
('Pro', 4900, 100000),
('Enterprise', 19900, 1000000);

INSERT INTO permissions (key, description) VALUES
('metrics:read', 'Read metrics'),
('metrics:write', 'Write metrics'),
('billing:read', 'Read billing'),
('billing:write', 'Write billing'),
('incidents:manage', 'Manage incidents');

-- Create 20 accounts
INSERT INTO accounts (name)
SELECT 'acct_' || g
FROM generate_series(1, 20) g;

-- Users: 50 per account
INSERT INTO users (account_id, email, full_name)
SELECT a.id, 'user_' || a.id || '_' || g || '@example.com', 'User ' || g
FROM accounts a
CROSS JOIN generate_series(1, 50) g;

-- Roles: 3 per account
INSERT INTO roles (account_id, name)
SELECT a.id, r
FROM accounts a
CROSS JOIN (VALUES ('admin'), ('dev'), ('viewer')) AS t(r);

-- Assign permissions to roles (simple mapping)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON (
  (r.name = 'admin') OR
  (r.name = 'dev' AND p.key IN ('metrics:read','metrics:write','incidents:manage')) OR
  (r.name = 'viewer' AND p.key IN ('metrics:read','billing:read'))
);

-- Assign roles to users (round-robin)
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.account_id = u.account_id
WHERE (u.id % 3 = 0 AND r.name='admin')
   OR (u.id % 3 = 1 AND r.name='dev')
   OR (u.id % 3 = 2 AND r.name='viewer');

-- Subscriptions: 1 per account
INSERT INTO subscriptions (account_id, plan_id, status, start_date)
SELECT a.id,
       CASE WHEN a.id % 3 = 0 THEN (SELECT id FROM plans WHERE name='Enterprise')
            WHEN a.id % 3 = 1 THEN (SELECT id FROM plans WHERE name='Pro')
            ELSE (SELECT id FROM plans WHERE name='Starter')
       END,
       'active',
       (CURRENT_DATE - ((a.id % 90)::int))
FROM accounts a;

-- Invoices: 6 per account (past 6 months)
INSERT INTO invoices (account_id, subscription_id, amount_cents, period_start, period_end, paid_at)
SELECT s.account_id, s.id,
       (SELECT monthly_price_cents FROM plans p WHERE p.id = s.plan_id),
       (date_trunc('month', now()) - (g || ' months')::interval)::date,
       (date_trunc('month', now()) - ((g-1) || ' months')::interval)::date,
       CASE WHEN g > 1 THEN now() - (g || ' months')::interval ELSE NULL END
FROM subscriptions s
CROSS JOIN generate_series(1, 6) g;

-- Metrics: 10 per account
INSERT INTO metrics (account_id, name, tags)
SELECT a.id, 'metric_' || g, jsonb_build_object('env', CASE WHEN g%2=0 THEN 'prod' ELSE 'staging' END, 'service', 'svc_'|| (g%5))
FROM accounts a
CROSS JOIN generate_series(1, 10) g;

-- Metric points: 100 per metric (enough volume)
INSERT INTO metric_points (metric_id, ts, value)
SELECT m.id,
       now() - (g || ' minutes')::interval,
       random() * 100
FROM metrics m
CROSS JOIN generate_series(1, 100) g;

-- Alerts: 2 per account
INSERT INTO alerts (account_id, metric_id, name, threshold)
SELECT a.id, m.id, 'alert_' || a.id || '_' || g, 75.0
FROM accounts a
JOIN LATERAL (
  SELECT id FROM metrics m WHERE m.account_id = a.id ORDER BY id LIMIT 1
) m ON true
CROSS JOIN generate_series(1, 2) g;

-- Incidents: 30 total
INSERT INTO incidents (account_id, alert_id, severity, title, status, opened_at)
SELECT a.id, al.id,
       CASE WHEN g%4=0 THEN 'sev1' WHEN g%4=1 THEN 'sev2' WHEN g%4=2 THEN 'sev3' ELSE 'sev4' END::incident_severity,
       'Incident ' || g,
       CASE WHEN g%5=0 THEN 'closed' ELSE 'open' END,
       now() - (g || ' hours')::interval
FROM accounts a
JOIN LATERAL (
  SELECT id FROM alerts al WHERE al.account_id = a.id ORDER BY id LIMIT 1
) al ON true
CROSS JOIN generate_series(1, 30) g
WHERE a.id <= 5;

-- Notes: 3 per incident
INSERT INTO incident_notes (incident_id, author_user_id, note)
SELECT i.id,
       (SELECT u.id FROM users u WHERE u.account_id=i.account_id ORDER BY u.id LIMIT 1),
       'Note ' || g || ' for incident ' || i.id
FROM incidents i
CROSS JOIN generate_series(1, 3) g;

-- Audit events: 5000 events
INSERT INTO audit_events (account_id, actor_user_id, action, object_type, object_id, metadata, created_at)
SELECT a.id,
       (SELECT u.id FROM users u WHERE u.account_id=a.id ORDER BY u.id LIMIT 1),
       CASE WHEN g%5=0 THEN 'login' WHEN g%5=1 THEN 'logout' WHEN g%5=2 THEN 'create' WHEN g%5=3 THEN 'update' ELSE 'delete' END::audit_action,
       'resource',
       'obj_' || g,
       jsonb_build_object('ip', '10.0.' || (g%255) || '.' || ((g*7)%255), 'user_agent', 'test-agent'),
       now() - (g || ' seconds')::interval
FROM accounts a
CROSS JOIN generate_series(1, 250) g
WHERE a.id <= 20;

REFRESH MATERIALIZED VIEW mv_daily_usage;
