import json
import math
import random
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Estimate:
    estimate: float
    standard_error: float
    ci_low: float
    ci_high: float


@dataclass(frozen=True)
class ExperimentResult:
    true_effect: float
    difference_in_means: Estimate
    cuped: Estimate
    variance_reduction: float
    required_sample_size: int


@dataclass(frozen=True)
class DidResult:
    true_effect: float
    estimate: Estimate
    placebo: Estimate


def _inverse(matrix: list[list[float]]) -> list[list[float]]:
    size = len(matrix)
    augmented = [row[:] + [float(i == j) for j in range(size)] for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular design matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column], strict=True)
            ]
    return [row[size:] for row in augmented]


def _ols(features: list[list[float]], outcomes: list[float]) -> tuple[list[float], list[float]]:
    columns = len(features[0])
    xtx = [[0.0] * columns for _ in range(columns)]
    xty = [0.0] * columns
    for row, outcome in zip(features, outcomes, strict=True):
        for left in range(columns):
            xty[left] += row[left] * outcome
            for right in range(columns):
                xtx[left][right] += row[left] * row[right]
    inverse = _inverse(xtx)
    coefficients = [
        sum(inverse[row][col] * xty[col] for col in range(columns)) for row in range(columns)
    ]
    residuals = [
        outcome
        - sum(coefficient * value for coefficient, value in zip(coefficients, row, strict=True))
        for row, outcome in zip(features, outcomes, strict=True)
    ]
    variance = sum(value**2 for value in residuals) / (len(features) - columns)
    standard_errors = [
        math.sqrt(max(0.0, variance * inverse[index][index])) for index in range(columns)
    ]
    return coefficients, standard_errors


def estimate_price_elasticity(database: Path) -> Estimate:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            """SELECT quantity, unit_price_cents, list_price_cents, promotion, channel,
                      CAST(strftime('%j', transaction_date) AS INTEGER)
               FROM stg_sales"""
        ).fetchall()
    if len(rows) > 100_000:
        rows = rows[:: math.ceil(len(rows) / 100_000)]
    features = []
    outcomes = []
    for quantity, price, list_price, promotion, channel, day_of_year in rows:
        angle = 2 * math.pi * day_of_year / 365.25
        features.append(
            [
                1.0,
                math.log(price / list_price),
                float(promotion),
                float(channel == "online"),
                math.sin(angle),
                math.cos(angle),
            ]
        )
        outcomes.append(math.log(quantity))
    coefficients, errors = _ols(features, outcomes)
    estimate = coefficients[1]
    standard_error = errors[1]
    return Estimate(
        estimate,
        standard_error,
        estimate - 1.96 * standard_error,
        estimate + 1.96 * standard_error,
    )


def _difference(values: list[float], treatment: list[int]) -> Estimate:
    treated = [value for value, group in zip(values, treatment, strict=True) if group]
    control = [value for value, group in zip(values, treatment, strict=True) if not group]
    estimate = sum(treated) / len(treated) - sum(control) / len(control)
    treated_mean = sum(treated) / len(treated)
    control_mean = sum(control) / len(control)
    variance_t = sum((value - treated_mean) ** 2 for value in treated) / (len(treated) - 1)
    variance_c = sum((value - control_mean) ** 2 for value in control) / (len(control) - 1)
    standard_error = math.sqrt(variance_t / len(treated) + variance_c / len(control))
    return Estimate(
        estimate,
        standard_error,
        estimate - 1.96 * standard_error,
        estimate + 1.96 * standard_error,
    )


def simulate_experiment(seed: int = 42, sample_size: int = 5_000) -> ExperimentResult:
    rng = random.Random(seed)
    treatment = [int(rng.random() < 0.5) for _ in range(sample_size)]
    pre = [rng.gauss(50, 12) for _ in range(sample_size)]
    true_effect = 5.0
    outcome = [
        50 + 0.7 * (before - 50) + true_effect * group + rng.gauss(0, 8)
        for before, group in zip(pre, treatment, strict=True)
    ]
    raw = _difference(outcome, treatment)
    pre_mean = sum(pre) / len(pre)
    outcome_mean = sum(outcome) / len(outcome)
    covariance = sum(
        (x - pre_mean) * (y - outcome_mean) for x, y in zip(pre, outcome, strict=True)
    ) / len(pre)
    pre_variance = sum((value - pre_mean) ** 2 for value in pre) / len(pre)
    theta = covariance / pre_variance
    adjusted = [
        value - theta * (before - pre_mean) for value, before in zip(outcome, pre, strict=True)
    ]
    cuped = _difference(adjusted, treatment)
    variance_reduction = 1 - cuped.standard_error**2 / raw.standard_error**2
    pooled_sd = math.sqrt(raw.standard_error**2 * sample_size / 4)
    required = math.ceil(2 * ((1.96 + 0.84) * pooled_sd / true_effect) ** 2)
    return ExperimentResult(true_effect, raw, cuped, variance_reduction, required)


def simulate_difference_in_differences(seed: int = 42, units: int = 2_000) -> DidResult:
    rng = random.Random(seed)
    values: dict[tuple[int, int], list[float]] = {
        (group, period): [] for group in (0, 1) for period in (-1, 0, 1)
    }
    true_effect = 8.0
    for group in (0, 1):
        for period in (-1, 0, 1):
            for _ in range(units):
                outcome = 100 + 4 * group + 6 * (period + 1)
                outcome += true_effect * group * int(period == 1) + rng.gauss(0, 15)
                values[(group, period)].append(outcome)
    means = {key: sum(group_values) / len(group_values) for key, group_values in values.items()}
    estimate = (means[(1, 1)] - means[(1, 0)]) - (means[(0, 1)] - means[(0, 0)])
    placebo = (means[(1, 0)] - means[(1, -1)]) - (means[(0, 0)] - means[(0, -1)])
    standard_error = math.sqrt(sum(15**2 / len(group_values) for group_values in values.values()))
    effect_result = Estimate(
        estimate,
        standard_error,
        estimate - 1.96 * standard_error,
        estimate + 1.96 * standard_error,
    )
    placebo_result = Estimate(
        placebo,
        standard_error,
        placebo - 1.96 * standard_error,
        placebo + 1.96 * standard_error,
    )
    return DidResult(true_effect, effect_result, placebo_result)


def build_causal_artifacts(database: Path, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    elasticity = estimate_price_elasticity(database)
    experiment = simulate_experiment()
    did = simulate_difference_in_differences()
    results = output_dir / "causal_metrics.json"
    results.write_text(
        json.dumps(
            {
                "elasticity": asdict(elasticity),
                "experiment": asdict(experiment),
                "did": asdict(did),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    decision = output_dir / "causal_decision.md"
    decision.write_text(
        "\n".join(
            (
                "# Decisión causal sintética",
                "",
                f"- Elasticidad controlada: {elasticity.estimate:.3f} "
                f"(IC95% {elasticity.ci_low:.3f}, {elasticity.ci_high:.3f}).",
                f"- Efecto A/B estimado: {experiment.cuped.estimate:.2f}; "
                f"verdad sintética: {experiment.true_effect:.2f}.",
                f"- CUPED reduce la varianza un {experiment.variance_reduction * 100:.1f}%.",
                f"- DiD estimado: {did.estimate.estimate:.2f}; "
                f"verdad sintética: {did.true_effect:.2f}.",
                f"- Placebo pretratamiento DiD: {did.placebo.estimate:.2f}.",
                "",
                "Recomendación: usar experimentación aleatoria para intervenciones de retención; "
                "tratar la elasticidad observacional como evidencia condicionada a sus controles.",
                "",
            )
        ),
        encoding="utf-8",
    )
    return {"metrics": results, "decision": decision}
