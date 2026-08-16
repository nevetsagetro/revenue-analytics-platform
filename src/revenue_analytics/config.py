from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 42
    start_date: date = date(2024, 1, 1)
    end_date: date = date(2025, 12, 31)
    n_customers: int = 200
    n_products: int = 24
    n_transactions: int = 2_000

    @classmethod
    def from_profile(cls, profile: str, seed: int) -> "GeneratorConfig":
        if profile == "demo":
            return cls(seed=seed)
        if profile == "portfolio":
            return cls(seed=seed, n_customers=50_000, n_products=500, n_transactions=250_000)
        raise ValueError(f"Unknown profile: {profile}")


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def warehouse(self) -> Path:
        return self.root / "warehouse" / "revenue.db"
