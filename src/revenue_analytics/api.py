import csv
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse


class ArtifactRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _json(self, filename: str) -> dict[str, object]:
        path = self.root / filename
        if not path.is_file():
            raise HTTPException(status_code=503, detail=f"Missing artifact: {filename}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _csv(self, filename: str) -> list[dict[str, str]]:
        path = self.root / filename
        if not path.is_file():
            raise HTTPException(status_code=503, detail=f"Missing artifact: {filename}")
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def ready(self) -> bool:
        required = (
            "predictive_metrics.json",
            "demand_forecast.csv",
            "churn_scores.csv",
            "customer_segments.csv",
        )
        return all((self.root / filename).is_file() for filename in required)


def _dashboard(
    metrics: dict[str, object],
    forecasts: list[dict[str, str]],
    segments: list[dict[str, str]],
    causal: dict[str, object] | None,
) -> str:
    churn = metrics["churn"]
    best_forecast = metrics["forecast"][0]
    segment_counts: dict[str, int] = {}
    for row in segments:
        segment_counts[row["segment"]] = segment_counts.get(row["segment"], 0) + 1
    segment_text = ", ".join(f"{name}: {count:,}" for name, count in sorted(segment_counts.items()))
    elasticity = causal["elasticity"]["estimate"] if causal else "no disponible"
    forecast_rows = "".join(
        f"<tr><td>{row['week_start']}</td><td>{row['forecast_units']}</td></tr>"
        for row in forecasts
    )
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Revenue Analytics</title>
<style>body{{font-family:system-ui;max-width:1000px;margin:40px auto;color:#17202a}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
.card{{padding:20px;border:1px solid #ddd;border-radius:10px}}table{{width:100%;margin-top:24px}}
td,th{{padding:8px;text-align:left;border-bottom:1px solid #eee}}</style></head>
<body><h1>Revenue Analytics Platform</h1>
<p>Resultados sintéticos para demostrar el flujo de decisión.</p><div class="cards">
<div class="card"><b>Forecast WAPE</b><br>{best_forecast["wape"]:.2%}</div>
<div class="card"><b>Churn AUC</b><br>{churn["auc"]:.3f}</div>
<div class="card"><b>Churn Brier</b><br>{churn["brier"]:.3f}</div></div>
<h2>Decisiones</h2><p><b>Segmentos:</b> {segment_text}</p>
<p><b>Elasticidad precio-demanda:</b> {elasticity}</p>
<h2>Demanda proyectada</h2><table><tr><th>Semana</th><th>Unidades</th></tr>{forecast_rows}</table>
</body></html>"""


def create_app(artifact_dir: Path | None = None, causal_dir: Path | None = None) -> FastAPI:
    root = artifact_dir or Path(os.getenv("RAP_ARTIFACT_DIR", "artifacts/predictive"))
    repository = ArtifactRepository(root)
    causal_root = causal_dir or Path(os.getenv("RAP_CAUSAL_DIR", str(root.parent / "causal")))
    causal_repository = ArtifactRepository(causal_root)
    app = FastAPI(title="Revenue Analytics API", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok" if repository.ready() else "degraded"}

    @app.get("/v1/metrics")
    def metrics() -> dict[str, object]:
        return repository._json("predictive_metrics.json")

    @app.get("/v1/causal")
    def causal_metrics() -> dict[str, object]:
        return causal_repository._json("causal_metrics.json")

    @app.get("/v1/forecast")
    def forecast(horizon: int = Query(default=8, ge=1, le=8)) -> list[dict[str, str]]:
        filename = (
            "demand_forecast.csv"
            if (repository.root / "demand_forecast.csv").is_file()
            else "fallback_forecast.csv"
        )
        return repository._csv(filename)[:horizon]

    @app.get("/v1/churn/{customer_id}")
    def churn(customer_id: str) -> dict[str, str]:
        match = next(
            (
                row
                for row in repository._csv("churn_scores.csv")
                if row["customer_id"] == customer_id
            ),
            None,
        )
        if match is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return match

    @app.get("/v1/segments/{customer_id}")
    def segment(customer_id: str) -> dict[str, str]:
        match = next(
            (
                row
                for row in repository._csv("customer_segments.csv")
                if row["customer_id"] == customer_id
            ),
            None,
        )
        if match is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        return match

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard() -> str:
        forecast_file = (
            "demand_forecast.csv"
            if (repository.root / "demand_forecast.csv").is_file()
            else "fallback_forecast.csv"
        )
        return _dashboard(
            repository._json("predictive_metrics.json"),
            repository._csv(forecast_file),
            repository._csv("customer_segments.csv"),
            causal_repository._json("causal_metrics.json")
            if (causal_root / "causal_metrics.json").is_file()
            else None,
        )

    return app


app = create_app()
