import json
from pathlib import Path

import pytest

from revenue_analytics.config import GeneratorConfig
from revenue_analytics.generator import generate_dataset


def test_generation_is_deterministic(tmp_path: Path) -> None:
    config = GeneratorConfig(seed=7, n_customers=12, n_products=8, n_transactions=30)
    first = generate_dataset(config, tmp_path / "first")
    second = generate_dataset(config, tmp_path / "second")
    assert first.checksums == second.checksums


def test_different_seed_changes_output(tmp_path: Path) -> None:
    one = generate_dataset(
        GeneratorConfig(seed=1, n_customers=5, n_products=4, n_transactions=8), tmp_path / "one"
    )
    two = generate_dataset(
        GeneratorConfig(seed=2, n_customers=5, n_products=4, n_transactions=8), tmp_path / "two"
    )
    assert one.checksums != two.checksums


def test_manifest_records_configuration_counts_and_checksums(tmp_path: Path) -> None:
    dataset = generate_dataset(
        GeneratorConfig(seed=4, n_customers=5, n_products=4, n_stores=2, n_transactions=8),
        tmp_path,
    )
    manifest = json.loads(dataset.manifest.read_text(encoding="utf-8"))
    assert manifest["config"]["seed"] == 4
    assert manifest["row_counts"] == dataset.row_counts
    assert manifest["sha256"] == dataset.checksums
    assert dataset.row_counts["stores"] == 3


def test_invalid_size_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_dataset(GeneratorConfig(n_customers=0), tmp_path)
