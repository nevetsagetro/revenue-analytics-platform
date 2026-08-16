# Gate causal — v0.3

Fecha de verificación: 2026-08-16. Véase también [DAG causal](../causal-dag.md).

## Resultados reproducibles

| Análisis | Estimación | IC 95% / referencia |
|---|---:|---:|
| Elasticidad precio-demanda controlada | -1,123 | [-1,210; -1,037] |
| A/B diferencia de medias | 4,960 | verdad sintética 5,000 |
| A/B con CUPED | 4,835 | [4,395; 5,276] |
| Difference-in-Differences | 8,662 | verdad sintética 8,000; IC [7,051; 10,272] |
| Placebo DiD pretratamiento | -0,092 | IC [-1,702; 1,519] incluye cero |

CUPED reduce la varianza estimada un 51,6%. Para detectar un efecto de cinco unidades
con los supuestos simulados se requieren aproximadamente 82 observaciones por el
cálculo implementado.

## Decisión

- Para retención, priorizar un experimento aleatorio y usar CUPED si existe una métrica
  pretratamiento correlacionada.
- Para pricing, presentar la elasticidad como asociación controlada: el DAG muestra
  confusión por estacionalidad, categoría y canal, pero puede quedar demanda no
  observada que afecte simultáneamente el precio.
- Usar DiD solo cuando tendencias paralelas y placebos sean defendibles en datos reales.

## Evidencia técnica

- muestreo y simulaciones deterministas con seed;
- OLS implementado sobre precio relativo, promoción, canal y estacionalidad;
- intervalos explícitos en todos los efectos;
- comparación contra verdad sintética conocida;
- placebo pretratamiento compatible con tendencias paralelas;
- artefactos `causal_metrics.json` y `causal_decision.md`.
