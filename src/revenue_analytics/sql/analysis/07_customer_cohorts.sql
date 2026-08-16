WITH first_purchase AS (
  SELECT customer_id, substr(MIN(transaction_date), 1, 7) AS cohort_month
  FROM stg_sales GROUP BY customer_id
)
SELECT f.cohort_month, substr(s.transaction_date, 1, 7) AS activity_month,
       COUNT(DISTINCT s.customer_id) AS active_customers
FROM stg_sales s JOIN first_purchase f USING (customer_id)
GROUP BY f.cohort_month, activity_month ORDER BY f.cohort_month, activity_month;
