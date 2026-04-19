-- Invarians — Polygon invariants extraction — Φ=720 (aligned with production)
-- BigQuery dataset: bigquery-public-data.crypto_polygon
-- Φ = 720 blocks (production-aligned, ~1h sampling cadence)
-- Window: 2020-06-01 → 2023-12-31
-- Export → pol_invariants_2020_2024_phi720.csv
--
-- Rationale: the published v1.0 backtest uses Φ=1800 while production
-- uses Φ=720 (cf. invarians-L1-collector/ans-engine/src/main.rs row 323).
-- This query produces a backtest aligned with the production configuration.

WITH numbered AS (
  SELECT
    number            AS block_number,
    `timestamp`       AS block_time,
    gas_used,
    gas_limit,
    transaction_count,
    size,
    FLOOR((ROW_NUMBER() OVER (ORDER BY number) - 1) / 720) AS window_id
  FROM `bigquery-public-data.crypto_polygon.blocks`
  WHERE DATE(`timestamp`) BETWEEN '2020-06-01' AND '2023-12-31'
    AND number > 0
),
windows AS (
  SELECT
    window_id,
    MIN(block_number)  AS first_block,
    MAX(block_number)  AS last_block,
    MIN(block_time)    AS window_start,
    MAX(block_time)    AS window_end,
    COUNT(*)           AS block_count,
    AVG(SAFE_DIVIDE(gas_used, gas_limit))  AS rho_s,
    AVG(size)                              AS size_avg,
    AVG(transaction_count)                 AS tx_count_avg,
    TIMESTAMP_DIFF(MAX(block_time), MIN(block_time), MILLISECOND) / 1000.0
      / NULLIF(COUNT(*) - 1, 0)            AS rho_ts
  FROM numbered
  GROUP BY window_id
  HAVING COUNT(*) >= 2
)
SELECT
  window_id                          AS inv_idx,
  UNIX_SECONDS(window_start)         AS window_start,
  UNIX_SECONDS(window_end)           AS window_end,
  block_count,
  first_block,
  last_block,
  ROUND(rho_ts, 6)                   AS rho_ts,
  ROUND(rho_s,  6)                   AS rho_s,
  ROUND(size_avg, 2)                 AS size_avg,
  ROUND(tx_count_avg, 4)             AS tx_count_avg,
  block_count / 720.0                AS c_s
FROM windows
WHERE window_id > 0
  AND window_id < (SELECT MAX(window_id) FROM windows)
ORDER BY window_id;
