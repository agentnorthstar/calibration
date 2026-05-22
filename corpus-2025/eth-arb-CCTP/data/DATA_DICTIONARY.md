# Data Dictionary, annual_panel_2025

Hourly panel of ETH-ARB substrate observability for 2025. Columns aligned strictly with the Invarians v2.0 API contract (developers.html). Each row is one UTC hour.

## Identifier and time

- **hour_utc** (index, datetime64[ns, UTC]): start of the hour, UTC. Range 2025-01-01 00:00 to 2025-12-31 23:00.

## Regime codes (categorical, v2.0 API)

- **regime_eth** (str): Ethereum L1 regime, 1 of 12 signed codes. Possible values: S1D1, S1D2+, S1D2-, S1D2±, S2+D1, S2+D2+, S2+D2-, S2+D2±, S2-D1, S2-D2+, S2-D2-, S2-D2±. Computed by the prod SQL view from L1 ratios + thresholds in `l1_thresholds`. ETH thresholds: threshold_s2=1.12, d2_sigma=1.10, d2_size=1.20, d2_tx=1.10, d2_logic="2 of 3", event-based calibration TPR 100% (4/4), FPR 1.23%.
- **regime_arb** (str): Arbitrum L2 regime, same 12 codes possible. ARB calibration is MEDIUM statistical; sigma_demand axis is structurally degenerated (Nitro gas constraint), so D2 rule for ARB uses 2-of-2 (size>1.20 AND tx>1.10) excluding sigma.

## Bridge state (categorical, v2.0 API)

- **bridge_state_eth_arb** (str): BS1 (sain) or BS2 (stressed) for CCTP Ethereum-to-Arbitrum. Research calibration P97/14d rolling on attestation_latency_p90_s. NOT yet equal to prod calibration (which uses circle_api_latency_ms via Iris probe, post-2026-05-20 expected).
- **bridge_state_arb_eth** (str): same for Arbitrum-to-Ethereum direction.

## ETH signed shifts, 5 axes (v2.0 API L1 panel)

All shifts are signed differences `ratio - ratio_long` per metric, where ratio is current ratio vs fast EMA baseline and ratio_long is the same vs slow EMA (30-day baseline). Computed by ans-l2-validator and ans-chain-validator binaries.

- **eth_struct_rhythm_shift** (float): structural rhythm deviation (block time inertia vs baseline). Positive = blocks slower.
- **eth_struct_continuity_shift** (float): structural continuity deviation (slot occupation %). Positive = more continuous than baseline.
- **eth_demand_sigma_shift** (float): demand sigma (saturation) deviation. Positive = blocks more saturated.
- **eth_demand_size_shift** (float): demand size (avg bytes per block) deviation. Positive = larger blocks.
- **eth_demand_tx_shift** (float): demand tx count deviation. Positive = more transactions per block.

Note: `beacon_participation_shift` is exposed by the API as a third ETH structural axis but NOT included in this 2025 dataset (prod sensor deployed ~2026-05-01 only, no historical backfill).

## ARB signed shifts, 8 axes (v2.0 API L2 panel)

- **arb_struct_rhythm_shift** (float): same definition as ETH.
- **arb_struct_continuity_shift** (float): same.
- **arb_struct_seq_publish_latency_shift** (float): L2 third structural axis. Delay between L2 block produced and batch posted on L1. Positive = sequencer slower to publish.
- **arb_demand_sigma_shift** (float): BLINDSPOT. Nitro gas constraint = sigma_ratio permanently near 1.0. Variable carries little signal on ARB. Excluded from regime D2 rule by design (2-of-2 size+tx instead).
- **arb_demand_size_shift** (float): same definition.
- **arb_demand_tx_shift** (float): same.
- **arb_demand_complexity_shift** (float): demand complexity (composition of operations). L2-specific observable, not in L1.
- **arb_demand_gas_complexity_shift** (float): demand gas_complexity (ratio of complex ops to total). L2-specific.

## CCTP attestation latency, raw observable (v2.0 API bridges.metrics)

Latency between source-side burn event (DepositForBurn + MessageSent on TokenMessenger v1) and observed receive on destination. Reconstructed from on-chain timing in BigQuery, NOT prod Iris probe.

- **cctp_eth_arb_latency_p50_s** (float): median per hour, eth-to-arb direction.
- **cctp_eth_arb_latency_p90_s** (float): p90 per hour, eth-to-arb. **Drives bridge_state_eth_arb classification.**
- **cctp_eth_arb_latency_p99_s** (float): p99 per hour, eth-to-arb. NOT used for BS classification (potential calibration enrichment).
- **cctp_eth_arb_messages_1h** (int): number of messages observed in the hour.
- **cctp_arb_eth_latency_p50_s** (float): same for arb-to-eth direction.
- **cctp_arb_eth_latency_p90_s** (float): same.
- **cctp_arb_eth_latency_p99_s** (float): same.
- **cctp_arb_eth_messages_1h** (int): same.

## Derived and annotation columns

- **combined_cell** (str): joint tuple `ETH:{regime_eth}|ARB:{regime_arb}|BS_e2a:{bridge_state_eth_arb}|BS_a2e:{bridge_state_arb_eth}`. Up to 432 categorical levels, empirically observed 99 unique in 2025 baseline.
- **in_incident_window_pm6h** (bool): True if hour is within +/- 6 hours of one of the 5 infra-critical incident hot windows. Used to define the baseline (False rows = baseline non-event hours).
- **incident_id** (str or None): incident identifier (S03, L02, D01, S04, S05) if in_incident_window_pm6h is True. Else None.
- **incident_label** (str or None): human-readable incident label.
- **in_incident_hot** (bool): True if hour is strictly within the hot window (no buffer). For incidents with sub-hour duration (L02, etc.), pandas hourly index may capture 0 or fewer hours than expected.
- **incident_hot_id** (str or None): incident id for strict hot only.

## The 5 infra-critical incidents

| id  | label                                       | hot_start_utc        | hot_end_utc          |
|-----|---------------------------------------------|----------------------|----------------------|
| S03 | Pectra mainnet activation                   | 2025-05-07 10:05     | 2025-05-07 18:00     |
| L02 | ARB One sequencer connectivity 2h35         | 2025-06-12 19:05     | 2025-06-12 21:40     |
| D01 | USDe Binance cascade $19B liquidations      | 2025-10-10 20:30     | 2025-10-11 06:00     |
| S04 | Fusaka mainnet activation (PeerDAS)         | 2025-12-03 21:49     | 2025-12-04 05:00     |
| S05 | BPO1 mainnet activation (blob target)       | 2025-12-09 14:21     | 2025-12-09 22:00     |

## Caveats for ML use

1. **Research vs prod calibration**: this dataset uses event-agent BigQuery-derived parquets. Prod calibration (Supabase) for BS may differ.
2. **ARB sigma blindspot**: `arb_demand_sigma_shift` carries no usable signal. Recommend dropping for any ML model.
3. **Bridge state pending**: `bridge_state_*` is research P97/14d, prod calibration pending post-2026-05-20.
4. **CCTP V1 only**: V2 launched ARB 2025-05-02, but the bridge_state parquet is V1-only by construction.
5. **Highly imbalanced classes for ML**: 46.4% of rows are the single dominant cell `(S1D1, S1D1, BS1, BS1)`. Top 10 cells account for 83% of hours. Consider stratified sampling or class-weighting for ML.
6. **Time series structure**: hourly index is sequential; auto-correlation expected within ~6-24 hour windows. Use temporal CV (rolling/expanding window) instead of random split.
7. **Incident labels are weak**: only 5 events labeled across 8760 hours = severely imbalanced for supervised learning. Anomaly detection (unsupervised) or one-class classification may fit better than supervised classification.
8. **EMA decay characteristics**: `*_shift` columns use fast EMA (alpha=2/11, period ~10h) and slow EMA (alpha=2/721, period ~30d). The slow EMA needed ~30d post-launch to stabilize; early 2025 rows may have transient shift values.

## Suggested ML angles for a data scientist

- **Anomaly detection on continuous shifts**: isolation forest or LOF on the 13 shift columns (5 ETH + 8 ARB). Check whether incidents emerge in the top 1% anomalies. Hypothesis: D01 yes, L02 no, S03/S04 yes, S05 maybe.
- **Sequence model on hourly cell trajectories**: HMM or RNN to predict next-hour combined_cell from past N hours. Identify hours with low transition probability.
- **Bridge-state predictor**: classify next-hour bridge_state_eth_arb from current substrate shifts. Test whether p99 latency adds signal over p90 (calibration enrichment hypothesis).
- **Latent embedding of combined_cell**: t-SNE or UMAP on continuous shifts colored by combined_cell. Verify whether the 99 observed cells cluster into coherent groups.
- **Causal direction tests**: does an ETH structural shift precede an ARB demand shift? Granger causality or transfer entropy on the shift columns.

## File outputs

- `annual_panel_2025.parquet` : binary, ~500 KB, pandas-readable.
- `annual_panel_2025.csv` : text, ~3 MB, generic.
- `DATA_DICTIONARY.md` : this file.

## Reproducibility

Source script: `scripts/export_panel_2025.py`
Source data: `data/metrics/{ethereum,arbitrum}_2025-Q[1-4]-application_with_regime.parquet` + `data/bridge_state_eth_arb_cctp_2025.parquet`
