"""End-to-end pipeline OP for the ETH-OP-CCTP OOS validation.

Inputs (already pulled):
  data/blocks/op_2025.csv                 (year-long)
  data/l2_batches/op_batches_2025.csv     (year-long)
  data/cctp_events/op_burns_2025-Q[1-4].parquet     (raw logs, decoded here)
  data/cctp_events/op_receives_2025-Q[1-4].parquet  (raw logs, decoded here)
  data/cctp_events/ethereum_burns_2025-Q[1-4].parquet     (already decoded by ARB pipeline? raw logs)
  data/cctp_events/ethereum_receives_2025-Q[1-4].parquet  (same)

Outputs:
  data/blocks/op_2025-Q[1-4]-application.parquet      (quarterly split, hour_utc index)
  data/l2_batches/op_2025-Q[1-4]-application.parquet  (same)
  data/metrics/op_2025-Q[1-4]-application_with_regime.parquet
  data/bridge_state_eth_op_cctp_2025.parquet
  data/op_panel_2025.parquet                          (the OOS input panel)

Run:
  python scripts/build_op_pipeline.py

Note: this script depends on a `lib/` package (compute_l2_metrics, add_ema_and_shifts,
calibrate_l2_thresholds, apply_l2_regime, decode_burns_df, decode_receives_df,
match_messages, calibrate_cctp_route_threshold, apply_bridge_state_per_quarter,
aggregate_hourly_latencies) that is part of the Invarians reference pipeline.
The resulting outputs (`op_panel_2025.parquet`, `bridge_state_eth_op_cctp_2025.parquet`)
are shipped under data/ for direct consumption without re-running the pipeline.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BLOCKS = DATA / "blocks"
L2_BATCHES = DATA / "l2_batches"
CCTP = DATA / "cctp_events"
METRICS = DATA / "metrics"
METRICS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

from lib.metrics import compute_l2_metrics
from lib.ema import add_ema_and_shifts
from lib.calibrate import calibrate_l2_thresholds
from lib.regime import apply_l2_regime
from lib.decode_cctp import decode_burns_df, decode_receives_df, match_messages
from lib.bridge_state import (
    calibrate_cctp_route_threshold,
    apply_bridge_state_per_quarter,
)


OP_TARGET_BLOCK_TIME_S = 2.0  # OP Stack
QUARTERS = [
    ("2025-Q1", datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 4, 1, tzinfo=timezone.utc)),
    ("2025-Q2", datetime(2025, 4, 1, tzinfo=timezone.utc), datetime(2025, 7, 1, tzinfo=timezone.utc)),
    ("2025-Q3", datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 10, 1, tzinfo=timezone.utc)),
    ("2025-Q4", datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
]
# Calibration window for the year: first 14 days of Jan (matches eth-arb convention,
# kept short to leave Feb-Dec for application). Used for both L2 thresholds AND CCTP
# route BS1 threshold.
CAL_START = datetime(2025, 1, 1, tzinfo=timezone.utc)
CAL_END = datetime(2025, 1, 15, tzinfo=timezone.utc)


# =============================================================================
# Step 1: Split year CSV into quarterly application parquets
# =============================================================================

def split_year_csv_to_quarterly(csv_path: Path, prefix: str, dest_dir: Path) -> dict[str, Path]:
    """Split a year-long CSV (with `hour_utc` first col) into 4 quarterly parquets."""
    out: dict[str, Path] = {}
    print(f"\nSplitting {csv_path.name} -> {prefix}_*-application.parquet ...")
    df = pd.read_csv(csv_path)
    df["hour_utc"] = pd.to_datetime(df["hour_utc"], utc=True)
    df = df.set_index("hour_utc").sort_index()
    for label, start, end in QUARTERS:
        target = dest_dir / f"{prefix}_{label}-application.parquet"
        if target.exists():
            print(f"  cache {target.name}")
            out[label] = target
            continue
        sub = df.loc[(df.index >= start) & (df.index < end)]
        sub.to_parquet(target)
        print(f"  wrote {target.name}: {len(sub)} rows")
        out[label] = target
    return out


# =============================================================================
# Step 2: Compute L2 metrics + EMA + calibration + regime per quarter
# =============================================================================

def compute_op_metrics_with_regime() -> pd.DataFrame:
    """Build the year-long OP enriched metrics frame (metrics + EMA + shift + regime)."""
    blocks_q = {}
    batches_q = {}
    for label, _, _ in QUARTERS:
        blocks_q[label] = pd.read_parquet(BLOCKS / f"op_{label}-application.parquet")
        batches_q[label] = pd.read_parquet(L2_BATCHES / f"op_batches_{label}-application.parquet")

    # Step 2a: compute metrics each quarter, concat year
    metrics_year = []
    for label in [q[0] for q in QUARTERS]:
        m = compute_l2_metrics(blocks_q[label], batches_q[label], OP_TARGET_BLOCK_TIME_S)
        metrics_year.append(m)
    metrics_year = pd.concat(metrics_year).sort_index()
    print(f"\nOP metrics (concat): {len(metrics_year)} rows")

    # Step 2b: EMA + shifts on the full year (year-long EMA, halflife default 720h)
    # Pass the L2 metric set explicitly so sequencer_publish_latency and
    # gas_complexity_ratio get their _shift columns (default list omits them).
    L2_METRIC_COLS = [
        "rhythm_ratio", "continuity_ratio",
        "sigma_demand", "size_demand", "tx_demand",
        "complexity_value", "gas_complexity_ratio",
        "sequencer_publish_latency",
    ]
    enriched = add_ema_and_shifts(metrics_year, metric_cols=L2_METRIC_COLS)
    print(f"OP enriched (with EMA + shifts): {len(enriched)} rows, cols={len(enriched.columns)}")

    # Step 2c: calibrate L2 thresholds on Jan 1-15 window
    thresholds = calibrate_l2_thresholds(
        enriched, chain="optimism",
        calibration_start=CAL_START, calibration_end=CAL_END,
    )
    print(f"OP L2 thresholds: {thresholds}")

    # Step 2d: apply regime
    enriched["regime"] = apply_l2_regime(enriched, thresholds)
    print(f"OP regime distribution (head):")
    print(enriched["regime"].value_counts().head(8))

    # Step 2e: save per quarter
    for label, start, end in QUARTERS:
        target = METRICS / f"op_{label}-application_with_regime.parquet"
        sub = enriched.loc[(enriched.index >= start) & (enriched.index < end)]
        sub.to_parquet(target)
        print(f"  wrote {target.name}: {len(sub)} rows")

    return enriched


# =============================================================================
# Step 3: Build bridge_state_eth_op_cctp_2025
# =============================================================================

def build_bridge_state_eth_op() -> pd.DataFrame:
    """Match ETH burns -> OP receives + OP burns -> ETH receives, build hourly state."""
    print("\nLoading raw burns + receives ETH (filter dst=OP, src=OP)...")
    eth_burns_raw = pd.concat([
        pd.read_parquet(CCTP / f"ethereum_burns_{q[0]}.parquet") for q in QUARTERS
    ])
    eth_receives_raw = pd.concat([
        pd.read_parquet(CCTP / f"ethereum_receives_{q[0]}.parquet") for q in QUARTERS
    ])
    print(f"  eth burns raw rows total: {len(eth_burns_raw)}")
    print(f"  eth receives raw rows total: {len(eth_receives_raw)}")

    print("Loading raw burns + receives OP...")
    op_burns_raw = pd.concat([
        pd.read_parquet(CCTP / f"op_burns_{q[0]}.parquet") for q in QUARTERS
    ])
    op_receives_raw = pd.concat([
        pd.read_parquet(CCTP / f"op_receives_{q[0]}.parquet") for q in QUARTERS
    ])
    print(f"  op burns raw rows total: {len(op_burns_raw)}")
    print(f"  op receives raw rows total: {len(op_receives_raw)}")

    print("Decoding events…")
    eth_burns = decode_burns_df(eth_burns_raw)
    eth_receives = decode_receives_df(eth_receives_raw)
    op_burns = decode_burns_df(op_burns_raw)
    op_receives = decode_receives_df(op_receives_raw)
    print(f"  decoded: eth_burns={len(eth_burns)} eth_receives={len(eth_receives)}"
          f" op_burns={len(op_burns)} op_receives={len(op_receives)}")

    print("Matching messages…")
    # Route eth-op: ETH burns -> OP receives
    matched_eo = match_messages(eth_burns, op_receives, "ethereum", "optimism")
    # Route op-eth: OP burns -> ETH receives
    matched_oe = match_messages(op_burns, eth_receives, "optimism", "ethereum")
    print(f"  matched eth->op: {len(matched_eo)}")
    print(f"  matched op->eth: {len(matched_oe)}")

    print("Aggregating hourly latencies…")
    from lib.decode_cctp import aggregate_hourly_latencies
    hourly_eo = aggregate_hourly_latencies(matched_eo, "eth-op").reset_index()
    hourly_oe = aggregate_hourly_latencies(matched_oe, "op-eth").reset_index()
    hourly_combined = pd.concat([hourly_eo, hourly_oe]).sort_values(["hour_utc", "route_id"])
    hourly_combined["hour_utc"] = pd.to_datetime(hourly_combined["hour_utc"], utc=True)
    hourly_combined = hourly_combined.set_index("hour_utc")

    print("Calibrating BS1 threshold per route (P97 on Jan 1-15)…")
    thresholds = {}
    for route_id in ["eth-op", "op-eth"]:
        thresholds[route_id] = calibrate_cctp_route_threshold(
            hourly_combined, route_id, CAL_START, CAL_END, high_pct=97,
        )
        print(f"  {route_id}: {thresholds[route_id]}")

    print("Applying state per hour…")
    bs = apply_bridge_state_per_quarter(hourly_combined, thresholds)

    out_path = DATA / "bridge_state_eth_op_cctp_2025.parquet"
    bs.to_parquet(out_path)
    print(f"  wrote {out_path.name}: {len(bs)} rows")
    return bs


# =============================================================================
# Step 4: Build op_panel_2025 (mirrors annual_panel_2025 schema)
# =============================================================================

def build_op_panel() -> pd.DataFrame:
    """Assemble the OP OOS panel : eth substrate + op substrate + bridge state eth-op."""
    print("\nLoading existing annual panel (for ETH columns)…")
    # Reads the ETH columns from the eth-arb-CCTP panel.
    panel_arb = pd.read_parquet(
        ROOT.parent / "eth-arb-CCTP" / "data" / "annual_panel_2025.parquet"
    )

    eth_cols = [
        "regime_eth",
        "eth_struct_rhythm_shift", "eth_struct_continuity_shift",
        "eth_demand_sigma_shift", "eth_demand_size_shift", "eth_demand_tx_shift",
    ]
    eth_keep = panel_arb[eth_cols].copy()
    print(f"  ETH panel rows: {len(eth_keep)}")

    print("Loading OP enriched metrics…")
    op_year = []
    for label, _, _ in QUARTERS:
        op_year.append(pd.read_parquet(
            METRICS / f"op_{label}-application_with_regime.parquet"
        ))
    op_year = pd.concat(op_year).sort_index()
    print(f"  OP enriched rows: {len(op_year)}")

    op_keep = op_year[[
        "regime",
        "rhythm_ratio_shift", "continuity_ratio_shift", "sequencer_publish_latency_shift",
        "sigma_demand_shift", "size_demand_shift", "tx_demand_shift",
        "complexity_value_shift", "gas_complexity_ratio_shift",
    ]].copy()
    op_keep.columns = [
        "regime_op",
        "op_struct_rhythm_shift", "op_struct_continuity_shift", "op_struct_seq_publish_latency_shift",
        "op_demand_sigma_shift", "op_demand_size_shift", "op_demand_tx_shift",
        "op_demand_complexity_shift", "op_demand_gas_complexity_shift",
    ]

    print("Loading bridge state eth-op…")
    bs = pd.read_parquet(DATA / "bridge_state_eth_op_cctp_2025.parquet").reset_index()
    bs_eo = bs[bs["route_id"] == "eth-op"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s",
         "messages_observed_1h"]
    ].rename(columns={
        "state": "bridge_state_eth_op",
        "attestation_latency_p50_s": "cctp_eth_op_latency_p50_s",
        "attestation_latency_p90_s": "cctp_eth_op_latency_p90_s",
        "attestation_latency_p99_s": "cctp_eth_op_latency_p99_s",
        "messages_observed_1h": "cctp_eth_op_messages_1h",
    })
    bs_oe = bs[bs["route_id"] == "op-eth"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s",
         "messages_observed_1h"]
    ].rename(columns={
        "state": "bridge_state_op_eth",
        "attestation_latency_p50_s": "cctp_op_eth_latency_p50_s",
        "attestation_latency_p90_s": "cctp_op_eth_latency_p90_s",
        "attestation_latency_p99_s": "cctp_op_eth_latency_p99_s",
        "messages_observed_1h": "cctp_op_eth_messages_1h",
    })
    print(f"  bs_eo: {len(bs_eo)} | bs_oe: {len(bs_oe)}")

    panel = eth_keep.join(op_keep, how="inner").join(bs_eo, how="left").join(bs_oe, how="left")
    panel = panel.sort_index()
    print(f"\nPanel final shape: {panel.shape}")
    print(f"Time range: {panel.index.min()} -> {panel.index.max()}")
    print(f"Bridge eth-op classified hours: {(panel['bridge_state_eth_op'].notna()).sum()}")
    print(f"Bridge op-eth classified hours: {(panel['bridge_state_op_eth'].notna()).sum()}")

    out_path = DATA / "op_panel_2025.parquet"
    panel.to_parquet(out_path)
    print(f"\nWrote {out_path}")
    return panel


def main():
    # Step 1
    split_year_csv_to_quarterly(BLOCKS / "op_2025.csv", "op", BLOCKS)
    split_year_csv_to_quarterly(L2_BATCHES / "op_batches_2025.csv", "op_batches", L2_BATCHES)

    # Step 2
    if not all((METRICS / f"op_{q[0]}-application_with_regime.parquet").exists()
               for q in QUARTERS):
        compute_op_metrics_with_regime()
    else:
        print("\n[Step 2] OP metrics_with_regime parquets cached, skipping")

    # Step 3
    if not (DATA / "bridge_state_eth_op_cctp_2025.parquet").exists():
        build_bridge_state_eth_op()
    else:
        print("\n[Step 3] bridge_state_eth_op_cctp_2025.parquet cached, skipping")

    # Step 4
    build_op_panel()


if __name__ == "__main__":
    main()
