# Operación y fallback

## Revisión periódica

1. ejecutar `validate` sobre raw y warehouse;
2. generar artefactos actuales con `predict`;
3. comparar contra una referencia con `monitor`;
4. revisar PSI (`warning ≥0,10`, `critical ≥0,25`), calibración y fairness;
5. registrar decisión: continuar, investigar o reentrenar.

## Fallos

- Artefacto de forecast ausente: servir `naive_fallback`.
- Datos o manifiesto inválidos: detener `build-all`; no publicar resultados parciales.
- Artefactos predictivos ausentes: `/health` responde `degraded` y endpoints afectados
  responden 503.
- PSI crítico o calibración degradada: suspender decisiones automatizadas y volver al
  baseline documentado hasta revisión.
