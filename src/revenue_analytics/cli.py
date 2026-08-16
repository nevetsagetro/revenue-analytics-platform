import argparse
from pathlib import Path

from revenue_analytics.causal import build_causal_artifacts
from revenue_analytics.config import GeneratorConfig, ProjectPaths
from revenue_analytics.generator import generate_dataset
from revenue_analytics.predictive import build_predictive_artifacts
from revenue_analytics.quality import validate_all
from revenue_analytics.reporting import build_business_report
from revenue_analytics.warehouse import (
    available_analyses,
    build_warehouse,
    business_summary,
    run_analysis,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="revenue-analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="generate data and build the local warehouse")
    demo.add_argument("--output-dir", type=Path, default=Path("data"))
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--profile", choices=("demo", "portfolio"), default="demo")
    inspect = subparsers.add_parser("inspect", help="show warehouse business totals")
    inspect.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
    validate = subparsers.add_parser("validate", help="validate raw data and warehouse contracts")
    validate.add_argument("--data-dir", type=Path, default=Path("data"))
    analyze = subparsers.add_parser("analyze", help="run a versioned analytical query")
    analyze.add_argument("query", choices=available_analyses())
    analyze.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
    analyze.add_argument("--limit", type=int, default=20)
    report = subparsers.add_parser("report", help="build the initial business and OLS report")
    report.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
    report.add_argument("--output", type=Path, default=Path("artifacts/business-report.md"))
    predict = subparsers.add_parser(
        "predict", help="build forecasting, churn, and segment artifacts"
    )
    predict.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
    predict.add_argument("--output-dir", type=Path, default=Path("artifacts/predictive"))
    causal = subparsers.add_parser("causal", help="build elasticity and experiment artifacts")
    causal.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
    causal.add_argument("--output-dir", type=Path, default=Path("artifacts/causal"))
    return parser


def _print_summary(summary: dict[str, int]) -> None:
    print(f"Revenue: EUR {summary['revenue_cents'] / 100:,.2f}")
    print(f"Units: {summary['units']:,}")
    print(f"Tickets: {summary['tickets']:,}")
    print(f"Active customers: {summary['customers']:,}")


def main() -> None:
    args = _parser().parse_args()
    if args.command == "demo":
        paths = ProjectPaths(args.output_dir)
        config = GeneratorConfig.from_profile(args.profile, args.seed)
        dataset = generate_dataset(config, paths.raw)
        build_warehouse(paths.raw, paths.warehouse)
        print(f"Generated {len(dataset.files)} deterministic tables in {paths.raw}")
        print(f"Warehouse: {paths.warehouse}")
        _print_summary(business_summary(paths.warehouse))
    elif args.command == "inspect":
        _print_summary(business_summary(args.database))
    elif args.command == "validate":
        paths = ProjectPaths(args.data_dir)
        result = validate_all(paths.raw, paths.warehouse)
        for check, passed in result.checks.items():
            print(f"{'PASS' if passed else 'FAIL'} {check}")
        if not result.passed:
            raise SystemExit(1)
    elif args.command == "analyze":
        columns, rows = run_analysis(args.database, args.query)
        print(" | ".join(columns))
        for row in rows[: args.limit]:
            print(" | ".join(str(value) for value in row))
    elif args.command == "report":
        print(build_business_report(args.database, args.output))
    elif args.command == "predict":
        artifacts = build_predictive_artifacts(args.database, args.output_dir)
        for name, path in artifacts.items():
            print(f"{name}: {path}")
    else:
        artifacts = build_causal_artifacts(args.database, args.output_dir)
        for name, path in artifacts.items():
            print(f"{name}: {path}")
