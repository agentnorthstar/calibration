# BigQuery Extracts Used in This Analysis

The 2025 hourly panel in `data/annual_panel_2025.parquet` is reconstructed from BigQuery public datasets through the Invarians reference pipeline. The SQL queries used for the source extraction are included in `sql_extracts/` for full reproducibility.

## Source datasets

All queries target Google BigQuery public datasets:

- `bigquery-public-data.crypto_ethereum`: Ethereum L1 blocks, transactions, logs, traces.
- `bigquery-public-data.crypto_arbitrum`: Arbitrum L2 blocks, transactions, logs.

No paid third-party indexers are used. No private API keys are required to reproduce the extracts from BigQuery.

## Extracts performed

### 1. ETH and ARB block-level statistics

Files: `sql_extracts/extract_blocks.sql`, `sql_extracts/extract_blocks_l2.sql`

Pulls per-block timestamp, gas_used, gas_limit, size, transaction_count, base_fee_per_gas. Output is processed by the Invarians L0 pipeline (`lib/` in parent repository) into hourly invariants (rhythm, continuity, sigma, size, tx, complexity).

### 2. CCTP V1 burn events (source side)

File: `sql_extracts/extract_cctp_burns.sql`

Pulls `DepositForBurn` events emitted by the TokenMessenger V1 contract on each source chain, plus the associated `MessageSent` events from the MessageTransmitter V1 contract. The match is by (source_domain, destination_domain, nonce) tuple.

TokenMessenger V1 mainnet addresses:
- Ethereum: 0xBd3fa81B58Ba92a82136038B25aDec7066af3155
- Arbitrum: 0x19330d10D9Cc8751218eaf51E8885D058642E08A
- Base: 0x1682Ae6375C4E4A97e4B583BC394c861A46D8962
- Optimism: 0x2B4069517957735bE00ceE0fadAE88a26365528f
- Avalanche: 0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982

MessageTransmitter V1 mainnet addresses:
- Ethereum: 0x0a992d191DEeC32aFe36203Ad87D7d289a738F81
- Arbitrum: 0xC30362313FBBA5cf9163F0bb16a0e01f01a896ca
- Base: 0xAD09780d193884d503182aD4588450C416D6F9D4
- Optimism: 0x4d41f22c5a0e5c74090899E5a8Fb597a8842b3e8
- Avalanche: 0x8186359aF5F57FbB40c6b14A588d2A59C0C29880

Domains: ETH=0, AVAX=1, OP=2, ARB=3, BASE=6.

### 3. CCTP V1 receive events (destination side)

File: `sql_extracts/extract_cctp_receives.sql`

Pulls `MessageReceived` events on each destination chain. Matched against burns from step 2 via (source_domain, destination_domain, nonce) for end-to-end latency reconstruction.

### 4. L2 batch posting events (Arbitrum sequencer)

File: `sql_extracts/extract_l2_batches.sql`

Pulls SequencerInbox `BatchDelivered` events on Ethereum L1, indexed by Arbitrum sequencer batch number. Used to compute `sequencer_publish_latency` as the time from L2 block production to L1 batch posting.

## Processing pipeline

The Invarians reference pipeline (Rust, `lib/` in parent repository) transforms the raw extracts into:

1. Per-block raw observables: load, capacity, size, tx count.
2. Hourly invariants: rhythm, continuity, sigma, size_avg, tx_count_avg, complexity, gas_complexity, sequencer_publish_latency (L2 only).
3. EMA ratios: short (~10 hours) and long (~30 days) baselines.
4. Signed shifts: per-axis deviation from the long EMA baseline.
5. Categorical regime: 12 codes per chain, applied per the calibration thresholds in `l1_thresholds` and `l2_thresholds` (see CALIBRATION_METHODOLOGY_RECAP.md in parent).
6. Bridge state: BS1 vs BS2 per route, P97 over rolling 14 days on attestation_latency_p90_s.

All processing is deterministic. Re-running the pipeline on the same BigQuery extracts produces bit-identical outputs.

## BigQuery cost note

The full 2025 extracts for the four queries listed above consume approximately 100 GB of BigQuery processing on the free tier, which is below the monthly free quota of 1 TB. Re-running the queries on a fresh account incurs no cost.

## Caveat on beacon participation

Beacon Chain consensus layer data (validator participation rate, attestation rate, finality checkpoints) is NOT in the BigQuery public datasets. The Invarians production sensor for beacon participation reads directly from a Beacon API endpoint (Lighthouse or equivalent), separately from the BigQuery pipeline. The 2025 historical reconstruction of beacon participation is therefore not derivable from BigQuery and is excluded from this dataset. See `../LIMITATIONS.md` section 2.
