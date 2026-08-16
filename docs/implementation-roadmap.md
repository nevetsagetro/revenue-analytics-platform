# Roadmap de implementación del producto

Este plan traduce el roadmap académico de 52 semanas a entregas de software. Las
semanas siguen siendo una guía de estudio; el repositorio avanza mediante vertical
slices que terminan en un comportamiento demostrable.

## Arquitectura objetivo

```text
datos sintéticos -> raw -> staging -> marts -> features
                                            |-> forecasting
                                            |-> churn/segmentación
                                            |-> causalidad
                                            v
                              artefactos -> API/dashboard
                                            |
                                      monitorización
```

Es un monolito modular batch. Los módulos intercambian tablas y artefactos versionados;
no se crearán microservicios ni infraestructura de tiempo real sin un requisito real.

## Releases

| Release | Resultado de negocio | Componentes | Criterio de salida |
|---|---|---|---|
| `v0.1-foundation` | Revenue diario y actividad de cliente confiables | generador, raw/staging/marts, CLI, tests, CI | misma seed = mismos datos; PK/FK válidas; revenue reconciliado; demo limpia |
| `v0.2-predictive` | Anticipar demanda y priorizar retención | snapshots point-in-time, baselines de forecast, churn calibrado, segmentos | splits temporales; WAPE/MASE vs naïve; AUC/Brier y coste; sin leakage |
| `v0.3-causal` | Recomendar precio/intervención con supuestos visibles | DAG, elasticidad, A/B simulado, DiD, CUPED | efecto con IC; placebo/supuestos; comparación con verdad sintética |
| `v0.4-product` | Una persona de negocio puede explorar y consumir resultados | FastAPI, dashboard, Docker, caso de negocio | cifras reconciliadas; endpoints testeados; arranque con un comando |
| `v0.5-operations` | Detectar degradación y operar con fallback | calidad, PSI, calibración, fairness, business review | umbrales configurables; fallback probado; reporte periódico |
| `v1.0-portfolio` | Evidencia pública completa y reproducible | hardening, cards, ADRs, benchmark, demo | instalación limpia; CI verde; documentación y demo end-to-end |

## Backlog inmediato de `v0.1`

Estado al 2026-08-16:

- [x] paquete Python, configuración, CLI y ADR inicial;
- [x] perfiles `demo` y `portfolio`;
- [x] clientes, productos, tickets y líneas deterministas;
- [x] warehouse SQLite con `stg_sales`, `mart_sales_daily` y
  `mart_customer_activity`;
- [x] tests de determinismo, integridad, grano y reconciliación;
- [x] quickstart y CI;
- [x] separar SQL en archivos versionados y añadir comando `validate`;
- [x] añadir tiendas e historial de precios con intervalos no solapados;
- [x] escribir manifiesto de ejecución con configuración, filas y SHA-256;
- [x] crear diez consultas analíticas de cohortes, ranking y RFM;
- [x] añadir informe dirigido y modelo econométrico de referencia;
- [x] ejecutar el perfil `portfolio`: 549.360 líneas en 18,6 segundos;
- [x] ensayo del Gate 1 con instalación limpia en CI.

## Release `v0.2-predictive`

- [x] backtesting temporal rolling-origin con cinco candidatos;
- [x] forecast de ocho semanas y WAPE/MASE contra naïve;
- [x] snapshots de churn point-in-time con horizonte de 60 días;
- [x] regresión logística calibrada vs. regla de recencia;
- [x] scores de churn con fecha de corte explícita;
- [x] segmentación RFM accionable;
- [x] artefactos JSON/CSV reproducibles y sin usar `latent_churn_date` como feature.

## Release `v0.3-causal`

- [x] DAG y controles para precio → demanda;
- [x] elasticidad log-log con intervalo de confianza;
- [x] diseño A/B reproducible y cálculo de tamaño muestral;
- [x] CUPED con medición de reducción de varianza;
- [x] Difference-in-Differences con verdad sintética conocida;
- [x] documento que separa asociación, causalidad y recomendación.

## Contratos para trabajo con agentes

El trabajo se reparte por ownership de módulos, nunca por archivos compartidos:

| Agente | Ownership | Contrato de salida |
|---|---|---|
| Plataforma y datos | configuración, generación, warehouse, CLI | tablas raw/staging/mart versionadas |
| ML predictivo | `forecasting/`, `churn/`, `segmentation/` | artefactos y tablas de scoring con métricas |
| Causal | `causal/` y mecanismo económico sintético | estimaciones, IC, diagnósticos y supuestos |
| Producto y QA | API, dashboard, monitoring, E2E, documentación | interfaces de consumo y evidencia de gate |

Antes de paralelizar modelos deben congelarse nombres, granos, fechas de corte y
semántica monetaria. El agente integrador revisa reconciliación, compatibilidad y
Definition of Done.

## Riesgos que bloquean avance

- Un generador sin mecanismo económico conocido invalida la demostración causal.
- Mezclar grano ticket/línea duplica revenue.
- Crear features con información posterior a la fecha de corte causa leakage.
- Ejecutar 500K filas en cada CI vuelve lento el feedback; CI usa `demo` y el perfil
  completo se valida periódicamente.
- Notebooks no serán fuente de verdad: consumen marts, nunca sustituyen el pipeline.
