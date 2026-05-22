"""Full Delta exploration: 4 strategy families + per-family FDR + combined FDR.

Strategy families:
  F1: multi-axis grouped predictors (union/voting variants)
  F2: alternative outcomes (BS2 only, latency only) with single-axis grid
  F3: ML logistic regression on all shifts (train S1 2025, test S2 2025)
  F4: cross-chain (ETH -> ARB bridge, ARB -> ETH bridge)

Plus existing single-axis grid (referenced as F0).

Total: 640 configurations. BH FDR applied within each family and combined across
all 640. Survival criterion: combined FDR p_adj < 0.05 AND lift >= 1.5x.

Outputs:
  delta_full_exploration_output.json
  delta_full_exploration_report.md
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data" / "op_panel_2025.parquet"
RESULTS = BASE.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = RESULTS / "delta_full_exploration_op_output.json"
OUT_MD = RESULTS / "delta_full_exploration_op_report.md"

ETH_SHIFTS = [
    "eth_struct_rhythm_shift", "eth_struct_continuity_shift",
    "eth_demand_sigma_shift", "eth_demand_size_shift", "eth_demand_tx_shift",
]
# OP shifts available in op_panel_2025.parquet, mirror the ARB grid axes
# (rhythm, continuity, seq_publish_latency / size, tx, complexity, gas_complexity).
# sigma_demand intentionally omitted (same Nitro-style blindspot pattern).
OP_SHIFTS_EFFECTIVE = [
    "op_struct_rhythm_shift", "op_struct_continuity_shift",
    "op_struct_seq_publish_latency_shift",
    "op_demand_size_shift", "op_demand_tx_shift",
    "op_demand_complexity_shift", "op_demand_gas_complexity_shift",
]
ARB_SHIFTS_EFFECTIVE = OP_SHIFTS_EFFECTIVE  # alias for code symmetry
SUBSTRATE_SHIFTS = ETH_SHIFTS + OP_SHIFTS_EFFECTIVE
STRUCTURAL_SHIFTS = [s for s in SUBSTRATE_SHIFTS if "struct" in s]
DEMAND_SHIFTS = [s for s in SUBSTRATE_SHIFTS if "demand" in s]

LEADS = [3, 6, 12, 24]
KS = [1, 2]
PCTLS = [0.85, 0.90, 0.95]
PCTL_FIXED = 0.90
PLACEBO_PERMS = 500
FDR_ALPHA = 0.05
LIFT_THRESHOLD = 1.5
BRIDGE_LATENCY_RATIO_THRESHOLD = 50.0
SEED = 42

LABELED_EVENTS = {
    "S03": ("2025-05-07 10:05", "2025-05-07 18:00"),
    "L02": ("2025-06-12 19:05", "2025-06-12 21:40"),
    "D01": ("2025-10-10 20:30", "2025-10-11 06:00"),
    "S04": ("2025-12-03 21:49", "2025-12-04 05:00"),
    "S05": ("2025-12-09 14:21", "2025-12-09 22:00"),
}


def bridge_latency_ratio_monthly(df, col, exclude_mask):
    msg_col = "cctp_eth_op_messages_1h" if "eth_op" in col else "cctp_op_eth_messages_1h"
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


def benjamini_hochberg(pvalues, alpha=0.05):
    p = np.array(pvalues)
    n = len(p)
    if n == 0:
        return np.array([]), np.array([])
    order = np.argsort(p)
    ranked = p[order]
    adj = ranked * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.minimum(adj, 1.0)
    survival = adj < alpha
    adj_orig = np.empty_like(adj)
    survival_orig = np.empty_like(survival)
    adj_orig[order] = adj
    survival_orig[order] = survival
    return adj_orig, survival_orig


def eval_predictor(fire_arr, outcome_arr, placebo_perms=PLACEBO_PERMS, seed=SEED):
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


def main():
    np.random.seed(SEED)
    print("Loading panel...")
    df = pd.read_parquet(DATA).sort_index()
    jan_mask = df.index.month == 1

    # Compute smd per axis
    smd = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        s = df[col].abs()
        smd[col] = s - s.shift(1)

    axis_thresholds = {}
    for col in SUBSTRATE_SHIFTS:
        valid = smd.loc[~jan_mask, col].dropna()
        axis_thresholds[col] = {p: float(valid.quantile(p)) for p in PCTLS}

    # Bridge layer signals (ETH-OP-CCTP corridor)
    bridge_ratios = pd.DataFrame(index=df.index)
    for col in ["cctp_eth_op_latency_p90_s", "cctp_eth_op_latency_p99_s",
                "cctp_op_eth_latency_p90_s", "cctp_op_eth_latency_p99_s"]:
        if col in df.columns:
            bridge_ratios[col] = bridge_latency_ratio_monthly(df, col, jan_mask)
        else:
            bridge_ratios[col] = np.nan
    df["bridge_stress_full"] = (
        (df.get("bridge_state_eth_op", pd.Series("BS1", index=df.index)) == "BS2") |
        (df.get("bridge_state_op_eth", pd.Series("BS1", index=df.index)) == "BS2") |
        (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )
    df["bs2_only"] = (
        (df.get("bridge_state_eth_op", pd.Series("BS1", index=df.index)) == "BS2") |
        (df.get("bridge_state_op_eth", pd.Series("BS1", index=df.index)) == "BS2")
    )
    df["latency_high_only"] = (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    # Per-direction bridge stress for cross-chain family
    df["bridge_eth_to_op"] = (
        (df.get("bridge_state_eth_op", pd.Series("BS1", index=df.index)) == "BS2") |
        (bridge_ratios[[c for c in ["cctp_eth_op_latency_p90_s", "cctp_eth_op_latency_p99_s"] if c in bridge_ratios.columns]].max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )
    df["bridge_op_to_eth"] = (
        (df.get("bridge_state_op_eth", pd.Series("BS1", index=df.index)) == "BS2") |
        (bridge_ratios[[c for c in ["cctp_op_eth_latency_p90_s", "cctp_op_eth_latency_p99_s"] if c in bridge_ratios.columns]].max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )

    def shift_label_lead(label_series, lead):
        out = pd.Series(False, index=label_series.index)
        for h in range(1, lead + 1):
            out |= label_series.shift(-h).fillna(False)
        return out

    # Eligible mask base: not January
    eligible_base = ~jan_mask

    all_configs = []

    # =========================================================================
    # FAMILY 0: existing single-axis grid (288 configs), re-run for completeness
    # =========================================================================
    print("\n--- F0: single-axis grid (288) ---")
    t0 = time.time()
    F0_count = 0
    for axis in SUBSTRATE_SHIFTS:
        for pctl in PCTLS:
            threshold = axis_thresholds[axis][pctl]
            instant = (smd[axis] >= threshold).fillna(False).astype(int)
            for K in KS:
                rolling = instant.rolling(K, min_periods=K).sum()
                fire = (rolling == K)
                for lead in LEADS:
                    outcome_full = shift_label_lead(df["bridge_stress_full"], lead)
                    mask = eligible_base & ~df["bridge_stress_full"]
                    metrics = eval_predictor(fire[mask].values, outcome_full[mask].values)
                    cfg = {
                        "family": "F0_single_axis",
                        "predictor_label": f"{axis}|pctl={pctl}|K={K}",
                        "axis": axis, "pctl": pctl, "K": K, "lead": lead,
                        "outcome": "bridge_stress_full",
                        **metrics,
                    }
                    all_configs.append(cfg)
                    F0_count += 1
    print(f"  F0: {F0_count} configs in {time.time()-t0:.1f}s")

    # =========================================================================
    # FAMILY 1: multi-axis grouped predictors (64 configs)
    # =========================================================================
    print("\n--- F1: multi-axis grouped predictors (64) ---")
    t0 = time.time()

    def make_group_fire(axes_list, K, pctl):
        # Union: any axis amplifying for K consecutive hours
        any_fire = pd.Series(False, index=df.index)
        for axis in axes_list:
            threshold = axis_thresholds[axis][pctl]
            instant = (smd[axis] >= threshold).fillna(False).astype(int)
            rolling = instant.rolling(K, min_periods=K).sum()
            any_fire |= (rolling == K)
        return any_fire

    def make_voting_fire(min_axes, K, pctl):
        # Count axes amplifying at each T, fire if >= min_axes
        counts = pd.Series(0, index=df.index)
        for axis in SUBSTRATE_SHIFTS:
            threshold = axis_thresholds[axis][pctl]
            instant = (smd[axis] >= threshold).fillna(False).astype(int)
            rolling = instant.rolling(K, min_periods=K).sum()
            amp = (rolling == K).astype(int)
            counts = counts + amp
        return (counts >= min_axes)

    F1_groups = {
        "all12_union": ("union", SUBSTRATE_SHIFTS),
        "eth_only_union": ("union", ETH_SHIFTS),
        "arb_only_union": ("union", ARB_SHIFTS_EFFECTIVE),
        "structural_only_union": ("union", STRUCTURAL_SHIFTS),
        "demand_only_union": ("union", DEMAND_SHIFTS),
        "voting_ge2": ("voting", 2),
        "voting_ge3": ("voting", 3),
        "voting_ge4": ("voting", 4),
    }

    F1_count = 0
    for group_name, (kind, arg) in F1_groups.items():
        for K in KS:
            for lead in LEADS:
                pctl = PCTL_FIXED  # fixed at 0.90 for F1 to limit grid size
                if kind == "union":
                    fire = make_group_fire(arg, K, pctl)
                else:
                    fire = make_voting_fire(arg, K, pctl)
                outcome_full = shift_label_lead(df["bridge_stress_full"], lead)
                mask = eligible_base & ~df["bridge_stress_full"]
                metrics = eval_predictor(fire[mask].values, outcome_full[mask].values)
                cfg = {
                    "family": "F1_multi_axis",
                    "predictor_label": f"{group_name}|K={K}|pctl={pctl}",
                    "group": group_name, "K": K, "lead": lead, "pctl": pctl,
                    "outcome": "bridge_stress_full",
                    **metrics,
                }
                all_configs.append(cfg)
                F1_count += 1
    print(f"  F1: {F1_count} configs in {time.time()-t0:.1f}s")

    # =========================================================================
    # FAMILY 2: alternative outcomes (192 configs)
    # =========================================================================
    print("\n--- F2: alternative outcomes (192) ---")
    t0 = time.time()
    F2_count = 0
    for axis in SUBSTRATE_SHIFTS:
        threshold = axis_thresholds[axis][PCTL_FIXED]
        instant = (smd[axis] >= threshold).fillna(False).astype(int)
        for K in KS:
            rolling = instant.rolling(K, min_periods=K).sum()
            fire = (rolling == K)
            for lead in LEADS:
                for outcome_name, outcome_col in [("BS2_only", "bs2_only"), ("latency_high_only", "latency_high_only")]:
                    outcome_lead = shift_label_lead(df[outcome_col], lead)
                    mask = eligible_base & ~df[outcome_col]
                    metrics = eval_predictor(fire[mask].values, outcome_lead[mask].values)
                    cfg = {
                        "family": "F2_alt_outcomes",
                        "predictor_label": f"{axis}|K={K}|pctl={PCTL_FIXED}",
                        "axis": axis, "K": K, "lead": lead, "pctl": PCTL_FIXED,
                        "outcome": outcome_name,
                        **metrics,
                    }
                    all_configs.append(cfg)
                    F2_count += 1
    print(f"  F2: {F2_count} configs in {time.time()-t0:.1f}s")

    # =========================================================================
    # FAMILY 3: ML logistic regression (16 configs)
    # =========================================================================
    print("\n--- F3: ML logistic regression (16) ---")
    t0 = time.time()
    F3_count = 0
    # Features: 12 shifts + 12 smd
    feature_df = pd.concat([df[SUBSTRATE_SHIFTS], smd.rename(columns=lambda c: c + "_smd")], axis=1)
    h1_mask = pd.Series(df.index.month.isin([2, 3, 4, 5, 6]), index=df.index)  # H1 (Feb-Jun), skip Jan
    h2_mask = pd.Series(df.index.month.isin([7, 8, 9, 10, 11, 12]), index=df.index)

    for outcome_name, outcome_col in [("bridge_stress_full", "bridge_stress_full"),
                                       ("bs2_only", "bs2_only")]:
        for lead in LEADS:
            outcome_lead = shift_label_lead(df[outcome_col], lead)
            X_full = feature_df.dropna()
            y_full = outcome_lead.loc[X_full.index]
            train_mask = h1_mask.reindex(X_full.index).fillna(False) & (~df[outcome_col].reindex(X_full.index).fillna(False))
            test_mask = h2_mask.reindex(X_full.index).fillna(False) & (~df[outcome_col].reindex(X_full.index).fillna(False))

            X_train = X_full[train_mask].values
            y_train = y_full[train_mask].values.astype(int)
            X_test = X_full[test_mask].values
            y_test = y_full[test_mask].values.astype(int)

            if len(X_train) < 100 or len(X_test) < 100:
                continue

            scaler = StandardScaler()
            X_train_s = scaler.fit_transform(X_train)
            X_test_s = scaler.transform(X_test)

            lr = LogisticRegression(C=1.0, max_iter=200, class_weight="balanced")
            try:
                lr.fit(X_train_s, y_train)
                proba = lr.predict_proba(X_test_s)[:, 1]
                # Threshold at 0.5 to get binary predictions
                fire_arr = (proba >= 0.5)
                metrics = eval_predictor(fire_arr, y_test.astype(bool), placebo_perms=PLACEBO_PERMS)
                cfg = {
                    "family": "F3_ML_LR",
                    "predictor_label": f"LR(L2,balanced)|features=24|train=H1|test=H2",
                    "lead": lead, "outcome": outcome_name,
                    "n_train": int(len(X_train)), "n_test": int(len(X_test)),
                    **metrics,
                }
                all_configs.append(cfg)
                F3_count += 1
            except Exception as e:
                print(f"    LR failed lead={lead} outcome={outcome_name}: {e}")
    print(f"  F3: {F3_count} configs in {time.time()-t0:.1f}s")

    # =========================================================================
    # FAMILY 4: cross-chain (80 configs)
    # =========================================================================
    print("\n--- F4: cross-chain (80) ---")
    t0 = time.time()
    F4_count = 0
    # Direction 1: ETH shifts -> bridge_eth_to_op (predict bridge to OP)
    # Direction 2: OP shifts -> bridge_op_to_eth (predict bridge to ETH)
    for direction, axes, outcome_col in [
        ("ETH_predict_eth_to_op_bridge", ETH_SHIFTS, "bridge_eth_to_op"),
        ("OP_predict_op_to_eth_bridge", OP_SHIFTS_EFFECTIVE, "bridge_op_to_eth"),
    ]:
        for axis in axes:
            threshold = axis_thresholds[axis][PCTL_FIXED]
            instant = (smd[axis] >= threshold).fillna(False).astype(int)
            for K in KS:
                rolling = instant.rolling(K, min_periods=K).sum()
                fire = (rolling == K)
                for lead in LEADS:
                    outcome_lead = shift_label_lead(df[outcome_col], lead)
                    mask = eligible_base & ~df[outcome_col]
                    metrics = eval_predictor(fire[mask].values, outcome_lead[mask].values)
                    cfg = {
                        "family": "F4_cross_chain",
                        "predictor_label": f"{direction}|{axis}|K={K}|pctl={PCTL_FIXED}",
                        "direction": direction, "axis": axis, "K": K, "lead": lead, "pctl": PCTL_FIXED,
                        "outcome": outcome_col,
                        **metrics,
                    }
                    all_configs.append(cfg)
                    F4_count += 1
    print(f"  F4: {F4_count} configs in {time.time()-t0:.1f}s")

    print(f"\nTotal configs: {len(all_configs)}")

    # Per-family FDR
    family_summary = {}
    by_family = {}
    for cfg in all_configs:
        by_family.setdefault(cfg["family"], []).append(cfg)
    for fam, items in by_family.items():
        pvals = [c["placebo_p_value"] for c in items]
        adj, surv = benjamini_hochberg(pvals, alpha=FDR_ALPHA)
        for c, a, s in zip(items, adj, surv):
            c["p_adj_family"] = round(float(a), 4)
            c["fdr_survives_family"] = bool(s)
        n_raw = sum(1 for c in items if c["placebo_p_value"] < 0.05)
        n_fdr = sum(c["fdr_survives_family"] for c in items)
        n_overall = sum(1 for c in items if c["fdr_survives_family"] and c["lift"] >= LIFT_THRESHOLD)
        family_summary[fam] = {
            "n_configs": len(items),
            "n_raw_p_lt_05": n_raw,
            "n_fdr_survives": n_fdr,
            "n_fdr_plus_lift_survives": n_overall,
        }

    # Combined FDR
    pvals_all = [c["placebo_p_value"] for c in all_configs]
    adj_all, surv_all = benjamini_hochberg(pvals_all, alpha=FDR_ALPHA)
    for c, a, s in zip(all_configs, adj_all, surv_all):
        c["p_adj_combined"] = round(float(a), 4)
        c["fdr_survives_combined"] = bool(s)
        c["overall_survives_combined"] = bool(s) and c["lift"] >= LIFT_THRESHOLD

    n_combined_fdr = sum(c["fdr_survives_combined"] for c in all_configs)
    n_combined_overall = sum(c["overall_survives_combined"] for c in all_configs)

    print("\n=== PER-FAMILY SUMMARY ===")
    for fam, s in family_summary.items():
        print(f"  {fam}: {s['n_configs']} configs | raw_p<0.05: {s['n_raw_p_lt_05']} | "
              f"FDR_fam_survives: {s['n_fdr_survives']} | FDR+lift_survives: {s['n_fdr_plus_lift_survives']}")
    print(f"\n=== COMBINED FDR on {len(all_configs)} configs ===")
    print(f"  combined FDR survives: {n_combined_fdr}")
    print(f"  combined FDR + lift>={LIFT_THRESHOLD}: {n_combined_overall}")

    # Top 15 by lift overall
    configs_sorted = sorted(all_configs, key=lambda c: (-c["lift"], c["p_adj_combined"]))
    top15 = configs_sorted[:15]
    print("\n=== TOP 15 by lift overall ===")
    print(f"{'Family':<20} {'Predictor':<60} {'Lead':>4} {'Lift':>5} {'P_raw':>6} {'P_comb':>7} {'Prec%':>6} {'Alert%':>6}")
    for c in top15:
        lbl = c.get("predictor_label", "")
        print(f"{c['family']:<20} {lbl[:58]:<60} {c['lead']:>4} {c['lift']:>5.2f} "
              f"{c['placebo_p_value']:>6.3f} {c['p_adj_combined']:>7.3f} "
              f"{c['precision']*100:>5.1f} {c['alert_rate']*100:>5.2f}")

    survivors = [c for c in all_configs if c["overall_survives_combined"]]
    print(f"\n=== COMBINED SURVIVORS ({len(survivors)}) ===")
    for c in survivors[:30]:
        lbl = c.get("predictor_label", "")
        print(f"  {c['family']} | {lbl} | lead={c['lead']} | lift={c['lift']} | "
              f"p_raw={c['placebo_p_value']} | p_comb={c['p_adj_combined']}")

    # Output
    output = {
        "grid": {
            "total_configs": len(all_configs),
            "placebo_perms_per_config": PLACEBO_PERMS,
            "fdr_alpha": FDR_ALPHA,
            "lift_threshold_for_survival": LIFT_THRESHOLD,
            "families": list(by_family.keys()),
        },
        "family_summary": family_summary,
        "combined": {
            "n_configs": len(all_configs),
            "fdr_survives_combined": n_combined_fdr,
            "fdr_plus_lift_survives_combined": n_combined_overall,
        },
        "top_15_by_lift": top15,
        "combined_survivors": survivors,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")

    # Markdown
    lines = ["# Delta Full Exploration: 4 families + combined FDR", ""]
    lines.append(f"Total configurations tested: **{len(all_configs)}**")
    lines.append("")
    lines.append("Strategy families:")
    lines.append(f"- F0 single-axis grid: {family_summary.get('F0_single_axis', {}).get('n_configs', 0)} configs")
    lines.append(f"- F1 multi-axis grouped: {family_summary.get('F1_multi_axis', {}).get('n_configs', 0)} configs")
    lines.append(f"- F2 alternative outcomes: {family_summary.get('F2_alt_outcomes', {}).get('n_configs', 0)} configs")
    lines.append(f"- F3 ML logistic regression: {family_summary.get('F3_ML_LR', {}).get('n_configs', 0)} configs")
    lines.append(f"- F4 cross-chain: {family_summary.get('F4_cross_chain', {}).get('n_configs', 0)} configs")
    lines.append("")
    lines.append("Multiple-testing correction: Benjamini-Hochberg FDR alpha=0.05.")
    lines.append("Survival criterion: combined FDR p_adj < 0.05 AND lift >= 1.5x.")
    lines.append("")
    lines.append("## Per-family summary")
    lines.append("")
    lines.append("| Family | Configs | Raw p<0.05 | FDR survives (within family) | FDR + lift >=1.5x |")
    lines.append("|---|---|---|---|---|")
    for fam, s in family_summary.items():
        lines.append(f"| {fam} | {s['n_configs']} | {s['n_raw_p_lt_05']} | {s['n_fdr_survives']} | {s['n_fdr_plus_lift_survives']} |")
    lines.append("")
    lines.append("## Combined FDR (across all configs)")
    lines.append("")
    lines.append(f"- Combined FDR survives: **{n_combined_fdr}** / {len(all_configs)}")
    lines.append(f"- Combined FDR + lift >= 1.5x: **{n_combined_overall}** / {len(all_configs)}")
    lines.append("")
    lines.append("## Top 15 by lift")
    lines.append("")
    lines.append("| Family | Predictor | Lead | Lift | P raw | P adj combined | Precision | Alert rate |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in top15:
        lbl = c.get("predictor_label", "")
        lines.append(f"| {c['family']} | `{lbl}` | {c['lead']}h | **{c['lift']}** | {c['placebo_p_value']} | "
                     f"{c['p_adj_combined']} | {c['precision']*100:.1f}% | {c['alert_rate']*100:.2f}% |")
    lines.append("")
    lines.append("## Combined survivors")
    lines.append("")
    if not survivors:
        lines.append("**NONE.** Out of 640 configurations spanning single-axis, multi-axis grouped, ")
        lines.append("alternative outcomes, ML logistic regression, and cross-chain prediction strategies, ")
        lines.append("ZERO survives the combined Benjamini-Hochberg FDR correction at alpha=0.05 ")
        lines.append("combined with a minimum lift of 1.5x.")
        lines.append("")
        lines.append("**Honest definitive verdict for ETH-ARB-CCTP 2025 corpus**: the Delta v2 primitive ")
        lines.append("does NOT produce a robust orientation signal for bridge stress prediction under ")
        lines.append("any of the 640 explored operational configurations, after multiple-testing correction.")
        lines.append("")
        lines.append("The Delta concept as currently exposed in the v2 API is statistically defaillant ")
        lines.append("for the agent-orientation use case on this corridor, on this year, for this outcome family.")
    else:
        lines.append(f"**{len(survivors)} configurations survive combined FDR + lift threshold.**")
        for c in survivors[:30]:
            lbl = c.get("predictor_label", "")
            lines.append(f"- {c['family']} | `{lbl}` | lead={c['lead']}h | lift={c['lift']} | "
                         f"precision={c['precision']*100:.1f}% | p_adj={c['p_adj_combined']}")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
