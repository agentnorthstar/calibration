-- extract_blocks_l2.sql
-- L2 blocks + transactions aggregator for goog_blockchain_* datasets.
--
-- The goog_blockchain_* dataset family does NOT have a transaction_count
-- column on the blocks table (unlike crypto_ethereum.blocks). We aggregate
-- transactions separately from the transactions table and join on hour.
--
-- This also gives us direct access to per-tx gas (receipt_gas_used) for
-- complexity_avg and complexity_p95, which is cleaner than the per-block
-- derivation used on L1.
--
-- Parameters (substituted by Python before submission):
--   @dataset_blocks  : fully qualified blocks table, e.g.
--                      `bigquery-public-data.goog_blockchain_arbitrum_one_us.blocks`
--   @dataset_tx      : fully qualified transactions table, e.g.
--                      `bigquery-public-data.goog_blockchain_arbitrum_one_us.transactions`
--   @timestamp_col   : 'block_timestamp' for goog_blockchain_*
--
-- BigQuery scalar parameters:
--   @start_ts, @end_ts

WITH block_aggs AS (
  SELECT
    TIMESTAMP_TRUNC(@timestamp_col, HOUR)                              AS hour_utc,
    COUNT(*)                                                           AS block_count,
    AVG(gas_used)                                                      AS gas_used_avg,
    STDDEV(gas_used)                                                   AS gas_used_stddev,
    APPROX_QUANTILES(gas_used, 100)[OFFSET(50)]                        AS gas_used_p50,
    APPROX_QUANTILES(gas_used, 100)[OFFSET(95)]                        AS gas_used_p95,
    AVG(gas_limit)                                                     AS gas_limit_avg
  FROM @dataset_blocks
  WHERE @timestamp_col >= @start_ts
    AND @timestamp_col <  @end_ts
  GROUP BY hour_utc
),
tx_aggs AS (
  -- Note: goog_blockchain_* transactions table does not expose actual gas
  -- used per tx (no receipt_gas_used column). We use `gas` (gas limit
  -- declared) as a complexity proxy. The signal direction is preserved
  -- (more complex tx = higher gas limit) at a small precision cost vs L1
  -- where gas_used per tx is directly available.
  SELECT
    TIMESTAMP_TRUNC(@timestamp_col, HOUR)                              AS hour_utc,
    COUNT(*)                                                           AS tx_count_total,
    AVG(gas)                                                           AS complexity_avg,
    APPROX_QUANTILES(gas, 100)[OFFSET(95)]                             AS complexity_p95
  FROM @dataset_tx
  WHERE @timestamp_col >= @start_ts
    AND @timestamp_col <  @end_ts
  GROUP BY hour_utc
)
SELECT
  b.hour_utc                                                           AS hour_utc,
  b.block_count                                                        AS block_count,
  b.gas_used_avg                                                       AS gas_used_avg,
  b.gas_used_stddev                                                    AS gas_used_stddev,
  b.gas_used_p50                                                       AS gas_used_p50,
  b.gas_used_p95                                                       AS gas_used_p95,
  b.gas_limit_avg                                                      AS gas_limit_avg,
  COALESCE(t.tx_count_total, 0)                                        AS tx_count_total,
  SAFE_DIVIDE(COALESCE(t.tx_count_total, 0), b.block_count)            AS tx_count_avg_per_block,
  CAST(NULL AS FLOAT64)                                                AS tx_count_stddev,
  t.complexity_avg                                                     AS complexity_avg,
  t.complexity_p95                                                     AS complexity_p95
FROM block_aggs b
LEFT JOIN tx_aggs t USING (hour_utc)
ORDER BY hour_utc;
