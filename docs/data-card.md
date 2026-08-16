# Data card — retail sintético

## Propósito

Dataset determinista para demostrar forecasting, churn, segmentación y causalidad sin
usar datos personales o propietarios. No representa una población ni empresa real.

## Contenido

Clientes, productos, tiendas, precios con vigencia, tickets y líneas. El perfil
portfolio validado contiene 50.000 clientes, 500 productos, 41 puntos/canales, 250.000
tickets y aproximadamente 550.000 líneas.

## Mecanismos conocidos

- elasticidad latente por categoría;
- promociones y estacionalidad;
- actividad heterogénea y fecha latente de churn;
- precios trimestrales por producto/canal.

`latent_churn_date` y `latent_elasticity` permiten auditar la simulación, pero no se usan
como features predictivas. El manifiesto registra configuración, filas y SHA-256.

## Límites y uso prohibido

No usar métricas del dataset para tomar decisiones reales, evaluar grupos humanos,
fijar precios o estimar ROI real. La fairness regional solo prueba el mecanismo de
auditoría; no demuestra equidad para atributos sensibles reales.
