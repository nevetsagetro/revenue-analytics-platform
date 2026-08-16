SELECT product_id, category, SUM(units) AS units,
       SUM(revenue_cents) / 100.0 AS revenue_eur
FROM mart_sales_daily GROUP BY product_id, category ORDER BY revenue_eur DESC LIMIT 20;
