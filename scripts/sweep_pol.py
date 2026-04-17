"""
Invarians — Sweep threshold_s2 Polygon
Phase A : sweep rhythm_p90 (threshold_s2)
Phase B : vérification continuity_p10 (c_s distribution)
Objectif : FPR < 1.5%, TPR max sur événements structurels connus
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "pol_invariants_2020_2024_phi1800.csv"
OUT_CHART  = DATA_DIR / "pol_sweep_chart.png"

ALPHA_FAST      = 2 / 11
THRESHOLD_SIGMA = 1.13594   # P95 initial — fixé pour Phase A
THRESHOLD_SIZE  = 1.17667   # P95 initial — fixé pour Phase A
THRESHOLD_TX    = 1.23474   # P95 initial — fixé pour Phase A
WARMUP_INV      = 50

# Événements structurels (τ) — attendus S2Dx
GROUND_TRUTH_TAU = [
    {"name": "Network Halt Mars 2021", "onset": "2021-03-11", "window_end": "2021-03-12",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Heimdall/Bor Jan 2023",  "onset": "2023-01-16", "window_end": "2023-01-18",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Reorg Storm Feb 2023",   "onset": "2023-02-22", "window_end": "2023-02-25",
     "expected": ["S2D1", "S2D2"]},
]

# Tous les événements (pour FPR combiné)
GROUND_TRUTH_ALL = [
    {"name": "Network Halt Mars 2021", "onset": "2021-03-11", "window_end": "2021-03-12",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Gas Crisis Mai 2021",    "onset": "2021-05-01", "window_end": "2021-06-30",
     "expected": ["S1D2", "S2D2"]},
    {"name": "Heimdall/Bor Jan 2023",  "onset": "2023-01-16", "window_end": "2023-01-18",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Reorg Storm Feb 2023",   "onset": "2023-02-22", "window_end": "2023-02-25",
     "expected": ["S2D1", "S2D2"]},
]

# Seuils à tester — Phase A
THRESHOLDS_S2 = [1.02, 1.03, 1.04, 1.05, 1.06, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20]

# ── Chargement + EMA ────────────────────────────────────────────────────────
print("[1] Chargement données ...")
df = pd.read_csv(INPUT_FILE).sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

print("[2] Calcul EMA ...")
df["ema_rho_ts"] = ema_seq(df["rho_ts"],       ALPHA_FAST)
df["ema_rho_s"]  = ema_seq(df["rho_s"],        ALPHA_FAST)
df["ema_size"]   = ema_seq(df["size_avg"],     ALPHA_FAST)
df["ema_tx"]     = ema_seq(df["tx_count_avg"], ALPHA_FAST)

df["rhythm_ratio"] = df["rho_ts"]       / df["ema_rho_ts"]
df["sigma_ratio"]  = df["rho_s"]        / df["ema_rho_s"]
df["size_ratio"]   = df["size_avg"]     / df["ema_size"]
df["tx_ratio"]     = df["tx_count_avg"] / df["ema_tx"]
df.loc[:WARMUP_INV, ["rhythm_ratio", "sigma_ratio", "size_ratio", "tx_ratio"]] = np.nan

# π fixe (pour calcul FPR combiné pendant Phase A)
df["sigma_dim"] = (df["sigma_ratio"] >= THRESHOLD_SIGMA).astype(int)
df["size_dim"]  = (df["size_ratio"]  >= THRESHOLD_SIZE).astype(int)
df["tx_dim"]    = (df["tx_ratio"]    >= THRESHOLD_TX).astype(int)
df["d2_dims"]   = df["sigma_dim"] + df["size_dim"] + df["tx_dim"]
df["pi_state"]  = np.where(df["d2_dims"] >= 2, "D2", "D1")

# Masque événements (tous)
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH_ALL:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"],      tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
df_normal = df[~mask_event & (df.index > WARMUP_INV)]

# ── PHASE A — Sweep rhythm_p90 ───────────────────────────────────────────────
print(f"\n[3] PHASE A — Sweep threshold_s2 ...")
print(f"\n{'threshold_s2':>14} {'FPR':>8} {'Halt':>8} {'Heimdall':>10} {'Reorg':>8} {'lat_halt':>10}")
print("─" * 65)

rows_a = []
for thr in THRESHOLDS_S2:
    df["tau_state"] = np.where(df["rhythm_ratio"] >= thr, "S2", "S1")
    df["state"]     = df["tau_state"] + df["pi_state"]

    fpr = df.loc[df_normal.index, "state"].isin(["S2D1", "S2D2", "S1D2"]).mean()

    evt_res = {}
    lat_halt = None
    for evt in GROUND_TRUTH_ALL:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
        det     = window[window["state"].isin(evt["expected"])]
        evt_res[evt["name"]] = bool(len(det))
        if evt["name"] == "Network Halt Mars 2021" and len(det):
            lat_halt = (det["dt"].iloc[0] - onset).total_seconds() / 3600

    h = "✅" if evt_res["Network Halt Mars 2021"] else "❌"
    b = "✅" if evt_res["Heimdall/Bor Jan 2023"]  else "❌"
    r = "✅" if evt_res["Reorg Storm Feb 2023"]   else "❌"
    lat_str = f"+{lat_halt:.1f}h" if lat_halt is not None else "—"

    print(f"{thr:>14.4f} {fpr:>7.2%} {h:>8} {b:>10} {r:>8} {lat_str:>10}")
    rows_a.append({
        "threshold_s2": thr, "fpr": round(fpr, 4),
        "halt": evt_res["Network Halt Mars 2021"],
        "heimdall": evt_res["Heimdall/Bor Jan 2023"],
        "reorg": evt_res["Reorg Storm Feb 2023"],
        "lat_halt_h": round(lat_halt, 1) if lat_halt else None,
    })

# ── PHASE B — Distribution c_s ───────────────────────────────────────────────
print(f"\n[4] PHASE B — Distribution c_s (continuity) ...")
cs = df["c_s"].dropna()
for p in [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]:
    print(f"    p{int(p*100):02d} = {cs.quantile(p):.6f}")

if cs.quantile(.10) > 0.99:
    print("\n    ✅ c_s invariant ~1.0 → continuity_p10 = null")
else:
    print(f"\n    ⚠️  c_s variance significative (p10={cs.quantile(.10):.4f}) — sweep continuity requis")
    print("    → Relancer avec sweep continuity_p10 [0.80 → 0.98]")

# ── RECOMMANDATION ───────────────────────────────────────────────────────────
print(f"\n[5] RECOMMANDATION :")
candidates = [(r for r in rows_a if r["halt"] and r["heimdall"] and r["reorg"])]
best = None
for r in rows_a:
    if r["halt"] and r["heimdall"] and r["reorg"]:
        if best is None or r["fpr"] < best["fpr"]:
            best = r

if best:
    print(f"    threshold_s2 recommandé : {best['threshold_s2']}")
    print(f"    FPR τ seul              : {best['fpr']:.2%}")
    print(f"    TPR τ                   : 3/3 événements structurels")
else:
    # Fallback : max TPR
    max_tp = max(int(r["halt"]) + int(r["heimdall"]) + int(r["reorg"]) for r in rows_a)
    candidates_fallback = [r for r in rows_a
                           if int(r["halt"]) + int(r["heimdall"]) + int(r["reorg"]) == max_tp]
    best = min(candidates_fallback, key=lambda r: r["fpr"])
    print(f"    ⚠️  TPR < 3/3 — meilleur compromis : threshold_s2={best['threshold_s2']}")
    print(f"    FPR : {best['fpr']:.2%}  |  TPR : {max_tp}/3")

# ── GRAPHIQUE ─────────────────────────────────────────────────────────────────
print("\n[6] Génération graphique ...")

fig, ax = plt.subplots(figsize=(12, 5), facecolor="#080A09")
ax.set_facecolor("#0d0d0d")
ax.tick_params(colors="#888", labelsize=8)
for spine in ax.spines.values():
    spine.set_edgecolor("#222")

thrs  = [r["threshold_s2"] for r in rows_a]
fprs  = [r["fpr"] * 100    for r in rows_a]
tprs  = [(int(r["halt"]) + int(r["heimdall"]) + int(r["reorg"])) / 3 * 100 for r in rows_a]

ax.plot(thrs, fprs, color="#e8a020", linewidth=2, marker="o", markersize=5, label="FPR (%)")
ax.plot(thrs, tprs, color="#5b9bd5", linewidth=2, marker="s", markersize=5, label="TPR (%)")
ax.axhline(y=1.5, color="#8b1a1a", linewidth=1, linestyle="--", alpha=0.6, label="FPR target 1.5%")

if best:
    ax.axvline(x=best["threshold_s2"], color="#ffffff", linewidth=1, linestyle=":",
               alpha=0.6, label=f"optimum={best['threshold_s2']}")

ax.set_xlabel("threshold_s2 (rhythm_p90)", color="#888", fontsize=9)
ax.set_ylabel("%", color="#888", fontsize=9)
ax.set_title("Polygon — Sweep threshold_s2 : FPR / TPR", color="white", fontsize=11)
ax.legend(fontsize=8, facecolor="#111", labelcolor="white")

plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"    Graphique → {OUT_CHART.name}")
