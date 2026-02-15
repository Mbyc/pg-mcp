-- Small DB: Basic E-commerce Schema
DROP VIEW IF EXISTS order_summary;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT DEFAULT 0
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    ordered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW order_summary AS
SELECT o.id, u.username, p.name as product_name, o.quantity, o.total_price
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN products p ON o.product_id = p.id;

-- Index
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Data
INSERT INTO users (username, email) VALUES 
('alice', 'alice@example.com'), 
('bob', 'bob@example.com');

INSERT INTO products (name, price, stock) VALUES 
('Laptop', 1200.00, 10), 
('Mouse', 25.00, 50);

INSERT INTO orders (user_id, product_id, quantity, total_price) VALUES 
(1, 1, 1, 1200.00), 
(2, 2, 2, 50.00);
