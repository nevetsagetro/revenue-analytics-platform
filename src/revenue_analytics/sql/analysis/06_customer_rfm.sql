WITH anchor AS (SELECT MAX(transaction_date) AS max_date FROM stg_sales)
SELECT customer_id,
       CAST(julianday(anchor.max_date) - julianday(last_purchase_date) AS INTEGER) AS recency_days,
       frequency, monetary_cents / 100.0 AS monetary_eur,
       NTILE(5) OVER (ORDER BY frequency) AS frequency_score,
       NTILE(5) OVER (ORDER BY monetary_cents) AS monetary_score
FROM mart_customer_activity CROSS JOIN anchor ORDER BY monetary_eur DESC;
