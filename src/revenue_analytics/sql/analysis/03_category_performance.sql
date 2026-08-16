SELECT category, SUM(units) AS units, SUM(revenue_cents) / 100.0 AS revenue_eur,
       SUM(margin_cents) / 100.0 AS margin_eur
FROM mart_sales_daily GROUP BY category ORDER BY revenue_eur DESC;
