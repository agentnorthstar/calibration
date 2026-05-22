# Methodology: ETH-OP-CCTP 2025

## 1. Scope

- **Chains**: Ethereum L1 mainnet, Optimism (OP Mainnet, L2).
- **Bridge**: CCTP V1 (Circle Cross-Chain Transfer Protocol version 1), both ETH-to-OP and OP-to-ETH directions.
- **Time window**: 2025-01-01 00:00 UTC to 2025-12-31 23:00 UTC, hourly granularity.
- **Observable set**: strictly the metrics exposed by the Invarians v2.0 API. The Optimism observables follow the same v2.0 L2 schema as Arbitrum (8 axes: 3 structural plus 5 demand).

Out of scope:
- Other corridors (ETH-ARB, ETH-BASE, ETH-POL, etc.) are documented separately.
- Application-layer events (smart contract bugs, governance compromises) by design.

## 2. Data sources

### 2.1 BigQuery public datasets

Two datasets are used:

- `bigquery-public-data.crypto_ethereum`: Ethereum L1 blocks, transactions, logs.
- `bigquery-public-data.goog_blockchain_optimism_mainnet_us.logs`: Optimism mainnet logs.

The ETH columns of the OP panel are reused from the ETH-ARB panel (the L1 observables are identical regardless of which L2 is paired with it). See `../eth-arb-CCTP/bigquery/queries.md` for the L1 source queries.

### 2.2 OP block-level pulls

The OP block dataset (`data/blocks/op_2025.csv`) and L2 batch-posting events (`data/l2_batches/op_batches_2025.csv`) are obtained via separate BigQuery extracts on the goog public Optimism dataset. These intermediate files are not shipped in this corpus (they are large and only needed to reconstruct from scratch); the resulting `op_panel_2025.parquet` is shipped under `data/`.

### 2.3 CCTP V1 events on Optimism

`scripts/pull_op_cctp.py` pulls Optimism `DepositForBurn` and `MessageReceived` events from the goog public dataset. Full SQL is documented in `bigquery/pull_op_cctp.md`. Quarterly windows are used to keep individual query payloads small.

The Ethereum-side CCTP events are pulled by the ARB pipeline (same TokenMessenger and MessageTransmitter contracts on L1). The OP-side message pairing uses domain id 2 (Optimism) and domain id 0 (Ethereum).

## 3. Panel construction

`scripts/build_op_pipeline.py` orchestrates the pipeline:

1. Split the year-long OP blocks CSV into quarterly application parquets.
2. Compute L2 metrics per quarter using the Invarians reference pipeline (`lib/`).
3. Apply EMA-based shifts (fast EMA period approximately 10 hours, slow EMA period approximately 30 days) on the L2 metric series.
4. Calibrate L2 thresholds on the first 14 days of January 2025, then apply the 12-code regime classification per hour.
5. Build the CCTP bridge state series by matching ETH burns to OP receives and OP burns to ETH receives, then computing per-hour latency p50, p90, p99. BS1 versus BS2 threshold is the P97 of `attestation_latency_p90_s` over the calibration window.
6. Assemble the final panel `op_panel_2025.parquet` joining ETH L1 columns (from the ARB panel), OP L2 columns, and both directions of the bridge state.

The schema mirrors the ETH-ARB panel column-for-column with `arb_` replaced by `op_` and `eth_arb` by `eth_op`. The ETH columns are identical to those in `../eth-arb-CCTP/data/annual_panel_2025.parquet`.

## 4. OP-specific calibration notes

### 4.1 Block cadence

OP Stack runs a 2-second L2 block target. The `rhythm_ratio` metric is normalized against this target rather than against the 12-second L1 cadence or the variable Arbitrum Nitro cadence. The structural axis remains comparable to ARB in terms of regime code semantics (`S1`, `S2+`, `S2-`).

### 4.2 Sigma demand blindspot

The `op_demand_sigma_shift` axis is excluded from the OP regime D2 classification rule, in symmetry with the ARB Nitro sigma blindspot. The OP gas-limit-vs-capacity ratio is similarly compressed and carries no usable signal. The OP regime D2 rule is 2-of-2 logic on `size_demand` and `tx_demand` shifts.

### 4.3 Bridge throughput

CCTP V1 throughput on OP is moderate, lower than on ARB. This produces hourly latency observations with smaller sample sizes per hour, which adds variance to the BS1 versus BS2 classification at low-volume hours. The bridge state classification is masked (NaN) when `messages_observed_1h < 5`.

## 5. Delta validation protocol

`scripts/delta_full_exploration_op.py` runs the 648-configuration Delta exploration on the OP panel.

### 5.1 Configuration grid

Same grid as ETH-ARB:

- **F0 single-axis**: 12 axes (5 ETH + 7 OP effective) times 4 lead windows (3, 6, 12, 24h) times 2 K-values (1, 2) times 3 percentile thresholds (0.85, 0.90, 0.95) = 288 configurations.
- **F1 multi-axis grouped**: 8 groupings times 2 K times 4 leads at fixed pctl=0.90 = 64 configurations.
- **F2 alternative outcomes**: 12 axes times 2 K times 4 leads times 2 outcomes (BS2-only, latency-only) = 192 configurations.
- **F3 ML logistic regression**: 8 configurations (2 outcomes times 4 leads), trained on H1 2025 and tested on H2 2025.
- **F4 cross-chain**: 96 configurations (5 ETH axes plus 7 OP axes, predicting opposite-direction bridge outcomes).

### 5.2 Statistical test

Per configuration: a placebo permutation distribution is built by shuffling the outcome labels 500 times and recomputing the lift. The placebo p-value is the share of permutations producing lift greater than or equal to the observed lift.

### 5.3 Multiple-testing correction

Benjamini-Hochberg FDR correction at alpha=0.05 is applied across all 648 configurations. Survival criterion: combined FDR p_adj less than 0.05 AND lift greater than or equal to 1.5x.

### 5.4 OOS protocol

`scripts/oos_validation_op.py` translates the 6 ARB survivors to OP by axis renaming (`arb_*` to `op_*`) and bridge-outcome substitution. The pre-engaged decision rule before observing OP results:

- PASS_strong: at least 4 of 6 survivors hold (lift >= 1.5x and placebo p < 0.05).
- PASS_weak: 2 to 3 survivors hold.
- FAIL: fewer than 2 survivors hold.

`scripts/oos_validation_op_survivor_on_arb.py` does the symmetric test: the one OP-corpus survivor applied to the ARB panel.

## 6. Differences from ETH-ARB methodology

The protocol is structurally identical. Differences specific to OP:

1. **Smaller documented event corpus in 2025**: 5 events shared with the ARB corpus (Pectra, Fusaka, BPO1, USDe cascade, plus the OP-Stack-only Isthmus hard fork), versus 6 documented events on ARB (including the L02 ARB sequencer connectivity issue without a 2025 OP analogue).
2. **Different L2 typology**: OP Stack versus Arbitrum Nitro. Block cadence, sequencer architecture, and batch-submission mechanism differ. The substrate observables capture this in absolute terms but the regime vocabulary remains comparable.
3. **One RPC endpoint outage reclassified**: the 2025-08-19 17:43-18:05 OP Public Endpoint outage (22 min, official status page reports RPC-layer only) was originally excluded as application-layer. Investigation showed `sequencer_publish_latency` rose from 516s (17h) to 708s (18h, +37%) with positive shift, and block production cadence remained stable (1800 blocks per hour). The cluster upgrade affected batch submission in addition to the public endpoint, producing a measurable substrate footprint that the matrix detected. The event is retained in the corpus for this reason.

## 7. Reproducibility

```
python scripts/pull_op_cctp.py           # Pulls quarterly OP CCTP events from BigQuery
python scripts/build_op_pipeline.py      # Builds op_panel_2025.parquet from raw events
python scripts/delta_full_exploration_op.py
python scripts/oos_validation_op.py
python scripts/oos_validation_op_survivor_on_arb.py
```

The `lib/` package required by `build_op_pipeline.py` is part of the Invarians reference pipeline. The output panel `op_panel_2025.parquet` is shipped under `data/` for consumers who only need the validated dataset.

## 8. Relation to the v2.0 API

The OP panel uses the same v2.0 API output schema as the ARB panel. Production OP observability is published at `https://api.invarians.com/v2/panel` alongside the other chains under monitoring. The reconstruction here matches the production schema one-to-one except for ETH beacon participation (the production sensor was deployed in mid-2026; see `LIMITATIONS.md`).
