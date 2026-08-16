SELECT product_id, ROUND(AVG(unit_price_cents) / 100.0, 2) AS avg_price_eur,
       ROUND(AVG(quantity), 3) AS avg_units, COUNT(*) AS observations
FROM stg_sales GROUP BY product_id HAVING COUNT(*) >= 10 ORDER BY observations DESC;
