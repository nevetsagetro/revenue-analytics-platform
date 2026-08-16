import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QualityResult:
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def validate_raw_manifest(raw_dir: Path) -> QualityResult:
    manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
    checks: dict[str, bool] = {}
    for table, expected_checksum in manifest["sha256"].items():
        path = raw_dir / f"{table}.csv"
        checksum = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        checks[f"checksum:{table}"] = checksum == expected_checksum
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                actual_rows = sum(1 for _ in handle) - 1
                checks[f"rows:{table}"] = actual_rows == manifest["row_counts"][table]
        else:
            checks[f"rows:{table}"] = False
    return QualityResult(checks)


def validate_warehouse(database: Path) -> QualityResult:
    queries = {
        "no_orphan_lines": """SELECT COUNT(*) = 0 FROM raw_transaction_lines l
            LEFT JOIN raw_transactions t USING(transaction_id)
            WHERE t.transaction_id IS NULL""",
        "unique_line_grain": """SELECT COUNT(*) = COUNT(DISTINCT line_id)
            FROM stg_sales""",
        "price_join_complete": """SELECT (SELECT COUNT(*) FROM stg_sales) =
            (SELECT COUNT(*) FROM raw_transaction_lines)""",
        "revenue_reconciles": """SELECT
            (SELECT SUM(quantity * unit_price_cents) FROM raw_transaction_lines) =
            (SELECT SUM(line_revenue_cents) FROM stg_sales)""",
        "mart_reconciles": """SELECT
            (SELECT SUM(line_revenue_cents) FROM stg_sales) =
            (SELECT SUM(revenue_cents) FROM mart_sales_daily)""",
        "no_overlapping_prices": """SELECT COUNT(*) = 0
            FROM raw_price_history a JOIN raw_price_history b
              ON a.product_id = b.product_id AND a.channel = b.channel
             AND a.price_id < b.price_id
             AND a.valid_from <= b.valid_to AND b.valid_from <= a.valid_to""",
    }
    with sqlite3.connect(database) as connection:
        checks = {
            name: bool(connection.execute(sql).fetchone()[0]) for name, sql in queries.items()
        }
        checks["foreign_keys"] = connection.execute("PRAGMA foreign_key_check").fetchone() is None
    return QualityResult(checks)


def validate_all(raw_dir: Path, database: Path) -> QualityResult:
    raw = validate_raw_manifest(raw_dir)
    warehouse = validate_warehouse(database)
    return QualityResult(raw.checks | warehouse.checks)
