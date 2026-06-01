#!/usr/bin/env python3
"""
BS_STRUCTURAL_PRECURSORS_v2 — extended feature space.

Implements PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md strictly. Successor to
v1, evaluating three substrate-shift representations against the unchanged
BRIDGE_STATE_STRUCTURAL_v1.1 BS2 outcome on the locked 2025 ETH-POL CCTP V2 corpus.

Representations evaluated:
  A — SMD of shift             |shift(t)| - |shift(t-1)|  (same as v1)
  B — Signed shift level       shift(t) directly, polarity-separated tails
  C — Drift composite level    drift_<axis-type>(t), polarity-separated tails

Inputs (locked Step 3 corpus):
  data/cctp_v2_events_2025_raw.parquet
  results/per_event_sheets/baseline.parquet  (substrate matrix + drift composites)
  results/per_event_sheets/*.parquet         (per-event sheets, same matrix shape)

Output:
  results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PUBLIABLE = Path(__file__).resolve().parent.parent
DATA = PUBLIABLE / "data"
RESULTS = PUBLIABLE / "results"
SHEETS = RESULTS / "per_event_sheets"

PROTOCOL_VERSION = "BS_STRUCTURAL_PRECURSORS_v2"

# ──────────────────────────────────────────────────────────────────────────────
# Constants — fixed by PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md
# ──────────────────────────────────────────────────────────────────────────────

WINDOW_START = pd.Timestamp("2025-06-09 18:45:00", tz="UTC")
WINDOW_END   = pd.Timestamp("2025-12-31 23:59:00", tz="UTC")
PCTL_FIT_START = pd.Timestamp("2025-02-01 00:00:00", tz="UTC")

SLA_FAST_SECS     = 120
SLA_STANDARD_SECS = 7200

MIN_OBSERVATIONS_BS  = 5
MIN_SUCCESS_RATE     = 0.995
MAX_FALLBACK_RATE    = 0.05

FDR_ALPHA            = 0.05
LIFT_THRESHOLD       = 1.5
N_PLACEBO            = 500

POWER_LOW_MIN          = 30
POWER_INSUFFICIENT_MIN = 10

DOMAIN_CHAIN = {0: "ethereum", 7: "polygon"}

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

DRIFT_COMPOSITES = [
    "eth_drift_structural",
    "eth_drift_demand",
    "pol_drift_structural",
    "pol_drift_demand",
]

PCTLS    = [0.85, 0.90, 0.95]
KS       = [1, 2]
LEADS    = [3, 6, 12, 24]
POLARITIES = ["pos", "neg"]

OUTCOMES = ["bs2_eth_to_pol_fast", "bs2_pol_to_eth_fast"]

F1_GROUPS = {
    "eth_demand_union":     {"axes": ["eth_sigma_demand_shift",
                                      "eth_size_demand_shift",
                                      "eth_tx_demand_shift"],
                             "thresholds": [2, 3]},
    "eth_structural_union": {"axes": ["eth_rhythm_ratio_shift",
                                      "eth_continuity_ratio_shift"],
                             "thresholds": [2]},
    "pol_demand_union":     {"axes": ["pol_sigma_demand_shift",
                                      "pol_size_demand_shift",
                                      "pol_tx_demand_shift"],
                             "thresholds": [2, 3]},
    "pol_structural_union": {"axes": ["pol_rhythm_ratio_shift",
                                      "pol_continuity_ratio_shift"],
                             "thresholds": [2]},
    "eth_all_union":        {"axes": ETH_AXES, "thresholds": [3, 4]},
    "pol_all_union":        {"axes": POL_AXES, "thresholds": [3, 4]},
    "all_demand_union":     {"axes": ["eth_sigma_demand_shift",
                                      "eth_size_demand_shift",
                                      "eth_tx_demand_shift",
                                      "pol_sigma_demand_shift",
                                      "pol_size_demand_shift",
                                      "pol_tx_demand_shift"],
                             "thresholds": [3, 4]},
    "all_structural_union": {"axes": ["eth_rhythm_ratio_shift",
                                      "eth_continuity_ratio_shift",
                                      "pol_rhythm_ratio_shift",
                                      "pol_continuity_ratio_shift"],
                             "thresholds": [2, 3]},
}

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
# Outcome reconstruction — verbatim from v1
# ──────────────────────────────────────────────────────────────────────────────

def pair_eth_pol_messages(events: pd.DataFrame) -> pd.DataFrame:
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


def compute_hourly_bs2(paired: pd.DataFrame) -> pd.DataFrame:
    grid = pd.date_range(WINDOW_START.floor("h"), WINDOW_END.floor("h"),
                         freq="h", tz="UTC")
    out = pd.DataFrame(index=grid)
    out.index.name = "hour_utc"

    fast_only = paired[paired["mode_requested"] == "fast"].copy()

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
# Substrate matrix loader
# ──────────────────────────────────────────────────────────────────────────────

def load_corpus_matrix() -> pd.DataFrame:
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


# ──────────────────────────────────────────────────────────────────────────────
# Representation A — SMD of shift (verbatim from v1)
# ──────────────────────────────────────────────────────────────────────────────

def smd_series(matrix: pd.DataFrame, axis: str) -> pd.Series:
    s = matrix[axis].astype(float)
    return s.abs().diff()


def axis_smd_threshold(smd: pd.Series, pctl: float) -> float:
    fit = smd[(smd.index >= PCTL_FIT_START) & (smd.index <= WINDOW_END)]
    return float(np.nanquantile(fit.values, pctl))


def smd_instant_alert(matrix: pd.DataFrame, axis: str, pctl: float) -> pd.Series:
    smd = smd_series(matrix, axis)
    threshold = axis_smd_threshold(smd, pctl)
    return smd > threshold


# ──────────────────────────────────────────────────────────────────────────────
# Representation B — Signed shift level, polarity-separated
# ──────────────────────────────────────────────────────────────────────────────

def signed_shift_thresholds(matrix: pd.DataFrame, series_name: str, pctl: float):
    """Returns (positive_threshold, negative_threshold) for the series, computed
    on the non-January distribution, separately for positive and negative tails."""
    s = matrix[series_name].astype(float)
    fit = s[(s.index >= PCTL_FIT_START) & (s.index <= WINDOW_END)]
    pos = fit[fit > 0].dropna()
    neg = fit[fit < 0].dropna()
    pos_t = float(np.nanquantile(pos.values, pctl)) if len(pos) > 0 else np.inf
    neg_t = float(np.nanquantile(neg.values, 1 - pctl)) if len(neg) > 0 else -np.inf
    return pos_t, neg_t


def signed_shift_instant_alert(matrix: pd.DataFrame, series_name: str,
                                pctl: float, polarity: str) -> pd.Series:
    pos_t, neg_t = signed_shift_thresholds(matrix, series_name, pctl)
    s = matrix[series_name].astype(float)
    if polarity == "pos":
        return s > pos_t
    else:
        return s < neg_t


# ──────────────────────────────────────────────────────────────────────────────
# Sustained alert (K consecutive)
# ──────────────────────────────────────────────────────────────────────────────

def sustained_alert(instant: pd.Series, k: int) -> pd.Series:
    if k <= 1:
        return instant.astype(bool)
    return instant.rolling(window=k, min_periods=k).sum() == k


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation helpers — verbatim from v1
# ──────────────────────────────────────────────────────────────────────────────

def evaluate_config(alert: pd.Series, outcome: pd.Series, lead_hours: int,
                    rng: np.random.Generator) -> dict:
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


def bh_adjust(pvalues: np.ndarray) -> np.ndarray:
    n = len(pvalues)
    if n == 0:
        return pvalues
    order = np.argsort(pvalues)
    ranked = pvalues[order]
    adj = ranked * n / (np.arange(n) + 1)
    adj_min = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj_min, 1.0)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Configuration enumeration — extended for v2
# ──────────────────────────────────────────────────────────────────────────────

def enumerate_configurations() -> list:
    configs = []

    # F0a — SMD of shift (Representation A) — verbatim v1
    for axis in ALL_AXES:
        for pctl in PCTLS:
            for k in KS:
                for lead in LEADS:
                    for outcome in OUTCOMES:
                        configs.append({
                            "family": "F0a",
                            "representation": "A",
                            "axis": axis,
                            "pctl": pctl,
                            "k": k,
                            "lead": lead,
                            "outcome": outcome,
                            "polarity": None,
                        })

    # F0b — Signed shift level (Representation B)
    for axis in ALL_AXES:
        for polarity in POLARITIES:
            for pctl in PCTLS:
                for k in KS:
                    for lead in LEADS:
                        for outcome in OUTCOMES:
                            configs.append({
                                "family": "F0b",
                                "representation": "B",
                                "axis": axis,
                                "pctl": pctl,
                                "k": k,
                                "lead": lead,
                                "outcome": outcome,
                                "polarity": polarity,
                            })

    # F0c — Drift composite level (Representation C)
    for composite in DRIFT_COMPOSITES:
        for polarity in POLARITIES:
            for pctl in PCTLS:
                for k in KS:
                    for lead in LEADS:
                        for outcome in OUTCOMES:
                            configs.append({
                                "family": "F0c",
                                "representation": "C",
                                "axis": composite,
                                "pctl": pctl,
                                "k": k,
                                "lead": lead,
                                "outcome": outcome,
                                "polarity": polarity,
                            })

    # F1 — Multi-axis grouped (Representation A) — verbatim v1
    for group_name, group_def in F1_GROUPS.items():
        for threshold in group_def["thresholds"]:
            for k in KS:
                for lead in LEADS:
                    for outcome in OUTCOMES:
                        configs.append({
                            "family": "F1",
                            "representation": "A",
                            "axis": f"{group_name}_t{threshold}",
                            "group_axes": group_def["axes"],
                            "group_threshold": threshold,
                            "pctl": 0.90,
                            "k": k,
                            "lead": lead,
                            "outcome": outcome,
                            "polarity": None,
                        })

    # F4 — Cross-chain (Representation A) — verbatim v1
    for group_name, group_def in F4_GROUPS.items():
        for axis in group_def["axes"]:
            for k in KS:
                for lead in LEADS:
                    configs.append({
                        "family": "F4",
                        "representation": "A",
                        "axis": axis,
                        "group_label": group_name,
                        "pctl": 0.90,
                        "k": k,
                        "lead": lead,
                        "outcome": group_def["outcome"],
                        "polarity": None,
                    })

    return configs


def build_alert_for_config(matrix: pd.DataFrame, cfg: dict,
                            instant_cache: dict) -> pd.Series:
    rep = cfg["representation"]
    axis = cfg["axis"]
    pctl = cfg["pctl"]

    if cfg["family"] == "F1":
        axes = cfg["group_axes"]
        vote_threshold = cfg["group_threshold"]
        votes = None
        for ax in axes:
            key = ("A", ax, pctl, None)
            if key not in instant_cache:
                instant_cache[key] = smd_instant_alert(matrix, ax, pctl)
            instant = instant_cache[key].astype(int)
            votes = instant if votes is None else votes.add(instant, fill_value=0)
        group_instant = votes >= vote_threshold
        return sustained_alert(group_instant, cfg["k"])

    if rep == "A":
        key = ("A", axis, pctl, None)
        if key not in instant_cache:
            instant_cache[key] = smd_instant_alert(matrix, axis, pctl)
        return sustained_alert(instant_cache[key], cfg["k"])

    if rep == "B":
        polarity = cfg["polarity"]
        key = ("B", axis, pctl, polarity)
        if key not in instant_cache:
            instant_cache[key] = signed_shift_instant_alert(matrix, axis, pctl, polarity)
        return sustained_alert(instant_cache[key], cfg["k"])

    if rep == "C":
        polarity = cfg["polarity"]
        key = ("C", axis, pctl, polarity)
        if key not in instant_cache:
            instant_cache[key] = signed_shift_instant_alert(matrix, axis, pctl, polarity)
        return sustained_alert(instant_cache[key], cfg["k"])

    raise ValueError(f"Unknown representation {rep}")


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
    family_counts = {}
    for c in configs:
        family_counts[c["family"]] = family_counts.get(c["family"], 0) + 1
    print(f"  total: {len(configs)}")
    for f, n in sorted(family_counts.items()):
        print(f"    {f}: {n}")

    print("Evaluating configurations...")
    rng = np.random.default_rng(seed=42)
    instant_cache = {}
    rows = []

    for i, cfg in enumerate(configs):
        outcome = outcome_df[cfg["outcome"]]
        alert = build_alert_for_config(matrix, cfg, instant_cache)
        valid_idx = outcome.index.intersection(alert.index)
        alert_w = alert.reindex(valid_idx)
        outcome_w = outcome.reindex(valid_idx)

        stats = evaluate_config(alert_w, outcome_w, cfg["lead"], rng)

        n_pos = stats["n_positive_outcomes"]
        if n_pos < POWER_INSUFFICIENT_MIN:
            power_flag = "INSUFFICIENT_POWER"
        elif n_pos < POWER_LOW_MIN:
            power_flag = "LOW_POWER"
        else:
            power_flag = "OK"

        rows.append({**cfg, **stats, "power_flag": power_flag})

        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(configs)} configs evaluated")

    df_eval = pd.DataFrame(rows)

    print("Applying BH FDR within family + combined...")
    df_eval["bh_within_family_p_adj"] = np.nan
    df_eval["bh_combined_p_adj"] = np.nan

    for family in sorted(family_counts.keys()):
        mask = (df_eval["family"] == family) & (df_eval["power_flag"] != "INSUFFICIENT_POWER")
        if mask.sum() > 0:
            df_eval.loc[mask, "bh_within_family_p_adj"] = bh_adjust(
                df_eval.loc[mask, "placebo_p"].fillna(1.0).values
            )

    combined_mask = df_eval["power_flag"] != "INSUFFICIENT_POWER"
    if combined_mask.sum() > 0:
        df_eval.loc[combined_mask, "bh_combined_p_adj"] = bh_adjust(
            df_eval.loc[combined_mask, "placebo_p"].fillna(1.0).values
        )

    survivors = df_eval[
        (df_eval["bh_combined_p_adj"] < FDR_ALPHA)
        & (df_eval["lift"] >= LIFT_THRESHOLD)
        & (df_eval["power_flag"] != "INSUFFICIENT_POWER")
    ].sort_values("lift", ascending=False)

    print(f"  raw placebo_p < 0.05:     {int((df_eval['placebo_p'] < 0.05).sum())}")
    print(f"  within-family FDR pass:   {int((df_eval['bh_within_family_p_adj'] < FDR_ALPHA).sum())}")
    print(f"  combined FDR + lift pass: {len(survivors)}")

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
        "predictor_representations": ["A_smd_of_shift", "B_signed_shift_level", "C_drift_composite_level"],
        "outcomes_evaluated": OUTCOMES,
        "outcome_positive_rate_per_hour": {
            col: float(outcome_df[col].fillna(0).sum() / max(int(outcome_df[col].notna().sum()), 1))
            for col in OUTCOMES
        },
        "n_configurations_total":             len(configs),
        "n_configurations_per_family":        {k: int(v) for k, v in family_counts.items()},
        "n_configurations_raw_p_lt_005":      int((df_eval["placebo_p"] < 0.05).sum()),
        "n_configurations_fdr_within_family": int((df_eval["bh_within_family_p_adj"] < FDR_ALPHA).sum()),
        "n_survivors_combined_fdr_and_lift":  int(len(survivors)),
        "survivors": [
            {
                "family":              row["family"],
                "representation":      row["representation"],
                "axis":                row["axis"],
                "polarity":            row.get("polarity"),
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

    out_path = RESULTS / "BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
