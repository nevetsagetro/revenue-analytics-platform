SELECT store_id, channel, SUM(revenue_cents) / 100.0 AS revenue_eur,
       RANK() OVER (ORDER BY SUM(revenue_cents) DESC) AS revenue_rank
FROM mart_sales_daily GROUP BY store_id, channel ORDER BY revenue_rank;
