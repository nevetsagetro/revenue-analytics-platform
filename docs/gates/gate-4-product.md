# Gate producto y operaciones — v0.4/v0.5

Fecha de verificación: 2026-08-16.

## Flujo end-to-end

`revenue-analytics build-all` produjo desde cero, en 1,1 segundos con perfil demo:

- seis tablas raw, manifiesto y warehouse SQLite;
- informe de negocio y quality gate;
- métricas, forecast, scores de churn y segmentos;
- resultados causales y documento de decisión;
- reporte de monitorización con PSI, freshness, calibración y fairness regional.

## API y dashboard

Contratos verificados mediante TestClient y una prueba HTTP real con Uvicorn:

| Ruta | Función | Evidencia |
|---|---|---|
| `GET /health` | readiness de artefactos | HTTP 200, `status=ok` |
| `GET /v1/forecast` | horizonte 1–8 semanas | HTTP 200 y validación de rango |
| `GET /v1/churn/{customer_id}` | probabilidad con fecha de corte | 200/404 testeados |
| `GET /v1/segments/{customer_id}` | segmento RFM | 200/404 testeados |
| `GET /v1/metrics` | métricas y parámetros | contrato JSON |
| `GET /dashboard` | consumo ejecutivo | HTML conectado a artefactos |

Si falta el forecast candidato, la API sirve `naive_fallback`; este comportamiento está
cubierto por tests. El contenedor está definido, pero la imagen no se construyó en el
entorno de validación porque Docker no está instalado.

## Calidad

- 23 tests aprobados;
- cobertura 85,92%;
- Ruff lint y format aprobados;
- lockfile de `uv` generado;
- wheel `1.0.0` construido, instalado en un entorno limpio y validado con `build-all`;
- ejecución local real de Uvicorn y consultas HTTP aprobadas.
