import csv
import sqlite3
from pathlib import Path

from revenue_analytics.config import GeneratorConfig
from revenue_analytics.generator import generate_dataset
from revenue_analytics.quality import validate_all
from revenue_analytics.warehouse import (
    available_analyses,
    build_warehouse,
    business_summary,
    run_analysis,
)


def test_warehouse_preserves_grains_and_totals(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse" / "revenue.db"
    generate_dataset(GeneratorConfig(seed=11, n_customers=15, n_products=8, n_transactions=40), raw)
    build_warehouse(raw, database)

    with sqlite3.connect(database) as connection:
        tickets = connection.execute("SELECT COUNT(*) FROM raw_transactions").fetchone()[0]
        duplicate_lines = connection.execute(
            "SELECT COUNT(*) - COUNT(DISTINCT line_id) FROM stg_sales"
        ).fetchone()[0]
        orphan_lines = connection.execute(
            """SELECT COUNT(*) FROM raw_transaction_lines l
               LEFT JOIN raw_transactions t USING(transaction_id)
               WHERE t.transaction_id IS NULL"""
        ).fetchone()[0]
    assert tickets == 40
    assert duplicate_lines == 0
    assert orphan_lines == 0
    assert business_summary(database)["revenue_cents"] > 0


def test_summary_matches_raw_line_calculation(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse.db"
    generate_dataset(GeneratorConfig(n_customers=8, n_products=6, n_transactions=20), raw)
    build_warehouse(raw, database)
    with (raw / "transaction_lines.csv").open(newline="", encoding="utf-8") as handle:
        expected = sum(
            int(row["quantity"]) * int(row["unit_price_cents"]) for row in csv.DictReader(handle)
        )
    assert business_summary(database)["revenue_cents"] == expected


def test_quality_gate_and_analyses_pass(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse.db"
    generate_dataset(
        GeneratorConfig(seed=19, n_customers=12, n_products=8, n_stores=4, n_transactions=60),
        raw,
    )
    build_warehouse(raw, database)
    result = validate_all(raw, database)
    assert result.passed, [name for name, passed in result.checks.items() if not passed]
    assert len(available_analyses()) == 10
    columns, rows = run_analysis(database, "01_monthly_revenue")
    assert columns == ["month", "revenue_eur"]
    assert rows
