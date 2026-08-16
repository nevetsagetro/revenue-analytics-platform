import json
from pathlib import Path

from revenue_analytics.config import GeneratorConfig
from revenue_analytics.generator import generate_dataset
from revenue_analytics.predictive import (
    backtest_forecasts,
    build_predictive_artifacts,
    customer_segments,
    forecast_next_weeks,
    train_churn_baseline,
)
from revenue_analytics.warehouse import build_warehouse


def _database(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse.db"
    generate_dataset(
        GeneratorConfig(seed=23, n_customers=80, n_products=12, n_stores=6, n_transactions=1200),
        raw,
    )
    build_warehouse(raw, database)
    return database


def test_temporal_forecast_baselines_return_finite_metrics(tmp_path: Path) -> None:
    metrics = backtest_forecasts(_database(tmp_path), folds=4)
    assert {metric.model for metric in metrics} == {
        "naive",
        "seasonal_naive",
        "moving_average_4",
        "exponential_smoothing",
        "linear_trend_12",
    }
    assert all(metric.folds == 4 and metric.wape >= 0 and metric.mase >= 0 for metric in metrics)
    forecast = forecast_next_weeks(_database(tmp_path), horizon=3)
    assert len(forecast) == 3
    assert all(row["forecast_units"] >= 0 for row in forecast)


def test_churn_and_segments_are_bounded_and_complete(tmp_path: Path) -> None:
    database = _database(tmp_path)
    churn = train_churn_baseline(database)
    assert churn.observations > 0
    assert 0 <= churn.auc <= 1
    assert 0 <= churn.brier <= 1
    assert 0 <= churn.calibration_error <= 1
    assert 0 <= churn.rule_auc <= 1
    segments = customer_segments(database)
    assert segments
    assert {row["segment"] for row in segments} <= {"champions", "loyal", "at_risk", "developing"}


def test_predictive_artifacts_are_reproducible_files(tmp_path: Path) -> None:
    paths = build_predictive_artifacts(_database(tmp_path), tmp_path / "artifacts")
    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    assert len(metrics["forecast"]) == 5
    assert paths["segments"].read_text(encoding="utf-8").startswith("customer_id,")
    assert paths["churn_scores"].read_text(encoding="utf-8").startswith("customer_id,")
    assert paths["forecast"].read_text(encoding="utf-8").startswith("week_start,")
