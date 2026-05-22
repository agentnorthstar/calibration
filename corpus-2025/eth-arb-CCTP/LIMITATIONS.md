# Limitations

Four caveats apply across the analysis. Each is stated honestly so an external reviewer can weight the findings.

## 1. Research calibration versus production calibration

The data in `data/annual_panel_2025.parquet` is reconstructed from BigQuery public datasets through the Invarians reference pipeline applied retrospectively to 2025. The production calibration of the v2.0 API uses runtime measurements (Iris probe latency for CCTP, beacon API for participation, etc.) that differ from the BigQuery reconstruction in two ways.

- The bridge state BS1 versus BS2 in the parquet uses research P97 over rolling 14 days on `attestation_latency_p90_s` in seconds, reconstructed from on-chain timing.
- The production calibration of BS1 versus BS2 uses `circle_api_latency_ms` in milliseconds, from the Iris health probe, with thresholds finalized post-2026-05-20 after 30 days of runtime collection.

The two carry different semantics. The research reconstruction shown here is the best available retrospective approximation, not a substitute for the production calibration.

## 2. Beacon participation absent from the 2025 panel

The v2.0 API exposes `structural.beacon_participation` as a third structural observable on Ethereum L1 (alongside `rhythm` and `continuity`). The production sensor that writes `validator_participation_rate` to the public panel was calibrated at threshold 0.97 on 2026-05-01 and started writing records to the panel around that date.

For 2025 historical reconstruction, the equivalent data is not held locally. Backfill via beaconcha.in public API (rate-limited free tier, approximately 15 hours of continuous polling) or via paid third-party providers (Goldsky, Allium) was evaluated and declined.

Consequence for this analysis: the ETH structural panel shows 2 axes (rhythm, continuity) instead of the 3 the API exposes. For events post-2026-05-01, the third axis is available in production and can be integrated in future analyses.

## 3. Arbitrum sigma blindspot

By design of Arbitrum Nitro, the gas capacity used for computing `sigma_ratio` (capacity utilization) is the protocol theoretical maximum, approximately 1.125 × 10^15, while the effective gas limit per block is around 3.2 × 10^7. The ratio is therefore permanently close to 1.0, and the `sigma_demand_shift` column on Arbitrum carries no usable signal.

The Arbitrum D2 classification rule in the production API applies a 2-of-2 logic on `size_demand_shift` and `tx_demand_shift`, explicitly excluding `sigma_demand_shift`. The blindspot is documented in the calibration methodology and the agent context documentation.

For ML or statistical work on the panel: recommend dropping `arb_demand_sigma_shift` from the feature set.

## 4. CCTP V1 only

The CCTP collector deployed in production at the time of the 2025 reconstruction captures only V1 (hard finality, 13 to 19 minutes on Ethereum). Circle launched CCTP V2 (fast finality, 8 to 20 seconds) on Arbitrum on 2025-05-02. Any 2025 hour after that date may carry mixed V1 and V2 traffic in the raw block observations, but the `bridge_state_eth_arb_cctp_2025.parquet` is V1-only by construction (the matched-message function filters on V1 TokenMessenger addresses).

Implication: latency observations in `cctp_*_latency_p*_s` columns reflect V1 message timing only. Any V2 message that crossed the corridor after 2025-05-02 is not in this dataset. For 2025-05-02 onward, the dataset is a subset of total CCTP traffic, not the complete picture.

## Combined effect

The four caveats narrow the scope of the analysis to:

- Substrate reconstruction matching the production v2.0 API minus beacon participation,
- For Ethereum and Arbitrum specifically,
- For CCTP V1 routes between them,
- Calendar year 2025.

Within this scope, the analysis is reproducible from the included parquets and scripts without external API calls.

The five events in `EVENTS_2025.md` are interpreted in the context of these caveats. None of the caveats affects the categorical regime classification produced by the v2.0 API (the regime codes use only ratios and EMA baselines that are fully reconstructable from BigQuery), and the qualitative interpretation of pre, during, and post pattern shifts is unaffected by them.

## Out of scope by design

The analysis does not address:

- Application-layer event detection (smart contract bugs, governance compromises, exchange hacks).
- Code defect prediction.
- Profitability of any trading or arbitrage strategy.
- Causal attribution of substrate changes to economic factors.
- Cross-corridor extrapolation (Base, Optimism, Polygon, Avalanche).

These exclusions are deliberate and align with the Invarians substrate observability mandate.
