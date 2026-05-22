"""Delta reconfiguration tests A, B, C.

Initial test (delta_temporal_precedence_test.py) returned lift 1.05x, placebo
p=0.19 (non-significant). Hypothesis: canonical Delta operational definition is
poorly calibrated, not that Delta concept is invalid. Three pre-engaged
reconfigurations test specific issues identified in the diagnosis.

Test A: cross-axis normalization (each axis normalized to its own z-score
distribution, then a threshold of |smd_z| >= 2.0 sustained K=2 hours)

Test B: single-axis predictor on arb_struct_seq_publish_latency_shift
(the axis that fired on D01 and has lowest autocorrelation r=0.07)

Test C: monotonic trend over 12h window (at least 9 of 11 step-increases in
shift magnitude within the rolling 12h window)

Same outcome, same lead window, same placebo. No post-hoc tuning. All 3 configs
pre-engaged before looking at results.

Outputs:
  delta_reconfig_tests_ABC_output.json
  delta_reconfig_tests_ABC_report.md
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data" / "annual_panel_2025.parquet"
RESULTS = BASE.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = RESULTS / "delta_reconfig_tests_ABC_output.json"
OUT_MD = RESULTS / "delta_reconfig_tests_ABC_report.md"

ETH_SHIFTS = [
    "eth_struct_rhythm_shift", "eth_struct_continuity_shift",
    "eth_demand_sigma_shift", "eth_demand_size_shift", "eth_demand_tx_shift",
]
ARB_SHIFTS_EFFECTIVE = [
    "arb_struct_rhythm_shift", "arb_struct_continuity_shift",
    "arb_struct_seq_publish_latency_shift",
    "arb_demand_size_shift", "arb_demand_tx_shift",
    "arb_demand_complexity_shift", "arb_demand_gas_complexity_shift",
]
SUBSTRATE_SHIFTS = ETH_SHIFTS + ARB_SHIFTS_EFFECTIVE
SEQUENCER_AXIS = "arb_struct_seq_publish_latency_shift"

# Pre-engaged thresholds (no post-hoc tuning)
TEST_A_SMD_Z_THRESHOLD = 2.0
TEST_A_K_CONSECUTIVE = 2
TEST_B_SMD_PCTL = 0.90
TEST_B_K_CONSECUTIVE = 2
TEST_C_TREND_WINDOW = 12
TEST_C_MIN_INCREASES = 9  # out of 11 pairs in 12h window

LEAD_WINDOW_HOURS = 6
BRIDGE_LATENCY_RATIO_THRESHOLD = 50.0
PLACEBO_PERMUTATIONS = 1000
RANDOM_SEED = 42

LABELED_EVENTS = {
    "S03": ("2025-05-07 10:05", "2025-05-07 18:00"),
    "L02": ("2025-06-12 19:05", "2025-06-12 21:40"),
    "D01": ("2025-10-10 20:30", "2025-10-11 06:00"),
    "S04": ("2025-12-03 21:49", "2025-12-04 05:00"),
    "S05": ("2025-12-09 14:21", "2025-12-09 22:00"),
}


def bridge_latency_ratio_monthly(df, col, exclude_mask):
    msg_col = "cctp_eth_arb_messages_1h" if "eth_arb" in col else "cctp_arb_eth_messages_1h"
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


def compute_metrics(eligible, delta_fire_col, outcome_col, placebo_n=PLACEBO_PERMUTATIONS, seed=RANDOM_SEED):
    n = len(eligible)
    delta_fire = eligible[delta_fire_col].values
    outcome = eligible[outcome_col].values

    tp = int(((delta_fire) & (outcome)).sum())
    fp = int(((delta_fire) & (~outcome)).sum())
    fn = int(((~delta_fire) & (outcome)).sum())
    tn = int(((~delta_fire) & (~outcome)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    base_rate = (tp + fn) / n if n > 0 else 0.0
    alert_rate = (tp + fp) / n if n > 0 else 0.0
    lift = precision / base_rate if base_rate > 0 else 0.0
    fp_rate = fp / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Placebo permutation
    np.random.seed(seed)
    outcome_arr = outcome.copy()
    null_lifts = []
    for _ in range(placebo_n):
        np.random.shuffle(outcome_arr)
        tp_p = int(((delta_fire) & (outcome_arr)).sum())
        fp_p = int(((delta_fire) & (~outcome_arr)).sum())
        precision_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
        lift_p = precision_p / base_rate if base_rate > 0 else 0.0
        null_lifts.append(lift_p)
    null_lifts = np.array(null_lifts)
    p_value = float((null_lifts >= lift).mean())

    return {
        "n_eligible": n,
        "n_delta_fires": int(tp + fp),
        "n_positive_outcomes": int(tp + fn),
        "base_rate": round(base_rate, 4),
        "alert_rate": round(alert_rate, 4),
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "lift": round(lift, 3),
        "fp_rate": round(fp_rate, 4),
        "f1": round(f1, 4),
        "placebo_null_mean_lift": round(float(null_lifts.mean()), 3),
        "placebo_null_p95_lift": round(float(np.percentile(null_lifts, 95)), 3),
        "placebo_null_max_lift": round(float(null_lifts.max()), 3),
        "placebo_p_value": round(p_value, 4),
    }


def per_event_precursor(df, delta_fire_col):
    out = []
    for inc_id, (start, end) in LABELED_EVENTS.items():
        ts_start = pd.Timestamp(start, tz="UTC")
        window_start = ts_start - pd.Timedelta(hours=LEAD_WINDOW_HOURS)
        window_end = ts_start - pd.Timedelta(hours=1)
        sub = df.loc[window_start:window_end]
        fired = bool(sub[delta_fire_col].any())
        out.append({"event": inc_id, "delta_fired_in_6h_prior": fired})
    return out


def main():
    np.random.seed(RANDOM_SEED)
    print("Loading panel...")
    df = pd.read_parquet(DATA).sort_index()
    jan_mask = df.index.month == 1
    print(f"Panel shape: {df.shape}, January excluded: {jan_mask.sum()}")

    # Compute shift_magnitude_delta per axis
    smd = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        s = df[col].abs()
        smd[col] = s - s.shift(1)

    # Bridge stress label (same as initial test)
    bridge_ratios = pd.DataFrame(index=df.index)
    for col in ["cctp_eth_arb_latency_p90_s", "cctp_eth_arb_latency_p99_s",
                "cctp_arb_eth_latency_p90_s", "cctp_arb_eth_latency_p99_s"]:
        bridge_ratios[col] = bridge_latency_ratio_monthly(df, col, jan_mask)

    df["bridge_stress"] = (
        (df["bridge_state_eth_arb"] == "BS2") |
        (df["bridge_state_arb_eth"] == "BS2") |
        (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )

    bridge_stress_in_next = pd.Series(False, index=df.index)
    for shift_h in range(1, LEAD_WINDOW_HOURS + 1):
        bridge_stress_in_next |= df["bridge_stress"].shift(-shift_h).fillna(False)
    df["bridge_stress_in_next_6h"] = bridge_stress_in_next

    # === TEST A: cross-axis normalization ===
    print("\n=== TEST A: cross-axis normalization (|smd_z| >= 2, K=2) ===")
    smd_z = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        valid = smd.loc[~jan_mask, col].dropna()
        # robust z using median + MAD
        med = valid.median()
        mad = (valid - med).abs().median() * 1.4826
        mad = max(mad, 1e-9)
        smd_z[col] = (smd[col] - med) / mad

    amplifying_a = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        instant = (smd_z[col].abs() >= TEST_A_SMD_Z_THRESHOLD).fillna(False).astype(int)
        rolling = instant.rolling(TEST_A_K_CONSECUTIVE, min_periods=TEST_A_K_CONSECUTIVE).sum()
        amplifying_a[col] = (rolling == TEST_A_K_CONSECUTIVE)
    df["delta_fire_A"] = amplifying_a.any(axis=1)

    # === TEST B: sequencer_publish_latency only, top 10% smd K=2 ===
    print("\n=== TEST B: sequencer_publish_latency seul, smd top 10%, K=2 ===")
    valid_b = smd.loc[~jan_mask, SEQUENCER_AXIS].dropna()
    threshold_b = float(valid_b.quantile(TEST_B_SMD_PCTL))
    instant_b = (smd[SEQUENCER_AXIS] >= threshold_b).fillna(False).astype(int)
    rolling_b = instant_b.rolling(TEST_B_K_CONSECUTIVE, min_periods=TEST_B_K_CONSECUTIVE).sum()
    df["delta_fire_B"] = (rolling_b == TEST_B_K_CONSECUTIVE)
    print(f"Test B threshold (top 10% smd on sequencer axis): {threshold_b:.4f}")

    # === TEST C: monotonic trend over 12h ===
    print("\n=== TEST C: monotonic trend (>=9 of 11 step-increases in 12h) ===")
    amplifying_c = pd.DataFrame(False, index=df.index, columns=SUBSTRATE_SHIFTS)
    for col in SUBSTRATE_SHIFTS:
        s_abs = df[col].abs()
        # for each hour T, count |shift_T| > |shift_T-1| over the past 12h (11 pairs)
        step_inc = (s_abs > s_abs.shift(1)).fillna(False).astype(int)
        rolling_inc = step_inc.rolling(TEST_C_TREND_WINDOW - 1, min_periods=TEST_C_TREND_WINDOW - 1).sum()
        amplifying_c[col] = (rolling_inc >= TEST_C_MIN_INCREASES).fillna(False)
    df["delta_fire_C"] = amplifying_c.any(axis=1)

    # Initial canonical (for comparison): top 10% raw smd K=2 any axis
    print("\n=== INITIAL (canonical, for comparison): top 10% raw smd K=2 any axis ===")
    thresholds_init = {}
    for col in SUBSTRATE_SHIFTS:
        valid = smd.loc[~jan_mask, col].dropna()
        thresholds_init[col] = float(valid.quantile(0.90))

    amplifying_init = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        instant = (smd[col] >= thresholds_init[col]).fillna(False).astype(int)
        rolling = instant.rolling(2, min_periods=2).sum()
        amplifying_init[col] = (rolling == 2)
    df["delta_fire_init"] = amplifying_init.any(axis=1)

    # Filter eligible hours (exclude January + currently-stressed) AFTER all columns added
    mask_eligible = (~jan_mask) & (~df["bridge_stress"])
    eligible = df[mask_eligible].copy()

    # Compute metrics for each test
    print("\nComputing metrics + placebo for all 4 configs (3 reconfig + initial)...")
    results = {}
    for test_name, fire_col in [("A_normalized", "delta_fire_A"), ("B_sequencer_only", "delta_fire_B"), ("C_trend_12h", "delta_fire_C")]:
        m = compute_metrics(eligible, fire_col, "bridge_stress_in_next_6h")
        ev = per_event_precursor(df, fire_col)
        m["per_event_precursor"] = ev
        m["n_events_with_precursor"] = sum(1 for e in ev if e["delta_fired_in_6h_prior"])
        results[test_name] = m

    m_init = compute_metrics(eligible, "delta_fire_init", "bridge_stress_in_next_6h")
    ev_init = per_event_precursor(df, "delta_fire_init")
    m_init["per_event_precursor"] = ev_init
    m_init["n_events_with_precursor"] = sum(1 for e in ev_init if e["delta_fired_in_6h_prior"])
    results["INITIAL_canonical"] = m_init

    # Print summary
    print("\n=== SUMMARY ===")
    print(f"{'Config':<25} {'Lift':>8} {'P-value':>10} {'Precision':>12} {'Recall':>10} {'Alert%':>10} {'Events':>10}")
    for name, m in results.items():
        print(f"{name:<25} {m['lift']:>8.2f} {m['placebo_p_value']:>10.3f} "
              f"{m['precision']*100:>11.1f}% {m['recall']*100:>9.1f}% "
              f"{m['alert_rate']*100:>9.2f}% {m['n_events_with_precursor']:>7}/5")

    # Save
    output = {
        "config_pre_engaged": {
            "Test_A_normalized": {
                "smd_z_threshold": TEST_A_SMD_Z_THRESHOLD,
                "K_consecutive": TEST_A_K_CONSECUTIVE,
                "axes": "all 12 substrate shifts",
            },
            "Test_B_sequencer_only": {
                "axis": SEQUENCER_AXIS,
                "smd_percentile": TEST_B_SMD_PCTL,
                "K_consecutive": TEST_B_K_CONSECUTIVE,
                "threshold_value": round(threshold_b, 5),
            },
            "Test_C_trend_12h": {
                "window_hours": TEST_C_TREND_WINDOW,
                "min_step_increases": TEST_C_MIN_INCREASES,
                "axes": "all 12 substrate shifts",
            },
            "common": {
                "outcome": "bridge stress in (T, T+6h] = BS2 OR latency ratio >= 50x monthly median",
                "exclusions": "January 2025 + currently bridge-stressed hours",
                "placebo_permutations": PLACEBO_PERMUTATIONS,
                "anti_tautology": "predictor uses substrate shifts only; outcome uses bridge state + latency",
            },
        },
        "results": results,
    }

    OUT_JSON.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")

    # Markdown report
    lines = ["# Delta Reconfiguration Tests A, B, C", ""]
    lines.append("Three pre-engaged reconfigurations of the canonical Delta operational definition. ")
    lines.append("Same outcome (bridge stress in next 6h), same eligible hours, same placebo. ")
    lines.append("No post-hoc tuning.")
    lines.append("")
    lines.append("## Comparison summary")
    lines.append("")
    lines.append("| Config | Lift | Placebo p | Precision | Recall | Alert rate | Events w/ precursor |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, m in results.items():
        lines.append(f"| {name} | **{m['lift']}x** | {m['placebo_p_value']} | {m['precision']*100:.1f}% | {m['recall']*100:.1f}% | {m['alert_rate']*100:.2f}% | {m['n_events_with_precursor']}/5 |")
    lines.append("")
    lines.append("## Per-configuration verdict")
    lines.append("")
    for name, m in results.items():
        lines.append(f"### {name}")
        lines.append("")
        if m["placebo_p_value"] >= 0.05:
            lines.append(f"**Placebo non-significant (p={m['placebo_p_value']}).** Observed lift compatible with random.")
        else:
            lines.append(f"**Placebo significant (p={m['placebo_p_value']}).** Lift unlikely under random labels.")
        lines.append("")
        if m["lift"] >= 2.0 and m["placebo_p_value"] < 0.05 and m["precision"] >= 0.30:
            lines.append("**PASS strong**: lift >= 2x, precision >= 30%, placebo significant.")
        elif m["lift"] >= 1.5 and m["placebo_p_value"] < 0.05:
            lines.append("**PASS weak**: signal real but precision below product-usable threshold.")
        else:
            lines.append("**FAIL**: signal does not meaningfully exceed null distribution.")
        lines.append("")
        lines.append(f"- Precision: {m['precision']*100:.1f}%")
        lines.append(f"- Recall: {m['recall']*100:.1f}%")
        lines.append(f"- Alert rate: {m['alert_rate']*100:.2f}%")
        lines.append(f"- Lift: {m['lift']}x (vs base rate {m['base_rate']*100:.1f}%)")
        lines.append(f"- Events with precursor: {m['n_events_with_precursor']}/5")
        for e in m["per_event_precursor"]:
            lines.append(f"  - {e['event']}: {'YES' if e['delta_fired_in_6h_prior'] else 'NO'}")
        lines.append("")

    lines.append("## Reading")
    lines.append("")
    # Best config
    best_name, best_m = max(results.items(), key=lambda kv: (kv[1]['lift'], -kv[1]['placebo_p_value']))
    lines.append(f"Best lift overall: **{best_name}** with lift {best_m['lift']}x, placebo p={best_m['placebo_p_value']}.")
    lines.append("")
    if best_m["lift"] >= 2.0 and best_m["placebo_p_value"] < 0.05:
        lines.append("At least one reconfiguration produces a meaningful signal. The Delta concept "
                     "is not invalidated; the canonical v2 operationalization is. Next step: validate "
                     "the best reconfiguration on an out-of-sample corridor (ETH-BASE-CCTP).")
    else:
        lines.append("None of the three reconfigurations produce a lift sufficient for agent "
                     "orientation use. The Delta concept may require a different reformulation "
                     "(other outcome, longer lead window, or cross-channel integration). "
                     "Honest reading: the v2 substrate Delta primitive does not orient agent "
                     "decisions on bridge stress in 2025 ETH-ARB-CCTP under any of the four tested "
                     "operational definitions.")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
