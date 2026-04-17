-- Invarians — Extract Solana invariants (Φ = 800 slots)
-- Source  : bigquery-public-data.crypto_solana_mainnet_us.Blocks
-- Period  : 2021-01-01 → 2024-01-01  (~270 windows/day, ~3 ans)
-- Output  : ~295 000 windows (~800 slots ≈ 320s nominal, ~5.3 min)
--
-- AVANT DE LANCER : vérifier que la table existe
--   SELECT table_name
--   FROM   bigquery-public-data.crypto_solana_mainnet_us.INFORMATION_SCHEMA.TABLES
--   LIMIT  10
--
-- Si le dataset s'appelle goog_blockchain_solana_mainnet_us :
--   remplacer toutes les occurrences ci-dessous.
--
-- Colonnes produites :
--   inv_idx       — index séquentiel fenêtre
--   window_id     — FLOOR(block_slot / 800)
--   block_count   — blocs observés dans la fenêtre (max 800)
--   window_start  — UNIX timestamp premier bloc (secondes)
--   window_end    — UNIX timestamp dernier  bloc (secondes)
--   rho_ts        — temps inter-bloc moyen (secondes) — signal τ
--                   spikes quand slots skippés ou réseau ralenti
--   c_s           — continuité fraction 0→1 = block_count / 800
--                   drop quand skip rate monte (outage)
--   tx_count_avg  — transactions/bloc moyen — proxy demande π
--   size_avg      — taille estimée (tx × 180 octets) — proxy taille bloc
--
-- Note size_avg : Solana n'expose pas la taille totale bloc dans Blocks.
-- Proxy : 180 bytes/tx (avg user+vote tx mixte).
-- Pour améliorer : joindre avec Transactions table (voir extract_sol_size.sql).

-- Schéma réel table Blocks (vérifié 16 Mars 2026) :
--   slot (INT64), block_hash (STRING), block_timestamp (TIMESTAMP), height (INT64)
-- Pas de transaction_count → calibration τ uniquement avec ce SQL.
-- Pour π (demande), voir extract_sol_tx.sql si table Transactions disponible.

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

    -- rho_ts : avg inter-block time en ms
    -- Spike quand slots skippés ou réseau ralenti → signal τ
    CASE
      WHEN COUNT(*) > 1
        THEN CAST(
               TIMESTAMP_DIFF(MAX(block_timestamp), MIN(block_timestamp), MILLISECOND)
               AS FLOAT64
             ) / CAST(COUNT(*) - 1 AS FLOAT64)
      ELSE 400.0   -- fenêtre à 1 seul bloc → nominal 400ms
    END                                               AS rho_ts_ms,

    -- c_s : fraction de slots ayant produit un bloc (0 → 1)
    -- Drop quand skip rate monte → signal continuity stress
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
  ROUND(w.rho_ts_ms / 1000.0, 6)           AS rho_ts,   -- secondes
  ROUND(w.c_s,         6)                   AS c_s       -- fraction 0-1
FROM   windowed  w
CROSS  JOIN bounds b
WHERE  w.window_id > b.w_min
  AND  w.window_id < b.w_max
ORDER  BY w.window_id
