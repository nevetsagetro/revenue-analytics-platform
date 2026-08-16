import csv
import json
import math
import time
from pathlib import Path


def population_stability_index(reference: list[float], current: list[float]) -> float:
    if not reference or not current:
        raise ValueError("PSI requires non-empty reference and current samples")
    total = 0.0
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10
        expected = sum(lower <= value < upper for value in reference) / len(reference)
        actual = sum(lower <= value < upper for value in current) / len(current)
        expected = max(expected, 1e-6)
        actual = max(actual, 1e-6)
        total += (actual - expected) * math.log(actual / expected)
    return total


def _scores(directory: Path) -> list[float]:
    with (directory / "churn_scores.csv").open(newline="", encoding="utf-8") as handle:
        return [float(row["churn_probability"]) for row in csv.DictReader(handle)]


def _fairness(current_dir: Path, customers_csv: Path | None) -> dict[str, object] | None:
    if customers_csv is None or not customers_csv.is_file():
        return None
    with customers_csv.open(newline="", encoding="utf-8") as handle:
        regions = {row["customer_id"]: row["region"] for row in csv.DictReader(handle)}
    grouped: dict[str, list[float]] = {}
    with (current_dir / "churn_scores.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            region = regions.get(row["customer_id"], "unknown")
            grouped.setdefault(region, []).append(float(row["churn_probability"]))
    averages = {region: sum(values) / len(values) for region, values in grouped.items()}
    disparity = max(averages.values()) - min(averages.values()) if averages else 0.0
    return {"average_score_by_region": averages, "max_score_gap": disparity}


def build_monitoring_report(
    reference_dir: Path,
    current_dir: Path,
    output: Path,
    now: float | None = None,
    customers_csv: Path | None = None,
) -> dict[str, object]:
    required = (
        "predictive_metrics.json",
        "churn_scores.csv",
        "customer_segments.csv",
    )
    missing = [filename for filename in required if not (current_dir / filename).is_file()]
    forecast_fallback = (
        not (current_dir / "demand_forecast.csv").is_file()
        and (current_dir / "fallback_forecast.csv").is_file()
    )
    if missing:
        psi = None
        status = "critical"
    else:
        psi = population_stability_index(_scores(reference_dir), _scores(current_dir))
        status = "critical" if psi >= 0.25 else "warning" if psi >= 0.1 else "ok"
    timestamp = now if now is not None else time.time()
    ages = {
        filename: round((timestamp - (current_dir / filename).stat().st_mtime) / 3600, 2)
        for filename in required
        if (current_dir / filename).is_file()
    }
    report: dict[str, object] = {
        "status": status,
        "psi": psi,
        "missing_artifacts": missing,
        "artifact_age_hours": ages,
        "forecast_fallback_active": forecast_fallback,
        "thresholds": {"warning": 0.1, "critical": 0.25},
    }
    if not missing:
        metrics = json.loads((current_dir / "predictive_metrics.json").read_text(encoding="utf-8"))
        report["churn_calibration_error"] = metrics.get("churn", {}).get("calibration_error")
        report["fairness"] = _fairness(current_dir, customers_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
