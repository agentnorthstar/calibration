"""
Invarians — Sweep threshold_s2 ETH
Objectif : trouver le seuil optimal S2 pour ETH (FPR < 2%, TPR max)
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CHART  = DATA_DIR / "eth_sweep_chart.png"

ALPHA_FAST   = 2 / 11
THRESHOLD_D2 = 1.05
WARMUP_INV   = 50

GROUND_TRUTH = [
    {"name": "DeFi Summer",     "onset": "2020-06-15", "window_end": "2020-09-30", "expected": ["S1D2","S2D2"]},
    {"name": "NFT Mania",       "onset": "2021-03-01", "window_end": "2021-05-30", "expected": ["S1D2","S2D2"]},
    {"name": "The Merge",       "onset": "2022-09-14", "window_end": "2022-09-17", "expected": ["S2D1","S2D2"]},
    {"name": "Shanghai",        "onset": "2023-04-12", "window_end": "2023-04-15", "expected": ["S2D1","S1D2","S2D2"]},
]

# Seuils à tester
THRESHOLDS_S2 = [1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20, 1.25]

# ── Chargement + EMA (une seule fois) ────────────────────────────────────────
df = pd.read_csv(INPUT_FILE).sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)

def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

df["ema_fast_rho_ts"] = ema_seq(df["rho_ts"], ALPHA_FAST)
df["ema_fast_rho_s"]  = ema_seq(df["rho_s"],  ALPHA_FAST)
df["rhythm_ratio"]    = df["rho_ts"] / df["ema_fast_rho_ts"]
df["sigma_ratio"]     = df["rho_s"]  / df["ema_fast_rho_s"]
df.loc[:WARMUP_INV, ["rhythm_ratio", "sigma_ratio"]] = np.nan

# Masque événements ground truth
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"], tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
df_normal = df[~mask_event & (df.index > WARMUP_INV)]

# ── Sweep ─────────────────────────────────────────────────────────────────────
print(f"\n{'threshold_s2':>14} {'FPR':>8} {'S2_total':>10} {'The Merge':>12} {'Shanghai':>12} {'lat_merge':>12}")
print("─" * 75)

rows = []
for thr in THRESHOLDS_S2:
    df["tau_state"] = np.where(df["rhythm_ratio"] >= thr, "S2", "S1")
    df["pi_state"]  = np.where(df["sigma_ratio"]  >= THRESHOLD_D2, "D2", "D1")
    df["state"]     = df["tau_state"] + df["pi_state"]

    # FPR — utiliser les index de df_normal sur df (slice = copie, pas vue)
    stress_states = ["S2D1", "S2D2", "S1D2"]
    fpr = df.loc[df_normal.index, "state"].isin(stress_states).mean()

    # TPR par événement
    event_results = {}
    for evt in GROUND_TRUTH:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
        detected = window[window["state"].isin(evt["expected"])]
        if len(detected):
            lat_h = (detected["dt"].iloc[0] - onset).total_seconds() / 3600
            event_results[evt["name"]] = {"tp": True, "lat_h": lat_h}
        else:
            event_results[evt["name"]] = {"tp": False, "lat_h": None}

    merge_tp  = "✅" if event_results["The Merge"]["tp"]  else "❌"
    shangh_tp = "✅" if event_results["Shanghai"]["tp"]   else "❌"
    merge_lat = f"{event_results['The Merge']['lat_h']:.1f}h" if event_results["The Merge"]["lat_h"] else "—"

    n_s2_total = df.loc[df.index > WARMUP_INV, "state"].isin(["S2D1","S2D2"]).sum()

    print(f"{thr:>14.2f} {fpr:>7.2%} {n_s2_total:>10} {merge_tp:>12} {shangh_tp:>12} {merge_lat:>12}")

    rows.append({
        "threshold_s2"      : thr,
        "fpr"               : round(fpr, 4),
        "n_s2d1_s2d2"       : int(n_s2_total),
        "merge_detected"    : event_results["The Merge"]["tp"],
        "merge_latency_h"   : event_results["The Merge"]["lat_h"],
        "shanghai_detected" : event_results["Shanghai"]["tp"],
        "shanghai_latency_h": event_results["Shanghai"]["lat_h"],
    })

sweep_df = pd.DataFrame(rows)
sweep_df.to_csv(DATA_DIR / "eth_sweep_results.csv", index=False)

# ── Graphique courbe FPR vs threshold ────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5), facecolor="#080A09")
ax.set_facecolor("#0d0d0d")
ax.tick_params(colors="#888", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#222")

ax.plot(sweep_df["threshold_s2"], sweep_df["fpr"] * 100,
        color="#5b9bd5", linewidth=2, marker="o", markersize=6, label="FPR (%)")

# Zone cible FPR < 2%
ax.axhline(y=2.0, color="#4a7c59", linewidth=1, linestyle="--", label="cible FPR < 2%")
ax.axhline(y=1.0, color="#4a7c59", linewidth=0.6, linestyle=":", label="cible FPR < 1%")

# Annoter chaque point : TP Merge ?
for _, row in sweep_df.iterrows():
    merge_ok = "✓ Merge" if row["merge_detected"] else "✗ Merge"
    color = "#4a7c59" if row["merge_detected"] else "#8b1a1a"
    ax.annotate(merge_ok,
                xy=(row["threshold_s2"], row["fpr"] * 100),
                xytext=(0, 12), textcoords="offset points",
                ha="center", fontsize=7, color=color)

ax.set_xlabel("threshold_s2", color="#888", fontsize=10)
ax.set_ylabel("FPR (%)", color="#888", fontsize=10)
ax.set_title("ETH — FPR vs threshold_s2  (D2=1.05 fixe)", color="white", fontsize=11)
ax.legend(fontsize=8, facecolor="#111", labelcolor="white")
ax.set_ylim(0, None)

plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"\nGraphique → {OUT_CHART.name}")
print(f"CSV       → eth_sweep_results.csv")
