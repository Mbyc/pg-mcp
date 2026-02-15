\echo '=== pgmcp_small: schema + data checks ==='
\c pgmcp_small
SELECT 'tables_public' AS check, count(*) AS value
FROM information_schema.tables
WHERE table_schema='public' AND table_type='BASE TABLE';

SELECT 'views_public' AS check, count(*) AS value
FROM information_schema.views
WHERE table_schema='public';

SELECT 'users_rows' AS check, count(*) AS value FROM users;
SELECT 'products_rows' AS check, count(*) AS value FROM products;
SELECT 'orders_rows' AS check, count(*) AS value FROM orders;
SELECT 'order_summary_rows' AS check, count(*) AS value FROM order_summary;

\echo '=== pgmcp_medium: schema + types + data checks ==='
\c pgmcp_medium
SELECT 'tables_public' AS check, count(*) AS value
FROM information_schema.tables
WHERE table_schema='public' AND table_type='BASE TABLE';

SELECT 'views_public' AS check, count(*) AS value
FROM information_schema.views
WHERE table_schema='public';

SELECT 'mviews_public' AS check, count(*) AS value
FROM pg_matviews
WHERE schemaname='public';

SELECT 'domain_email_address_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='email_address';

SELECT 'enum_ticket_status_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='ticket_status';

SELECT 'composite_address_type_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='address_type';

SELECT 'customers_rows' AS check, count(*) AS value FROM customers;
SELECT 'subscriptions_rows' AS check, count(*) AS value FROM subscriptions;
SELECT 'support_tickets_rows' AS check, count(*) AS value FROM support_tickets;
SELECT 'v_active_subscriptions_rows' AS check, count(*) AS value FROM v_active_subscriptions;
SELECT 'mv_customer_stats_rows' AS check, count(*) AS value FROM mv_customer_stats;

\echo '=== pgmcp_large: schema + types + data volume checks ==='
\c pgmcp_large
SELECT 'tables_public' AS check, count(*) AS value
FROM information_schema.tables
WHERE table_schema='public' AND table_type='BASE TABLE';

SELECT 'views_public' AS check, count(*) AS value
FROM information_schema.views
WHERE table_schema='public';

SELECT 'mviews_public' AS check, count(*) AS value
FROM pg_matviews
WHERE schemaname='public';

SELECT 'domain_nonempty_text_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='nonempty_text';

SELECT 'enum_incident_severity_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='incident_severity';

SELECT 'enum_audit_action_exists' AS check,
       count(*) AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE n.nspname='public' AND t.typname='audit_action';

SELECT 'accounts_rows' AS check, count(*) AS value FROM accounts;
SELECT 'users_rows' AS check, count(*) AS value FROM users;
SELECT 'metrics_rows' AS check, count(*) AS value FROM metrics;
SELECT 'metric_points_rows' AS check, count(*) AS value FROM metric_points;
SELECT 'audit_events_rows' AS check, count(*) AS value FROM audit_events;
SELECT 'incidents_rows' AS check, count(*) AS value FROM incidents;
SELECT 'v_recent_incidents_rows' AS check, count(*) AS value FROM v_recent_incidents;
SELECT 'mv_daily_usage_rows' AS check, count(*) AS value FROM mv_daily_usage;

\echo '=== done ==='
