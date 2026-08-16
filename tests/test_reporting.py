from pathlib import Path

from revenue_analytics.config import GeneratorConfig
from revenue_analytics.generator import generate_dataset
from revenue_analytics.reporting import build_business_report
from revenue_analytics.warehouse import build_warehouse


def test_business_report_contains_findings_and_causal_warning(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse.db"
    output = tmp_path / "report.md"
    generate_dataset(
        GeneratorConfig(seed=2, n_customers=12, n_products=8, n_stores=4, n_transactions=80),
        raw,
    )
    build_warehouse(raw, database)
    build_business_report(database, output)
    report = output.read_text(encoding="utf-8")
    assert "Cinco hallazgos verificables" in report
    assert "asociación OLS simple" in report
    assert "no identifica un efecto causal" in report
