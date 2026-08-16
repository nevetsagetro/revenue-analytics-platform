SELECT promotion, COUNT(*) AS lines, ROUND(AVG(quantity), 3) AS avg_units,
       ROUND(AVG(line_revenue_cents) / 100.0, 2) AS avg_line_revenue_eur
FROM stg_sales GROUP BY promotion ORDER BY promotion;
