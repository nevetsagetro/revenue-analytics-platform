CREATE VIEW stg_sales AS
SELECT
  l.line_id,
  t.transaction_id,
  t.customer_id,
  t.transaction_date,
  t.store_id,
  s.channel,
  s.region,
  l.product_id,
  p.category,
  l.quantity,
  ph.list_price_cents,
  l.unit_price_cents,
  l.discount_pct,
  l.promotion,
  l.quantity * l.unit_price_cents AS line_revenue_cents,
  l.quantity * (l.unit_price_cents - p.unit_cost_cents) AS line_margin_cents
FROM raw_transaction_lines AS l
JOIN raw_transactions AS t USING (transaction_id)
JOIN raw_stores AS s USING (store_id)
JOIN raw_products AS p USING (product_id)
JOIN raw_price_history AS ph
  ON ph.product_id = l.product_id
 AND ph.channel = s.channel
 AND t.transaction_date BETWEEN ph.valid_from AND ph.valid_to;
