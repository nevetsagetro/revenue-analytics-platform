import csv
import sqlite3
from pathlib import Path

SQL_DIR = Path(__file__).with_name("sql")
TABLE_FILES = {
    "raw_customers": "customers.csv",
    "raw_products": "products.csv",
    "raw_stores": "stores.csv",
    "raw_price_history": "price_history.csv",
    "raw_transactions": "transactions.csv",
    "raw_transaction_lines": "transaction_lines.csv",
}
TABLE_COLUMNS = {
    "raw_customers": ("customer_id", "signup_date", "region", "activity_score"),
    "raw_products": (
        "product_id",
        "sku",
        "category",
        "base_price_cents",
        "unit_cost_cents",
        "latent_elasticity",
    ),
    "raw_stores": ("store_id", "store_name", "channel", "region"),
    "raw_price_history": (
        "price_id",
        "product_id",
        "channel",
        "valid_from",
        "valid_to",
        "list_price_cents",
    ),
    "raw_transactions": ("transaction_id", "customer_id", "store_id", "transaction_date"),
    "raw_transaction_lines": (
        "line_id",
        "transaction_id",
        "product_id",
        "quantity",
        "unit_price_cents",
        "discount_pct",
        "promotion",
    ),
}


def _read_sql(filename: str) -> str:
    return (SQL_DIR / filename).read_text(encoding="utf-8")


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
        connection.executescript(_read_sql("001_raw_schema.sql"))
        for table, filename in TABLE_FILES.items():
            _load_csv(connection, table, raw_dir / filename)
        connection.executescript(_read_sql("002_staging.sql"))
        connection.executescript(_read_sql("003_marts.sql"))


def business_summary(database: Path) -> dict[str, int]:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """SELECT COALESCE(SUM(line_revenue_cents), 0), COALESCE(SUM(quantity), 0),
                      COUNT(DISTINCT transaction_id), COUNT(DISTINCT customer_id)
               FROM stg_sales"""
        ).fetchone()
    assert row is not None
    return dict(zip(("revenue_cents", "units", "tickets", "customers"), row, strict=True))


def run_analysis(database: Path, query_name: str) -> tuple[list[str], list[tuple[object, ...]]]:
    query_path = SQL_DIR / "analysis" / f"{query_name}.sql"
    if not query_path.is_file():
        available = ", ".join(available_analyses())
        raise ValueError(f"Unknown analysis: {query_name}. Available: {available}")
    with sqlite3.connect(database) as connection:
        cursor = connection.execute(query_path.read_text(encoding="utf-8"))
        columns = [item[0] for item in cursor.description]
        return columns, cursor.fetchall()


def available_analyses() -> list[str]:
    return sorted(path.stem for path in (SQL_DIR / "analysis").glob("*.sql"))
