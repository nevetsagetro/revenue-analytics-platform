PRAGMA foreign_keys = ON;

CREATE TABLE raw_customers (
  customer_id TEXT PRIMARY KEY,
  signup_date TEXT NOT NULL,
  region TEXT NOT NULL,
  activity_score REAL NOT NULL CHECK(activity_score BETWEEN 0 AND 1),
  latent_churn_date TEXT
);
CREATE TABLE raw_products (
  product_id TEXT PRIMARY KEY,
  sku TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL,
  base_price_cents INTEGER NOT NULL CHECK(base_price_cents > 0),
  unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents > 0),
  latent_elasticity REAL NOT NULL
);
CREATE TABLE raw_stores (
  store_id TEXT PRIMARY KEY,
  store_name TEXT NOT NULL,
  channel TEXT NOT NULL CHECK(channel IN ('store', 'online')),
  region TEXT NOT NULL
);
CREATE TABLE raw_price_history (
  price_id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES raw_products(product_id),
  channel TEXT NOT NULL CHECK(channel IN ('store', 'online')),
  valid_from TEXT NOT NULL,
  valid_to TEXT NOT NULL CHECK(valid_from <= valid_to),
  list_price_cents INTEGER NOT NULL CHECK(list_price_cents > 0),
  UNIQUE(product_id, channel, valid_from)
);
CREATE TABLE raw_transactions (
  transaction_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES raw_customers(customer_id),
  store_id TEXT NOT NULL REFERENCES raw_stores(store_id),
  transaction_date TEXT NOT NULL
);
CREATE TABLE raw_transaction_lines (
  line_id TEXT PRIMARY KEY,
  transaction_id TEXT NOT NULL REFERENCES raw_transactions(transaction_id),
  product_id TEXT NOT NULL REFERENCES raw_products(product_id),
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents > 0),
  discount_pct REAL NOT NULL CHECK(discount_pct BETWEEN 0 AND 1),
  promotion INTEGER NOT NULL CHECK(promotion IN (0, 1))
);
