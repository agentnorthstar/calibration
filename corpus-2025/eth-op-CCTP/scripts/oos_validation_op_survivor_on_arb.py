"""Cross-OOS test : the unique OP-corpus survivor tested on the ARB panel.

The OP grid (648 configs, BH FDR, lift >= 1.5x) produced exactly one survivor:
  eth_struct_continuity_shift, pctl=0.95, K=2, lead=6h, outcome=bridge_stress_full

This script applies that pre-engaged configuration to the ARB panel without
tuning, to test whether the signal is OP-corridor-specific or also visible
on the ARB corridor (i.e. L1-driven, would suggest partial generalization).

PASS (cross-corridor): lift >= 1.5x AND placebo p < 0.05
FAIL: otherwise (signal is OP-specific or sample-noise on ARB)

Output:
  oos_validation_op_survivor_on_arb_output.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
PANEL_ARB = ROOT.parent / "eth-arb-CCTP" / "data" / "annual_panel_2025.parquet"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = RESULTS / "oos_validation_op_survivor_on_arb_output.json"

PLACEBO_PERMS = 1000
SEED = 42
LIFT_THRESHOLD = 1.5
P_THRESHOLD = 0.05
BRIDGE_LATENCY_RATIO_THRESHOLD = 50.0

# The OP-corpus survivor, frozen from delta_full_exploration_op_output.json
SURVIVOR = {
    "axis": "eth_struct_continuity_shift",
    "K": 2,
    "pctl": 0.95,
    "lead": 6,
    "outcome": "bridge_stress_full",
    "op_baseline_lift": 3.717,
    "op_baseline_p": 0.000,
}


def bridge_latency_ratio_monthly(df, col, exclude_mask, msg_col):
    low_volume = df[msg_col].fillna(0) < 5
    full_mask = exclude_mask | low_volume
    base = df[~full_mask].copy()
    base["month"] = base.index.month
    monthly_median = base.groupby("month")[col].median().replace(0, np.nan)
    month_col = pd.Series(df.index.month, index=df.index)
    med = month_col.map(monthly_median)
    ratio = df[col] / med
    ratio[low_volume] = np.nan
    return ratio


def eval_predictor(fire_arr, outcome_arr):
    fire_arr = np.asarray(fire_arr).astype(bool)
    outcome_arr = np.asarray(outcome_arr).astype(bool)
    n = len(fire_arr)
    tp = int((fire_arr & outcome_arr).sum())
    fp = int((fire_arr & ~outcome_arr).sum())
    fn = int((~fire_arr & outcome_arr).sum())
    tn = int((~fire_arr & ~outcome_arr).sum())
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    base_rate = (tp + fn) / n if n else 0.0
    alert_rate = (tp + fp) / n if n else 0.0
    lift = precision / base_rate if base_rate > 0 else 0.0

    rng = np.random.default_rng(SEED)
    null_lifts = np.zeros(PLACEBO_PERMS)
    for i in range(PLACEBO_PERMS):
        shuffled = rng.permutation(outcome_arr)
        tp_p = int((fire_arr & shuffled).sum())
        fp_p = int((fire_arr & ~shuffled).sum())
        prec_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
        null_lifts[i] = prec_p / base_rate if base_rate > 0 else 0.0
    p_value = float((null_lifts >= lift).mean())
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "base_rate": round(base_rate, 4), "alert_rate": round(alert_rate, 4),
        "lift": round(lift, 3), "placebo_p_value": round(p_value, 4),
    }


def shift_label_lead(label_series, lead):
    out = pd.Series(False, index=label_series.index)
    for h in range(1, lead + 1):
        out |= label_series.shift(-h).fillna(False)
    return out


def main():
    print(f"Loading ARB panel: {PANEL_ARB}")
    df = pd.read_parquet(PANEL_ARB).sort_index()
    jan_mask = df.index.month == 1
    eligible_base = ~jan_mask

    axis = SURVIVOR["axis"]
    if axis not in df.columns:
        raise SystemExit(f"axis {axis} not in ARB panel columns")

    # smd[t] = |shift[t]| - |shift[t-1]|
    s_abs = df[axis].abs()
    smd = s_abs - s_abs.shift(1)

    # Calibrate pctl=0.95 threshold on non-Jan
    valid = smd.loc[~jan_mask].dropna()
    threshold = float(valid.quantile(SURVIVOR["pctl"]))
    print(f"axis={axis} pctl=0.95 threshold_smd={threshold:.6f}")

    # Fire signal
    instant = (smd >= threshold).fillna(False).astype(int)
    rolling = instant.rolling(SURVIVOR["K"], min_periods=SURVIVOR["K"]).sum()
    fire = (rolling == SURVIVOR["K"])

    # Outcome bridge_stress_full on ARB corridor
    bridge_ratios = pd.DataFrame(index=df.index)
    bridge_ratios["cctp_eth_arb_latency_p90_s"] = bridge_latency_ratio_monthly(
        df, "cctp_eth_arb_latency_p90_s", jan_mask, "cctp_eth_arb_messages_1h"
    )
    bridge_ratios["cctp_eth_arb_latency_p99_s"] = bridge_latency_ratio_monthly(
        df, "cctp_eth_arb_latency_p99_s", jan_mask, "cctp_eth_arb_messages_1h"
    )
    bridge_ratios["cctp_arb_eth_latency_p90_s"] = bridge_latency_ratio_monthly(
        df, "cctp_arb_eth_latency_p90_s", jan_mask, "cctp_arb_eth_messages_1h"
    )
    bridge_ratios["cctp_arb_eth_latency_p99_s"] = bridge_latency_ratio_monthly(
        df, "cctp_arb_eth_latency_p99_s", jan_mask, "cctp_arb_eth_messages_1h"
    )
    df["bridge_stress_full"] = (
        (df["bridge_state_eth_arb"] == "BS2") |
        (df["bridge_state_arb_eth"] == "BS2") |
        (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )

    outcome_lead = shift_label_lead(df["bridge_stress_full"], SURVIVOR["lead"])
    mask = eligible_base & ~df["bridge_stress_full"]
    n_pos = int(df["bridge_stress_full"].sum())
    print(f"ARB bridge_stress_full positive hours: {n_pos}")

    metrics = eval_predictor(fire[mask].values, outcome_lead[mask].values)
    passed = (metrics["lift"] >= LIFT_THRESHOLD) and (metrics["placebo_p_value"] < P_THRESHOLD)
    status = "PASS_cross" if passed else "FAIL_cross"

    print(f"\nARB cross-OOS result for OP survivor:")
    print(f"  lift={metrics['lift']:.3f} | placebo_p={metrics['placebo_p_value']:.4f}")
    print(f"  precision={metrics['precision']*100:.1f}% | alert_rate={metrics['alert_rate']*100:.2f}%")
    print(f"  status={status}")

    output = {
        "test": "OP survivor tested on ARB corpus (cross-corridor OOS)",
        "predictor_axis": axis,
        "K": SURVIVOR["K"],
        "pctl": SURVIVOR["pctl"],
        "lead_hours": SURVIVOR["lead"],
        "outcome": SURVIVOR["outcome"],
        "test_corpus": "ETH-ARB-CCTP 2025",
        "n_eligible_hours": int(mask.sum()),
        "smd_threshold_value": round(threshold, 6),
        "op_baseline_lift": SURVIVOR["op_baseline_lift"],
        "op_baseline_p": SURVIVOR["op_baseline_p"],
        **metrics,
        "lift_threshold": LIFT_THRESHOLD,
        "p_threshold": P_THRESHOLD,
        "status": status,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")


if __name__ == "__main__":
    main()
