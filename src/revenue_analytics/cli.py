import argparse
from pathlib import Path

from revenue_analytics.config import GeneratorConfig, ProjectPaths
from revenue_analytics.generator import generate_dataset
from revenue_analytics.warehouse import build_warehouse, business_summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="revenue-analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="generate data and build the local warehouse")
    demo.add_argument("--output-dir", type=Path, default=Path("data"))
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--profile", choices=("demo", "portfolio"), default="demo")
    inspect = subparsers.add_parser("inspect", help="show warehouse business totals")
    inspect.add_argument("--database", type=Path, default=Path("data/warehouse/revenue.db"))
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
    else:
        _print_summary(business_summary(args.database))
