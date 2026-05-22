# Limitations: ETH-OP-CCTP 2025

Five caveats apply across the OP corridor analysis. Each is stated honestly so an external reviewer can weight the findings.

## 1. Research calibration versus production calibration

The data in `data/op_panel_2025.parquet` is reconstructed from BigQuery public datasets through the Invarians reference pipeline applied retrospectively to 2025. The production calibration of the v2.0 API uses runtime measurements (Iris probe latency for CCTP, beacon API for participation, etc.) that differ from the BigQuery reconstruction in two ways.

- The bridge state BS1 versus BS2 in the parquet uses research P97 over the first 14 days of January 2025 on `attestation_latency_p90_s` in seconds, reconstructed from on-chain timing.
- The production calibration of BS1 versus BS2 uses `circle_api_latency_ms` in milliseconds, from the Iris health probe, with thresholds finalized post-2026-05-20 after 30 days of runtime collection.

The two carry different semantics. The research reconstruction shown here is the best available retrospective approximation, not a substitute for the production calibration.

## 2. Beacon participation absent from the 2025 panel

The v2.0 API exposes `structural.beacon_participation` as a third structural observable on Ethereum L1. The production sensor that writes this observable to the public panel was deployed in mid-2026. For 2025 historical reconstruction the equivalent data is not held locally and is excluded from this dataset, consistent with the ETH-ARB panel.

Consequence: the ETH structural panel in the OP corpus shows 2 axes (rhythm, continuity) rather than the 3 the API exposes.

## 3. Single validated Delta precursor

The 648-configuration Delta exploration on the OP panel produced exactly one configuration surviving the combined Benjamini-Hochberg FDR correction at alpha=0.05 with lift greater than or equal to 1.5x: `eth_struct_continuity_shift|pctl=0.95|K=2`, at lead 6h on the `bridge_stress_full` outcome (lift 3.72x, p_adj=0.0, precision 71.4%).

A single survivor on a small documented event corpus (5 events in 2025) is fragile evidence. The result is conformant pre-engagement but lacks the diversity that would support broader inference. The cross-corridor test of this survivor on the ARB panel produced a non-significant result (see `results/oos_validation_op_survivor_on_arb_output.json`), confirming the chain-type-exclusive character of the OP-discovered configuration.

## 4. Documented 2025 OP mainnet event corpus is small

For calendar year 2025, the documented infrastructure-grade events on the OP corridor (substrate or bridge) consist of:

- Two Ethereum L1 hard forks (Pectra 2025-05-07, Fusaka 2025-12-03).
- One Ethereum L1 blob parameter activation (BPO1 2025-12-09).
- One OP Stack hard fork (Isthmus 2025-05-09).
- One macro liquidation cascade affecting CCTP latency (USDe cascade 2025-10-10 to 2025-10-11).
- One reclassified RPC endpoint outage with measurable substrate footprint (2025-08-19, 22 min).

The status.optimism.io page reports 100.0% uptime on Transaction Sequencing, Batch Submission, and Node Sync components for 2025 with the exception above. No mainnet sequencer downtime comparable to the Arbitrum L02 incident is documented.

The small N constrains statistical power for any analysis that depends on event diversity (matrix lift, supervised classification, calibration cross-validation).

## 5. OP RPC reclassification

The 2025-08-19 OP Public Endpoint outage was initially characterized as RPC-layer only by the official status page. The matrix qualified that hour as 100% divergent on the OP panel, while official telemetry reports nominal sequencer behavior. Investigation found `sequencer_publish_latency` rose from 516s to 708s during the affected hour, with positive shift, and block production cadence remained stable.

Two readings are possible:

- The cluster upgrade behind the RPC outage also affected batch submission, producing a real substrate footprint that the matrix detected before official reclassification.
- The matrix is sensitive to data-collection-side RPC health, which would mean a single-hour RPC outage at the data collector can produce a false-positive divergent classification.

Either interpretation has consequences for the matrix calibration. The event is retained in the corpus and documented as ambiguous. The corpus does not pre-commit to one interpretation.

## Out of scope by design

The analysis does not address:

- Application-layer event detection (smart contract bugs, governance compromises, exchange hacks).
- Causal attribution of substrate changes to economic factors.
- Cross-corridor extrapolation other than to the ETH-ARB-CCTP corridor (separate file).
- Profitability of any trading or arbitrage strategy.
- Solana or other non-EVM chains (separate corpora when calibrated).

These exclusions align with the Invarians substrate observability mandate.
