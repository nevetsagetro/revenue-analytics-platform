# Gate predictivo — v0.2

Fecha de verificación: 2026-08-16. Dataset portfolio con 250.000 tickets y 549.602
líneas sintéticas.

## Forecasting

Backtesting rolling-origin de ocho folds semanales:

| Modelo | WAPE | MASE |
|---|---:|---:|
| linear trend 12 semanas | 9,51% | 2,154 |
| naïve | 9,54% | 2,162 |
| media móvil 4 | 10,21% | 2,314 |
| exponential smoothing | 10,74% | 2,434 |
| seasonal naïve | 78,15% | 17,707 |

El challenger mejora ligeramente al naïve. La mejora pequeña es un hallazgo válido:
no justifica incorporar todavía un framework de forecasting más pesado.

## Churn

Los snapshots se construyen cada 60 días y solo usan compras anteriores al cutoff. La
etiqueta observa los 60 días posteriores. `latent_churn_date` audita el mecanismo
sintético y está excluida de las features.

| Métrica | Logística calibrada | Regla de recencia |
|---|---:|---:|
| AUC | 0,675 | 0,639 |
| Brier | 0,166 | 0,219 |
| Error esperado de calibración | 0,055 | — |

La calibración se aprende en una ventana temporal separada del entrenamiento y del
test. El test final contiene 7.206 observaciones y una tasa positiva de 77,45%.

## Artefactos

- `predictive_metrics.json`: métricas y parámetros reproducibles del modelo;
- `demand_forecast.csv`: forecast de ocho semanas;
- `churn_scores.csv`: probabilidad por cliente y `as_of_date`;
- `customer_segments.csv`: segmentos `champions`, `loyal`, `developing` y `at_risk`.

## Límites

- Las métricas prueban el mecanismo sintético, no performance sobre clientes reales.
- El drift de demanda inducido por churn hace que seasonal naïve sea inadecuado.
- El modelo se mantendrá como baseline hasta que un challenger demuestre mejora temporal
  y de negocio, no solo mayor complejidad.
