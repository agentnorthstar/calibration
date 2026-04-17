"""
Invarians — Sweep τ Solana (rhythm_p90 + continuity_p10)

Solana a deux signaux structurels OR-combinés :
  struct_stress = rhythm_ratio > threshold_s2  OR  c_s < continuity_p10

Phase A : sweep threshold_s2 seul (continuity_p10 fixé haut = déactivé)
Phase B : sweep continuity_p10 seul (threshold_s2 fixé à valeur Phase A)
Phase C : vérification combinée optimale

Événements structurels cibles :
  - Outage Sept 2021 (~17h)  → S2D1
  - Outage Jan  2022 (~4h)   → S2D1
  - Outage Mai  2022 (~4.5h) → S2D1
  - Outage Oct  2022 (~8h)   → S2D1

Input  : sol_invariants_2021_2024_phi800.csv
Output : sol_sweep_chart.png + sol_sweep_results.csv
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "sol_invariants_2021_2024_phi800.csv"
OUT_CHART  = DATA_DIR / "sol_sweep_chart.png"
OUT_CSV    = DATA_DIR / "sol_sweep_results.csv"

ALPHA_FAST = 2 / 11
WARMUP_INV = 50

# Phase A : sweep rhythm_p90, continuity désactivée (valeur très haute)
THRESHOLDS_S2      = [1.01, 1.02, 1.03, 1.04, 1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20]
CONTINUITY_FIXED   = 0.50   # P10 très bas = pratiquement désactivé pour Phase A

# Phase B : sweep continuity_p10, threshold_s2 fixé après Phase A
# (sera remplacé au runtime par le résultat de Phase A)
THRESHOLDS_CONT    = [0.80, 0.85, 0.88, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98]

# Événements structurels uniquement pour τ
STRUCTURAL_EVENTS = [
    {"name": "Outage Sept 2021",  "onset": "2021-09-14", "window_end": "2021-09-17"},
    {"name": "Outage Jan 2022",   "onset": "2022-01-21", "window_end": "2022-01-22"},
    {"name": "Outage Mai 2022",   "onset": "2022-05-31", "window_end": "2022-06-01"},
    {"name": "Outage Oct 2022",   "onset": "2022-10-01", "window_end": "2022-10-02"},
]

# ── Chargement + gaps + EMA ───────────────────────────────────────────────────
print("[1] Chargement + remplissage gaps ...")
df = pd.read_csv(INPUT_FILE).sort_values("window_id").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)

all_win = pd.DataFrame({"window_id": range(df["window_id"].min(),
                                           df["window_id"].max() + 1)})
df = all_win.merge(df, on="window_id", how="left")
df["rho_ts"]       = df["rho_ts"].fillna(999.0)
df["c_s"]          = df["c_s"].fillna(0.0)
df["dt"]           = pd.to_datetime(
    df["window_start"].fillna(df["window_id"] * 800 * 0.4), unit="s", utc=True
)
df["inv_idx"] = np.arange(len(df))

def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0] if not pd.isna(series.iloc[0]) else 1.0
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        v = arr[i]
        result[i] = (alpha * v + (1 - alpha) * result[i - 1]) if not pd.isna(v) else result[i - 1]
    return pd.Series(result, index=series.index)

print("[2] Calcul EMA rho_ts ...")
rho_ts_capped = df["rho_ts"].clip(upper=5.0)
df["ema_rho_ts"]   = ema_seq(rho_ts_capped, ALPHA_FAST)
df["rhythm_ratio"] = df["rho_ts"].clip(upper=20.0) / df["ema_rho_ts"]
df.loc[:WARMUP_INV, "rhythm_ratio"] = np.nan

valid = df.index > WARMUP_INV

# Masques événements
mask_evt = pd.Series(False, index=df.index)
for evt in STRUCTURAL_EVENTS:
    mask_evt |= (df["dt"] >= pd.Timestamp(evt["onset"],      tz="UTC")) & \
                (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
normal_idx = df[~mask_evt & valid].index

# ── Distributions des signaux en conditions normales ──────────────────────────
print("\n[3] Distributions signaux normaux :")
for col in ["rhythm_ratio", "c_s"]:
    s = df.loc[normal_idx, col].dropna()
    print(f"   {col:15s}  p50={s.quantile(.50):.4f}  p90={s.quantile(.90):.4f}  "
          f"p95={s.quantile(.95):.4f}  p99={s.quantile(.99):.4f}  "
          f"p10={s.quantile(.10):.4f}")

# ── Phase A : sweep threshold_s2 ─────────────────────────────────────────────
print(f"\n[4] Phase A — Sweep threshold_s2 (continuity_p10={CONTINUITY_FIXED} désactivé)")
print(f"\n{'threshold_s2':>14} {'FPR_τ':>8} {'n_S2':>8} " +
      "  ".join(f"{e['name'][:12]:>14}" for e in STRUCTURAL_EVENTS))
print("─" * 100)

rows_a = []
for ts2 in THRESHOLDS_S2:
    # struct_stress = rhythm_ratio > ts2 OR c_s < CONTINUITY_FIXED (≈ jamais)
    df["tau_s2"] = ((df["rhythm_ratio"] > ts2) | (df["c_s"] < CONTINUITY_FIXED)).astype(int)
    df.loc[:WARMUP_INV, "tau_s2"] = 0

    fpr_tau = df.loc[normal_idx, "tau_s2"].mean()
    n_s2    = df.loc[valid, "tau_s2"].sum()

    det_list = []
    latencies = []
    for evt in STRUCTURAL_EVENTS:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end) & (df["tau_s2"] == 1)]
        det = len(window) > 0
        det_list.append(det)
        if det:
            lat_h = (window["dt"].min() - onset).total_seconds() / 3600
            latencies.append(lat_h)
        else:
            latencies.append(None)

    symbols = ["✅" if d else "❌" for d in det_list]
    lat_str = "  ".join(f"{'✅' if d else '❌'} {f'+{l:.1f}h' if l is not None else '    ':>6}"
                         for d, l in zip(det_list, latencies))
    print(f"   {ts2:12.3f} {fpr_tau:>7.2%} {n_s2:>8}  {lat_str}")
    rows_a.append({
        "phase": "A_s2",
        "param": ts2,
        "fpr": round(fpr_tau, 4),
        "n_s2": int(n_s2),
        **{evt["name"]: det for evt, det in zip(STRUCTURAL_EVENTS, det_list)},
        **{f"latency_{evt['name']}": lat for evt, lat in zip(STRUCTURAL_EVENTS, latencies)},
    })

# ── Sélection automatique valeur Phase A ─────────────────────────────────────
# Meilleure valeur : toutes détections + FPR < 3%
best_a = None
for r in sorted(rows_a, key=lambda x: x["fpr"]):
    all_det = all(r[e["name"]] for e in STRUCTURAL_EVENTS)
    if all_det and r["fpr"] < 0.05:
        if best_a is None or r["fpr"] < best_a["fpr"]:
            best_a = r
if best_a is None:
    # Relaxer : au moins 3 sur 4
    for r in sorted(rows_a, key=lambda x: -sum(x.get(e["name"], False) for e in STRUCTURAL_EVENTS)):
        if r["fpr"] < 0.05:
            best_a = r
            break

if best_a:
    THRESHOLD_S2_OPT = best_a["param"]
    print(f"\n→ Phase A : threshold_s2 retenu = {THRESHOLD_S2_OPT} (FPR_τ={best_a['fpr']:.2%})")
else:
    THRESHOLD_S2_OPT = THRESHOLDS_S2[len(THRESHOLDS_S2)//2]
    print(f"\n→ Phase A : aucun seuil optimal trouvé automatiquement, utiliser {THRESHOLD_S2_OPT}")

# ── Phase B : sweep continuity_p10 ───────────────────────────────────────────
print(f"\n[5] Phase B — Sweep continuity_p10 (threshold_s2={THRESHOLD_S2_OPT} fixé)")
print(f"\n{'continuity_p10':>15} {'FPR_τ':>8} {'n_S2':>8} " +
      "  ".join(f"{e['name'][:12]:>14}" for e in STRUCTURAL_EVENTS))
print("─" * 100)

rows_b = []
for cp10 in THRESHOLDS_CONT:
    df["tau_s2"] = ((df["rhythm_ratio"] > THRESHOLD_S2_OPT) | (df["c_s"] < cp10)).astype(int)
    df.loc[:WARMUP_INV, "tau_s2"] = 0

    fpr_tau = df.loc[normal_idx, "tau_s2"].mean()
    n_s2    = df.loc[valid, "tau_s2"].sum()

    det_list = []
    latencies = []
    for evt in STRUCTURAL_EVENTS:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end) & (df["tau_s2"] == 1)]
        det = len(window) > 0
        det_list.append(det)
        latencies.append((window["dt"].min() - onset).total_seconds() / 3600 if det else None)

    lat_str = "  ".join(f"{'✅' if d else '❌'} {f'+{l:.1f}h' if l is not None else '    ':>6}"
                         for d, l in zip(det_list, latencies))
    print(f"   {cp10:13.3f} {fpr_tau:>7.2%} {n_s2:>8}  {lat_str}")
    rows_b.append({
        "phase": "B_continuity",
        "param": cp10,
        "fpr": round(fpr_tau, 4),
        "n_s2": int(n_s2),
        **{evt["name"]: det for evt, det in zip(STRUCTURAL_EVENTS, det_list)},
    })

# ── Sauvegarde ────────────────────────────────────────────────────────────────
sweep_df = pd.DataFrame(rows_a + rows_b)
sweep_df.to_csv(OUT_CSV, index=False)

# ── Graphique ─────────────────────────────────────────────────────────────────
print("\n[6] Génération graphique ...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor="#080A09")
fig.suptitle("Solana — Sweep τ : rhythm_p90 (Phase A) + continuity_p10 (Phase B)",
             color="white", fontsize=11)

for ax in axes:
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=8)
    for s in ax.spines.values(): s.set_edgecolor("#222")

# Phase A
pa = [r for r in rows_a]
xs_a = [r["param"] for r in pa]
fprs_a = [r["fpr"] * 100 for r in pa]
axes[0].plot(xs_a, fprs_a, color="#55aaff", lw=1.5, marker="o", ms=4)
axes[0].axhline(1.5, color="#ff5555", lw=0.8, ls="--", label="FPR cible 1.5%")
axes[0].axhline(3.0, color="#ffaa55", lw=0.8, ls="--", label="FPR cible 3.0%")
if best_a:
    axes[0].axvline(THRESHOLD_S2_OPT, color="#55ff55", lw=1.0, ls="--",
                    label=f"retenu={THRESHOLD_S2_OPT}")
axes[0].set_xlabel("threshold_s2 (rhythm_ratio)", color="#888")
axes[0].set_ylabel("FPR τ (%)", color="#888")
axes[0].set_title("Phase A — sweep rhythm_p90", color="white", fontsize=9)
axes[0].legend(fontsize=7, facecolor="#222", labelcolor="white")

# Phase B
pb = [r for r in rows_b]
xs_b = [r["param"] for r in pb]
fprs_b = [r["fpr"] * 100 for r in pb]
axes[1].plot(xs_b, fprs_b, color="#55ffaa", lw=1.5, marker="o", ms=4)
axes[1].axhline(1.5, color="#ff5555", lw=0.8, ls="--", label="FPR cible 1.5%")
axes[1].axhline(3.0, color="#ffaa55", lw=0.8, ls="--")
axes[1].set_xlabel("continuity_p10 (c_s minimum)", color="#888")
axes[1].set_ylabel("FPR τ (%)", color="#888")
axes[1].set_title("Phase B — sweep continuity_p10", color="white", fontsize=9)
axes[1].invert_xaxis()
axes[1].legend(fontsize=7, facecolor="#222", labelcolor="white")

plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"Chart → {OUT_CHART.name}")
print(f"CSV   → {OUT_CSV.name}")
print("\nSweep τ terminé. Lance sweep_sol_d2.py pour calibrer π.")
