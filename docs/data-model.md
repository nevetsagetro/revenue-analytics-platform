# Modelo de datos

## Dominio

Comercio minorista omnicanal sintético. La demanda depende de estacionalidad, promoción
y precio; esa señal conocida permitirá validar después forecasting y elasticidad.

| Tabla | Grano | Clave | Uso |
|---|---|---|---|
| `raw_customers` | un cliente registrado | `customer_id` | churn y RFM |
| `raw_products` | un producto vendible | `product_id` | catálogo y margen |
| `raw_stores` | una tienda o canal online | `store_id` | canal y región |
| `raw_price_history` | producto, canal y vigencia | `price_id` | precio expuesto |
| `raw_transactions` | un ticket | `transaction_id` | frecuencia y canal |
| `raw_transaction_lines` | un producto en un ticket | `line_id` | demanda e ingresos |
| `stg_sales` | una línea válida enriquecida | `line_id` | contrato analítico |
| `mart_sales_daily` | fecha, producto y canal | compuesta | forecasting |
| `mart_customer_activity` | un cliente | `customer_id` | RFM/churn |

Las cantidades monetarias se guardan como centavos enteros en raw para evitar errores
binarios. `unit_price_cents` ya representa el precio pagado después del descuento;
`line_revenue_cents = quantity * unit_price_cents`. `discount_pct` conserva la
explicación comercial del precio. Las claves foráneas y reglas de rango se validan al
cargar.

## Supuestos sintéticos

- Fechas fijas entre 2024-01-01 y 2025-12-31; nunca se usa la fecha del sistema.
- Elasticidad latente por categoría entre -0,8 y -1,8.
- Promociones elevan conversión y reducen precio entre 5% y 25%.
- Los precios cambian trimestralmente y sus intervalos no se solapan.
- La actividad del cliente es heterogénea y algunos clientes dejan de comprar.
- Los resultados sirven para comprobar mecanismos del sistema, no para afirmar impacto
  comercial real.

## Controles automatizados

`revenue-analytics validate` verifica checksums, conteos, claves foráneas, unicidad del
grano, cobertura del join temporal de precios, ausencia de intervalos solapados y
reconciliación de revenue raw → staging → mart.
