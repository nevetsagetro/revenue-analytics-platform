# ADR-001: stack tecnológico inicial

- Estado: aceptada
- Fecha: 2026-08-16

## Contexto

El producto debe ser reproducible por un estudiante, crecer desde análisis local hasta
modelos y una API ligera, y mantener el foco en decisiones de negocio. El primer
recorrido no debería depender de servicios externos.

## Decisión

Usar Python 3.12 con layout `src/`, SQLite como warehouse local y SQL explícito para las
capas staging/mart. La interfaz inicial será una CLI. `pytest` y Ruff forman la barrera
de calidad. Los modelos posteriores podrán añadir librerías científicas sin cambiar los
contratos de datos.

## Consecuencias

- El ejemplo inicial funciona offline y es fácil de inspeccionar.
- SQLite no representa un warehouse distribuido, pero enseña granos, claves y capas sin
  ocultarlos tras infraestructura.
- CSV prioriza transparencia en el primer incremento; Parquet se añadirá cuando entre
  una dependencia columnar.
- No se incorpora todavía dbt, MLflow, FastAPI ni Docker: cada herramienta entrará al
  existir un consumidor concreto que justifique su coste.
