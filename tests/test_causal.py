import json
from pathlib import Path

from revenue_analytics.causal import (
    build_causal_artifacts,
    estimate_price_elasticity,
    simulate_difference_in_differences,
    simulate_experiment,
)
from revenue_analytics.config import GeneratorConfig
from revenue_analytics.generator import generate_dataset
from revenue_analytics.warehouse import build_warehouse


def _database(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    database = tmp_path / "warehouse.db"
    generate_dataset(
        GeneratorConfig(seed=31, n_customers=100, n_products=16, n_stores=6, n_transactions=3000),
        raw,
    )
    build_warehouse(raw, database)
    return database


def test_experiment_and_cuped_recover_effect() -> None:
    result = simulate_experiment(seed=7, sample_size=8_000)
    assert result.cuped.ci_low < result.true_effect < result.cuped.ci_high
    assert result.variance_reduction > 0.3
    assert result.required_sample_size > 0


def test_did_recovers_known_effect() -> None:
    result = simulate_difference_in_differences(seed=9, units=4_000)
    assert result.estimate.ci_low < result.true_effect < result.estimate.ci_high
    assert result.placebo.ci_low < 0 < result.placebo.ci_high


def test_elasticity_and_artifacts_are_finite(tmp_path: Path) -> None:
    database = _database(tmp_path)
    elasticity = estimate_price_elasticity(database)
    assert elasticity.estimate < 0
    assert elasticity.ci_low < elasticity.estimate < elasticity.ci_high
    artifacts = build_causal_artifacts(database, tmp_path / "causal")
    metrics = json.loads(artifacts["metrics"].read_text(encoding="utf-8"))
    assert "elasticity" in metrics and "experiment" in metrics and "did" in metrics
    assert "Decisión causal sintética" in artifacts["decision"].read_text(encoding="utf-8")
