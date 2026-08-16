import csv
import hashlib
import math
import random
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from revenue_analytics.config import GeneratorConfig


@dataclass(frozen=True)
class GeneratedDataset:
    files: dict[str, Path]
    checksums: dict[str, str]


REGIONS = ("norte", "centro", "este", "sur")
CHANNELS = ("store", "online")
CATEGORIES = ("bebidas", "despensa", "hogar", "cuidado_personal")


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate_dataset(config: GeneratorConfig, output_dir: Path) -> GeneratedDataset:
    if config.start_date >= config.end_date:
        raise ValueError("start_date must be before end_date")
    if min(config.n_customers, config.n_products, config.n_transactions) <= 0:
        raise ValueError("dataset sizes must be positive")

    rng = random.Random(config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    days = (config.end_date - config.start_date).days + 1

    customers = [
        {
            "customer_id": f"C{i:06d}",
            "signup_date": (config.start_date - timedelta(days=rng.randrange(0, 730))).isoformat(),
            "region": rng.choice(REGIONS),
            "activity_score": f"{rng.betavariate(2, 5):.6f}",
        }
        for i in range(1, config.n_customers + 1)
    ]
    category_elasticity = dict(zip(CATEGORIES, (-1.1, -0.8, -1.4, -1.8), strict=True))
    products: list[dict[str, object]] = []
    for i in range(1, config.n_products + 1):
        category = CATEGORIES[(i - 1) % len(CATEGORIES)]
        base_price = rng.randrange(250, 8_001)
        products.append(
            {
                "product_id": f"P{i:04d}",
                "sku": f"SKU-{i:04d}",
                "category": category,
                "base_price_cents": base_price,
                "unit_cost_cents": round(base_price * rng.uniform(0.35, 0.7)),
                "latent_elasticity": category_elasticity[category],
            }
        )

    transactions: list[dict[str, object]] = []
    lines: list[dict[str, object]] = []
    for ticket_number in range(1, config.n_transactions + 1):
        transaction_id = f"T{ticket_number:09d}"
        customer = rng.choice(customers)
        transaction_date = config.start_date + timedelta(days=rng.randrange(days))
        channel = rng.choices(CHANNELS, weights=(0.7, 0.3), k=1)[0]
        transactions.append(
            {
                "transaction_id": transaction_id,
                "customer_id": customer["customer_id"],
                "transaction_date": transaction_date.isoformat(),
                "channel": channel,
                "region": customer["region"],
            }
        )
        line_count = rng.choices((1, 2, 3, 4), weights=(25, 40, 25, 10), k=1)[0]
        selected_products = rng.sample(products, k=min(line_count, len(products)))
        annual = 1 + 0.15 * math.sin(2 * math.pi * transaction_date.timetuple().tm_yday / 365)
        for line_number, product in enumerate(selected_products, start=1):
            promotion = rng.random() < (0.18 * annual)
            discount = rng.choice((0.05, 0.10, 0.15, 0.20, 0.25)) if promotion else 0.0
            observed_price = round(int(product["base_price_cents"]) * (1 - discount))
            demand_multiplier = (observed_price / int(product["base_price_cents"])) ** float(
                product["latent_elasticity"]
            )
            quantity = max(1, round(rng.lognormvariate(0.3, 0.55) * demand_multiplier))
            lines.append(
                {
                    "line_id": f"{transaction_id}-{line_number}",
                    "transaction_id": transaction_id,
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "unit_price_cents": observed_price,
                    "discount_pct": f"{discount:.2f}",
                    "promotion": int(promotion),
                }
            )

    tables = {
        "customers": (customers, ("customer_id", "signup_date", "region", "activity_score")),
        "products": (
            products,
            (
                "product_id",
                "sku",
                "category",
                "base_price_cents",
                "unit_cost_cents",
                "latent_elasticity",
            ),
        ),
        "transactions": (
            transactions,
            ("transaction_id", "customer_id", "transaction_date", "channel", "region"),
        ),
        "transaction_lines": (
            lines,
            (
                "line_id",
                "transaction_id",
                "product_id",
                "quantity",
                "unit_price_cents",
                "discount_pct",
                "promotion",
            ),
        ),
    }
    files: dict[str, Path] = {}
    checksums: dict[str, str] = {}
    for name, (rows, fieldnames) in tables.items():
        path = output_dir / f"{name}.csv"
        files[name] = path
        checksums[name] = _write_csv(path, fieldnames, rows)
    return GeneratedDataset(files=files, checksums=checksums)
