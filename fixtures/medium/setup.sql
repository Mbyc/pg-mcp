-- Medium DB: CRM & Analytics Schema
DROP MATERIALIZED VIEW IF EXISTS mv_customer_stats;
DROP VIEW IF EXISTS v_active_subscriptions;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS customer_profiles;
DROP TABLE IF EXISTS customers;
DROP TYPE IF EXISTS ticket_status;
DROP TYPE IF EXISTS address_type;
DROP DOMAIN IF EXISTS email_address;

-- Domain
CREATE DOMAIN email_address AS TEXT CHECK (VALUE ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$');

-- Enum Type
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed');

-- Composite Type
CREATE TYPE address_type AS (
    street TEXT,
    city TEXT,
    zip_code TEXT
);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email email_address UNIQUE,
    home_address address_type,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customer_profiles (
    customer_id INT PRIMARY KEY REFERENCES customers(id),
    bio TEXT,
    preferences JSONB,
    last_login TIMESTAMP
);

CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    plan_name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    start_date DATE NOT NULL,
    end_date DATE
);

CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    subject TEXT NOT NULL,
    status ticket_status DEFAULT 'open',
    priority INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW v_active_subscriptions AS
SELECT c.name, s.plan_name, s.start_date
FROM subscriptions s
JOIN customers c ON s.customer_id = c.id
WHERE s.status = 'active';

CREATE MATERIALIZED VIEW mv_customer_stats AS
SELECT c.id, c.name, COUNT(t.id) as total_tickets
FROM customers c
LEFT JOIN support_tickets t ON c.id = t.customer_id
GROUP BY c.id, c.name;

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_support_tickets_status ON support_tickets(status);
CREATE INDEX idx_customer_profiles_preferences ON customer_profiles USING GIN (preferences);

-- Data
INSERT INTO customers (name, email, home_address) VALUES 
('Charlie', 'charlie@dev.com', ROW('123 Main St', 'Boston', '02108')),
('Diana', 'diana@test.com', ROW('456 Oak Rd', 'Seattle', '98101'));

INSERT INTO customer_profiles (customer_id, bio, preferences) VALUES 
(1, 'Dev enthusiast', '{"theme": "dark", "notifications": true}'),
(2, 'Test manager', '{"theme": "light", "notifications": false}');

INSERT INTO subscriptions (customer_id, plan_name, start_date) VALUES 
(1, 'Premium', '2024-01-01'),
(2, 'Basic', '2024-02-15');

INSERT INTO support_tickets (customer_id, subject, status, priority) VALUES 
(1, 'Login issue', 'resolved', 2),
(1, 'Billing question', 'open', 1),
(2, 'Feature request', 'open', 3);

REFRESH MATERIALIZED VIEW mv_customer_stats;
