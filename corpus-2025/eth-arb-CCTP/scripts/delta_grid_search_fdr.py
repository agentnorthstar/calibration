"""Delta grid search with FDR correction.

Honest exhaustive(ish) exploration of Delta operational configurations.
Tests 288 configs parameterized along 4 dimensions (axis, lead, K, threshold),
applies Benjamini-Hochberg FDR correction to placebo p-values.

Grid:
  - axis (12 single substrate shift axes)
  - lead window in hours (3, 6, 12, 24)
  - K consecutive hours (1, 2)
  - smd threshold percentile (0.85, 0.90, 0.95)

Cartesian = 288 configurations.

Placebo: 500 permutations per config. Top survivors re-validated with 1000.

Outputs:
  delta_grid_search_fdr_output.json
  delta_grid_search_fdr_report.md
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE.parent / "data" / "annual_panel_2025.parquet"
RESULTS = BASE.parent / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
OUT_JSON = RESULTS / "delta_grid_search_fdr_output.json"
OUT_MD = RESULTS / "delta_grid_search_fdr_report.md"

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
SUBSTRATE_SHIFTS = ETH_SHIFTS + ARB_SHIFTS_EFFECTIVE  # 12 axes

LEADS = [3, 6, 12, 24]
KS = [1, 2]
PCTLS = [0.85, 0.90, 0.95]
PLACEBO_PERMS = 500
FDR_ALPHA = 0.05
LIFT_THRESHOLD_SURVIVAL = 1.5
VALIDATION_PERMS = 1000
BRIDGE_LATENCY_RATIO_THRESHOLD = 50.0
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


def benjamini_hochberg(pvalues, alpha=0.05):
    """Return BH-adjusted p-values and survival boolean."""
    p = np.array(pvalues)
    n = len(p)
    order = np.argsort(p)
    ranked_p = p[order]
    bh_thresholds = (np.arange(1, n + 1) / n) * alpha
    # adjusted p (BH): p_adj[i] = min(p_ranked[j] * n / j for j >= i)
    adj = ranked_p * n / np.arange(1, n + 1)
    # enforce monotonicity (running min from largest rank)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    adj = np.minimum(adj, 1.0)
    survival = adj < alpha
    # reorder to original indexing
    adj_orig = np.empty_like(adj)
    survival_orig = np.empty_like(survival)
    adj_orig[order] = adj
    survival_orig[order] = survival
    return adj_orig, survival_orig


def main():
    np.random.seed(RANDOM_SEED)
    print("Loading panel...")
    df = pd.read_parquet(DATA).sort_index()
    jan_mask = df.index.month == 1

    # Compute shift_magnitude_delta per axis once
    smd = pd.DataFrame(index=df.index)
    for col in SUBSTRATE_SHIFTS:
        s = df[col].abs()
        smd[col] = s - s.shift(1)

    # Compute axis thresholds for each percentile once
    axis_thresholds = {}
    for col in SUBSTRATE_SHIFTS:
        valid = smd.loc[~jan_mask, col].dropna()
        axis_thresholds[col] = {p: float(valid.quantile(p)) for p in PCTLS}

    # Compute bridge stress label per hour once
    bridge_ratios = pd.DataFrame(index=df.index)
    for col in ["cctp_eth_arb_latency_p90_s", "cctp_eth_arb_latency_p99_s",
                "cctp_arb_eth_latency_p90_s", "cctp_arb_eth_latency_p99_s"]:
        bridge_ratios[col] = bridge_latency_ratio_monthly(df, col, jan_mask)
    df["bridge_stress"] = (
        (df["bridge_state_eth_arb"] == "BS2") |
        (df["bridge_state_arb_eth"] == "BS2") |
        (bridge_ratios.max(axis=1) >= BRIDGE_LATENCY_RATIO_THRESHOLD).fillna(False)
    )

    # Precompute bridge_stress shifted by each lead value for outcome
    print("Precomputing outcome arrays for each lead...")
    outcome_by_lead = {}
    for lead in LEADS:
        bridge_in_next = pd.Series(False, index=df.index)
        for h in range(1, lead + 1):
            bridge_in_next |= df["bridge_stress"].shift(-h).fillna(False)
        outcome_by_lead[lead] = bridge_in_next

    # Eligible hours: not January, not currently bridge-stressed
    mask_eligible = (~jan_mask) & (~df["bridge_stress"])
    n_eligible = int(mask_eligible.sum())
    print(f"Eligible hours: {n_eligible}")

    # Run grid
    print(f"\nRunning grid: {len(SUBSTRATE_SHIFTS)} axes x {len(LEADS)} leads x {len(KS)} K x {len(PCTLS)} pctl = "
          f"{len(SUBSTRATE_SHIFTS) * len(LEADS) * len(KS) * len(PCTLS)} configs, placebo {PLACEBO_PERMS} perms each.")

    configs = []
    t0 = time.time()
    for axis in SUBSTRATE_SHIFTS:
        # Precompute amplifying boolean for each K and pctl (depends on axis but not on lead)
        for pctl in PCTLS:
            threshold = axis_thresholds[axis][pctl]
            instant = (smd[axis] >= threshold).fillna(False).astype(int)
            for K in KS:
                rolling = instant.rolling(K, min_periods=K).sum()
                fire = (rolling == K)
                # For each lead, compute outcome and metrics
                for lead in LEADS:
                    outcome = outcome_by_lead[lead]
                    # Build eligible subset
                    mask = mask_eligible
                    fire_arr = fire[mask].values
                    outcome_arr = outcome[mask].values

                    tp = int(((fire_arr) & (outcome_arr)).sum())
                    fp = int(((fire_arr) & (~outcome_arr)).sum())
                    fn = int(((~fire_arr) & (outcome_arr)).sum())
                    tn = int(((~fire_arr) & (~outcome_arr)).sum())

                    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
                    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                    base_rate = (tp + fn) / len(fire_arr) if len(fire_arr) > 0 else 0.0
                    alert_rate = (tp + fp) / len(fire_arr) if len(fire_arr) > 0 else 0.0
                    lift = precision / base_rate if base_rate > 0 else 0.0
                    fp_rate = fp / (tn + fp) if (tn + fp) > 0 else 0.0

                    # Placebo permutation
                    null_lifts = np.zeros(PLACEBO_PERMS)
                    rng = np.random.default_rng(RANDOM_SEED)
                    for i in range(PLACEBO_PERMS):
                        shuffled = rng.permutation(outcome_arr)
                        tp_p = int((fire_arr & shuffled).sum())
                        fp_p = int((fire_arr & ~shuffled).sum())
                        prec_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
                        null_lifts[i] = prec_p / base_rate if base_rate > 0 else 0.0
                    p_value = float((null_lifts >= lift).mean())

                    configs.append({
                        "axis": axis,
                        "lead": lead,
                        "K": K,
                        "pctl": pctl,
                        "threshold_value": threshold,
                        "n_fires": int(tp + fp),
                        "n_positive_outcomes": int(tp + fn),
                        "base_rate": round(base_rate, 4),
                        "alert_rate": round(alert_rate, 4),
                        "precision": round(precision, 4),
                        "recall": round(recall, 4),
                        "lift": round(lift, 3),
                        "fp_rate": round(fp_rate, 4),
                        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                        "placebo_p_value": round(p_value, 4),
                    })
    elapsed = time.time() - t0
    print(f"Grid completed in {elapsed:.1f}s. {len(configs)} configs evaluated.")

    # FDR Benjamini-Hochberg on p-values
    p_values = [c["placebo_p_value"] for c in configs]
    p_adj, survival = benjamini_hochberg(p_values, alpha=FDR_ALPHA)
    for c, pa, sv in zip(configs, p_adj, survival):
        c["placebo_p_adj_BH"] = round(float(pa), 4)
        c["fdr_survives"] = bool(sv)
        c["meets_lift_threshold"] = c["lift"] >= LIFT_THRESHOLD_SURVIVAL
        c["overall_survives"] = c["fdr_survives"] and c["meets_lift_threshold"]

    n_p_lt_05_raw = sum(1 for c in configs if c["placebo_p_value"] < 0.05)
    n_fdr_survive = sum(1 for c in configs if c["fdr_survives"])
    n_overall_survive = sum(1 for c in configs if c["overall_survives"])
    print(f"\nRaw p < 0.05: {n_p_lt_05_raw} / {len(configs)}")
    print(f"BH FDR survives (alpha=0.05): {n_fdr_survive} / {len(configs)}")
    print(f"Overall survives (FDR + lift >= 1.5x): {n_overall_survive} / {len(configs)}")

    # Sort by lift descending, then by p_adj ascending
    configs_sorted = sorted(configs, key=lambda c: (-c["lift"], c["placebo_p_adj_BH"]))
    top10 = configs_sorted[:10]
    survivors = [c for c in configs_sorted if c["overall_survives"]]

    print("\n=== TOP 10 configs by lift ===")
    print(f"{'Axis':<40} {'Lead':>5} {'K':>3} {'Pctl':>5} {'Lift':>6} {'P_raw':>7} {'P_adj':>7} {'Prec%':>6} {'Alert%':>7} {'FDR':>5}")
    for c in top10:
        print(f"{c['axis']:<40} {c['lead']:>5} {c['K']:>3} {c['pctl']:>5.2f} {c['lift']:>6.2f} "
              f"{c['placebo_p_value']:>7.3f} {c['placebo_p_adj_BH']:>7.3f} "
              f"{c['precision']*100:>5.1f} {c['alert_rate']*100:>6.2f} {('Y' if c['fdr_survives'] else 'N'):>5}")

    print(f"\n=== ALL SURVIVORS (FDR + lift >= 1.5x): {n_overall_survive} ===")
    for c in survivors:
        print(f"  {c['axis']} | lead={c['lead']}h | K={c['K']} | pctl={c['pctl']} | "
              f"lift={c['lift']} | p_raw={c['placebo_p_value']} | p_adj={c['placebo_p_adj_BH']}")

    # Validate top survivors with 1000 permutations
    print(f"\nValidating top survivors with {VALIDATION_PERMS} permutations...")
    validated = []
    for c in survivors[:10]:  # validate up to top 10 survivors
        axis = c["axis"]
        K = c["K"]
        lead = c["lead"]
        pctl = c["pctl"]
        threshold = axis_thresholds[axis][pctl]
        instant = (smd[axis] >= threshold).fillna(False).astype(int)
        rolling = instant.rolling(K, min_periods=K).sum()
        fire = (rolling == K)
        outcome = outcome_by_lead[lead]
        mask = mask_eligible
        fire_arr = fire[mask].values
        outcome_arr = outcome[mask].values
        base_rate = c["base_rate"]
        lift = c["lift"]

        null_lifts = np.zeros(VALIDATION_PERMS)
        rng = np.random.default_rng(RANDOM_SEED + 1)  # different seed for validation
        for i in range(VALIDATION_PERMS):
            shuffled = rng.permutation(outcome_arr)
            tp_p = int((fire_arr & shuffled).sum())
            fp_p = int((fire_arr & ~shuffled).sum())
            prec_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
            null_lifts[i] = prec_p / base_rate if base_rate > 0 else 0.0
        p_validated = float((null_lifts >= lift).mean())
        c["placebo_p_validated_1000"] = round(p_validated, 4)
        validated.append(c)

    # Save
    output = {
        "config_grid": {
            "axes": SUBSTRATE_SHIFTS,
            "leads": LEADS,
            "K_values": KS,
            "thresholds_pctl": PCTLS,
            "total_configs": len(configs),
            "placebo_perms": PLACEBO_PERMS,
            "fdr_alpha": FDR_ALPHA,
            "lift_threshold_for_survival": LIFT_THRESHOLD_SURVIVAL,
            "validation_perms": VALIDATION_PERMS,
            "outcome_definition": "bridge stress (BS2 OR latency ratio >= 50x monthly median) in (T, T+lead]",
            "anti_tautology": "single-axis substrate predictor; outcome on bridge layer; structurally disjoint",
        },
        "summary": {
            "configs_evaluated": len(configs),
            "raw_p_lt_05": n_p_lt_05_raw,
            "fdr_survivors": n_fdr_survive,
            "fdr_plus_lift_survivors": n_overall_survive,
            "validation_perms_top": VALIDATION_PERMS,
        },
        "top_10_by_lift": top10,
        "all_survivors": validated,
        "all_configs": configs,
    }
    OUT_JSON.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {OUT_JSON}")

    # Markdown report
    lines = ["# Delta Grid Search with FDR Correction", ""]
    lines.append(f"Exploration of {len(configs)} pre-engaged configurations along 4 dimensions: ")
    lines.append("axis (single-axis predictor among 12 substrate shifts), lead window (3/6/12/24h), ")
    lines.append("K consecutive hours (1/2), smd threshold percentile (0.85/0.90/0.95).")
    lines.append("")
    lines.append("**Multiple testing correction**: Benjamini-Hochberg FDR at alpha=0.05.")
    lines.append("**Survival criterion**: FDR-corrected p < 0.05 AND lift >= 1.5x.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Configs evaluated: **{len(configs)}**")
    lines.append(f"- Raw p < 0.05 (uncorrected): {n_p_lt_05_raw} / {len(configs)} = {n_p_lt_05_raw/len(configs)*100:.1f}%")
    lines.append(f"- BH FDR survives (alpha=0.05): **{n_fdr_survive}** / {len(configs)} = {n_fdr_survive/len(configs)*100:.1f}%")
    lines.append(f"- FDR + lift >= 1.5x survives: **{n_overall_survive}** / {len(configs)}")
    lines.append("")
    lines.append("## Top 10 by lift")
    lines.append("")
    lines.append("| Axis | Lead | K | Pctl | Lift | P raw | P adj BH | Precision | Alert rate | FDR survives |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for c in top10:
        lines.append(f"| `{c['axis']}` | {c['lead']}h | {c['K']} | {c['pctl']} | "
                     f"**{c['lift']}** | {c['placebo_p_value']} | {c['placebo_p_adj_BH']} | "
                     f"{c['precision']*100:.1f}% | {c['alert_rate']*100:.2f}% | "
                     f"{'YES' if c['fdr_survives'] else 'NO'} |")
    lines.append("")
    lines.append("## Survivors (FDR + lift >= 1.5x)")
    lines.append("")
    if not survivors:
        lines.append("**NONE.** No configuration passed both FDR correction and lift threshold.")
        lines.append("")
        lines.append("Honest verdict: under this 288-configuration grid search with BH FDR alpha=0.05 ")
        lines.append("and lift >= 1.5x threshold, the Delta primitive in any single-axis configuration ")
        lines.append("(varied along axis, lead window, K, and threshold percentile) does NOT produce a ")
        lines.append("statistically robust orientation signal for bridge stress in 6h-24h windows on the ")
        lines.append("ETH-ARB-CCTP 2025 corpus.")
    else:
        lines.append(f"**{n_overall_survive} configurations survive.**")
        lines.append("")
        lines.append("| Axis | Lead | K | Pctl | Lift | P adj BH | P validated 1000 | Precision | Recall | Alert rate |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for c in validated:
            lines.append(f"| `{c['axis']}` | {c['lead']}h | {c['K']} | {c['pctl']} | "
                         f"**{c['lift']}** | {c['placebo_p_adj_BH']} | "
                         f"{c.get('placebo_p_validated_1000', '-')} | "
                         f"{c['precision']*100:.1f}% | {c['recall']*100:.1f}% | "
                         f"{c['alert_rate']*100:.2f}% |")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
