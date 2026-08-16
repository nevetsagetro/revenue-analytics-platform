import csv
import json
import math
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class ForecastMetrics:
    model: str
    folds: int
    wape: float
    mase: float


@dataclass(frozen=True)
class ChurnMetrics:
    observations: int
    positive_rate: float
    auc: float
    brier: float
    calibration_error: float
    rule_auc: float
    rule_brier: float


def _weekly_demand(database: Path) -> list[tuple[date, int]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """SELECT date(transaction_date, '-' || ((strftime('%w', transaction_date) + 6) % 7)
                       || ' days') AS week_start, SUM(units)
               FROM mart_sales_daily GROUP BY week_start ORDER BY week_start"""
        ).fetchall()
    return [(date.fromisoformat(week), int(units)) for week, units in rows]


def _forecast_errors(
    actual: list[float], predicted: list[float], training: list[float]
) -> tuple[float, float]:
    absolute_errors = [abs(a - p) for a, p in zip(actual, predicted, strict=True)]
    wape = sum(absolute_errors) / sum(abs(value) for value in actual)
    scale = sum(abs(training[i] - training[i - 1]) for i in range(1, len(training))) / (
        len(training) - 1
    )
    mase = sum(absolute_errors) / len(absolute_errors) / scale
    return wape, mase


def backtest_forecasts(database: Path, folds: int = 8) -> list[ForecastMetrics]:
    series = [float(units) for _, units in _weekly_demand(database)]
    if len(series) < folds + 53:
        raise ValueError("forecast backtest requires at least 61 complete weeks")
    models: dict[str, list[tuple[float, float, list[float]]]] = defaultdict(list)
    for index in range(len(series) - folds, len(series)):
        training = series[:index]
        actual = series[index]
        models["naive"].append((actual, training[-1], training))
        models["seasonal_naive"].append((actual, training[-52], training))
        models["moving_average_4"].append((actual, sum(training[-4:]) / 4, training))
        level = training[0]
        for value in training[1:]:
            level = 0.3 * value + 0.7 * level
        models["exponential_smoothing"].append((actual, level, training))
        trend_window = training[-12:]
        mean_x = (len(trend_window) - 1) / 2
        mean_y = sum(trend_window) / len(trend_window)
        slope = sum(
            (position - mean_x) * (value - mean_y) for position, value in enumerate(trend_window)
        ) / sum((position - mean_x) ** 2 for position in range(len(trend_window)))
        trend_forecast = max(0.0, mean_y + slope * (len(trend_window) - mean_x))
        models["linear_trend_12"].append((actual, trend_forecast, training))
    results: list[ForecastMetrics] = []
    for model, observations in models.items():
        actual = [row[0] for row in observations]
        predicted = [row[1] for row in observations]
        wape, mase = _forecast_errors(actual, predicted, observations[-1][2])
        results.append(ForecastMetrics(model, len(observations), wape, mase))
    return sorted(results, key=lambda metric: metric.wape)


def forecast_next_weeks(database: Path, horizon: int = 8) -> list[dict[str, object]]:
    weekly = _weekly_demand(database)
    window = [float(units) for _, units in weekly[-12:]]
    mean_x = (len(window) - 1) / 2
    mean_y = sum(window) / len(window)
    slope = sum(
        (position - mean_x) * (value - mean_y) for position, value in enumerate(window)
    ) / sum((position - mean_x) ** 2 for position in range(len(window)))
    last_week = weekly[-1][0]
    forecasts = []
    for step in range(1, horizon + 1):
        prediction = mean_y + slope * (len(window) - 1 + step - mean_x)
        forecasts.append(
            {
                "week_start": (last_week + timedelta(days=7 * step)).isoformat(),
                "forecast_units": round(max(0.0, prediction), 2),
                "model": "linear_trend_12",
            }
        )
    return forecasts


def _customer_history(database: Path) -> tuple[date, date, dict[str, list[tuple[date, int]]]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """SELECT customer_id, transaction_date, SUM(line_revenue_cents)
               FROM stg_sales GROUP BY customer_id, transaction_date
               ORDER BY customer_id, transaction_date"""
        ).fetchall()
    history: dict[str, list[tuple[date, int]]] = defaultdict(list)
    for customer_id, purchase_date, revenue in rows:
        history[customer_id].append((date.fromisoformat(purchase_date), int(revenue)))
    dates = [purchase_date for purchases in history.values() for purchase_date, _ in purchases]
    return min(dates), max(dates), history


def _churn_observations(database: Path) -> list[tuple[list[float], int]]:
    start, end, history = _customer_history(database)
    cutoff = start + timedelta(days=180)
    observations: list[tuple[list[float], int]] = []
    while cutoff + timedelta(days=60) <= end:
        for purchases in history.values():
            past = [(day, revenue) for day, revenue in purchases if day <= cutoff]
            if not past:
                continue
            future = any(cutoff < day <= cutoff + timedelta(days=60) for day, _ in purchases)
            recency = (cutoff - past[-1][0]).days
            frequency = len(past)
            monetary = sum(revenue for _, revenue in past) / 100.0
            features = [recency, math.log1p(frequency), math.log1p(monetary)]
            observations.append((features, int(not future)))
        cutoff += timedelta(days=60)
    return observations


def _standardize(rows: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    means = [sum(row[i] for row in rows) / len(rows) for i in range(len(rows[0]))]
    scales = [
        math.sqrt(sum((row[i] - means[i]) ** 2 for row in rows) / len(rows)) or 1.0
        for i in range(len(rows[0]))
    ]
    standardized = [[(value - means[i]) / scales[i] for i, value in enumerate(row)] for row in rows]
    return standardized, means, scales


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(-30.0, min(30.0, value))))


def _fit_logistic(features: list[list[float]], labels: list[int]) -> list[float]:
    weights = [0.0] * (len(features[0]) + 1)
    for _ in range(250):
        gradients = [0.0] * len(weights)
        for row, label in zip(features, labels, strict=True):
            linear_score = weights[0] + sum(w * x for w, x in zip(weights[1:], row, strict=True))
            probability = _sigmoid(linear_score)
            error = probability - label
            gradients[0] += error
            for index, value in enumerate(row, start=1):
                gradients[index] += error * value
        for index in range(len(weights)):
            penalty = 0.01 * weights[index] if index else 0.0
            weights[index] -= 0.1 * (gradients[index] / len(features) + penalty)
    return weights


def _auc(labels: list[int], probabilities: list[float]) -> float:
    positive = [prob for label, prob in zip(labels, probabilities, strict=True) if label]
    negative = [prob for label, prob in zip(labels, probabilities, strict=True) if not label]
    if not positive or not negative:
        return 0.5
    wins = sum((p > n) + 0.5 * (p == n) for p in positive for n in negative)
    return wins / (len(positive) * len(negative))


def _train_churn_model(database: Path) -> tuple[ChurnMetrics, dict[str, list[float]]]:
    observations = _churn_observations(database)
    if len(observations) > 50_000:
        stride = math.ceil(len(observations) / 50_000)
        observations = observations[::stride]
    train_end = int(len(observations) * 0.7)
    calibration_end = int(len(observations) * 0.85)
    train = observations[:train_end]
    calibration = observations[train_end:calibration_end]
    test = observations[calibration_end:]
    train_x, means, scales = _standardize([row for row, _ in train])
    calibration_x = [
        [(value - means[i]) / scales[i] for i, value in enumerate(row)] for row, _ in calibration
    ]
    test_x = [[(value - means[i]) / scales[i] for i, value in enumerate(row)] for row, _ in test]
    weights = _fit_logistic(train_x, [label for _, label in train])
    calibration_scores = [
        weights[0] + sum(w * x for w, x in zip(weights[1:], row, strict=True))
        for row in calibration_x
    ]
    calibration_weights = _fit_logistic(
        [[score] for score in calibration_scores], [label for _, label in calibration]
    )
    test_scores = [
        weights[0] + sum(w * x for w, x in zip(weights[1:], row, strict=True)) for row in test_x
    ]
    probabilities = [
        _sigmoid(calibration_weights[0] + calibration_weights[1] * score) for score in test_scores
    ]
    labels = [label for _, label in test]
    brier = sum(
        (prob - label) ** 2 for prob, label in zip(probabilities, labels, strict=True)
    ) / len(labels)
    calibration_error = 0.0
    for lower in (index / 10 for index in range(10)):
        bucket = [
            (probability, label)
            for probability, label in zip(probabilities, labels, strict=True)
            if lower <= probability < lower + 0.1
        ]
        if bucket:
            calibration_error += (
                len(bucket)
                / len(labels)
                * abs(
                    sum(probability for probability, _ in bucket) / len(bucket)
                    - sum(label for _, label in bucket) / len(bucket)
                )
            )
    rule_probabilities = [min(0.95, max(0.05, row[0] / 120)) for row, _ in test]
    rule_brier = sum(
        (prob - label) ** 2 for prob, label in zip(rule_probabilities, labels, strict=True)
    ) / len(labels)
    metrics = ChurnMetrics(
        len(test),
        sum(labels) / len(labels),
        _auc(labels, probabilities),
        brier,
        calibration_error,
        _auc(labels, rule_probabilities),
        rule_brier,
    )
    model = {
        "means": means,
        "scales": scales,
        "weights": weights,
        "calibration_weights": calibration_weights,
    }
    return metrics, model


def train_churn_baseline(database: Path) -> ChurnMetrics:
    return _train_churn_model(database)[0]


def _current_churn_scores(database: Path, model: dict[str, list[float]]) -> list[dict[str, object]]:
    _, cutoff, history = _customer_history(database)
    means = model["means"]
    scales = model["scales"]
    weights = model["weights"]
    calibration = model["calibration_weights"]
    scores: list[dict[str, object]] = []
    for customer_id, purchases in history.items():
        recency = (cutoff - purchases[-1][0]).days
        features = [
            recency,
            math.log1p(len(purchases)),
            math.log1p(sum(revenue for _, revenue in purchases) / 100.0),
        ]
        standardized = [
            (value - means[index]) / scales[index] for index, value in enumerate(features)
        ]
        raw_score = weights[0] + sum(
            weight * value for weight, value in zip(weights[1:], standardized, strict=True)
        )
        probability = _sigmoid(calibration[0] + calibration[1] * raw_score)
        scores.append(
            {
                "customer_id": customer_id,
                "as_of_date": cutoff.isoformat(),
                "churn_probability": f"{probability:.6f}",
            }
        )
    return scores


def customer_segments(database: Path) -> list[dict[str, object]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """SELECT customer_id, last_purchase_date, frequency, monetary_cents
               FROM mart_customer_activity ORDER BY customer_id"""
        ).fetchall()
        max_date = connection.execute("SELECT MAX(transaction_date) FROM stg_sales").fetchone()[0]
        anchor = date.fromisoformat(max_date)
    recencies = sorted((anchor - date.fromisoformat(row[1])).days for row in rows)
    frequencies = sorted(row[2] for row in rows)
    monetary = sorted(row[3] for row in rows)

    def tertile(value: int, values: list[int], reverse: bool = False) -> int:
        score = 1 + int(value >= values[len(values) // 3])
        score += int(value >= values[2 * len(values) // 3])
        return 4 - score if reverse else score

    segments = []
    for customer_id, last_purchase, frequency, monetary_cents in rows:
        recency = (anchor - date.fromisoformat(last_purchase)).days
        r = tertile(recency, recencies, reverse=True)
        f = tertile(frequency, frequencies)
        m = tertile(monetary_cents, monetary)
        total = r + f + m
        if total >= 8:
            label = "champions"
        elif total >= 6:
            label = "loyal"
        elif r == 1:
            label = "at_risk"
        else:
            label = "developing"
        segments.append(
            {
                "customer_id": customer_id,
                "recency_days": recency,
                "frequency": frequency,
                "monetary_cents": monetary_cents,
                "segment": label,
            }
        )
    return segments


def build_predictive_artifacts(database: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    forecast = backtest_forecasts(database)
    churn, churn_model = _train_churn_model(database)
    metrics_path = output_dir / "predictive_metrics.json"
    metrics = {
        "forecast": [asdict(item) for item in forecast],
        "churn": asdict(churn),
        "churn_model": churn_model,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    segments_path = output_dir / "customer_segments.csv"
    segments = customer_segments(database)
    with segments_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=segments[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(segments)
    churn_scores_path = output_dir / "churn_scores.csv"
    churn_scores = _current_churn_scores(database, churn_model)
    with churn_scores_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=churn_scores[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(churn_scores)
    forecast_path = output_dir / "demand_forecast.csv"
    forecasts = forecast_next_weeks(database)
    with forecast_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=forecasts[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(forecasts)
    return {
        "metrics": metrics_path,
        "segments": segments_path,
        "churn_scores": churn_scores_path,
        "forecast": forecast_path,
    }
