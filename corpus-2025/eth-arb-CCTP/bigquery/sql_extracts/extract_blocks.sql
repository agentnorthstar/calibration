-- extract_blocks.sql
-- Parametrized substrate blocks extractor.
--
-- Parameters (substituted by Python before submission):
--   @dataset_table  : fully qualified table reference, e.g.
--                     `bigquery-public-data.crypto_ethereum.blocks`
--   @timestamp_col  : the timestamp column name in that dataset.
--                     - crypto_ethereum.blocks uses 'timestamp'
--                     - goog_blockchain_*.blocks uses 'block_timestamp'
--
-- BigQuery scalar parameters:
--   @start_ts       : inclusive lower bound on the timestamp column
--   @end_ts         : exclusive upper bound on the timestamp column
--
-- Output columns (one row per hour UTC):
--   hour_utc, block_count, gas_used_avg, gas_used_stddev, gas_used_p50, gas_used_p95,
--   gas_limit_avg, tx_count_total, tx_count_avg_per_block, tx_count_stddev,
--   complexity_avg, complexity_p95
--
-- Partitioning hint: all chains in scope are partitioned on the timestamp
-- column. Always pass tight @start_ts and @end_ts to keep scanned bytes minimal.

SELECT
  TIMESTAMP_TRUNC(@timestamp_col, HOUR)                               AS hour_utc,
  COUNT(*)                                                            AS block_count,
  AVG(gas_used)                                                       AS gas_used_avg,
  STDDEV(gas_used)                                                    AS gas_used_stddev,
  APPROX_QUANTILES(gas_used, 100)[OFFSET(50)]                         AS gas_used_p50,
  APPROX_QUANTILES(gas_used, 100)[OFFSET(95)]                         AS gas_used_p95,
  AVG(gas_limit)                                                      AS gas_limit_avg,
  SUM(transaction_count)                                              AS tx_count_total,
  AVG(transaction_count)                                              AS tx_count_avg_per_block,
  STDDEV(transaction_count)                                           AS tx_count_stddev,
  AVG(SAFE_DIVIDE(gas_used, NULLIF(transaction_count, 0)))            AS complexity_avg,
  APPROX_QUANTILES(SAFE_DIVIDE(gas_used, NULLIF(transaction_count, 0)), 100)[OFFSET(95)] AS complexity_p95
FROM @dataset_table
WHERE @timestamp_col >= @start_ts
  AND @timestamp_col <  @end_ts
GROUP BY hour_utc
ORDER BY hour_utc;
