# Model card — baselines predictivos

## Forecast

Tendencia lineal sobre doce semanas, comparada en rolling-origin contra naïve, seasonal
naïve, media móvil y suavizado exponencial. Produce ocho semanas. Si el artefacto falta,
la API usa el último valor semanal como fallback.

## Churn

Regresión logística regularizada implementada sobre recencia, log-frecuencia y
log-monetary. Entrenamiento, calibración y test usan ventanas temporales separadas. El
horizonte de etiqueta es 60 días. Se compara contra una regla de recencia.

## Performance sintética

- forecast WAPE: 9,51%; naïve: 9,54%;
- churn AUC: 0,675; regla: 0,639;
- churn Brier: 0,166; regla: 0,219;
- error de calibración: 0,055.

## Riesgos

Las métricas no se transfieren a producción. Deben revisarse drift, calibración,
disparidad por grupos y coste de falsos positivos/negativos antes de cualquier uso. No
automatizar intervenciones adversas: el score prioriza revisión humana.
