# Caso de negocio sintético

## Decisión

Combinar forecast para planificación semanal con churn para priorizar una intervención
de retención. Ejecutar la intervención como A/B test y aplicar CUPED si la métrica
pretratamiento mantiene correlación suficiente.

## Impacto ilustrativo

Con efecto sintético de cinco unidades de métrica por cliente, el experimento recupera
4,84 y su intervalo incluye la verdad. CUPED reduce 51,6% de varianza. Estos valores
demuestran sensibilidad metodológica, no euros reales.

Para un piloto real se deben sustituir tres supuestos:

1. margen incremental por cliente retenido;
2. coste completo de la intervención;
3. capacidad operativa y tasa real de contacto.

El resultado se comunicará como rango:

```text
impacto neto = clientes tratados × uplift de retención × margen incremental - coste
```

No se recomienda desplegar si el límite inferior del rango es negativo, las guardrails
empeoran o existe una disparidad regional/sensible sin explicación aceptable.
