SELECT substr(transaction_date, 1, 7) AS month,
       SUM(revenue_cents) / 100.0 AS revenue_eur
FROM mart_sales_daily GROUP BY month ORDER BY month;
