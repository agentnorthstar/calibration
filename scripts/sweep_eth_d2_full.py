"""
Invarians — Sweep D2 complet ETH (sigma + size + tx)
threshold_s2 = 1.12 fixé (validé)
threshold_d2 sigma = 1.10 fixé (validé)
Objectif : valider size_demand et tx_demand (actuellement P95 ancien backtest)
Logique prod : D2 si 2 dims sur 3 au-dessus de leur seuil respectif
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CHART  = DATA_DIR / "eth_sweep_d2_full_chart.png"
OUT_CSV    = DATA_DIR / "eth_sweep_d2_full_results.csv"

ALPHA_FAST    = 2 / 11
THRESHOLD_S2  = 1.12
SIGMA_DEMAND  = 1.10   # validé
WARMUP_INV    = 50

# Seuils à tester pour size et tx
THRESHOLDS_SIZE = [1.10, 1.15, 1.20, 1.25, 1.30]
THRESHOLDS_TX   = [1.10, 1.15, 1.20, 1.25, 1.30]

GROUND_TRUTH = [
    {"name": "DeFi Summer",  "onset": "2020-06-15", "window_end": "2020-09-30", "expected": ["S1D2","S2D2"]},
    {"name": "NFT Mania",    "onset": "2021-03-01", "window_end": "2021-05-30", "expected": ["S1D2","S2D2"]},
    {"name": "The Merge",    "onset": "2022-09-14", "window_end": "2022-09-17", "expected": ["S2D1","S2D2"]},
    {"name": "Shanghai",     "onset": "2023-04-12", "window_end": "2023-04-15", "expected": ["S2D1","S1D2","S2D2"]},
]

# ── Chargement + EMA ─────────────────────────────────────────────────────────
print("[1] Chargement données ...")
df = pd.read_csv(INPUT_FILE).sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)

def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

print("[2] Calcul EMA (rho_ts, rho_s, size_avg, tx_count_avg) ...")
df["ema_rho_ts"]      = ema_seq(df["rho_ts"],       ALPHA_FAST)
df["ema_rho_s"]       = ema_seq(df["rho_s"],        ALPHA_FAST)
df["ema_size"]        = ema_seq(df["size_avg"],      ALPHA_FAST)
df["ema_tx"]          = ema_seq(df["tx_count_avg"],  ALPHA_FAST)

df["rhythm_ratio"]    = df["rho_ts"]       / df["ema_rho_ts"]
df["sigma_ratio"]     = df["rho_s"]        / df["ema_rho_s"]
df["size_ratio"]      = df["size_avg"]     / df["ema_size"]
df["tx_ratio"]        = df["tx_count_avg"] / df["ema_tx"]

df.loc[:WARMUP_INV, ["rhythm_ratio","sigma_ratio","size_ratio","tx_ratio"]] = np.nan

# tau_state et sigma_dim fixes
df["tau_state"]  = np.where(df["rhythm_ratio"] >= THRESHOLD_S2, "S2", "S1")
df["sigma_dim"]  = (df["sigma_ratio"] >= SIGMA_DEMAND).astype(int)

# Masque hors événements
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"],      tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
normal_idx = df[~mask_event & (df.index > WARMUP_INV)].index

# ── Distributions des ratios en conditions normales ───────────────────────────
print("\n[3] Distributions normales (hors événements) :")
for col in ["sigma_ratio", "size_ratio", "tx_ratio"]:
    s = df.loc[normal_idx, col].dropna()
    print(f"   {col:15s}  p50={s.quantile(.50):.4f}  p90={s.quantile(.90):.4f}  "
          f"p95={s.quantile(.95):.4f}  p99={s.quantile(.99):.4f}")

# ── Sweep size × tx ───────────────────────────────────────────────────────────
print("\n[4] Sweep size_demand × tx_demand ...")
print(f"\n{'size':>6} {'tx':>6} {'FPR':>8} {'n_D2':>8} {'Merge':>8} {'Shanghai':>10} {'DeFi':>8} {'NFT':>6}")
print("─" * 68)

rows = []
for sz in THRESHOLDS_SIZE:
    for tx in THRESHOLDS_TX:
        df["size_dim"] = (df["size_ratio"] >= sz).astype(int)
        df["tx_dim"]   = (df["tx_ratio"]   >= tx).astype(int)
        df["d2_dims"]  = df["sigma_dim"] + df["size_dim"] + df["tx_dim"]
        df["pi_state"] = np.where(df["d2_dims"] >= 2, "D2", "D1")
        df["state"]    = df["tau_state"] + df["pi_state"]

        fpr   = df.loc[normal_idx, "state"].isin(["S2D1","S2D2","S1D2"]).mean()
        n_d2  = df.loc[df.index > WARMUP_INV, "state"].isin(["S1D2","S2D2"]).sum()

        evt_res = {}
        for evt in GROUND_TRUTH:
            onset   = pd.Timestamp(evt["onset"],      tz="UTC")
            win_end = pd.Timestamp(evt["window_end"], tz="UTC")
            window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
            det     = window[window["state"].isin(evt["expected"])]
            evt_res[evt["name"]] = bool(len(det))

        m = "✅" if evt_res["The Merge"]   else "❌"
        s = "✅" if evt_res["Shanghai"]    else "❌"
        d = "✅" if evt_res["DeFi Summer"] else "❌"
        n = "✅" if evt_res["NFT Mania"]   else "❌"

        print(f"{sz:>6.2f} {tx:>6.2f} {fpr:>7.2%} {n_d2:>8} {m:>8} {s:>10} {d:>8} {n:>6}")
        rows.append({
            "size_demand": sz, "tx_demand": tx,
            "sigma_demand": SIGMA_DEMAND,
            "fpr": round(fpr, 4), "n_d2": int(n_d2),
            "merge": evt_res["The Merge"], "shanghai": evt_res["Shanghai"],
            "defi": evt_res["DeFi Summer"], "nft": evt_res["NFT Mania"],
        })

sweep_df = pd.DataFrame(rows)
sweep_df.to_csv(OUT_CSV, index=False)

# ── Graphique heatmap FPR ─────────────────────────────────────────────────────
print("\n[5] Génération heatmap ...")
pivot = sweep_df.pivot(index="size_demand", columns="tx_demand", values="fpr") * 100

fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor="#080A09")
fig.suptitle("ETH — Sweep D2 : size_demand × tx_demand  (sigma=1.10 fixé, S2=1.12 fixé)",
             color="white", fontsize=11)

for ax in axes:
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#222")

# Heatmap FPR
im = axes[0].imshow(pivot.values, cmap="RdYlGn_r", aspect="auto",
                    vmin=0, vmax=5)
axes[0].set_xticks(range(len(pivot.columns)))
axes[0].set_xticklabels([f"{v:.2f}" for v in pivot.columns], color="#888")
axes[0].set_yticks(range(len(pivot.index)))
axes[0].set_yticklabels([f"{v:.2f}" for v in pivot.index], color="#888")
axes[0].set_xlabel("tx_demand", color="#888")
axes[0].set_ylabel("size_demand", color="#888")
axes[0].set_title("FPR (%)", color="white", fontsize=9)
for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        axes[0].text(j, i, f"{pivot.values[i,j]:.2f}%",
                     ha="center", va="center", fontsize=7, color="white")
plt.colorbar(im, ax=axes[0])

# Heatmap n_D2
pivot_n = sweep_df.pivot(index="size_demand", columns="tx_demand", values="n_d2")
im2 = axes[1].imshow(pivot_n.values, cmap="Blues", aspect="auto")
axes[1].set_xticks(range(len(pivot_n.columns)))
axes[1].set_xticklabels([f"{v:.2f}" for v in pivot_n.columns], color="#888")
axes[1].set_yticks(range(len(pivot_n.index)))
axes[1].set_yticklabels([f"{v:.2f}" for v in pivot_n.index], color="#888")
axes[1].set_xlabel("tx_demand", color="#888")
axes[1].set_ylabel("size_demand", color="#888")
axes[1].set_title("n_D2 alarms / 4 ans", color="white", fontsize=9)
for i in range(len(pivot_n.index)):
    for j in range(len(pivot_n.columns)):
        axes[1].text(j, i, str(pivot_n.values[i,j]),
                     ha="center", va="center", fontsize=7, color="white")
plt.colorbar(im2, ax=axes[1])

plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"Heatmap → {OUT_CHART.name}")
print(f"CSV     → {OUT_CSV.name}")
