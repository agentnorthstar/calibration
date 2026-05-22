"""OOS validation of the 6 ETH-ARB-CCTP survivors on ETH-OP-CCTP.

Pre-engaged thresholds. No post-hoc tuning. No grid search. Inputs:
  data/op_panel_2025.parquet (built by build_op_pipeline.py)

The 6 configurations are translated from ARB to OP by axis renaming
(arb_* -> op_*) and outcome substitution (latency on the ETH-OP-CCTP bridge
instead of the ETH-ARB-CCTP bridge). The eth_demand_tx survivor keeps its
predictor on Ethereum but its outcome moves to the ETH-OP-CCTP corridor.

Decision rule (pre-engaged, no post-hoc tuning):
  PASS_strong: >=4 of 6 survivors maintain lift >= 1.5x AND placebo p < 0.05
  PASS_weak:   2-3 of 6 survivors maintain lift >= 1.5x AND placebo p < 0.05
  FAIL:        fewer than 2 survivors maintain those thresholds

Outputs:
  oos_validation_op_output.json
  oos_validation_op_report.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR.parent
PANEL = ROOT / "data" / "op_panel_2025.parquet"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = RESULTS / "oos_validation_op_output.json"
OUT_MD = RESULTS / "oos_validation_op_report.md"

PLACEBO_PERMS = 1000
SEED = 42
LIFT_THRESHOLD = 1.5
P_THRESHOLD = 0.05
BRIDGE_LATENCY_RATIO_THRESHOLD = 50.0

SURVIVORS = [
    {
        "id": "S1",
        "predictor_axis": "op_struct_seq_publish_latency_shift",
        "K": 2, "pctl": 0.90, "lead": 3,
        "outcome": "latency_high_only",
        "arb_baseline_lift": 2.357, "arb_baseline_p": 0.004,
    },
    {
        "id": "S2",
        "predictor_axis": "op_struct_seq_publish_latency_shift",
        "K": 2, "pctl": 0.90, "lead": 6,
        "outcome": "latency_high_only",
        "arb_baseline_lift": 1.913, "arb_baseline_p": 0.002,
    },
    {
        "id": "S3",
        "predictor_axis": "op_demand_tx_shift",
        "K": 2, "pctl": 0.90, "lead": 6,
        "outcome": "latency_high_only",
        "arb_baseline_lift": 1.846, "arb_baseline_p": 0.000,
    },
    {
        "id": "S4",
        "predictor_axis": "op_demand_size_shift",
        "K": 2, "pctl": 0.90, "lead": 6,
        "outcome": "latency_high_only",
        "arb_baseline_lift": 1.815, "arb_baseline_p": 0.000,
    },
    {
        "id": "S5",
        "predictor_axis": "eth_demand_tx_shift",
        "K": 2, "pctl": 0.90, "lead": 6,
        "outcome": "bs2_only",
        "arb_baseline_lift": 1.558, "arb_baseline_p": 0.002,
    },
    {
        "id": "S6",
        "predictor_axis": "op_struct_seq_publish_latency_shift",
        "K": 2, "pctl": 0.90, "lead": 12,
        "outcome": "bridge_op_to_eth",
        "arb_baseline_lift": 1.531, "arb_baseline_p": 0.004,
    },
]


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


def eval_predictor(fire_arr, outcome_arr, placebo_perms=PLACEBO_PERMS, seed=SEED):
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

    rng = np.random.default_rng(seed)
    null_lifts = np.zeros(placebo_perms)
    for i in range(placebo_perms):
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
    if not PANEL.exists():
        print(f"ERROR: panel parquet missing: {PANEL}")
        sys.exit(1)

    print(f"Loading {PANEL}")
    df = pd.read_parquet(PANEL).sort_index()
    jan_mask = df.index.month == 1
    eligible_base = ~jan_mask

    # Substrate shifts (year already calibrated by pipeline)
    op_shifts = [c for c in df.columns if c.startswith("op_") and c.endswith("_shift")]
    eth_shifts = [c for c in df.columns if c.startswith("eth_") and c.endswith("_shift")]
    substrate_shifts = op_shifts + eth_shifts

    # Compute shift_magnitude_delta per axis (smd[t] = |shift[t]| - |shift[t-1]|)
    smd = pd.DataFrame(index=df.index)
    for col in substrate_shifts:
        s = df[col].abs()
        smd[col] = s - s.shift(1)

    # Calibrate axis thresholds at pctl=0.90 on non-January data (mirrors ARB grid)
    axis_thresholds = {}
    for col in substrate_shifts:
        valid = smd.loc[~jan_mask, col].dropna()
        if len(valid) == 0:
            axis_thresholds[col] = {0.90: float("nan")}
            continue
        axis_thresholds[col] = {0.90: float(valid.quantile(0.90))}

    # Build bridge layer outcomes
    bridge_ratios = pd.DataFrame(index=df.index)
    for col, msg_col in [
        ("cctp_eth_op_latency_p90_s", "cctp_eth_op_messages_1h"),
        ("cctp_eth_op_latency_p99_s", "cctp_eth_op_messages_1h"),
        ("cctp_op_eth_latency_p90_s", "cctp_op_eth_messages_1h"),
        ("cctp_op_eth_latency_p99_s", "cctp_op_eth_messages_1h"),
    ]:
        if col in df.columns and msg_col in df.columns:
            bridge_ratios[col] = bridge_latency_ratio_monthly(df, col, jan_mask, msg_col)
        else:
            bridge_ratios[col] = np.nan

    bs2_eth_op = df.get("bridge_state_eth_op", pd.Series("BS1", index=df.index)) == "BS2"
    bs2_op_eth = df.get("bridge_state_op_eth", pd.Series("BS1", index=df.index)) == "BS2"
    latency_high = (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)

    df["bs2_only"] = (bs2_eth_op | bs2_op_eth)
    df["latency_high_only"] = latency_high

    op_eth_dir_ratios = bridge_ratios[[
        c for c in ["cctp_op_eth_latency_p90_s", "cctp_op_eth_latency_p99_s"]
        if c in bridge_ratios.columns
    ]] if any(c in bridge_ratios.columns for c in ["cctp_op_eth_latency_p90_s", "cctp_op_eth_latency_p99_s"]) else pd.DataFrame(index=df.index)
    df["bridge_op_to_eth"] = (
        bs2_op_eth |
        (op_eth_dir_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
        if not op_eth_dir_ratios.empty else bs2_op_eth
    )

    print(f"Eligible hours (non-Jan): {int(eligible_base.sum())}")
    print(f"latency_high_only positive hours: {int(df['latency_high_only'].sum())}")
    print(f"bs2_only positive hours: {int(df['bs2_only'].sum())}")
    print(f"bridge_op_to_eth positive hours: {int(df['bridge_op_to_eth'].sum())}")
    print()

    results = []
    for cfg in SURVIVORS:
        axis = cfg["predictor_axis"]
        if axis not in smd.columns:
            print(f"  {cfg['id']} {axis}: MISSING_AXIS")
            results.append({**cfg, "status": "MISSING_AXIS", "lift": None, "placebo_p_value": None})
            continue
        threshold = axis_thresholds[axis][cfg["pctl"]]
        instant = (smd[axis] >= threshold).fillna(False).astype(int)
        rolling = instant.rolling(cfg["K"], min_periods=cfg["K"]).sum()
        fire = (rolling == cfg["K"])

        outcome_col = cfg["outcome"]
        if outcome_col not in df.columns:
            print(f"  {cfg['id']} outcome {outcome_col}: MISSING_OUTCOME")
            results.append({**cfg, "status": "MISSING_OUTCOME", "lift": None, "placebo_p_value": None})
            continue
        outcome_lead = shift_label_lead(df[outcome_col], cfg["lead"])
        mask = eligible_base & ~df[outcome_col]
        metrics = eval_predictor(fire[mask].values, outcome_lead[mask].values)

        passed = (metrics["lift"] >= LIFT_THRESHOLD) and (metrics["placebo_p_value"] < P_THRESHOLD)
        status = "PASS" if passed else "FAIL"
        print(f"  {cfg['id']} {axis} lead={cfg['lead']}h outcome={outcome_col}: "
              f"lift={metrics['lift']:.3f} p={metrics['placebo_p_value']:.4f} -> {status}")
        results.append({**cfg, "threshold_smd": round(threshold, 6),
                        "n_eligible_hours": int(mask.sum()),
                        **metrics,
                        "status": status})

    n_pass = sum(1 for r in results if r.get("status") == "PASS")
    if n_pass >= 4:
        verdict = "PASS_strong"
    elif n_pass >= 2:
        verdict = "PASS_weak"
    else:
        verdict = "FAIL"

    output = {
        "corridor": "ETH-OP-CCTP",
        "year": 2025,
        "placebo_perms": PLACEBO_PERMS,
        "lift_threshold": LIFT_THRESHOLD,
        "p_threshold": P_THRESHOLD,
        "n_survivors_tested": len(SURVIVORS),
        "n_pass_oos": n_pass,
        "verdict": verdict,
        "panel_rows": int(len(df)),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nVerdict: {verdict} ({n_pass} / {len(SURVIVORS)} maintain lift>={LIFT_THRESHOLD} + p<{P_THRESHOLD})")
    print(f"Wrote {OUT_JSON}")

    lines = ["# OOS validation report: ETH-OP-CCTP 2025", ""]
    lines.append("Corridor tested: ETH-OP-CCTP (out-of-sample relative to ETH-ARB-CCTP).")
    lines.append("")
    lines.append(f"Pre-engaged survivors re-tested: **{len(SURVIVORS)}**")
    lines.append(f"Placebo permutations per survivor: {PLACEBO_PERMS}")
    lines.append(f"PASS criterion per survivor: lift >= {LIFT_THRESHOLD} AND placebo p < {P_THRESHOLD}.")
    lines.append("")
    lines.append(f"## Verdict: **{verdict}**")
    lines.append("")
    lines.append(f"{n_pass} of {len(SURVIVORS)} survivors hold their effect on the out-of-sample corridor.")
    lines.append("")
    lines.append("Decision rule (pre-engaged):")
    lines.append("- PASS_strong: 4+ survivors hold")
    lines.append("- PASS_weak: 2-3 survivors hold")
    lines.append("- FAIL: fewer than 2 survivors hold")
    lines.append("")
    lines.append("## Per-survivor results")
    lines.append("")
    lines.append("| ID | Predictor axis | K | lead | outcome | ARB lift | OP lift | OP placebo p | status |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['id']} | `{r['predictor_axis']}` | {r['K']} | {r['lead']}h | "
            f"{r['outcome']} | {r['arb_baseline_lift']} | "
            f"{r.get('lift', 'n/a')} | {r.get('placebo_p_value', 'n/a')} | "
            f"**{r.get('status', '?')}** |"
        )
    lines.append("")
    if verdict.startswith("PASS"):
        lines.append("## Interpretation")
        lines.append("")
        lines.append("The surviving Delta configurations generalize beyond the ETH-ARB-CCTP corpus on which ")
        lines.append("they were discovered. The V3 design (precursors array carrying axis-specific calibration) ")
        lines.append("can proceed to deployment with the calibration metadata derived on ETH-ARB-CCTP plus an ")
        lines.append("OP recalibration entry. Per-corridor thresholds are still expected, but the underlying ")
        lines.append("signal is not corridor-specific.")
    else:
        lines.append("## Interpretation")
        lines.append("")
        lines.append("The Delta configurations that survived on ETH-ARB-CCTP do NOT generalize to ETH-OP-CCTP. ")
        lines.append("This indicates the surviving predictors were corridor-specific artefacts of the ARB corpus ")
        lines.append("rather than a generic agent-orientation signal. V3 deployment with the current ")
        lines.append("ARB-calibrated thresholds is paused. Next step: a per-corridor calibration registry, where ")
        lines.append("each corridor receives its own discovery process and its own validated precursors.")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
