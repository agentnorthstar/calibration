"""
Invarians — Sweep threshold_d2 ETH
threshold_s2 = 1.12 fixé (validé session 16 Mars 2026)
Objectif : FPR < 1.5%, conserver détection Merge + Shanghai
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR     = Path(__file__).parent
INPUT_FILE   = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CHART    = DATA_DIR / "eth_sweep_d2_chart.png"
OUT_CSV      = DATA_DIR / "eth_sweep_d2_results.csv"

ALPHA_FAST   = 2 / 11
THRESHOLD_S2 = 1.12       # fixé — validé
WARMUP_INV   = 50

THRESHOLDS_D2 = [1.02, 1.03, 1.05, 1.08, 1.10, 1.12, 1.15, 1.20]

GROUND_TRUTH = [
    {"name": "DeFi Summer",  "onset": "2020-06-15", "window_end": "2020-09-30", "expected": ["S1D2","S2D2"]},
    {"name": "NFT Mania",    "onset": "2021-03-01", "window_end": "2021-05-30", "expected": ["S1D2","S2D2"]},
    {"name": "The Merge",    "onset": "2022-09-14", "window_end": "2022-09-17", "expected": ["S2D1","S2D2"]},
    {"name": "Shanghai",     "onset": "2023-04-12", "window_end": "2023-04-15", "expected": ["S2D1","S1D2","S2D2"]},
]

# ── Chargement + EMA ─────────────────────────────────────────────────────────
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

# tau_state fixe (threshold_s2=1.12)
df["tau_state"] = np.where(df["rhythm_ratio"] >= THRESHOLD_S2, "S2", "S1")

# Masque hors événements
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"],      tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
normal_idx = df[~mask_event & (df.index > WARMUP_INV)].index

# ── Sweep ─────────────────────────────────────────────────────────────────────
print(f"\n{'threshold_d2':>13} {'FPR':>8} {'n_D2_alarms':>12} {'Merge':>8} {'Shanghai':>10} {'DeFi S':>8} {'NFT':>6}")
print("─" * 72)

rows = []
for thr_d2 in THRESHOLDS_D2:
    df["pi_state"] = np.where(df["sigma_ratio"] >= thr_d2, "D2", "D1")
    df["state"]    = df["tau_state"] + df["pi_state"]

    # FPR
    stress = ["S2D1","S2D2","S1D2"]
    fpr    = df.loc[normal_idx, "state"].isin(stress).mean()
    n_d2   = df.loc[df.index > WARMUP_INV, "state"].isin(["S1D2","S2D2"]).sum()

    # TPR par événement
    evt_res = {}
    for evt in GROUND_TRUTH:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
        det     = window[window["state"].isin(evt["expected"])]
        evt_res[evt["name"]] = det.iloc[0]["dt"] if len(det) else None

    m  = "✅" if evt_res["The Merge"]   else "❌"
    s  = "✅" if evt_res["Shanghai"]    else "❌"
    d  = "✅" if evt_res["DeFi Summer"] else "❌"
    n  = "✅" if evt_res["NFT Mania"]   else "❌"

    print(f"{thr_d2:>13.2f} {fpr:>7.2%} {n_d2:>12} {m:>8} {s:>10} {d:>8} {n:>6}")
    rows.append({
        "threshold_d2"      : thr_d2,
        "fpr"               : round(fpr, 4),
        "n_d2_alarms"       : int(n_d2),
        "merge_detected"    : bool(evt_res["The Merge"]),
        "shanghai_detected" : bool(evt_res["Shanghai"]),
        "defi_detected"     : bool(evt_res["DeFi Summer"]),
        "nft_detected"      : bool(evt_res["NFT Mania"]),
    })

sweep_df = pd.DataFrame(rows)
sweep_df.to_csv(OUT_CSV, index=False)

# ── Graphique ─────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5), facecolor="#080A09")
ax.set_facecolor("#0d0d0d")
ax.tick_params(colors="#888", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#222")

ax.plot(sweep_df["threshold_d2"], sweep_df["fpr"] * 100,
        color="#5b9bd5", linewidth=2, marker="o", markersize=6)
ax.axhline(y=1.5, color="#4a7c59", linewidth=1.0, linestyle="--", label="cible FPR < 1.5%")
ax.axhline(y=2.12, color="#c47a1e", linewidth=0.8, linestyle=":", label="plancher D2 session précédente (2.12%)")

for _, row in sweep_df.iterrows():
    m_ok = "✓M" if row["merge_detected"] else "✗M"
    color = "#4a7c59" if row["merge_detected"] else "#8b1a1a"
    ax.annotate(m_ok, xy=(row["threshold_d2"], row["fpr"]*100),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=7, color=color)

ax.set_xlabel("threshold_d2", color="#888", fontsize=10)
ax.set_ylabel("FPR (%)", color="#888", fontsize=10)
ax.set_title("ETH — FPR vs threshold_d2  (S2=1.12 fixé)", color="white", fontsize=11)
ax.legend(fontsize=8, facecolor="#111", labelcolor="white")

plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"\nGraphique → {OUT_CHART.name}")
print(f"CSV       → {OUT_CSV.name}")
