"""
Invarians — Sensitivity analysis on α_fast — Ethereum
======================================================
Goal: quantify how the detection pipeline reacts when the EMA memory
horizon (α_fast) is changed. The published v1.0 calibration uses
α_fast = 2/11 (N ≈ 10 windows, ~10h memory).

Sweep         : α_fast ∈ {2/5, 2/7, 2/11, 2/15, 2/21, 2/31}
                ⇒ N     ∈ {4,   6,   10,    14,   20,   30 }
Thresholds    : fixed (threshold_s2 = 1.12, threshold_d2 = 1.10)
Metrics       : FPR (normal windows), TPR (ground-truth windows),
                detection latency on The Merge and Shanghai.
Ground truth  : The Merge (2022-09-14), Shanghai (2023-04-12),
                DeFi Summer (2020-06-15 → 2020-09-30, demand-only),
                NFT Mania (2021-08-01 → 2021-11-30, demand-only).

Input         : eth_invariants_2020_2024_phi280.csv
Outputs       : eth_sensitivity_alpha_results.csv
                eth_sensitivity_alpha_chart.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ─────────────────────────────────────────────
# PARAMETERS
# ─────────────────────────────────────────────

CHAIN        = "ethereum"
WARMUP_INV   = 50
THRESHOLD_S2 = 1.12     # structural trigger (τ)
THRESHOLD_D2 = 1.10     # demand trigger (π)

DATA_DIR     = Path(__file__).parent
INPUT_FILE   = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CSV      = DATA_DIR / "eth_sensitivity_alpha_results.csv"
OUT_PNG      = DATA_DIR / "eth_sensitivity_alpha_chart.png"

# Alpha sweep — (label, α, N)
ALPHA_SWEEP = [
    ("2/5",  2/5,  4),
    ("2/7",  2/7,  6),
    ("2/11", 2/11, 10),   # ← published
    ("2/15", 2/15, 14),
    ("2/21", 2/21, 20),
    ("2/31", 2/31, 30),
]

# Ground truth windows
EVENTS_TAU = [  # structural → evaluated against rhythm_ratio
    {"name": "The Merge", "onset": "2022-09-14", "window_end": "2022-09-17"},
    {"name": "Shanghai",  "onset": "2023-04-12", "window_end": "2023-04-15"},
]
EVENTS_PI = [   # demand → evaluated against sigma_ratio
    {"name": "DeFi Summer", "onset": "2020-06-15", "window_end": "2020-09-30"},
    {"name": "NFT Mania",   "onset": "2021-08-01", "window_end": "2021-11-30"},
]

# ─────────────────────────────────────────────
# 1. LOAD
# ─────────────────────────────────────────────

print(f"\n[1] Loading {INPUT_FILE.name} ...")
df = pd.read_csv(INPUT_FILE).sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def ema_seq(series: pd.Series, alpha: float) -> pd.Series:
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

def event_mask(df_, events):
    m = pd.Series(False, index=df_.index)
    for evt in events:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        m |= (df_["dt"] >= onset) & (df_["dt"] <= win_end)
    return m

def detection_latency(df_, signal_col, threshold, onset_ts):
    """Time (hours) between event onset and first threshold crossing on-or-after onset."""
    post = df_[df_["dt"] >= onset_ts]
    crossings = post[post[signal_col] >= threshold]
    if crossings.empty:
        return None
    first = crossings["dt"].iloc[0]
    return (first - onset_ts).total_seconds() / 3600.0

# ─────────────────────────────────────────────
# 2. SWEEP
# ─────────────────────────────────────────────

print("\n[2] Sweeping α_fast ...")
rows = []
for label, alpha, n_windows in ALPHA_SWEEP:
    d = df.copy()
    d["ema_fast_rho_ts"] = ema_seq(d["rho_ts"], alpha)
    d["ema_fast_rho_s"]  = ema_seq(d["rho_s"],  alpha)
    d["rhythm_ratio"]    = d["rho_ts"] / d["ema_fast_rho_ts"]
    d["sigma_ratio"]     = d["rho_s"]  / d["ema_fast_rho_s"]
    d = d.iloc[WARMUP_INV:].reset_index(drop=True)
    d = d.dropna(subset=["rhythm_ratio", "sigma_ratio"])

    # τ metrics
    in_tau = event_mask(d, EVENTS_TAU)
    fired_tau = d["rhythm_ratio"] >= THRESHOLD_S2
    tp_tau = int((fired_tau & in_tau).sum())
    fn_tau = int((~fired_tau & in_tau).sum())
    fp_tau = int((fired_tau & ~in_tau).sum())
    tn_tau = int((~fired_tau & ~in_tau).sum())
    tpr_tau = tp_tau / (tp_tau + fn_tau) if (tp_tau + fn_tau) else 0.0
    fpr_tau = fp_tau / (fp_tau + tn_tau) if (fp_tau + tn_tau) else 0.0

    # π metrics
    in_pi = event_mask(d, EVENTS_PI)
    fired_pi = d["sigma_ratio"] >= THRESHOLD_D2
    tp_pi = int((fired_pi & in_pi).sum())
    fn_pi = int((~fired_pi & in_pi).sum())
    fp_pi = int((fired_pi & ~in_pi).sum())
    tn_pi = int((~fired_pi & ~in_pi).sum())
    tpr_pi = tp_pi / (tp_pi + fn_pi) if (tp_pi + fn_pi) else 0.0
    fpr_pi = fp_pi / (fp_pi + tn_pi) if (fp_pi + tn_pi) else 0.0

    # Detection latencies on τ events
    lat_merge    = detection_latency(d, "rhythm_ratio", THRESHOLD_S2,
                                     pd.Timestamp("2022-09-14", tz="UTC"))
    lat_shanghai = detection_latency(d, "rhythm_ratio", THRESHOLD_S2,
                                     pd.Timestamp("2023-04-12", tz="UTC"))

    row = {
        "alpha_label":      label,
        "alpha":            round(alpha, 6),
        "N_windows":        n_windows,
        "tpr_tau":          round(tpr_tau, 4),
        "fpr_tau":          round(fpr_tau, 4),
        "tpr_pi":           round(tpr_pi, 4),
        "fpr_pi":           round(fpr_pi, 4),
        "latency_merge_h":    None if lat_merge    is None else round(lat_merge, 2),
        "latency_shanghai_h": None if lat_shanghai is None else round(lat_shanghai, 2),
        "published":        (label == "2/11"),
    }
    rows.append(row)
    print(f"    α={label:>5s}  N={n_windows:>2d}  "
          f"τ: TPR={tpr_tau:.3f} FPR={fpr_tau:.3f}  "
          f"π: TPR={tpr_pi:.3f} FPR={fpr_pi:.3f}  "
          f"lat_merge={row['latency_merge_h']}h  lat_shang={row['latency_shanghai_h']}h")

# ─────────────────────────────────────────────
# 3. EXPORT CSV
# ─────────────────────────────────────────────

out_df = pd.DataFrame(rows)
out_df.to_csv(OUT_CSV, index=False)
print(f"\n[3] Results → {OUT_CSV.name}")

# ─────────────────────────────────────────────
# 4. CHART
# ─────────────────────────────────────────────

print("[4] Plotting sensitivity chart ...")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

xs = [r["N_windows"] for r in rows]
axes[0].plot(xs, [r["tpr_tau"] for r in rows], "o-", label="TPR τ (structural)")
axes[0].plot(xs, [r["fpr_tau"] for r in rows], "s--", label="FPR τ (structural)")
axes[0].plot(xs, [r["tpr_pi"]  for r in rows], "o-", label="TPR π (demand)")
axes[0].plot(xs, [r["fpr_pi"]  for r in rows], "s--", label="FPR π (demand)")
axes[0].axvline(10, color="red", linestyle=":", alpha=0.6, label="α=2/11 (published)")
axes[0].set_xlabel("EMA memory N (windows)")
axes[0].set_ylabel("Rate")
axes[0].set_title("TPR / FPR vs α_fast")
axes[0].legend(fontsize=8)
axes[0].grid(alpha=0.3)

lat_m = [r["latency_merge_h"]    for r in rows]
lat_s = [r["latency_shanghai_h"] for r in rows]
axes[1].plot(xs, lat_m, "o-", label="The Merge")
axes[1].plot(xs, lat_s, "s-", label="Shanghai")
axes[1].axvline(10, color="red", linestyle=":", alpha=0.6, label="α=2/11 (published)")
axes[1].set_xlabel("EMA memory N (windows)")
axes[1].set_ylabel("Detection latency (h)")
axes[1].set_title("Detection latency vs α_fast")
axes[1].legend(fontsize=8)
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=130)
print(f"    → {OUT_PNG.name}")
print("\n[done]")
