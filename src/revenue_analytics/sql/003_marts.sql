CREATE TABLE mart_sales_daily AS
SELECT
  transaction_date,
  product_id,
  category,
  store_id,
  channel,
  SUM(quantity) AS units,
  SUM(line_revenue_cents) AS revenue_cents,
  SUM(line_margin_cents) AS margin_cents,
  COUNT(DISTINCT transaction_id) AS tickets
FROM stg_sales
GROUP BY transaction_date, product_id, category, store_id, channel;

CREATE UNIQUE INDEX mart_sales_daily_grain
ON mart_sales_daily(transaction_date, product_id, store_id);

CREATE TABLE mart_customer_activity AS
SELECT
  customer_id,
  MAX(transaction_date) AS last_purchase_date,
  COUNT(DISTINCT transaction_id) AS frequency,
  SUM(line_revenue_cents) AS monetary_cents,
  COUNT(DISTINCT product_id) AS product_breadth
FROM stg_sales
GROUP BY customer_id;

CREATE UNIQUE INDEX mart_customer_activity_grain
ON mart_customer_activity(customer_id);
