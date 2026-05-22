"""Export the 2025 hourly panel used in plots/annual_baseline_2025.png.

Inputs (per-chain metrics, expected under data/metrics/):
  ethereum_2025-Q[1-4]-application_with_regime.parquet
  arbitrum_2025-Q[1-4]-application_with_regime.parquet
  bridge_state_eth_arb_cctp_2025.parquet (shipped under data/)

Outputs (under data/):
  annual_panel_2025.parquet  (binary)
  annual_panel_2025.csv      (text)

Note: this script regenerates the panel from intermediate metrics. The output
parquet/csv are already shipped in data/ for direct consumption.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = DATA_DIR
OUT_DIR.mkdir(exist_ok=True)

INCIDENTS = [
    ("S03", "Pectra mainnet activation", "2025-05-07 10:05", "2025-05-07 18:00"),
    ("L02", "ARB One sequencer connectivity 2h35", "2025-06-12 19:05", "2025-06-12 21:40"),
    ("D01", "USDe Binance cascade $19B liquidations", "2025-10-10 20:30", "2025-10-11 06:00"),
    ("S04", "Fusaka mainnet activation (PeerDAS)", "2025-12-03 21:49", "2025-12-04 05:00"),
    ("S05", "BPO1 mainnet activation (blob target)", "2025-12-09 14:21", "2025-12-09 22:00"),
]
BUFFER_H = 6


def load_chain(chain):
    frames = []
    for q in ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        path = DATA_DIR / "metrics" / f"{chain}_{q}-application_with_regime.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    return pd.concat(frames).sort_index() if frames else pd.DataFrame()


def build_full_panel():
    eth = load_chain("ethereum")
    arb = load_chain("arbitrum")
    bs = pd.read_parquet(DATA_DIR / "bridge_state_eth_arb_cctp_2025.parquet").reset_index()

    eth_keep = eth[["regime",
                    "rhythm_ratio_shift", "continuity_ratio_shift",
                    "sigma_demand_shift", "size_demand_shift", "tx_demand_shift"]].copy()
    eth_keep.columns = ["regime_eth",
                        "eth_struct_rhythm_shift", "eth_struct_continuity_shift",
                        "eth_demand_sigma_shift", "eth_demand_size_shift", "eth_demand_tx_shift"]

    arb_keep = arb[["regime",
                    "rhythm_ratio_shift", "continuity_ratio_shift", "sequencer_publish_latency_shift",
                    "sigma_demand_shift", "size_demand_shift", "tx_demand_shift",
                    "complexity_value_shift", "gas_complexity_ratio_shift"]].copy()
    arb_keep.columns = ["regime_arb",
                        "arb_struct_rhythm_shift", "arb_struct_continuity_shift", "arb_struct_seq_publish_latency_shift",
                        "arb_demand_sigma_shift", "arb_demand_size_shift", "arb_demand_tx_shift",
                        "arb_demand_complexity_shift", "arb_demand_gas_complexity_shift"]

    bs_e2a = bs[bs["route_id"] == "eth-arb"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s",
         "messages_observed_1h"]
    ].rename(columns={
        "state": "bridge_state_eth_arb",
        "attestation_latency_p50_s": "cctp_eth_arb_latency_p50_s",
        "attestation_latency_p90_s": "cctp_eth_arb_latency_p90_s",
        "attestation_latency_p99_s": "cctp_eth_arb_latency_p99_s",
        "messages_observed_1h": "cctp_eth_arb_messages_1h",
    })
    bs_a2e = bs[bs["route_id"] == "arb-eth"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s",
         "messages_observed_1h"]
    ].rename(columns={
        "state": "bridge_state_arb_eth",
        "attestation_latency_p50_s": "cctp_arb_eth_latency_p50_s",
        "attestation_latency_p90_s": "cctp_arb_eth_latency_p90_s",
        "attestation_latency_p99_s": "cctp_arb_eth_latency_p99_s",
        "messages_observed_1h": "cctp_arb_eth_messages_1h",
    })

    panel = eth_keep.join(arb_keep, how="inner").join(bs_e2a, how="inner").join(bs_a2e, how="inner")
    panel = panel.sort_index()

    # Add joint cell column
    panel["combined_cell"] = panel.apply(
        lambda r: f"ETH:{r['regime_eth']}|ARB:{r['regime_arb']}|BS_e2a:{r['bridge_state_eth_arb']}|BS_a2e:{r['bridge_state_arb_eth']}",
        axis=1
    )

    # Add incident flag and label
    panel["in_incident_window_pm6h"] = False
    panel["incident_id"] = None
    panel["incident_label"] = None
    for inc_id, inc_label, start, end in INCIDENTS:
        s = pd.Timestamp(start, tz="UTC") - pd.Timedelta(hours=BUFFER_H)
        e = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=BUFFER_H)
        mask = (panel.index >= s) & (panel.index <= e)
        panel.loc[mask, "in_incident_window_pm6h"] = True
        panel.loc[mask, "incident_id"] = inc_id
        panel.loc[mask, "incident_label"] = inc_label

    # Add narrower hot-only flag (no buffer)
    panel["in_incident_hot"] = False
    panel["incident_hot_id"] = None
    for inc_id, inc_label, start, end in INCIDENTS:
        s = pd.Timestamp(start, tz="UTC")
        e = pd.Timestamp(end, tz="UTC")
        mask = (panel.index >= s) & (panel.index <= e)
        panel.loc[mask, "in_incident_hot"] = True
        panel.loc[mask, "incident_hot_id"] = inc_id

    panel.index.name = "hour_utc"
    return panel


def write_data_dict():
    content = """# Data Dictionary, annual_panel_2025

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
"""
    out = OUT_DIR / "DATA_DICTIONARY.md"
    out.write_text(content, encoding="utf-8")
    print(f"Wrote {out}")


def main():
    print("Building panel...")
    panel = build_full_panel()
    print(f"Shape: {panel.shape}")
    print(f"Range: {panel.index.min()} -> {panel.index.max()}")
    print(f"Columns: {panel.columns.tolist()}")
    print(f"Baseline rows (in_incident_window_pm6h=False): {(~panel['in_incident_window_pm6h']).sum()}")
    print(f"Incident-window rows: {panel['in_incident_window_pm6h'].sum()}")
    print(f"Strict hot rows: {panel['in_incident_hot'].sum()}")

    parquet_path = OUT_DIR / "annual_panel_2025.parquet"
    csv_path = OUT_DIR / "annual_panel_2025.csv"
    panel.to_parquet(parquet_path)
    panel.to_csv(csv_path)
    print(f"\nWrote {parquet_path}  ({parquet_path.stat().st_size / 1024:.1f} KB)")
    print(f"Wrote {csv_path}  ({csv_path.stat().st_size / 1024:.1f} KB)")

    write_data_dict()


if __name__ == "__main__":
    main()
