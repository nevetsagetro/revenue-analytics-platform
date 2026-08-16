import csv
from pathlib import Path

import pytest

from revenue_analytics.monitoring import build_monitoring_report, population_stability_index


def _directory(path: Path, scores: list[float]) -> None:
    (path / "predictive_metrics.json").write_text("{}", encoding="utf-8")
    (path / "customer_segments.csv").write_text("customer_id,segment\n", encoding="utf-8")
    (path / "fallback_forecast.csv").write_text(
        "week_start,forecast_units,model\n2026-01-01,1,naive_fallback\n", encoding="utf-8"
    )
    with (path / "churn_scores.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("customer_id", "churn_probability"))
        writer.writerows((f"C{index}", score) for index, score in enumerate(scores))


def test_psi_detects_distribution_shift() -> None:
    assert population_stability_index([0.1, 0.2, 0.3], [0.1, 0.2, 0.3]) == 0
    assert population_stability_index([0.1] * 20, [0.9] * 20) > 0.25
    with pytest.raises(ValueError, match="non-empty"):
        population_stability_index([], [0.1])


def test_monitoring_reports_fallback_and_status(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    current = tmp_path / "current"
    reference.mkdir()
    current.mkdir()
    _directory(reference, [0.1, 0.2, 0.3, 0.4])
    _directory(current, [0.1, 0.2, 0.3, 0.4])
    customers = tmp_path / "customers.csv"
    customers.write_text(
        "customer_id,region\nC0,norte\nC1,sur\nC2,norte\nC3,sur\n",
        encoding="utf-8",
    )
    report = build_monitoring_report(
        reference,
        current,
        tmp_path / "report.json",
        now=1e10,
        customers_csv=customers,
    )
    assert report["status"] == "ok"
    assert report["forecast_fallback_active"] is True
    assert report["fairness"]["max_score_gap"] >= 0


def test_monitoring_reports_missing_artifacts(tmp_path: Path) -> None:
    reference = tmp_path / "reference"
    current = tmp_path / "current"
    reference.mkdir()
    current.mkdir()
    report = build_monitoring_report(reference, current, tmp_path / "report.json")
    assert report["status"] == "critical"
    assert report["missing_artifacts"]
