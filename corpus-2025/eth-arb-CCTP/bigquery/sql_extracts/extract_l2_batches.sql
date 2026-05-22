-- extract_l2_batches.sql
-- Parametrized L1 batch posting events extractor for one L2 chain.
--
-- The sequencer of an L2 posts batches to L1 by sending transactions
-- to its SequencerInbox contract on Ethereum. Each distinct transaction
-- to the SequencerInbox = one batch posting. The cadence of these batches
-- is the L2's sequencer_publish_latency observable.
--
-- Parameters (BigQuery scalar parameters):
--   @start_ts                : inclusive lower bound on block_timestamp on L1
--   @end_ts                  : exclusive upper bound on block_timestamp on L1
--   @sequencer_inbox_address : the L1 contract that receives batch postings
--                              (per chain: ARB SequencerInbox, etc.)
--
-- Output columns (one row per hour UTC):
--   hour_utc, batch_count, batch_gap_max_s, batch_gap_avg_s
--
-- Counting strategy: DISTINCT transaction_hash on the SequencerInbox
-- address. Each tx = one batch posting (a tx can emit multiple log entries
-- but counts as one batch). Gaps measured between consecutive batch tx
-- timestamps.

WITH batches AS (
  SELECT DISTINCT
    transaction_hash,
    block_timestamp
  FROM `bigquery-public-data.crypto_ethereum.logs`
  WHERE block_timestamp >= @start_ts
    AND block_timestamp <  @end_ts
    AND LOWER(address) = LOWER(@sequencer_inbox_address)
),
ordered AS (
  SELECT
    block_timestamp,
    LAG(block_timestamp) OVER (ORDER BY block_timestamp) AS prev_block_timestamp
  FROM batches
),
gaps AS (
  SELECT
    TIMESTAMP_TRUNC(block_timestamp, HOUR) AS hour_utc,
    TIMESTAMP_DIFF(block_timestamp, prev_block_timestamp, SECOND) AS gap_s
  FROM ordered
  WHERE prev_block_timestamp IS NOT NULL
)
SELECT
  hour_utc,
  COUNT(*)        AS batch_count,
  MAX(gap_s)      AS batch_gap_max_s,
  AVG(gap_s)      AS batch_gap_avg_s
FROM gaps
GROUP BY hour_utc
ORDER BY hour_utc;
