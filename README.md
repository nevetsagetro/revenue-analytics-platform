# Revenue Analytics Platform

Implementación de referencia del producto definido en el roadmap de Analytics Data
Science: una plataforma reproducible que conecta datos comerciales, analítica predictiva,
inferencia causal y decisiones de negocio.

El repositorio comienza con un **vertical slice de la Fase A**. Genera un comercio
minorista sintético y determinista, carga una base SQLite con capas `raw`, `stg` y `mart`,
y produce métricas comerciales verificables. No presenta los datos sintéticos como
evidencia real.

## Primer recorrido (5 minutos)

No requiere dependencias externas para ejecutar el pipeline:

```bash
PYTHONPATH=src python -m revenue_analytics demo --output-dir data --seed 42
PYTHONPATH=src python -m revenue_analytics validate --data-dir data
PYTHONPATH=src python -m revenue_analytics inspect --database data/warehouse/revenue.db
PYTHONPATH=src python -m revenue_analytics analyze 06_customer_rfm \
  --database data/warehouse/revenue.db --limit 10
PYTHONPATH=src python -m revenue_analytics report \
  --database data/warehouse/revenue.db --output artifacts/business-report.md
```

Salida esperada: seis CSV y `manifest.json` bajo `data/raw/`, una base en
`data/warehouse/revenue.db`, 19 controles de calidad y un resumen con ingresos,
unidades, tickets y clientes.
Repetir el comando con la misma configuración genera los mismos archivos.

Para desarrollar con `uv`:

```bash
uv sync --extra dev
uv run revenue-analytics demo --output-dir data --seed 42
uv run pytest
uv run ruff check .
```

## Perfiles de datos

- `demo`: 200 clientes, 24 productos y 2.000 tickets; rápido para aprender y probar.
- `portfolio`: 50.000 clientes, 500 productos y 250.000 tickets. La ejecución de
  referencia produjo 549.360 líneas en 18,6 segundos.

```bash
PYTHONPATH=src python -m revenue_analytics demo --profile portfolio --output-dir data
```

## Arquitectura y progreso

- [Roadmap de implementación](docs/implementation-roadmap.md)
- [Modelo de datos](docs/data-model.md)
- [ADR-001: stack tecnológico](docs/adr/001-stack-tecnologico.md)
- [Evidencia del Gate 1](docs/gates/gate-1.md)

La entrega actual cubre el vertical slice foundation: generación, contratos, SQL,
marts, consultas, validación e informe inicial. Forecasting, churn y causalidad se
implementarán sobre estos contratos para evitar notebooks desconectados.
