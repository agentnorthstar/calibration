"""
Invarians — Backtest ETH
Source : eth_invariants_2020_2024_phi280.csv (BigQuery, Φ=280 blocs, 2020-2024)

Protocole :
  1. Charger les invariants
  2. Calculer EMA fast/slow sur rho_ts et rho_s
  3. Classifier chaque fenêtre : S1D1 | S1D2 | S2D1 | S2D2
  4. Confronter aux événements ground truth
  5. Calculer TPR / FPR / latence de détection
  6. Exporter graphiques + CSV résultats
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ─────────────────────────────────────────────
# PARAMÈTRES ETH (empiriques, confidence: LOW)
# ─────────────────────────────────────────────

CHAIN            = "ethereum"
PHI              = 280
ALPHA_FAST       = 2 / 11       # EMA ~10h  (N=10)
ALPHA_SLOW       = 2 / 721      # EMA ~30j  (N=720)
THRESHOLD_S2     = 1.08         # rhythm_ratio > seuil → S2 (rho_ts)
THRESHOLD_D2     = 1.05         # sigma_ratio  > seuil → D2 (rho_s — ETH ultra-stable)
WARMUP_INV       = 50           # fenêtres ignorées le temps que l'EMA converge

DATA_DIR         = Path(__file__).parent
INPUT_FILE       = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CSV          = DATA_DIR / "eth_backtest_results.csv"
OUT_CHART        = DATA_DIR / "eth_backtest_chart.png"
OUT_DIST         = DATA_DIR / "eth_signal_distributions.png"

# ─────────────────────────────────────────────
# GROUND TRUTH — événements connus ETH
# Chaque événement a un onset (début stress) et une fenêtre de détection
# expected_state : états qui constituent un TP
# ─────────────────────────────────────────────

GROUND_TRUTH = [
    {
        "name"           : "DeFi Summer",
        "onset"          : "2020-06-15",
        "window_end"     : "2020-09-30",
        "expected_states": ["S1D2", "S2D2"],
        "notes"          : "Pic de demande gas / congestion fee. Signal π attendu.",
    },
    {
        "name"           : "NFT Mania",
        "onset"          : "2021-03-01",
        "window_end"     : "2021-05-30",
        "expected_states": ["S1D2", "S2D2"],
        "notes"          : "CryptoPunks / Bored Apes. Congestion fee. Signal π.",
    },
    {
        "name"           : "The Merge",
        "onset"          : "2022-09-14",
        "window_end"     : "2022-09-17",
        "expected_states": ["S2D1", "S2D2"],
        "notes"          : "Transition PoW→PoS. Stress structurel τ sans surge π. Cas S2D1 canonique.",
    },
    {
        "name"           : "Shanghai Upgrade",
        "onset"          : "2023-04-12",
        "window_end"     : "2023-04-15",
        "expected_states": ["S2D1", "S1D2", "S2D2"],
        "notes"          : "Activation withdrawals. Perturbation possible τ.",
    },
]

# ─────────────────────────────────────────────
# 1. CHARGEMENT
# ─────────────────────────────────────────────

print(f"\n[1] Chargement {INPUT_FILE.name} ...")
df = pd.read_csv(INPUT_FILE)
df = df.sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

# ─────────────────────────────────────────────
# 2. EMA SÉQUENTIELLES
# ─────────────────────────────────────────────

print("[2] Calcul EMA fast/slow ...")

def ema_seq(series: pd.Series, alpha: float) -> pd.Series:
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

df["ema_fast_rho_ts"]  = ema_seq(df["rho_ts"], ALPHA_FAST)
df["ema_slow_rho_ts"]  = ema_seq(df["rho_ts"], ALPHA_SLOW)
df["ema_fast_rho_s"]   = ema_seq(df["rho_s"],  ALPHA_FAST)
df["ema_slow_rho_s"]   = ema_seq(df["rho_s"],  ALPHA_SLOW)

# ─────────────────────────────────────────────
# 3. RATIOS + CLASSIFICATION
# ─────────────────────────────────────────────

print("[3] Classification ...")

df["rhythm_ratio"]  = df["rho_ts"] / df["ema_fast_rho_ts"]
df["sigma_ratio"]   = df["rho_s"]  / df["ema_fast_rho_s"]

# Ignorer warmup
df.loc[:WARMUP_INV, "rhythm_ratio"] = np.nan
df.loc[:WARMUP_INV, "sigma_ratio"]  = np.nan

df["tau_state"] = np.where(df["rhythm_ratio"] >= THRESHOLD_S2, "S2", "S1")
df["pi_state"]  = np.where(df["sigma_ratio"]  >= THRESHOLD_D2, "D2", "D1")
df["state"]     = df["tau_state"] + df["pi_state"]

# Distribution des états
state_counts = df["state"].value_counts()
total = len(df) - WARMUP_INV
print(f"\n    Distribution des états (hors warmup) :")
for s, n in state_counts.items():
    print(f"      {s:5s}  {n:5d}  ({n/total*100:.1f}%)")

# ─────────────────────────────────────────────
# 4. CONFRONTATION GROUND TRUTH
# ─────────────────────────────────────────────

print("\n[4] Confrontation ground truth ...")

results = []
for evt in GROUND_TRUTH:
    onset    = pd.Timestamp(evt["onset"],      tz="UTC")
    win_end  = pd.Timestamp(evt["window_end"], tz="UTC")
    expected = evt["expected_states"]

    # Fenêtre de détection : onset → window_end
    mask_window = (df["dt"] >= onset) & (df["dt"] <= win_end)
    window_df   = df[mask_window]

    # Fenêtre pre-onset : 24h avant → onset (pour mesurer le bruit)
    mask_pre = (df["dt"] >= onset - pd.Timedelta(hours=24)) & (df["dt"] < onset)
    pre_df   = df[mask_pre]

    detected = window_df[window_df["state"].isin(expected)]

    if len(detected) > 0:
        first_det = detected["dt"].iloc[0]
        latency_h = (first_det - onset).total_seconds() / 3600
        tp = True
    else:
        first_det = None
        latency_h = None
        tp = False

    # Ratio de détection dans la fenêtre
    detect_ratio = len(detected) / len(window_df) if len(window_df) > 0 else 0

    result = {
        "event"          : evt["name"],
        "onset"          : evt["onset"],
        "tp"             : tp,
        "latency_h"      : round(latency_h, 1) if latency_h is not None else None,
        "first_detection": first_det.isoformat() if first_det else None,
        "detect_ratio"   : round(detect_ratio, 3),
        "n_window"       : len(window_df),
        "n_detected"     : len(detected),
        "expected_states": str(expected),
        "notes"          : evt["notes"],
    }
    results.append(result)

    status = "✅ TP" if tp else "❌ FN"
    lat_str = f"latence {latency_h:.1f}h" if latency_h is not None else "non détecté"
    print(f"    {status}  {evt['name']:25s}  {lat_str}  (ratio {detect_ratio:.0%} dans la fenêtre)")

# ─────────────────────────────────────────────
# 5. FPR — BRUIT EN DEHORS DES ÉVÉNEMENTS
# ─────────────────────────────────────────────

# Masque "hors événements ground truth"
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    onset   = pd.Timestamp(evt["onset"],      tz="UTC")
    win_end = pd.Timestamp(evt["window_end"], tz="UTC")
    mask_event |= (df["dt"] >= onset) & (df["dt"] <= win_end)

df_normal = df[~mask_event & (df.index > WARMUP_INV)]
stress_states = ["S2D1", "S2D2", "S1D2"]
fpr = df_normal["state"].isin(stress_states).mean()
n_false_alarms = df_normal["state"].isin(stress_states).sum()

print(f"\n    FPR hors événements : {fpr:.2%}  ({n_false_alarms} fausses alarmes / {len(df_normal)} fenêtres normales)")
print(f"    threshold_s2={THRESHOLD_S2}  threshold_d2={THRESHOLD_D2}")

# ─────────────────────────────────────────────
# 6. EXPORT CSV RÉSULTATS
# ─────────────────────────────────────────────

res_df = pd.DataFrame(results)
res_df.to_csv(OUT_CSV, index=False)
tpr = sum(r["tp"] for r in results) / len(results)
print(f"\n    TPR = {tpr:.0%}  |  FPR = {fpr:.2%}")
print(f"    Résultats exportés → {OUT_CSV.name}")

# ─────────────────────────────────────────────
# 7. GRAPHIQUES
# ─────────────────────────────────────────────

print("\n[5] Génération graphiques ...")

STATE_COLORS = {"S1D1": "#1a3a1a", "S1D2": "#4a7c59", "S2D1": "#c47a1e", "S2D2": "#8b1a1a"}

# ── Chart 1 : Timeline rho_ts + sigma_ratio + états ──────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(18, 10), sharex=True,
                          facecolor="#080A09")
fig.suptitle("Invarians — Backtest ETH 2020–2024", color="white", fontsize=13, y=0.98)

for ax in axes:
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#222")

ax1, ax2, ax3 = axes

# rho_ts + EMA
ax1.plot(df["dt"], df["rho_ts"],         color="#444",   linewidth=0.4, alpha=0.8, label="rho_ts")
ax1.plot(df["dt"], df["ema_fast_rho_ts"], color="#5b9bd5", linewidth=1.0, label="EMA fast")
ax1.plot(df["dt"], df["ema_slow_rho_ts"], color="#e8a020", linewidth=0.8, linestyle="--", label="EMA slow")
ax1.set_ylabel("rho_ts (s)", color="#888", fontsize=8)
ax1.legend(fontsize=7, loc="upper right", facecolor="#111", labelcolor="white")
ax1.axhline(y=df["ema_fast_rho_ts"].median() * THRESHOLD_S2,
            color="#c47a1e", linewidth=0.6, linestyle=":", alpha=0.6)

# sigma_ratio
ax2.plot(df["dt"], df["sigma_ratio"], color="#5b9bd5", linewidth=0.6, label="sigma_ratio")
ax2.axhline(y=THRESHOLD_D2, color="#8b1a1a", linewidth=0.8, linestyle="--", label=f"threshold_d2={THRESHOLD_D2}")
ax2.axhline(y=1.0, color="#333", linewidth=0.5)
ax2.set_ylabel("sigma_ratio", color="#888", fontsize=8)
ax2.legend(fontsize=7, loc="upper right", facecolor="#111", labelcolor="white")

# États (scatter coloré)
state_map = {"S1D1": 0, "S1D2": 1, "S2D1": 2, "S2D2": 3}
for state, color in STATE_COLORS.items():
    mask = df["state"] == state
    if mask.any():
        ax3.scatter(df.loc[mask, "dt"], [state_map[state]] * mask.sum(),
                    c=color, s=1.5, alpha=0.8, label=state)
ax3.set_yticks([0, 1, 2, 3])
ax3.set_yticklabels(["S1D1", "S1D2", "S2D1", "S2D2"], color="white", fontsize=7)
ax3.set_ylabel("État", color="#888", fontsize=8)
ax3.legend(fontsize=7, loc="upper right", facecolor="#111", labelcolor="white",
           markerscale=4)

# Annotations événements ground truth
for evt in GROUND_TRUTH:
    onset = pd.Timestamp(evt["onset"], tz="UTC")
    for ax in axes:
        ax.axvline(x=onset, color="#ffffff", linewidth=0.7, linestyle="--", alpha=0.4)
    ax1.text(onset, ax1.get_ylim()[1] * 0.95, evt["name"],
             color="#aaa", fontsize=6, rotation=90, va="top", ha="right")

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"    Chart sauvegardé → {OUT_CHART.name}")

# ── Chart 2 : Distributions des signaux ──────────────────────────────────────
fig2, axes2 = plt.subplots(1, 3, figsize=(15, 4), facecolor="#080A09")
fig2.suptitle("Invarians ETH — Distributions rho_ts / rho_s / rhythm_ratio", color="white", fontsize=11)

labels = ["rho_ts (s)", "rho_s (%)", "rhythm_ratio"]
cols   = ["rho_ts", "rho_s", "rhythm_ratio"]
vlines = [None, None, THRESHOLD_S2]

for ax, col, label, vline in zip(axes2, cols, labels, vlines):
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#222")
    data = df[col].dropna()
    ax.hist(data, bins=100, color="#5b9bd5", alpha=0.7, edgecolor="none")
    if vline:
        ax.axvline(x=vline, color="#c47a1e", linewidth=1.2, linestyle="--",
                   label=f"threshold={vline}")
        ax.legend(fontsize=7, facecolor="#111", labelcolor="white")
    # percentiles
    for p, pct in [(0.85, "#888"), (0.95, "#aaa"), (0.99, "#ccc")]:
        v = data.quantile(p)
        ax.axvline(x=v, color=pct, linewidth=0.7, linestyle=":")
        ax.text(v, ax.get_ylim()[1] * 0.5, f"p{int(p*100)}={v:.3f}",
                color=pct, fontsize=6, rotation=90, va="center")
    ax.set_xlabel(label, color="#888", fontsize=8)
    ax.set_ylabel("count", color="#888", fontsize=8)

plt.tight_layout()
plt.savefig(OUT_DIST, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"    Distributions sauvegardées → {OUT_DIST.name}")

# ─────────────────────────────────────────────
# RÉSUMÉ FINAL
# ─────────────────────────────────────────────

print(f"""
╔══════════════════════════════════════════════════════╗
║  BACKTEST ETH 2020–2024 — RÉSUMÉ
╠══════════════════════════════════════════════════════╣
║  Invariants analysés : {len(df):>6,}  (Φ=280, ~1h/inv)
║  Paramètres          : S2={THRESHOLD_S2}  D2={THRESHOLD_D2}
║  EMA fast α          : {ALPHA_FAST:.4f}  (~10h)
║  EMA slow α          : {ALPHA_SLOW:.5f} (~30j)
╠══════════════════════════════════════════════════════╣
║  TPR (événements détectés) : {tpr:.0%}  ({sum(r['tp'] for r in results)}/{len(results)})
║  FPR (fausses alarmes)     : {fpr:.2%}
╠══════════════════════════════════════════════════════╣""")
for r in results:
    status = "✅" if r["tp"] else "❌"
    lat = f"{r['latency_h']:+.1f}h" if r["latency_h"] is not None else "—"
    print(f"║  {status} {r['event']:28s} lat={lat:>8s}  det={r['detect_ratio']:.0%}")
print(f"╚══════════════════════════════════════════════════════╝")
