#!/usr/bin/env python3
"""
BS_STRUCTURAL_PRECURSORS_v1 — substrate-shift precursors against BS_STRUCTURAL_v1.1 BS2 outcome.

Implements PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md strictly. Reconstructs
the binary outcome BS2(t) on a 1-hour aggregation window from the locked Step 3
raw events parquet, loads the locked substrate-shift baseline, evaluates the 768
configurations of the pre-engaged grid (F0 single-axis, F1 multi-axis grouped,
F4 cross-chain), applies BH FDR alpha=0.05 within each family and combined,
filters survivors at lift >= 1.5x, and writes a single signable JSON output.

Inputs (locked Step 3 corpus):
  data/cctp_v2_events_2025_raw.parquet
  results/per_event_sheets/baseline.parquet  (substrate-shift series)

Output:
  results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json
"""

import hashlib
import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


PUBLIABLE = Path(__file__).resolve().parent.parent
DATA = PUBLIABLE / "data"
RESULTS = PUBLIABLE / "results"
SHEETS = RESULTS / "per_event_sheets"

PROTOCOL_VERSION = "BS_STRUCTURAL_PRECURSORS_v1"

# ──────────────────────────────────────────────────────────────────────────────
# Constants — fixed by PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md
# ──────────────────────────────────────────────────────────────────────────────

WINDOW_START = pd.Timestamp("2025-06-09 18:45:00", tz="UTC")  # §6
WINDOW_END   = pd.Timestamp("2025-12-31 23:59:00", tz="UTC")
PCTL_FIT_START = pd.Timestamp("2025-02-01 00:00:00", tz="UTC")  # non-January, §6

SLA_FAST_SECS     = 120     # §2 (inherited from bridge_state_methodology v1.1 §3.5)
SLA_STANDARD_SECS = 7200

MIN_OBSERVATIONS_BS  = 5    # §2 invariant I4
MIN_SUCCESS_RATE     = 0.995
MAX_FALLBACK_RATE    = 0.05

FDR_ALPHA            = 0.05  # §7
LIFT_THRESHOLD       = 1.5
N_PLACEBO            = 500

POWER_LOW_MIN        = 30    # §8
POWER_INSUFFICIENT_MIN = 10

DOMAIN_CHAIN = {0: "ethereum", 7: "polygon"}

# 10 substrate-shift axes — §4
ETH_AXES = [
    "eth_rhythm_ratio_shift",
    "eth_continuity_ratio_shift",
    "eth_sigma_demand_shift",
    "eth_size_demand_shift",
    "eth_tx_demand_shift",
]
POL_AXES = [
    "pol_rhythm_ratio_shift",
    "pol_continuity_ratio_shift",
    "pol_sigma_demand_shift",
    "pol_size_demand_shift",
    "pol_tx_demand_shift",
]
ALL_AXES = ETH_AXES + POL_AXES

PCTLS    = [0.85, 0.90, 0.95]
KS       = [1, 2]
LEADS    = [3, 6, 12, 24]

OUTCOMES = ["bs2_eth_to_pol_fast", "bs2_pol_to_eth_fast"]  # §2.1 — Standard excluded

# F1 multi-axis groups, fixed at pctl = 0.90 — §5
F1_GROUPS = {
    "eth_demand_union":         {"axes": ["eth_sigma_demand_shift",
                                          "eth_size_demand_shift",
                                          "eth_tx_demand_shift"],
                                 "thresholds": [2, 3]},
    "eth_structural_union":     {"axes": ["eth_rhythm_ratio_shift",
                                          "eth_continuity_ratio_shift"],
                                 "thresholds": [2]},
    "pol_demand_union":         {"axes": ["pol_sigma_demand_shift",
                                          "pol_size_demand_shift",
                                          "pol_tx_demand_shift"],
                                 "thresholds": [2, 3]},
    "pol_structural_union":     {"axes": ["pol_rhythm_ratio_shift",
                                          "pol_continuity_ratio_shift"],
                                 "thresholds": [2]},
    "eth_all_union":            {"axes": ETH_AXES, "thresholds": [3, 4]},
    "pol_all_union":            {"axes": POL_AXES, "thresholds": [3, 4]},
    "all_demand_union":         {"axes": ["eth_sigma_demand_shift",
                                          "eth_size_demand_shift",
                                          "eth_tx_demand_shift",
                                          "pol_sigma_demand_shift",
                                          "pol_size_demand_shift",
                                          "pol_tx_demand_shift"],
                                 "thresholds": [3, 4]},
    "all_structural_union":     {"axes": ["eth_rhythm_ratio_shift",
                                          "eth_continuity_ratio_shift",
                                          "pol_rhythm_ratio_shift",
                                          "pol_continuity_ratio_shift"],
                                 "thresholds": [2, 3]},
}

# F4 cross-chain groups, fixed at pctl = 0.90 — §5
# ETH-side axes predict pol_to_eth outcome; POL-side axes predict eth_to_pol outcome.
F4_GROUPS = {
    "eth_axes_predict_pol_to_eth": {"axes": ETH_AXES, "outcome": "bs2_pol_to_eth_fast"},
    "pol_axes_predict_eth_to_pol": {"axes": POL_AXES, "outcome": "bs2_eth_to_pol_fast"},
}


# ──────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_mode(threshold) -> str:
    """v1.1 classifier — see calibration_log #045."""
    if pd.isna(threshold):
        return "other"
    t = int(threshold)
    if t == 0:
        return "other"
    if 1 <= t <= 1000:
        return "fast"
    if t == 2000:
        return "standard"
    return "other"


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 — load raw events, pair source-destination, retain ETH-POL corridor
# ──────────────────────────────────────────────────────────────────────────────

def pair_eth_pol_messages(events: pd.DataFrame) -> pd.DataFrame:
    """
    Pair MessageSent (source) ↔ MessageReceived (destination) via on-chain nonce,
    restricted to ETH-POL corridor (source_domain, destination_domain) ∈ {(0,7), (7,0)}.
    Returns one row per Fast-mode source message with attestation status and
    executed mode populated from the destination event when matched.
    """
    events = events.copy()
    events["block_timestamp"] = pd.to_datetime(events["block_timestamp"], utc=True)

    eth_pol = events[
        events["source_domain"].isin([0, 7])
        & events["destination_domain"].isin([0, 7])
    ]

    sent = eth_pol[
        (eth_pol["event_name"] == "MessageSent")
        & eth_pol["nonce"].notna()
    ].copy()

    recv = eth_pol[
        (eth_pol["event_name"] == "MessageReceived")
        & eth_pol["nonce"].notna()
    ].copy()

    sent["mode_requested"] = sent["min_finality_threshold"].apply(classify_mode)
    recv["mode_executed"]  = recv["min_finality_threshold"].apply(classify_mode)

    # Join on (source_domain, destination_domain, nonce)
    paired = sent.merge(
        recv[["source_domain", "destination_domain", "nonce",
              "block_timestamp", "mode_executed"]],
        on=["source_domain", "destination_domain", "nonce"],
        how="left",
        suffixes=("_src", "_dst"),
    )

    paired["attested"] = paired["block_timestamp_dst"].notna()
    paired["source_chain"] = paired["source_domain"].map(DOMAIN_CHAIN)
    paired["dest_chain"]   = paired["destination_domain"].map(DOMAIN_CHAIN)

    return paired[[
        "source_chain", "dest_chain", "mode_requested", "mode_executed",
        "block_timestamp_src", "block_timestamp_dst", "attested",
    ]]


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 — compute hourly BS2 outcome
# ──────────────────────────────────────────────────────────────────────────────

def compute_hourly_bs2(paired: pd.DataFrame) -> pd.DataFrame:
    """
    For each hour h in the calibration window, evaluate
    BS_STRUCTURAL_v1.1 BS2 on each Fast triplet (eth_to_pol, pol_to_eth).
    """
    grid = pd.date_range(WINDOW_START.floor("h"), WINDOW_END.floor("h"),
                         freq="h", tz="UTC")
    out = pd.DataFrame(index=grid)
    out.index.name = "hour_utc"

    fast_only = paired[paired["mode_requested"] == "fast"].copy()
    src_ts = fast_only["block_timestamp_src"].values

    for src, dst, direction in [
        ("ethereum", "polygon", "eth_to_pol"),
        ("polygon", "ethereum", "pol_to_eth"),
    ]:
        sub = fast_only[
            (fast_only["source_chain"] == src) & (fast_only["dest_chain"] == dst)
        ]
        col = f"bs2_{direction}_fast"
        bs2_vals = []

        for h in grid:
            w_lo = (h - pd.Timedelta(hours=1)).to_datetime64()
            w_hi = h.to_datetime64()
            sla  = (h - pd.Timedelta(seconds=SLA_FAST_SECS)).to_datetime64()

            ts = sub["block_timestamp_src"].values
            in_window = (ts >= w_lo) & (ts < w_hi)
            eligible  = in_window & (ts < sla)
            n_eligible = int(eligible.sum())

            if n_eligible < MIN_OBSERVATIONS_BS:
                bs2_vals.append(np.nan)
                continue

            eligible_rows = sub[eligible]
            n_attested = int(eligible_rows["attested"].sum())
            success_rate = n_attested / n_eligible

            resolved_rows = eligible_rows[eligible_rows["mode_executed"].notna()]
            n_resolved = len(resolved_rows)
            if n_resolved > 0:
                n_escalated = int((resolved_rows["mode_executed"] == "standard").sum())
                fallback_rate = n_escalated / n_resolved
            else:
                fallback_rate = 0.0

            bs2_vals.append(
                1 if (success_rate < MIN_SUCCESS_RATE
                      or fallback_rate > MAX_FALLBACK_RATE)
                else 0
            )

        out[col] = bs2_vals

    return out


# ──────────────────────────────────────────────────────────────────────────────
# Step 3 — build substrate-shift instant-alert series
# ──────────────────────────────────────────────────────────────────────────────

def load_corpus_matrix() -> pd.DataFrame:
    """Reconstitute the hourly substrate-shift matrix by concatenating baseline
    and per-event sheets (mirroring compute_bs_calibration_v2.py)."""
    baseline = pd.read_parquet(SHEETS / "baseline.parquet")
    per_event_paths = sorted(
        p for p in SHEETS.glob("*.parquet") if p.name != "baseline.parquet"
    )
    frames = [baseline] + [pd.read_parquet(p) for p in per_event_paths]
    df = pd.concat(frames, ignore_index=True)
    df["hour_utc"] = pd.to_datetime(df["hour_utc"], utc=True)
    df = df.drop_duplicates(subset=["hour_utc"], keep="first")
    df = df.sort_values("hour_utc").set_index("hour_utc")
    return df


def smd_series(matrix: pd.DataFrame, axis: str) -> pd.Series:
    """Shift-magnitude delta: smd(t) = |shift(t)| - |shift(t-1)|."""
    s = matrix[axis].astype(float)
    return s.abs().diff()


def axis_pctl_threshold(smd: pd.Series, pctl: float) -> float:
    """Quantile of the SMD series over the non-January 2025 window (§6)."""
    fit_window = smd[(smd.index >= PCTL_FIT_START) & (smd.index <= WINDOW_END)]
    return float(np.nanquantile(fit_window.values, pctl))


def instant_alert_series(matrix: pd.DataFrame, axis: str, pctl: float) -> pd.Series:
    """Boolean series: smd(t) > axis pctl threshold."""
    smd = smd_series(matrix, axis)
    threshold = axis_pctl_threshold(smd, pctl)
    return smd > threshold


def sustained_alert(instant: pd.Series, k: int) -> pd.Series:
    """K consecutive instant alerts."""
    if k <= 1:
        return instant.astype(bool)
    return instant.rolling(window=k, min_periods=k).sum() == k


# ──────────────────────────────────────────────────────────────────────────────
# Step 4 — evaluate one configuration: lift, placebo p-value
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_config(alert: pd.Series, outcome: pd.Series, lead_hours: int,
                    rng: np.random.Generator) -> dict:
    """
    Compute TP/FP/TN/FN, precision, alert_rate, base_rate, lift, placebo p-value.
    Assumes both series are aligned on the same hourly index and restricted to
    the calibration window.
    """
    # Lead-shifted outcome: at hour t, the prediction targets outcome at t + lead
    outcome_shifted = outcome.shift(-lead_hours)
    valid = alert.notna() & outcome_shifted.notna()
    a = alert[valid].astype(bool).values
    o = outcome_shifted[valid].astype(bool).values

    n = len(a)
    if n == 0:
        return {"lift": np.nan, "precision": np.nan, "alert_rate": np.nan,
                "base_rate": np.nan, "n_positive_outcomes": 0,
                "placebo_p": np.nan, "tp": 0, "fp": 0, "tn": 0, "fn": 0}

    tp = int(np.sum(a & o))
    fp = int(np.sum(a & ~o))
    tn = int(np.sum(~a & ~o))
    fn = int(np.sum(~a & o))

    n_positive_outcomes = tp + fn
    alert_rate = (tp + fp) / n if n > 0 else 0.0
    base_rate  = n_positive_outcomes / n if n > 0 else 0.0
    precision  = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    lift = precision / base_rate if base_rate > 0 else 0.0

    # Placebo p-value: 500 random shuffles of the outcome label sequence
    if base_rate > 0:
        lift_perm = np.empty(N_PLACEBO)
        for i in range(N_PLACEBO):
            o_perm = rng.permutation(o)
            tp_p = int(np.sum(a & o_perm))
            fp_p = int(np.sum(a & ~o_perm))
            precision_p = tp_p / (tp_p + fp_p) if (tp_p + fp_p) > 0 else 0.0
            lift_perm[i] = precision_p / base_rate
        placebo_p = float(np.mean(lift_perm >= lift))
    else:
        placebo_p = np.nan

    return {
        "lift": lift, "precision": precision, "alert_rate": alert_rate,
        "base_rate": base_rate, "n_positive_outcomes": n_positive_outcomes,
        "placebo_p": placebo_p, "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Step 5 — Benjamini-Hochberg FDR
# ──────────────────────────────────────────────────────────────────────────────

def bh_adjust(pvalues: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values."""
    n = len(pvalues)
    if n == 0:
        return pvalues
    order = np.argsort(pvalues)
    ranked = pvalues[order]
    adj = ranked * n / (np.arange(n) + 1)
    # Enforce monotone non-decreasing in original order
    adj_min = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj_min, 1.0)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Step 6 — enumerate and evaluate configurations
# ──────────────────────────────────────────────────────────────────────────────

def enumerate_configurations() -> list:
    """Enumerate the 768 configurations of the pre-engaged grid (§5)."""
    configs = []

    # F0 — single-axis: 10 × 3 × 2 × 4 × 2 = 480
    for axis in ALL_AXES:
        for pctl in PCTLS:
            for k in KS:
                for lead in LEADS:
                    for outcome in OUTCOMES:
                        configs.append({
                            "family": "F0",
                            "axis": axis,
                            "pctl": pctl,
                            "k": k,
                            "lead": lead,
                            "outcome": outcome,
                        })

    # F1 — multi-axis grouped: 8 groups × variable thresholds × 2 × 4 × 2
    for group_name, group_def in F1_GROUPS.items():
        for threshold in group_def["thresholds"]:
            for k in KS:
                for lead in LEADS:
                    for outcome in OUTCOMES:
                        configs.append({
                            "family": "F1",
                            "axis": f"{group_name}_t{threshold}",
                            "group_axes": group_def["axes"],
                            "group_threshold": threshold,
                            "pctl": 0.90,
                            "k": k,
                            "lead": lead,
                            "outcome": outcome,
                        })

    # F4 — cross-chain: 2 groups × 5 axes × 2 × 4 × 2 = 160
    # Each F4 config uses a single axis from one chain to predict the other-chain outcome
    for group_name, group_def in F4_GROUPS.items():
        for axis in group_def["axes"]:
            for k in KS:
                for lead in LEADS:
                    # F4 fixes the outcome to the cross-chain pair
                    outcome = group_def["outcome"]
                    configs.append({
                        "family": "F4",
                        "axis": axis,
                        "group_label": group_name,
                        "pctl": 0.90,
                        "k": k,
                        "lead": lead,
                        "outcome": outcome,
                    })

    return configs


def build_alert_for_config(matrix: pd.DataFrame, cfg: dict,
                            instant_cache: dict) -> pd.Series:
    """Materialize the (possibly multi-axis) alert series for a configuration."""
    if cfg["family"] in ("F0", "F4"):
        key = (cfg["axis"], cfg["pctl"])
        if key not in instant_cache:
            instant_cache[key] = instant_alert_series(matrix, cfg["axis"], cfg["pctl"])
        return sustained_alert(instant_cache[key], cfg["k"])

    # F1 — voting
    axes = cfg["group_axes"]
    pctl = cfg["pctl"]
    vote_threshold = cfg["group_threshold"]
    votes = None
    for ax in axes:
        key = (ax, pctl)
        if key not in instant_cache:
            instant_cache[key] = instant_alert_series(matrix, ax, pctl)
        instant = instant_cache[key].astype(int)
        votes = instant if votes is None else votes.add(instant, fill_value=0)
    group_instant = votes >= vote_threshold
    return sustained_alert(group_instant, cfg["k"])


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading raw events...")
    events = pd.read_parquet(DATA / "cctp_v2_events_2025_raw.parquet")

    print("Pairing source ↔ destination on ETH-POL corridor...")
    paired = pair_eth_pol_messages(events)
    print(f"  paired rows: {len(paired):,}")
    print(f"  fast mode_requested: {int((paired['mode_requested']=='fast').sum()):,}")

    print("Computing hourly BS2 outcome on Fast triplets...")
    outcome_df = compute_hourly_bs2(paired)
    for col in OUTCOMES:
        n_pos = int(outcome_df[col].fillna(0).sum())
        n_obs = int(outcome_df[col].notna().sum())
        print(f"  {col}: {n_pos}/{n_obs} hours BS2 "
              f"(rate {n_pos / max(n_obs, 1):.4f})")

    print("Loading substrate-shift matrix...")
    matrix = load_corpus_matrix()

    print("Enumerating configurations...")
    configs = enumerate_configurations()
    print(f"  total: {len(configs)}")

    print("Evaluating configurations...")
    rng = np.random.default_rng(seed=42)
    instant_cache = {}
    rows = []

    for i, cfg in enumerate(configs):
        outcome = outcome_df[cfg["outcome"]]
        alert = build_alert_for_config(matrix, cfg, instant_cache)

        # Restrict to calibration window on outcome
        valid_idx = outcome.index.intersection(alert.index)
        alert_w = alert.reindex(valid_idx)
        outcome_w = outcome.reindex(valid_idx)

        stats = evaluate_config(alert_w, outcome_w, cfg["lead"], rng)

        # Power flag (§8)
        n_pos = stats["n_positive_outcomes"]
        if n_pos < POWER_INSUFFICIENT_MIN:
            power_flag = "INSUFFICIENT_POWER"
        elif n_pos < POWER_LOW_MIN:
            power_flag = "LOW_POWER"
        else:
            power_flag = "OK"

        rows.append({**cfg, **stats, "power_flag": power_flag})

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(configs)} configs evaluated")

    df_eval = pd.DataFrame(rows)

    # BH FDR within family + combined (§7)
    print("Applying BH FDR...")
    for family in ["F0", "F1", "F4"]:
        mask = (df_eval["family"] == family) & (df_eval["power_flag"] != "INSUFFICIENT_POWER")
        if mask.sum() > 0:
            df_eval.loc[mask, "bh_within_family_p_adj"] = bh_adjust(
                df_eval.loc[mask, "placebo_p"].fillna(1.0).values
            )
        else:
            df_eval.loc[mask, "bh_within_family_p_adj"] = np.nan

    combined_mask = df_eval["power_flag"] != "INSUFFICIENT_POWER"
    if combined_mask.sum() > 0:
        df_eval.loc[combined_mask, "bh_combined_p_adj"] = bh_adjust(
            df_eval.loc[combined_mask, "placebo_p"].fillna(1.0).values
        )
    else:
        df_eval["bh_combined_p_adj"] = np.nan

    # Survivors
    survivors = df_eval[
        (df_eval["bh_combined_p_adj"] < FDR_ALPHA)
        & (df_eval["lift"] >= LIFT_THRESHOLD)
        & (df_eval["power_flag"] != "INSUFFICIENT_POWER")
    ].sort_values("lift", ascending=False)

    print(f"  n_raw_p_lt_005: {int((df_eval['placebo_p'] < 0.05).sum())}")
    print(f"  n_survivors:    {len(survivors)}")

    # Output JSON
    manifest_sha256 = sha256_file(PUBLIABLE / "MANIFEST.md")
    raw_sha256      = sha256_file(DATA / "cctp_v2_events_2025_raw.parquet")
    baseline_sha256 = sha256_file(SHEETS / "baseline.parquet")
    script_sha256   = sha256_file(Path(__file__))

    output = {
        "protocol_version": PROTOCOL_VERSION,
        "corpus_reference": f"ETH-POL-CCTP-V2 publiable corpus, MANIFEST.md sha-256 {manifest_sha256}",
        "calibration_window_start_utc": WINDOW_START.isoformat().replace("+00:00", "Z"),
        "calibration_window_end_utc":   WINDOW_END.isoformat().replace("+00:00", "Z"),
        "outcome_definition": (
            "BRIDGE_STATE_STRUCTURAL_v1.1 BS2 (success_rate < 0.995 OR mode_fallback_rate > 0.05) "
            "gated by SLA_fast=120s, SLA_standard=7200s, restricted to mode_requested ∈ {fast}"
        ),
        "classifier_semantics": (
            "min_finality_threshold_requested==0 → 'other' (excluded); "
            "1..=1000 → 'fast'; ==2000 → 'standard'; else → 'other'"
        ),
        "outcomes_evaluated": OUTCOMES,
        "outcome_positive_rate_per_hour": {
            col: float(outcome_df[col].fillna(0).sum() / max(int(outcome_df[col].notna().sum()), 1))
            for col in OUTCOMES
        },
        "n_configurations_total":                 len(configs),
        "n_configurations_raw_p_lt_005":          int((df_eval["placebo_p"] < 0.05).sum()),
        "n_configurations_fdr_within_family":     int((df_eval["bh_within_family_p_adj"] < FDR_ALPHA).sum()),
        "n_survivors_combined_fdr_and_lift":      int(len(survivors)),
        "survivors": [
            {
                "family":              row["family"],
                "axis":                row["axis"],
                "k_consecutive_hours": int(row["k"]),
                "pctl":                float(row["pctl"]),
                "lead_hours":          int(row["lead"]),
                "outcome":             row["outcome"],
                "lift":                float(row["lift"]),
                "precision":           float(row["precision"]),
                "alert_rate":          float(row["alert_rate"]),
                "placebo_p":           float(row["placebo_p"]),
                "bh_combined_p_adj":   float(row["bh_combined_p_adj"]),
                "n_positive_outcomes": int(row["n_positive_outcomes"]),
                "power_flag":          str(row["power_flag"]),
            }
            for _, row in survivors.iterrows()
        ],
        "script_sha256": script_sha256,
        "input_parquets_sha256": {
            "cctp_v2_events_2025_raw.parquet": raw_sha256,
            "baseline.parquet": baseline_sha256,
        },
    }

    out_path = RESULTS / "BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
