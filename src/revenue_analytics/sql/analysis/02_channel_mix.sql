SELECT channel, SUM(revenue_cents) / 100.0 AS revenue_eur,
       ROUND(100.0 * SUM(revenue_cents) / SUM(SUM(revenue_cents)) OVER (), 2) AS revenue_pct
FROM mart_sales_daily GROUP BY channel ORDER BY revenue_eur DESC;
