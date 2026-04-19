"""
Invarians — Sweep D2 Polygon — Φ=720 (production-aligned)
==========================================================
Same as sweep_pol_d2.py with INPUT_FILE = pol_invariants_2020_2024_phi720.csv.
threshold_s2 = 1.04 (to be re-evaluated based on sweep_pol.py re-run results if needed).
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "pol_invariants_2020_2024_phi720.csv"
OUT_CHART  = DATA_DIR / "pol_sweep_d2_chart_phi720.png"
OUT_CSV    = DATA_DIR / "pol_sweep_d2_results_phi720.csv"

ALPHA_FAST   = 2 / 11
WARMUP_INV   = 50
THRESHOLD_S2 = 1.04034

SIGMA_THRESHOLDS = [1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20]
SIZE_THRESHOLDS  = [1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20, 1.25]
TX_THRESHOLDS    = [1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20, 1.25]

GROUND_TRUTH = [
    {"name": "Network Halt March 2021", "onset": "2021-03-11", "window_end": "2021-03-12",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Gas Crisis May 2021",    "onset": "2021-05-01", "window_end": "2021-06-30",
     "expected": ["S1D2", "S2D2"]},
    {"name": "Heimdall/Bor Jan 2023",  "onset": "2023-01-16", "window_end": "2023-01-18",
     "expected": ["S2D1", "S2D2"]},
    {"name": "Reorg Storm Feb 2023",   "onset": "2023-02-22", "window_end": "2023-02-25",
     "expected": ["S2D1", "S2D2"]},
]

print(f"[1] {INPUT_FILE.name} (Φ=720)")
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

print("[2] EMA ...")
df["ema_rho_ts"] = ema_seq(df["rho_ts"],       ALPHA_FAST)
df["ema_rho_s"]  = ema_seq(df["rho_s"],        ALPHA_FAST)
df["ema_size"]   = ema_seq(df["size_avg"],     ALPHA_FAST)
df["ema_tx"]     = ema_seq(df["tx_count_avg"], ALPHA_FAST)
df["rhythm_ratio"] = df["rho_ts"]       / df["ema_rho_ts"]
df["sigma_ratio"]  = df["rho_s"]        / df["ema_rho_s"]
df["size_ratio"]   = df["size_avg"]     / df["ema_size"]
df["tx_ratio"]     = df["tx_count_avg"] / df["ema_tx"]
df.loc[:WARMUP_INV, ["rhythm_ratio", "sigma_ratio", "size_ratio", "tx_ratio"]] = np.nan

df["tau_state"] = np.where(df["rhythm_ratio"] >= THRESHOLD_S2, "S2", "S1")

mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"], tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))
normal_idx = df[~mask_event & (df.index > WARMUP_INV)].index

print(f"\n[3] PHASE 1 — sigma only :")
print(f"{'sigma':>8} {'FPR_π':>10} {'Gas':>8} {'n_D2':>8}")
print("─" * 40)
best_sigma = None
for sg in SIGMA_THRESHOLDS:
    df["sigma_dim_s"] = (df["sigma_ratio"] >= sg).astype(int)
    df["pi_sigma"]    = np.where(df["sigma_dim_s"] >= 1, "D2", "D1")
    df["state_s"]     = df["tau_state"] + df["pi_sigma"]
    fpr_s = df.loc[normal_idx, "state_s"].isin(["S2D1", "S2D2", "S1D2"]).mean()
    n_d2  = df.loc[df.index > WARMUP_INV, "state_s"].isin(["S1D2", "S2D2"]).sum()
    gas = df[(df["dt"] >= pd.Timestamp("2021-05-01", tz="UTC")) &
             (df["dt"] <= pd.Timestamp("2021-06-30", tz="UTC"))]
    gas_det = bool(len(gas[gas["state_s"].isin(["S1D2", "S2D2"])]))
    g = "✅" if gas_det else "❌"
    print(f"{sg:>8.2f} {fpr_s:>9.2%} {g:>8} {n_d2:>8}")
    if fpr_s < 0.015 and best_sigma is None:
        best_sigma = sg
if not best_sigma:
    best_sigma = SIGMA_THRESHOLDS[len(SIGMA_THRESHOLDS)//2]
    print(f"\n    ⚠️  No threshold < 1.5% — fallback {best_sigma}")
else:
    print(f"\n    recommended sigma_demand: {best_sigma}")

print(f"\n[4] PHASE 2 — size × tx (sigma={best_sigma}) :")
print(f"{'size':>6} {'tx':>6} {'FPR':>8} {'n_D2':>8} {'Halt':>6} {'Gas':>6} {'Heim':>6} {'Reorg':>6}")
print("─" * 60)

df["sigma_dim"] = (df["sigma_ratio"] >= best_sigma).astype(int)
rows = []
for sz in SIZE_THRESHOLDS:
    for tx in TX_THRESHOLDS:
        df["size_dim"] = (df["size_ratio"] >= sz).astype(int)
        df["tx_dim"]   = (df["tx_ratio"]   >= tx).astype(int)
        df["d2_dims"]  = df["sigma_dim"] + df["size_dim"] + df["tx_dim"]
        df["pi_state"] = np.where(df["d2_dims"] >= 2, "D2", "D1")
        df["state"]    = df["tau_state"] + df["pi_state"]
        fpr  = df.loc[normal_idx, "state"].isin(["S2D1", "S2D2", "S1D2"]).mean()
        n_d2 = df.loc[df.index > WARMUP_INV, "state"].isin(["S1D2", "S2D2"]).sum()
        evt_res = {}
        for evt in GROUND_TRUTH:
            onset   = pd.Timestamp(evt["onset"], tz="UTC")
            win_end = pd.Timestamp(evt["window_end"], tz="UTC")
            window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
            det     = window[window["state"].isin(evt["expected"])]
            evt_res[evt["name"]] = bool(len(det))
        h  = "✅" if evt_res["Network Halt March 2021"] else "❌"
        g  = "✅" if evt_res["Gas Crisis May 2021"] else "❌"
        bh = "✅" if evt_res["Heimdall/Bor Jan 2023"] else "❌"
        rr = "✅" if evt_res["Reorg Storm Feb 2023"] else "❌"
        print(f"{sz:>6.2f} {tx:>6.2f} {fpr:>7.2%} {n_d2:>8} {h:>6} {g:>6} {bh:>6} {rr:>6}")
        rows.append({
            "sigma_demand": best_sigma, "size_demand": sz, "tx_demand": tx,
            "fpr": round(fpr, 4), "n_d2": int(n_d2),
            "halt": evt_res["Network Halt March 2021"],
            "gas":  evt_res["Gas Crisis May 2021"],
            "heimdall": evt_res["Heimdall/Bor Jan 2023"],
            "reorg": evt_res["Reorg Storm Feb 2023"],
        })

sweep_df = pd.DataFrame(rows)
sweep_df.to_csv(OUT_CSV, index=False)

print(f"\n[5] RECOMMANDATION :")
qualified = [r for r in rows if r["fpr"] < 0.015]
tpr_fn = lambda r: int(r["halt"]) + int(r["gas"]) + int(r["heimdall"]) + int(r["reorg"])
if qualified:
    best_full = max(qualified, key=lambda r: (tpr_fn(r), -r["fpr"]))
    print(f"    σ={best_full['sigma_demand']}  sz={best_full['size_demand']}  tx={best_full['tx_demand']}")
    print(f"    FPR={best_full['fpr']:.2%}  TPR={tpr_fn(best_full)}/4")
else:
    best_full = max(rows, key=lambda r: (tpr_fn(r), -r["fpr"]))
    print(f"    ⚠️  no < 1.5% — best trade-off:")
    print(f"    σ={best_full['sigma_demand']}  sz={best_full['size_demand']}  tx={best_full['tx_demand']}  FPR={best_full['fpr']:.2%}")

print(f"\n[6] {OUT_CSV.name}")
