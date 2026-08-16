import json
from pathlib import Path

from revenue_analytics.causal import build_causal_artifacts
from revenue_analytics.config import GeneratorConfig, ProjectPaths
from revenue_analytics.generator import generate_dataset
from revenue_analytics.monitoring import build_monitoring_report
from revenue_analytics.predictive import build_predictive_artifacts
from revenue_analytics.quality import validate_all
from revenue_analytics.reporting import build_business_report
from revenue_analytics.warehouse import build_warehouse


def test_complete_product_flow(tmp_path: Path) -> None:
    paths = ProjectPaths(tmp_path / "data")
    generate_dataset(
        GeneratorConfig(seed=51, n_customers=100, n_products=16, n_stores=6, n_transactions=2000),
        paths.raw,
    )
    build_warehouse(paths.raw, paths.warehouse)
    assert validate_all(paths.raw, paths.warehouse).passed
    build_business_report(paths.warehouse, tmp_path / "business-report.md")
    predictive = tmp_path / "predictive"
    build_predictive_artifacts(paths.warehouse, predictive)
    build_causal_artifacts(paths.warehouse, tmp_path / "causal")
    build_monitoring_report(predictive, predictive, tmp_path / "monitoring.json")
    assert json.loads((tmp_path / "monitoring.json").read_text())["status"] == "ok"
    assert (predictive / "demand_forecast.csv").is_file()
    assert (tmp_path / "causal" / "causal_decision.md").is_file()
