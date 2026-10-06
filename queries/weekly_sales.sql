-- Weekly sales aggregation query using Monday-start complete calendar weeks
-- Input table: clean_tx (invoice_id, sku_id, description, quantity, transaction_at, sale_unit_price_gbp, country)
WITH tx_filtered AS (
    SELECT 
        sku_id,
        CAST(date_trunc('week', transaction_at) AS DATE) AS week_start,
        quantity
    FROM clean_tx
    WHERE transaction_at >= TIMESTAMP :first_monday_str
      AND transaction_at < TIMESTAMP :next_monday_after_last_sunday_str
)
SELECT 
    sku_id,
    week_start,
    CAST(SUM(quantity) AS BIGINT) AS units_sold
FROM tx_filtered
GROUP BY sku_id, week_start
ORDER BY sku_id, week_start;
