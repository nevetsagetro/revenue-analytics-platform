import csv
import sqlite3
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE raw_customers (
  customer_id TEXT PRIMARY KEY, signup_date TEXT NOT NULL,
  region TEXT NOT NULL, activity_score REAL NOT NULL CHECK(activity_score BETWEEN 0 AND 1)
);
CREATE TABLE raw_products (
  product_id TEXT PRIMARY KEY, sku TEXT NOT NULL UNIQUE, category TEXT NOT NULL,
  base_price_cents INTEGER NOT NULL CHECK(base_price_cents > 0),
  unit_cost_cents INTEGER NOT NULL CHECK(unit_cost_cents > 0),
  latent_elasticity REAL NOT NULL
);
CREATE TABLE raw_transactions (
  transaction_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES raw_customers(customer_id),
  transaction_date TEXT NOT NULL, channel TEXT NOT NULL CHECK(channel IN ('store', 'online')),
  region TEXT NOT NULL
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
CREATE VIEW stg_sales AS
SELECT l.line_id, t.transaction_id, t.customer_id, t.transaction_date, t.channel, t.region,
       l.product_id, p.category, l.quantity, l.unit_price_cents, l.discount_pct, l.promotion,
       l.quantity * l.unit_price_cents AS line_revenue_cents,
       l.quantity * (l.unit_price_cents - p.unit_cost_cents) AS line_margin_cents
FROM raw_transaction_lines l
JOIN raw_transactions t USING (transaction_id)
JOIN raw_products p USING (product_id);
CREATE TABLE mart_sales_daily AS
SELECT transaction_date, product_id, category, channel,
       SUM(quantity) AS units,
       SUM(line_revenue_cents) AS revenue_cents,
       SUM(line_margin_cents) AS margin_cents,
       COUNT(DISTINCT transaction_id) AS tickets
FROM stg_sales GROUP BY transaction_date, product_id, category, channel;
CREATE UNIQUE INDEX mart_sales_daily_grain
ON mart_sales_daily(transaction_date, product_id, channel);
CREATE TABLE mart_customer_activity AS
SELECT customer_id, MAX(transaction_date) AS last_purchase_date,
       COUNT(DISTINCT transaction_id) AS frequency,
       SUM(line_revenue_cents) AS monetary_cents,
       COUNT(DISTINCT product_id) AS product_breadth
FROM stg_sales GROUP BY customer_id;
CREATE UNIQUE INDEX mart_customer_activity_grain ON mart_customer_activity(customer_id);
"""


TABLE_COLUMNS = {
    "raw_customers": ("customer_id", "signup_date", "region", "activity_score"),
    "raw_products": (
        "product_id", "sku", "category", "base_price_cents", "unit_cost_cents",
        "latent_elasticity",
    ),
    "raw_transactions": (
        "transaction_id", "customer_id", "transaction_date", "channel", "region",
    ),
    "raw_transaction_lines": (
        "line_id", "transaction_id", "product_id", "quantity", "unit_price_cents",
        "discount_pct", "promotion",
    ),
}


def _load_csv(connection: sqlite3.Connection, table: str, path: Path) -> None:
    columns = TABLE_COLUMNS[table]
    placeholders = ", ".join("?" for _ in columns)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = ([row[column] for column in columns] for row in csv.DictReader(handle))
        connection.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows
        )


def build_warehouse(raw_dir: Path, database: Path) -> None:
    database.parent.mkdir(parents=True, exist_ok=True)
    database.unlink(missing_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_SQL.split("CREATE VIEW stg_sales", maxsplit=1)[0])
        for table, filename in (
            ("raw_customers", "customers.csv"),
            ("raw_products", "products.csv"),
            ("raw_transactions", "transactions.csv"),
            ("raw_transaction_lines", "transaction_lines.csv"),
        ):
            _load_csv(connection, table, raw_dir / filename)
        connection.executescript("CREATE VIEW stg_sales" + SCHEMA_SQL.split("CREATE VIEW stg_sales", maxsplit=1)[1])


def business_summary(database: Path) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """SELECT COALESCE(SUM(line_revenue_cents), 0), COALESCE(SUM(quantity), 0),
                      COUNT(DISTINCT transaction_id), COUNT(DISTINCT customer_id)
               FROM stg_sales"""
        ).fetchone()
    assert row is not None
    return dict(zip(("revenue_cents", "units", "tickets", "customers"), row, strict=True))
