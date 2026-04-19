"""
Invarians — M1 Polygon — Φ=720 (production-aligned)
====================================================
Formula identique a m1_pol.py (methodology.md §10.1).
Seule difference : INPUT_FILE = pol_invariants_2020_2024_phi720.csv.
"""

import pandas as pd
import numpy as np
from pathlib import Path

CHAIN        = "polygon"
ALPHA_FAST   = 2 / 11
WARMUP_INV   = 50
NOMINAL_CAP  = 1.05

DATA_DIR     = Path(__file__).parent
INPUT_FILE   = DATA_DIR / "pol_invariants_2020_2024_phi720.csv"
OUT_CSV      = DATA_DIR / "pol_m1_results_phi720.csv"

EVENTS_TAU = [
    {"name": "Network Halt",  "onset": "2021-03-01", "window_end": "2021-03-10"},
    {"name": "Heimdall/Bor",  "onset": "2023-01-10", "window_end": "2023-01-20"},
    {"name": "Reorg Storm",   "onset": "2023-02-20", "window_end": "2023-03-05"},
]
EVENTS_PI = [
    {"name": "Gas Crisis",    "onset": "2021-05-01", "window_end": "2021-05-31"},
    {"name": "Network Halt",  "onset": "2021-03-01", "window_end": "2021-03-10"},
]

print(f"\n[1] {INPUT_FILE.name} (Φ=720)")
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

print("[2] EMA + signals ...")
df["ema_fast_rho_ts"] = ema_seq(df["rho_ts"], ALPHA_FAST)
df["ema_fast_rho_s"]  = ema_seq(df["rho_s"],  ALPHA_FAST)
df["rhythm_ratio"]    = df["rho_ts"] / df["ema_fast_rho_ts"]
df["sigma_ratio"]     = df["rho_s"]  / df["ema_fast_rho_s"]
df.loc[:WARMUP_INV, ["rhythm_ratio", "sigma_ratio"]] = np.nan
df = df.dropna(subset=["rhythm_ratio", "sigma_ratio"])

def bootstrap_m1(full_signal, event_vals, n=1000, seed=42, nominal_cap=NOMINAL_CAP):
    rng = np.random.default_rng(seed)
    samples = np.empty(n)
    for i in range(n):
        full_rs = rng.choice(full_signal, size=len(full_signal), replace=True)
        evt_rs  = rng.choice(event_vals,  size=len(event_vals),  replace=True)
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
    print(f"\n--- M1 {label} ({signal_col}) ---")
    p50    = df[signal_col].median()
    nom    = df[df[signal_col] < NOMINAL_CAP][signal_col]
    bruit  = nom.std() / nom.mean()
    print(f"    p50={p50:.4f}  bruit={bruit:.4f}  (n_nom={len(nom):,})")
    results = []
    for evt in events:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        subset  = df.loc[(df["dt"] >= onset) & (df["dt"] <= win_end), signal_col]
        if len(subset) == 0:
            continue
        mx  = subset.max()
        amp = (mx - p50) / p50
        m1  = amp / bruit
        print(f"    {evt['name']:20s}  max={mx:.4f}  amp={amp:.4f}  M1={m1:.2f}")
        results.append({"event": evt["name"], "max": mx, "amplitude": amp,
                        "m1": m1, "values": subset.to_numpy()})
    if not results:
        return None
    best = max(results, key=lambda x: x["max"])
    final_m1 = best["amplitude"] / bruit
    print(f"    → best: {best['event']}  M1={final_m1:.2f}")

    m1_mean, ci_lo, ci_hi = bootstrap_m1(df[signal_col].to_numpy(), best["values"])
    p99_val = float(np.percentile(best["values"], 99))
    amp_p99 = (p99_val - p50) / p50
    m1_p99  = amp_p99 / bruit
    print(f"    bootstrap 95% CI : [{ci_lo:.2f}, {ci_hi:.2f}]  (mean={m1_mean:.2f})")
    print(f"    P99 variant      : p99={p99_val:.4f}  M1(P99)={m1_p99:.2f}")

    return {
        "chain": CHAIN, "signal": signal_col, "label": label,
        "best_event": best["event"],
        "max_event": round(best["max"], 4), "p50": round(p50, 4),
        "amplitude": round(best["amplitude"], 4), "bruit_cv": round(bruit, 4),
        "m1": round(final_m1, 2),
        "m1_ci95_low":       round(ci_lo, 2),
        "m1_ci95_high":      round(ci_hi, 2),
        "m1_bootstrap_mean": round(m1_mean, 2),
        "p99_event":         round(p99_val, 4),
        "m1_p99":            round(m1_p99, 2),
    }

r_tau = compute_m1(df, "rhythm_ratio", EVENTS_TAU, "τ structural")
r_pi  = compute_m1(df, "sigma_ratio",  EVENTS_PI,  "π demand")

print("\n" + "="*50)
print("SUMMARY — Φ=720")
print("="*50)
if r_tau: print(f"  τ M1 (rhythm_ratio, {r_tau['best_event']:15s}) = {r_tau['m1']:.2f}")
if r_pi:  print(f"  π M1 (sigma_ratio,  {r_pi['best_event']:15s}) = {r_pi['m1']:.2f}")

rows = [r for r in [r_tau, r_pi] if r is not None]
pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
print(f"\n[3] → {OUT_CSV.name}")
