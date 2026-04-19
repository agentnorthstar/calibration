"""
Invarians — Backtest Polygon — Φ=720 (production-aligned)
=========================================================
Source: pol_invariants_2020_2024_phi720.csv (BigQuery, Φ=720 blocks, 2020-2024)

Rationale: backtest v1.0 used Φ=1800 while production uses Φ=720 (ans-engine/src/main.rs:323).
This script reruns the backtest aligned with production configuration.

Protocol identical to backtest_pol.py — only Φ and filename change.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

CHAIN            = "polygon"
PHI              = 720
ALPHA_FAST       = 2 / 11
ALPHA_SLOW       = 2 / 721
THRESHOLD_S2     = 1.04034
THRESHOLD_SIGMA  = 1.13594
THRESHOLD_SIZE   = 1.17667
THRESHOLD_TX     = 1.23474
WARMUP_INV       = 50

DATA_DIR         = Path(__file__).parent
INPUT_FILE       = DATA_DIR / "pol_invariants_2020_2024_phi720.csv"
OUT_CSV          = DATA_DIR / "pol_backtest_results_phi720.csv"
OUT_CHART        = DATA_DIR / "pol_backtest_chart_phi720.png"
OUT_DIST         = DATA_DIR / "pol_signal_distributions_phi720.png"

GROUND_TRUTH = [
    {"name": "Network Halt March 2021",  "onset": "2021-03-11", "window_end": "2021-03-12",
     "expected_states": ["S2D1", "S2D2"], "notes": "Network halt ~11h."},
    {"name": "Gas Crisis May 2021",     "onset": "2021-05-01", "window_end": "2021-06-30",
     "expected_states": ["S1D2", "S2D2"], "notes": "Gas fees x10-100."},
    {"name": "Heimdall/Bor Incident Jan 2023", "onset": "2023-01-16", "window_end": "2023-01-18",
     "expected_states": ["S2D1", "S2D2"], "notes": "Heimdall consensus bug."},
    {"name": "Reorg Storm Feb 2023",    "onset": "2023-02-22", "window_end": "2023-02-25",
     "expected_states": ["S2D1", "S2D2"], "notes": "157 block reorg."},
]

print(f"\n[1] Loading {INPUT_FILE.name} ... (Φ={PHI})")
df = pd.read_csv(INPUT_FILE)
df = df.sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

cs = df["c_s"].dropna()
print(f"\n    c_s : p10={cs.quantile(.10):.4f}  p50={cs.quantile(.50):.4f}  p90={cs.quantile(.90):.4f}")

def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0]
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)

print("\n[2] EMA fast/slow ...")
df["ema_fast_rho_ts"]   = ema_seq(df["rho_ts"],       ALPHA_FAST)
df["ema_slow_rho_ts"]   = ema_seq(df["rho_ts"],       ALPHA_SLOW)
df["ema_fast_rho_s"]    = ema_seq(df["rho_s"],        ALPHA_FAST)
df["ema_fast_size"]     = ema_seq(df["size_avg"],     ALPHA_FAST)
df["ema_fast_tx"]       = ema_seq(df["tx_count_avg"], ALPHA_FAST)

df["rhythm_ratio"] = df["rho_ts"]       / df["ema_fast_rho_ts"]
df["sigma_ratio"]  = df["rho_s"]        / df["ema_fast_rho_s"]
df["size_ratio"]   = df["size_avg"]     / df["ema_fast_size"]
df["tx_ratio"]     = df["tx_count_avg"] / df["ema_fast_tx"]

for col in ["rhythm_ratio", "sigma_ratio", "size_ratio", "tx_ratio"]:
    df.loc[:WARMUP_INV, col] = np.nan

df["tau_state"] = np.where(df["rhythm_ratio"] >= THRESHOLD_S2, "S2", "S1")
df["sigma_dim"] = (df["sigma_ratio"] >= THRESHOLD_SIGMA).astype(int)
df["size_dim"]  = (df["size_ratio"]  >= THRESHOLD_SIZE).astype(int)
df["tx_dim"]    = (df["tx_ratio"]    >= THRESHOLD_TX).astype(int)
df["d2_dims"]   = df["sigma_dim"] + df["size_dim"] + df["tx_dim"]
df["pi_state"]  = np.where(df["d2_dims"] >= 2, "D2", "D1")
df["state"]     = df["tau_state"] + df["pi_state"]

state_counts = df["state"].value_counts()
total = len(df) - WARMUP_INV
print(f"\n    States (excluding warmup):")
for s, n in state_counts.items():
    print(f"      {s:5s}  {n:6d}  ({n/total*100:.1f}%)")

mask_event_tmp = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event_tmp |= (df["dt"] >= pd.Timestamp(evt["onset"], tz="UTC")) & \
                      (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
normal_idx_tmp = df[~mask_event_tmp & (df.index > WARMUP_INV)].index

print(f"\n    Distributions outside events:")
for col in ["rhythm_ratio", "sigma_ratio", "size_ratio", "tx_ratio"]:
    s = df.loc[normal_idx_tmp, col].dropna()
    print(f"      {col:14s}  p50={s.quantile(.50):.4f}  p90={s.quantile(.90):.4f}  "
          f"p95={s.quantile(.95):.4f}  p99={s.quantile(.99):.4f}")

print("\n[3] Ground truth ...")
results = []
for evt in GROUND_TRUTH:
    onset    = pd.Timestamp(evt["onset"],      tz="UTC")
    win_end  = pd.Timestamp(evt["window_end"], tz="UTC")
    expected = evt["expected_states"]
    window_df = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
    detected  = window_df[window_df["state"].isin(expected)]
    if len(detected) > 0:
        first_det = detected["dt"].iloc[0]
        latency_h = (first_det - onset).total_seconds() / 3600
        tp = True
    else:
        first_det = None
        latency_h = None
        tp = False
    detect_ratio = len(detected) / len(window_df) if len(window_df) > 0 else 0
    results.append({
        "event": evt["name"], "onset": evt["onset"], "tp": tp,
        "latency_h": round(latency_h, 1) if latency_h is not None else None,
        "first_detection": first_det.isoformat() if first_det else None,
        "detect_ratio": round(detect_ratio, 3),
        "n_window": len(window_df), "n_detected": len(detected),
        "expected_states": str(expected), "notes": evt["notes"],
    })
    status = "✅ TP" if tp else "❌ FN"
    lat_str = f"latency {latency_h:.1f}h" if latency_h is not None else "not detected"
    print(f"    {status}  {evt['name']:35s}  {lat_str}  (ratio {detect_ratio:.0%})")

mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"], tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
df_normal = df[~mask_event & (df.index > WARMUP_INV)]
stress_states = ["S2D1", "S2D2", "S1D2"]
fpr = df_normal["state"].isin(stress_states).mean()
n_false_alarms = df_normal["state"].isin(stress_states).sum()

print(f"\n    FPR outside events: {fpr:.2%}  ({n_false_alarms} / {len(df_normal)})")
print(f"    thresholds: S2={THRESHOLD_S2}  σ={THRESHOLD_SIGMA}  sz={THRESHOLD_SIZE}  tx={THRESHOLD_TX}")

res_df = pd.DataFrame(results)
res_df.to_csv(OUT_CSV, index=False)
tpr = sum(r["tp"] for r in results) / len(results)
print(f"\n    TPR = {tpr:.0%}  |  FPR = {fpr:.2%}")
print(f"    → {OUT_CSV.name}")

print(f"""
╔══════════════════════════════════════════════════════╗
║  BACKTEST POLYGON Φ=720 (production-aligned)
╠══════════════════════════════════════════════════════╣
║  Invariants : {len(df):>6,}  (Φ={PHI})
║  Thresholds : S2={THRESHOLD_S2}  σ={THRESHOLD_SIGMA}  sz={THRESHOLD_SIZE}  tx={THRESHOLD_TX}
║  EMA α_fast : {ALPHA_FAST:.4f}
╠══════════════════════════════════════════════════════╣
║  TPR : {tpr:.0%}  ({sum(r['tp'] for r in results)}/{len(results)})
║  FPR : {fpr:.2%}  ({n_false_alarms} / {len(df_normal)})
╠══════════════════════════════════════════════════════╣""")
for r in results:
    status = "✅" if r["tp"] else "❌"
    lat = f"{r['latency_h']:+.1f}h" if r["latency_h"] is not None else "—"
    print(f"║  {status} {r['event']:35s} lat={lat:>8s}  det={r['detect_ratio']:.0%}")
print(f"╚══════════════════════════════════════════════════════╝")
