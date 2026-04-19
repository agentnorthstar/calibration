-- Invarians — Extract Solana invariants (Φ = 800 slots)
-- Source  : bigquery-public-data.crypto_solana_mainnet_us.Blocks
-- Period  : 2021-01-01 → 2024-01-01  (~270 windows/day, ~3 ans)
-- Output  : ~295 000 windows (~800 slots ≈ 320s nominal, ~5.3 min)
--
-- BEFORE RUNNING: check that the table exists
--   SELECT table_name
--   FROM   bigquery-public-data.crypto_solana_mainnet_us.INFORMATION_SCHEMA.TABLES
--   LIMIT  10
--
-- If the dataset is named goog_blockchain_solana_mainnet_us:
--   replace all occurrences below.
--
-- Output columns:
--   inv_idx       — sequential window index
--   window_id     — FLOOR(block_slot / 800)
--   block_count   — blocks observed in the window (max 800)
--   window_start  — UNIX timestamp of first block (seconds)
--   window_end    — UNIX timestamp of last  block (seconds)
--   rho_ts        — mean inter-block time (seconds) — τ signal
--                   spikes when slots are skipped or the network slows
--   c_s           — continuity fraction 0→1 = block_count / 800
--                   drops when skip rate rises (outage)
--   tx_count_avg  — mean transactions/block — π demand proxy
--   size_avg      — estimated size (tx × 180 bytes) — block size proxy
--
-- Note on size_avg: Solana does not expose the total block size in Blocks.
-- Proxy: 180 bytes/tx (mean mixed user+vote tx).
-- To improve: join with the Transactions table (see extract_sol_size.sql).

-- Actual Blocks table schema (checked March 16, 2026):
--   slot (INT64), block_hash (STRING), block_timestamp (TIMESTAMP), height (INT64)
-- No transaction_count → τ calibration only with this SQL.
-- For π (demand), see extract_sol_tx.sql if the Transactions table is available.

WITH
raw AS (
  SELECT
    slot,
    block_timestamp
  FROM `bigquery-public-data.crypto_solana_mainnet_us.Blocks`
  WHERE DATE(block_timestamp) BETWEEN '2021-01-01' AND '2023-12-31'
    AND block_timestamp IS NOT NULL
),

windowed AS (
  SELECT
    CAST(FLOOR(slot / 800) AS INT64)                 AS window_id,
    COUNT(*)                                          AS block_count,
    MIN(UNIX_SECONDS(block_timestamp))                AS window_start,
    MAX(UNIX_SECONDS(block_timestamp))                AS window_end,

    -- rho_ts: mean inter-block time in ms
    -- Spikes when slots are skipped or the network slows → τ signal
    CASE
      WHEN COUNT(*) > 1
        THEN CAST(
               TIMESTAMP_DIFF(MAX(block_timestamp), MIN(block_timestamp), MILLISECOND)
               AS FLOAT64
             ) / CAST(COUNT(*) - 1 AS FLOAT64)
      ELSE 400.0   -- window with only 1 block → nominal 400ms
    END                                               AS rho_ts_ms,

    -- c_s: fraction of slots that produced a block (0 → 1)
    -- Drops when skip rate rises → continuity stress signal
    CAST(COUNT(*) AS FLOAT64) / 800.0                AS c_s

  FROM raw
  GROUP BY window_id
  HAVING COUNT(*) >= 2
),

bounds AS (
  SELECT MIN(window_id) AS w_min, MAX(window_id) AS w_max
  FROM windowed
)

SELECT
  ROW_NUMBER() OVER (ORDER BY w.window_id)  AS inv_idx,
  w.window_id,
  w.block_count,
  w.window_start,
  w.window_end,
  ROUND(w.rho_ts_ms / 1000.0, 6)           AS rho_ts,   -- seconds
  ROUND(w.c_s,         6)                   AS c_s       -- fraction 0-1
FROM   windowed  w
CROSS  JOIN bounds b
WHERE  w.window_id > b.w_min
  AND  w.window_id < b.w_max
ORDER  BY w.window_id
