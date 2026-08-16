WITH customer_orders AS (
  SELECT customer_id, COUNT(DISTINCT transaction_id) AS orders FROM stg_sales GROUP BY customer_id
)
SELECT COUNT(*) AS customers,
       SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
       ROUND(100.0 * SUM(CASE WHEN orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS repeat_pct
FROM customer_orders;
