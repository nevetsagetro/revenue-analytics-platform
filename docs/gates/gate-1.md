# Gate 1 — Foundation reproducible

Fecha de verificación: 2026-08-16.

## Evidencia

| Requisito | Evidencia observable | Estado |
|---|---|---|
| Ejecución reproducible | `demo --seed 42` y manifiesto SHA-256 | aprobado |
| Dataset de portfolio | 250.000 tickets y 549.360 líneas en 18,6 s | aprobado |
| Integridad raw | checksums, conteos, PK/FK y rangos | aprobado |
| Staging y marts | SQL versionado en el paquete | aprobado |
| Revenue confiable | reconciliación raw → staging → mart | aprobado |
| Historia de precios | cobertura temporal completa y sin solapamientos | aprobado |
| SQL analítico | diez consultas ejecutables desde CLI | aprobado |
| EDA y econometría | informe con cinco hallazgos y baseline log-log | aprobado |
| Calidad de código | Ruff, formato, 10 tests y cobertura 77,29% | aprobado |

## Comandos de reproducción

```bash
uv sync --extra dev
uv run revenue-analytics demo --output-dir data --seed 42
uv run revenue-analytics validate --data-dir data
uv run revenue-analytics report --database data/warehouse/revenue.db
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Límites conocidos

- Los datos son sintéticos y no prueban impacto comercial real.
- El baseline log-log es asociativo, no una estimación causal.
- SQLite es deliberadamente local; una migración solo se justificará por escala o
  consumidores reales.

El Gate 1 congela granos, semántica monetaria y vigencias de precio. La siguiente
release puede construir snapshots point-in-time y modelos predictivos sobre estos
contratos.
