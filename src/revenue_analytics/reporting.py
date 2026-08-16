import math
import sqlite3
from pathlib import Path


def _elasticity(rows: list[tuple[float, float]]) -> float | None:
    observations = [
        (math.log(price), math.log(quantity)) for price, quantity in rows if quantity > 0
    ]
    if len(observations) < 2:
        return None
    mean_x = sum(x for x, _ in observations) / len(observations)
    mean_y = sum(y for _, y in observations) / len(observations)
    denominator = sum((x - mean_x) ** 2 for x, _ in observations)
    if denominator == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in observations) / denominator


def build_business_report(database: Path, output: Path) -> Path:
    with sqlite3.connect(database) as connection:
        totals = connection.execute(
            """SELECT SUM(line_revenue_cents), SUM(line_margin_cents),
                      COUNT(DISTINCT transaction_id), COUNT(DISTINCT customer_id)
               FROM stg_sales"""
        ).fetchone()
        top_category = connection.execute(
            """SELECT category, SUM(line_revenue_cents) AS revenue
               FROM stg_sales GROUP BY category ORDER BY revenue DESC LIMIT 1"""
        ).fetchone()
        channel_rows = connection.execute(
            """SELECT channel, SUM(line_revenue_cents) FROM stg_sales
               GROUP BY channel ORDER BY 2 DESC"""
        ).fetchall()
        promo_rows = connection.execute(
            "SELECT promotion, AVG(quantity) FROM stg_sales GROUP BY promotion"
        ).fetchall()
        repeat = connection.execute(
            """WITH orders AS (
                 SELECT customer_id, COUNT(DISTINCT transaction_id) n
                 FROM stg_sales GROUP BY customer_id
               ) SELECT AVG(n > 1) FROM orders"""
        ).fetchone()[0]
        elasticity_rows = connection.execute(
            "SELECT unit_price_cents / 100.0, quantity FROM stg_sales"
        ).fetchall()

    revenue, margin, tickets, customers = totals
    channel_text = ", ".join(f"{name}: EUR {value / 100:,.2f}" for name, value in channel_rows)
    promotion = dict(promo_rows)
    elasticity = _elasticity(elasticity_rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            (
                "# Informe inicial de negocio",
                "",
                "> Datos completamente sintéticos: los hallazgos validan el producto, "
                "no un negocio real.",
                "",
                "## Cinco hallazgos verificables",
                "",
                f"1. Ingresos: **EUR {revenue / 100:,.2f}** en **{tickets:,}** tickets.",
                f"2. Margen sintético: **EUR {margin / 100:,.2f}**.",
                f"3. Categoría líder: **{top_category[0]}** con EUR {top_category[1] / 100:,.2f}.",
                f"4. Mix por canal: {channel_text}.",
                f"5. Clientes recurrentes: **{repeat * 100:.1f}%** "
                f"de {customers:,} clientes activos.",
                "",
                "## Diagnóstico de promoción",
                "",
                f"Unidades medias sin promoción: {promotion.get(0, 0):.2f}; "
                f"con promoción: {promotion.get(1, 0):.2f}.",
                "Esta comparación es descriptiva y no identifica un efecto causal.",
                "",
                "## Referencia econométrica",
                "",
                f"Pendiente log-log precio–cantidad: **{elasticity:.3f}**.",
                "Es una asociación OLS simple; promociones, estacionalidad y selección de producto "
                "pueden sesgarla. Se conserva como baseline para el análisis causal posterior.",
                "",
            )
        ),
        encoding="utf-8",
    )
    return output
