"""
Invarians — M1 Stability Score — Ethereum
==========================================
Formula (methodology.md §10.1):

    M1 = amplitude_dynamique / bruit_baseline

    amplitude_dynamique = (max_event − p50) / p50
        max_event : maximum of rhythm_ratio during the best ground truth event
        p50       : median of rhythm_ratio over the full backtest

    bruit_baseline = std(signal) / mean(signal)
        computed on windows where rhythm_ratio < 1.05 (strict nominal regime)

Signal   : rhythm_ratio = rho_ts / EMA_fast(rho_ts)
Chain    : Ethereum
Input    : eth_invariants_2020_2024_phi280.csv
Expected : M1 ≈ 5.07  (published on AgentNorthStar.com)

Verification (session 17 April 2026):
    max_event = 1.1548  (The Merge, 15 Sept 2022)
    p50       = 0.9993
    amplitude = (1.1548 − 0.9993) / 0.9993 = 0.1556
    bruit     = 0.0307
    M1        = 0.1556 / 0.0307 = 5.07
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
# PARAMETERS
# ─────────────────────────────────────────────

CHAIN        = "ethereum"
ALPHA_FAST   = 2 / 11       # EMA ~10h  (N=10)
WARMUP_INV   = 50           # windows discarded for EMA convergence
NOMINAL_CAP  = 1.05         # rhythm_ratio < this = nominal regime for noise calc

DATA_DIR     = Path(__file__).parent
INPUT_FILE   = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_CSV      = DATA_DIR / "eth_m1_results.csv"

# Ground truth events — used to find max_event
# M1 ETH is computed on the τ signal (rhythm_ratio = structural stress).
# Only S2D1 events (structural stress) are relevant for τ M1.
# DeFi Summer / NFT Mania are S1D2 (demand only) — excluded from τ M1.
GROUND_TRUTH = [
    {"name": "The Merge",         "onset": "2022-09-14", "window_end": "2022-09-17"},
    {"name": "Shanghai Upgrade",  "onset": "2023-04-12", "window_end": "2023-04-15"},
]

# ─────────────────────────────────────────────
# 1. LOAD
# ─────────────────────────────────────────────

print(f"\n[1] Loading {INPUT_FILE.name} ...")
df = pd.read_csv(INPUT_FILE)
df = df.sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

# ─────────────────────────────────────────────
# 2. EMA + SIGNAL
# ─────────────────────────────────────────────

print("[2] Computing EMA_fast and rhythm_ratio ...")

def ema_seq(series: pd.Series, alpha: float) -> pd.Series:
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

df["ema_fast_rho_ts"] = ema_seq(df["rho_ts"], ALPHA_FAST)
df["rhythm_ratio"]    = df["rho_ts"] / df["ema_fast_rho_ts"]

# Discard warmup
df.loc[:WARMUP_INV, "rhythm_ratio"] = np.nan
df_clean = df.dropna(subset=["rhythm_ratio"])

# ─────────────────────────────────────────────
# 3. M1 COMPONENTS
# ─────────────────────────────────────────────

print("[3] Computing M1 components ...")

# p50 — median over full backtest (post-warmup)
p50 = df_clean["rhythm_ratio"].median()

# bruit_baseline — CV on nominal windows (ratio < NOMINAL_CAP)
nominal = df_clean[df_clean["rhythm_ratio"] < NOMINAL_CAP]["rhythm_ratio"]
bruit   = nominal.std() / nominal.mean()

print(f"\n    p50          : {p50:.4f}")
print(f"    nominal windows : {len(nominal):,} (rhythm_ratio < {NOMINAL_CAP})")
print(f"    bruit (CV)   : {bruit:.4f}")

# ─────────────────────────────────────────────
# 4. MAX_EVENT — per ground truth event
# ─────────────────────────────────────────────

print("\n[4] Finding max_event per ground truth event ...")

event_results = []
for evt in GROUND_TRUTH:
    onset   = pd.Timestamp(evt["onset"],      tz="UTC")
    win_end = pd.Timestamp(evt["window_end"], tz="UTC")
    mask    = (df_clean["dt"] >= onset) & (df_clean["dt"] <= win_end)
    subset  = df_clean.loc[mask, "rhythm_ratio"]
    if len(subset) == 0:
        max_val = None
        print(f"    {evt['name']:25s}  → NO DATA in window")
    else:
        max_val = subset.max()
        amplitude = (max_val - p50) / p50
        m1_evt    = amplitude / bruit
        print(f"    {evt['name']:25s}  max={max_val:.4f}  amplitude={amplitude:.4f}  M1={m1_evt:.2f}")
    event_results.append({
        "event":     evt["name"],
        "max_ratio": max_val,
    })

# ─────────────────────────────────────────────
# 5. FINAL M1 — best event (highest max_event)
# ─────────────────────────────────────────────

valid = [(r["event"], r["max_ratio"]) for r in event_results if r["max_ratio"] is not None]
best_name, best_max = max(valid, key=lambda x: x[1])

amplitude_final = (best_max - p50) / p50
m1_final        = amplitude_final / bruit

print(f"\n[5] Final M1 — best event: {best_name}")
print(f"    max_event  : {best_max:.4f}")
print(f"    p50        : {p50:.4f}")
print(f"    amplitude  : {amplitude_final:.4f}")
print(f"    bruit      : {bruit:.4f}")
print(f"\n    ✅  M1 = {m1_final:.2f}  (published: 5.07)")

# ─────────────────────────────────────────────
# 6. EXPORT
# ─────────────────────────────────────────────

results_df = pd.DataFrame([{
    "chain":           CHAIN,
    "signal":          "rhythm_ratio",
    "best_event":      best_name,
    "max_event":       round(best_max, 4),
    "p50":             round(p50, 4),
    "amplitude":       round(amplitude_final, 4),
    "bruit_cv":        round(bruit, 4),
    "m1":              round(m1_final, 2),
    "m1_published":    5.07,
    "match":           abs(m1_final - 5.07) < 0.1,
}])

results_df.to_csv(OUT_CSV, index=False)
print(f"\n[6] Results saved → {OUT_CSV.name}")
