import csv
import json
from pathlib import Path

from fastapi.testclient import TestClient

from revenue_analytics.api import create_app


def _artifacts(root: Path) -> None:
    metrics = {
        "forecast": [{"model": "naive", "wape": 0.1, "mase": 1.0, "folds": 8}],
        "churn": {"auc": 0.7, "brier": 0.2},
    }
    (root / "predictive_metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    for filename, fields, rows in (
        (
            "demand_forecast.csv",
            ("week_start", "forecast_units", "model"),
            [("2026-01-05", "100", "naive"), ("2026-01-12", "110", "naive")],
        ),
        (
            "churn_scores.csv",
            ("customer_id", "as_of_date", "churn_probability"),
            [("C1", "2025-12-31", "0.7")],
        ),
        ("customer_segments.csv", ("customer_id", "segment"), [("C1", "at_risk")]),
    ):
        with (root / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(fields)
            writer.writerows(rows)


def _causal(root: Path) -> None:
    root.mkdir(exist_ok=True)
    (root / "causal_metrics.json").write_text(
        json.dumps({"elasticity": {"estimate": -1.2}}), encoding="utf-8"
    )


def test_api_contracts_and_dashboard(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    causal = tmp_path / "causal"
    _causal(causal)
    client = TestClient(create_app(tmp_path, causal))
    assert client.get("/health").json() == {"status": "ok"}
    assert len(client.get("/v1/forecast?horizon=1").json()) == 1
    assert client.get("/v1/churn/C1").json()["churn_probability"] == "0.7"
    assert client.get("/v1/segments/C1").json()["segment"] == "at_risk"
    assert client.get("/v1/causal").json()["elasticity"]["estimate"] == -1.2
    assert "Revenue Analytics Platform" in client.get("/dashboard").text
    assert "Elasticidad precio-demanda" in client.get("/dashboard").text
    assert client.get("/v1/churn/missing").status_code == 404


def test_missing_artifacts_report_degraded(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    assert client.get("/health").json() == {"status": "degraded"}
    assert client.get("/v1/metrics").status_code == 503


def test_forecast_falls_back_when_candidate_is_missing(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    (tmp_path / "demand_forecast.csv").unlink()
    (tmp_path / "fallback_forecast.csv").write_text(
        "week_start,forecast_units,model\n2026-01-05,90,naive_fallback\n", encoding="utf-8"
    )
    response = TestClient(create_app(tmp_path)).get("/v1/forecast")
    assert response.status_code == 200
    assert response.json()[0]["model"] == "naive_fallback"
