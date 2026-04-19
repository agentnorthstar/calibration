"""
Invarians — M1 Stability Score — Polygon
=========================================
Formula (methodology.md §10.1):

    M1 = amplitude_dynamique / bruit_baseline

    amplitude_dynamique = (max_event − p50) / p50
        max_event : maximum of signal during the best ground truth event
        p50       : median of signal over the full backtest

    bruit_baseline = std(signal) / mean(signal)
        computed on windows where signal < 1.05 (strict nominal regime)

Chain    : Polygon
Input    : pol_invariants_2020_2024_phi1800.csv  (28,744 windows, 2020–2023)

Computes M1 for both signals:
  - rhythm_ratio (τ) = rho_ts / EMA_fast(rho_ts)  → best event: Reorg Storm
  - sigma_ratio  (π) = rho_s  / EMA_fast(rho_s)   → best event: Gas Crisis (σ max=2.10)

Note on published value:
  M1=7.37 on AgentNorthStar.com was computed manually during session 17 April 2026
  using a preliminary method prior to formula documentation in methodology.md §10.1.
  This script implements the formalized formula — results may differ from the
  preliminary value. See m1_pol_results.csv for formula-v0.1 output.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ─────────────────────────────────────────────
# PARAMETERS
# ─────────────────────────────────────────────

CHAIN        = "polygon"
ALPHA_FAST   = 2 / 11       # EMA ~10h  (N=10)
WARMUP_INV   = 50
NOMINAL_CAP  = 1.05

DATA_DIR     = Path(__file__).parent
INPUT_FILE   = DATA_DIR / "pol_invariants_2020_2024_phi1800.csv"
OUT_CSV      = DATA_DIR / "pol_m1_results.csv"

# Events for τ (structural) — S2D1
EVENTS_TAU = [
    {"name": "Network Halt",  "onset": "2021-03-01", "window_end": "2021-03-10"},
    {"name": "Heimdall/Bor",  "onset": "2023-01-10", "window_end": "2023-01-20"},
    {"name": "Reorg Storm",   "onset": "2023-02-20", "window_end": "2023-03-05"},
]

# Events for π (demand) — S1D2
EVENTS_PI = [
    {"name": "Gas Crisis",    "onset": "2021-05-01", "window_end": "2021-05-31"},
    {"name": "Network Halt",  "onset": "2021-03-01", "window_end": "2021-03-10"},  # post-halt demand backlog
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
# 2. EMA + SIGNALS
# ─────────────────────────────────────────────

print("[2] Computing EMA_fast and signals ...")

def ema_seq(series: pd.Series, alpha: float) -> pd.Series:
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
df = df.dropna(subset=["rhythm_ratio", "sigma_ratio"])

# ─────────────────────────────────────────────
# 3. M1 FUNCTION
# ─────────────────────────────────────────────

def bootstrap_m1(full_signal: np.ndarray,
                 event_vals: np.ndarray,
                 n: int = 1000,
                 seed: int = 42,
                 nominal_cap: float = NOMINAL_CAP):
    """Resample full-signal and event-window windows with replacement to
    estimate the sampling distribution of M1. Returns (mean, ci95_low, ci95_high)."""
    rng = np.random.default_rng(seed)
    samples = np.empty(n)
    full_n = len(full_signal)
    evt_n  = len(event_vals)
    for i in range(n):
        full_rs = rng.choice(full_signal, size=full_n, replace=True)
        evt_rs  = rng.choice(event_vals,  size=evt_n,  replace=True)
        p50_rs  = np.median(full_rs)
        nom_rs  = full_rs[full_rs < nominal_cap]
        if len(nom_rs) < 2 or nom_rs.mean() == 0:
            samples[i] = np.nan; continue
        bruit_rs = nom_rs.std() / nom_rs.mean()
        if bruit_rs == 0:
            samples[i] = np.nan; continue
        amp_rs = (evt_rs.max() - p50_rs) / p50_rs
        samples[i] = amp_rs / bruit_rs
    samples = samples[~np.isnan(samples)]
    return (float(samples.mean()),
            float(np.percentile(samples, 2.5)),
            float(np.percentile(samples, 97.5)))

def compute_m1(df, signal_col, events, label):
    print(f"\n--- M1 for {label} ({signal_col}) ---")
    p50    = df[signal_col].median()
    nom    = df[df[signal_col] < NOMINAL_CAP][signal_col]
    bruit  = nom.std() / nom.mean()
    print(f"    p50   = {p50:.4f}")
    print(f"    bruit = {bruit:.4f}  (n_nominal={len(nom):,})")

    results = []
    for evt in events:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        subset  = df.loc[(df["dt"] >= onset) & (df["dt"] <= win_end), signal_col]
        if len(subset) == 0:
            print(f"    {evt['name']:20s}  → NO DATA")
            continue
        mx  = subset.max()
        amp = (mx - p50) / p50
        m1  = amp / bruit
        print(f"    {evt['name']:20s}  max={mx:.4f}  amplitude={amp:.4f}  M1={m1:.2f}")
        results.append({"event": evt["name"], "max": mx, "amplitude": amp,
                        "m1": m1, "values": subset.to_numpy()})

    if not results:
        return None
    best = max(results, key=lambda x: x["max"])
    final_m1 = best["amplitude"] / bruit
    print(f"\n    → Best event : {best['event']}  M1={final_m1:.2f}")

    # Bootstrap CI + P99 variant
    m1_mean, ci_lo, ci_hi = bootstrap_m1(df[signal_col].to_numpy(), best["values"])
    p99_val = float(np.percentile(best["values"], 99))
    amp_p99 = (p99_val - p50) / p50
    m1_p99  = amp_p99 / bruit
    print(f"    bootstrap 95% CI  : [{ci_lo:.2f}, {ci_hi:.2f}]  (mean={m1_mean:.2f})")
    print(f"    P99 variant       : p99={p99_val:.4f}  M1(P99)={m1_p99:.2f}")

    return {
        "chain":             CHAIN,
        "signal":            signal_col,
        "label":             label,
        "best_event":        best["event"],
        "max_event":         round(best["max"], 4),
        "p50":               round(p50, 4),
        "amplitude":         round(best["amplitude"], 4),
        "bruit_cv":          round(bruit, 4),
        "m1":                round(final_m1, 2),
        "m1_ci95_low":       round(ci_lo, 2),
        "m1_ci95_high":      round(ci_hi, 2),
        "m1_bootstrap_mean": round(m1_mean, 2),
        "p99_event":         round(p99_val, 4),
        "m1_p99":            round(m1_p99, 2),
        "m1_published":      7.37,
        "note":              "7.37 = preliminary session value; formula-v0.1 result above",
    }

# ─────────────────────────────────────────────
# 4. COMPUTE BOTH SIGNALS
# ─────────────────────────────────────────────

r_tau = compute_m1(df, "rhythm_ratio", EVENTS_TAU, "τ structural")
r_pi  = compute_m1(df, "sigma_ratio",  EVENTS_PI,  "π demand")

# ─────────────────────────────────────────────
# 5. SUMMARY
# ─────────────────────────────────────────────

print("\n" + "="*50)
print("SUMMARY")
print("="*50)
if r_tau: print(f"  τ M1 (rhythm_ratio, {r_tau['best_event']:15s}) = {r_tau['m1']:.2f}")
if r_pi:  print(f"  π M1 (sigma_ratio,  {r_pi['best_event']:15s}) = {r_pi['m1']:.2f}")
print(f"\n  Published ANS value: 7.37 (preliminary — formula §10.1 not yet applied)")
print(f"  Note: update ANS on next calibration cycle with formula-v0.1 result")

# ─────────────────────────────────────────────
# 6. EXPORT
# ─────────────────────────────────────────────

rows = [r for r in [r_tau, r_pi] if r is not None]
pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
print(f"\n[6] Results saved → {OUT_CSV.name}")
