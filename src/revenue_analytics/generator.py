import csv
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

from revenue_analytics import __version__
from revenue_analytics.config import GeneratorConfig


@dataclass(frozen=True)
class GeneratedDataset:
    files: dict[str, Path]
    checksums: dict[str, str]
    row_counts: dict[str, int]
    manifest: Path


REGIONS = ("norte", "centro", "este", "sur")
CATEGORIES = ("bebidas", "despensa", "hogar", "cuidado_personal")
TABLE_FIELDS = {
    "customers": ("customer_id", "signup_date", "region", "activity_score"),
    "products": (
        "product_id",
        "sku",
        "category",
        "base_price_cents",
        "unit_cost_cents",
        "latent_elasticity",
    ),
    "stores": ("store_id", "store_name", "channel", "region"),
    "price_history": (
        "price_id",
        "product_id",
        "channel",
        "valid_from",
        "valid_to",
        "list_price_cents",
    ),
    "transactions": (
        "transaction_id",
        "customer_id",
        "store_id",
        "transaction_date",
    ),
    "transaction_lines": (
        "line_id",
        "transaction_id",
        "product_id",
        "quantity",
        "unit_price_cents",
        "discount_pct",
        "promotion",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> str:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return _sha256(path)


def _serializable_config(config: GeneratorConfig) -> dict[str, object]:
    values = asdict(config)
    values["start_date"] = config.start_date.isoformat()
    values["end_date"] = config.end_date.isoformat()
    return values


def _quarter_starts(start: date, end: date) -> list[date]:
    current = date(start.year, 3 * ((start.month - 1) // 3) + 1, 1)
    starts: list[date] = []
    while current <= end:
        starts.append(current)
        month = current.month + 3
        current = date(current.year + (month - 1) // 12, (month - 1) % 12 + 1, 1)
    return starts


def generate_dataset(config: GeneratorConfig, output_dir: Path) -> GeneratedDataset:
    if config.start_date >= config.end_date:
        raise ValueError("start_date must be before end_date")
    if min(config.n_customers, config.n_products, config.n_stores, config.n_transactions) <= 0:
        raise ValueError("dataset sizes must be positive")

    rng = random.Random(config.seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    days = (config.end_date - config.start_date).days + 1

    customers = [
        {
            "customer_id": f"C{i:06d}",
            "signup_date": (config.start_date - timedelta(days=rng.randrange(730))).isoformat(),
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

    stores = [
        {
            "store_id": "S000",
            "store_name": "Tienda online",
            "channel": "online",
            "region": "nacional",
        }
    ]
    stores.extend(
        {
            "store_id": f"S{i:03d}",
            "store_name": f"Tienda {i:03d}",
            "channel": "store",
            "region": REGIONS[(i - 1) % len(REGIONS)],
        }
        for i in range(1, config.n_stores + 1)
    )

    quarter_starts = _quarter_starts(config.start_date, config.end_date)
    price_history: list[dict[str, object]] = []
    prices: dict[tuple[str, str, date], int] = {}
    for product in products:
        for channel in ("store", "online"):
            channel_factor = 1.02 if channel == "online" else 1.0
            for period, valid_from in enumerate(quarter_starts):
                valid_to = (
                    quarter_starts[period + 1] - timedelta(days=1)
                    if period + 1 < len(quarter_starts)
                    else config.end_date
                )
                trend = 1 + 0.008 * period + rng.uniform(-0.015, 0.015)
                list_price = round(int(product["base_price_cents"]) * channel_factor * trend)
                price_history.append(
                    {
                        "price_id": f"PH-{product['product_id']}-{channel}-{period:02d}",
                        "product_id": product["product_id"],
                        "channel": channel,
                        "valid_from": valid_from.isoformat(),
                        "valid_to": valid_to.isoformat(),
                        "list_price_cents": list_price,
                    }
                )
                prices[(str(product["product_id"]), channel, valid_from)] = list_price

    transactions: list[dict[str, object]] = []
    lines: list[dict[str, object]] = []
    for ticket_number in range(1, config.n_transactions + 1):
        transaction_id = f"T{ticket_number:09d}"
        customer = rng.choice(customers)
        transaction_date = config.start_date + timedelta(days=rng.randrange(days))
        online = rng.random() < 0.3
        candidate_stores = [
            store
            for store in stores
            if (store["channel"] == "online") == online
            and (online or store["region"] == customer["region"])
        ]
        if not candidate_stores:
            candidate_stores = [store for store in stores if store["channel"] == "store"]
        store = rng.choice(candidate_stores)
        transactions.append(
            {
                "transaction_id": transaction_id,
                "customer_id": customer["customer_id"],
                "store_id": store["store_id"],
                "transaction_date": transaction_date.isoformat(),
            }
        )
        line_count = rng.choices((1, 2, 3, 4), weights=(25, 40, 25, 10), k=1)[0]
        selected_products = rng.sample(products, k=min(line_count, len(products)))
        annual = 1 + 0.15 * math.sin(2 * math.pi * transaction_date.timetuple().tm_yday / 365)
        quarter_start = date(transaction_date.year, 3 * ((transaction_date.month - 1) // 3) + 1, 1)
        for line_number, product in enumerate(selected_products, start=1):
            promotion = rng.random() < (0.18 * annual)
            discount = rng.choice((0.05, 0.10, 0.15, 0.20, 0.25)) if promotion else 0.0
            list_price = prices[(str(product["product_id"]), str(store["channel"]), quarter_start)]
            observed_price = round(list_price * (1 - discount))
            demand_multiplier = (observed_price / list_price) ** float(product["latent_elasticity"])
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
        "customers": customers,
        "products": products,
        "stores": stores,
        "price_history": price_history,
        "transactions": transactions,
        "transaction_lines": lines,
    }
    files: dict[str, Path] = {}
    checksums: dict[str, str] = {}
    row_counts: dict[str, int] = {}
    for name, rows in tables.items():
        path = output_dir / f"{name}.csv"
        files[name] = path
        row_counts[name] = len(rows)
        checksums[name] = _write_csv(path, TABLE_FIELDS[name], rows)

    manifest = output_dir / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "generator_version": __version__,
                "config": _serializable_config(config),
                "row_counts": row_counts,
                "sha256": checksums,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return GeneratedDataset(files, checksums, row_counts, manifest)
