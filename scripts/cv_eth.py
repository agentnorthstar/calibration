"""
Invarians — Cross-validation temporelle ETH
============================================

Objective
---------
Test whether the published ETH thresholds (threshold_s2 = 1.12,
D2 sigma = 1.10, size = 1.20, tx = 1.10) generalize out-of-sample.

Method (temporal split)
-----------------------
Train window :  2020-01-01 → 2022-08-01
Test  window :  2022-09-01 → 2024-12-31

Train events :  DeFi Summer, NFT Mania                (both D2-type)
Test  events :  The Merge, Shanghai Upgrade           (both mixed, τ-dominant)

Procedure
---------
1. Fit D2 thresholds (sigma, size, tx) on train events using a grid sweep,
   selecting the (sigma, size, tx) triplet with max TPR_train and min FPR_train.
2. threshold_s2 is held fixed at its published value because no τ-type event
   exists before 2022-09 to temporally calibrate it. This limitation is stated
   explicitly in the output.
3. Apply the train-selected D2 triplet + fixed threshold_s2 to the test window.
   Report TPR_test, FPR_test with exact Clopper-Pearson IC95%.

Output
------
Prints a structured report + writes cv_eth_results.json next to the script.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import beta

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

# Convention: place BigQuery CSV extracts next to this script.
# See scripts/README.md for reproduction instructions.
DATA_DIR    = Path(__file__).parent
INPUT_FILE  = DATA_DIR / "eth_invariants_2020_2024_phi280.csv"
OUT_JSON    = DATA_DIR / "cv_eth_results.json"

ALPHA_FAST    = 2 / 11
WARMUP_INV    = 50
THRESHOLD_S2  = 1.12   # fixed — held constant (see caveat in output)

# D2 sweep grid (train)
GRID_SIGMA = [1.05, 1.08, 1.10, 1.12, 1.15]
GRID_SIZE  = [1.10, 1.15, 1.20, 1.25, 1.30]
GRID_TX    = [1.05, 1.10, 1.15, 1.20, 1.25]

TRAIN_END  = pd.Timestamp("2022-08-01", tz="UTC")
TEST_START = pd.Timestamp("2022-09-01", tz="UTC")

GROUND_TRUTH = [
    {"name": "DeFi Summer",      "onset": "2020-06-15", "window_end": "2020-09-30",
     "expected": ["S1D2", "S2D2"], "split": "train"},
    {"name": "NFT Mania",        "onset": "2021-03-01", "window_end": "2021-05-30",
     "expected": ["S1D2", "S2D2"], "split": "train"},
    {"name": "The Merge",        "onset": "2022-09-14", "window_end": "2022-09-17",
     "expected": ["S2D1", "S2D2"], "split": "test"},
    {"name": "Shanghai Upgrade", "onset": "2023-04-12", "window_end": "2023-04-15",
     "expected": ["S2D1", "S1D2", "S2D2"], "split": "test"},
]

STRESS_STATES = ["S2D1", "S2D2", "S1D2"]

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def ema_seq(series, alpha):
    a = series.to_numpy()
    r = np.empty(len(a))
    r[0] = a[0]
    for i in range(1, len(a)):
        r[i] = alpha * a[i] + (1 - alpha) * r[i - 1]
    return pd.Series(r, index=series.index)

def clopper_pearson(k, n, alpha=0.05):
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return (float(lo), float(hi))

def classify(df, s2, sigma, size_t, tx_t):
    tau  = np.where(df["rhythm_ratio"] >= s2, "S2", "S1")
    sig  = (df["sigma_ratio"] >= sigma).astype(int)
    sz   = (df["size_ratio"]  >= size_t).astype(int)
    tx   = (df["tx_ratio"]    >= tx_t).astype(int)
    dims = sig + sz + tx
    pi   = np.where(dims >= 2, "D2", "D1")
    return pd.Series([t + p for t, p in zip(tau, pi)], index=df.index)

def detect_events(df, events):
    detected = 0
    details  = []
    for evt in events:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
        hits    = window[window["state"].isin(evt["expected"])]
        is_tp   = len(hits) > 0
        detected += int(is_tp)
        latency_h = ((hits["dt"].iloc[0] - onset).total_seconds() / 3600) if is_tp else None
        details.append({
            "name": evt["name"], "tp": is_tp,
            "latency_h": round(latency_h, 2) if latency_h is not None else None,
            "n_window": len(window), "n_detected": len(hits),
        })
    return detected, details

def compute_fpr(df, events, stress=STRESS_STATES):
    mask_event = pd.Series(False, index=df.index)
    for evt in events:
        onset   = pd.Timestamp(evt["onset"],      tz="UTC")
        win_end = pd.Timestamp(evt["window_end"], tz="UTC")
        mask_event |= (df["dt"] >= onset) & (df["dt"] <= win_end)
    normal = df[~mask_event & (df.index > WARMUP_INV)]
    k = int(normal["state"].isin(stress).sum())
    n = int(len(normal))
    return k, n, (k / n if n else 0.0)

# ─────────────────────────────────────────────
# LOAD + EMA + RATIOS
# ─────────────────────────────────────────────

print(f"[1] Loading {INPUT_FILE.name} ...")
df = pd.read_csv(INPUT_FILE).sort_values("inv_idx").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
print(f"    {len(df):,} invariants  |  {df['dt'].min().date()} → {df['dt'].max().date()}")

print("[2] Computing EMAs and ratios ...")
df["ema_rho_ts"] = ema_seq(df["rho_ts"],       ALPHA_FAST)
df["ema_rho_s"]  = ema_seq(df["rho_s"],        ALPHA_FAST)
df["ema_size"]   = ema_seq(df["size_avg"],     ALPHA_FAST)
df["ema_tx"]     = ema_seq(df["tx_count_avg"], ALPHA_FAST)

df["rhythm_ratio"] = df["rho_ts"]       / df["ema_rho_ts"]
df["sigma_ratio"]  = df["rho_s"]        / df["ema_rho_s"]
df["size_ratio"]   = df["size_avg"]     / df["ema_size"]
df["tx_ratio"]     = df["tx_count_avg"] / df["ema_tx"]
df.loc[:WARMUP_INV, ["rhythm_ratio","sigma_ratio","size_ratio","tx_ratio"]] = np.nan

# Train / test partitions
df_train = df[df["dt"] < TRAIN_END].copy()
df_test  = df[df["dt"] >= TEST_START].copy()
train_events = [e for e in GROUND_TRUTH if e["split"] == "train"]
test_events  = [e for e in GROUND_TRUTH if e["split"] == "test"]

print(f"    Train : {df_train['dt'].min().date()} → {df_train['dt'].max().date()}  "
      f"({len(df_train):,} inv, events: {[e['name'] for e in train_events]})")
print(f"    Test  : {df_test['dt'].min().date()} → {df_test['dt'].max().date()}  "
      f"({len(df_test):,} inv, events: {[e['name'] for e in test_events]})")

# ─────────────────────────────────────────────
# 3. TRAIN SWEEP — find best (sigma, size, tx)
# ─────────────────────────────────────────────

print(f"\n[3] Sweep on TRAIN ({len(GRID_SIGMA)*len(GRID_SIZE)*len(GRID_TX)} combos) ...")

best = None
all_combos = []
for sigma in GRID_SIGMA:
    for size_t in GRID_SIZE:
        for tx_t in GRID_TX:
            df_train["state"] = classify(df_train, THRESHOLD_S2, sigma, size_t, tx_t)
            tpr_k, tpr_details = detect_events(df_train, train_events)
            tpr_n = len(train_events)
            fpr_k, fpr_n, fpr = compute_fpr(df_train, train_events)
            combo = {
                "sigma": sigma, "size": size_t, "tx": tx_t,
                "tpr_train_k": tpr_k, "tpr_train_n": tpr_n,
                "tpr_train": tpr_k / tpr_n,
                "fpr_train_k": fpr_k, "fpr_train_n": fpr_n, "fpr_train": fpr,
            }
            all_combos.append(combo)
            # Selection rule: max TPR, then min FPR
            if best is None \
               or combo["tpr_train"] > best["tpr_train"] \
               or (combo["tpr_train"] == best["tpr_train"] and combo["fpr_train"] < best["fpr_train"]):
                best = combo

print(f"\n    Best on TRAIN:")
print(f"       sigma={best['sigma']}  size={best['size']}  tx={best['tx']}")
print(f"       TPR_train = {best['tpr_train_k']}/{best['tpr_train_n']} = {best['tpr_train']:.0%}")
print(f"       FPR_train = {best['fpr_train_k']}/{best['fpr_train_n']} = {best['fpr_train']:.4%}")

published = {"sigma": 1.10, "size": 1.20, "tx": 1.10}
print(f"\n    Published (full-period) : sigma={published['sigma']}  size={published['size']}  tx={published['tx']}")

# ─────────────────────────────────────────────
# 4. APPLY to TEST
# ─────────────────────────────────────────────

print("\n[4] Applying train-selected parameters to TEST window ...")

df_test["state"] = classify(df_test, THRESHOLD_S2, best["sigma"], best["size"], best["tx"])
tpr_test_k, tpr_test_details = detect_events(df_test, test_events)
tpr_test_n = len(test_events)
tpr_test = tpr_test_k / tpr_test_n
tpr_ci = clopper_pearson(tpr_test_k, tpr_test_n)

fpr_test_k, fpr_test_n, fpr_test = compute_fpr(df_test, test_events)
fpr_ci = clopper_pearson(fpr_test_k, fpr_test_n)

for det in tpr_test_details:
    lat = f"{det['latency_h']:+.1f}h" if det["latency_h"] is not None else "—"
    mark = "✅ TP" if det["tp"] else "❌ FN"
    print(f"    {mark}  {det['name']:22s}  lat={lat:>8s}  "
          f"det={det['n_detected']}/{det['n_window']}")

print(f"\n    TPR_test = {tpr_test_k}/{tpr_test_n} = {tpr_test:.0%}  "
      f"CI95% = [{tpr_ci[0]:.4f}, {tpr_ci[1]:.4f}]")
print(f"    FPR_test = {fpr_test_k}/{fpr_test_n} = {fpr_test:.4%}  "
      f"CI95% = [{fpr_ci[0]:.4f}, {fpr_ci[1]:.4f}]")

# ─────────────────────────────────────────────
# 5. COMPARISON: train-selected vs published on TEST
# ─────────────────────────────────────────────

print("\n[5] Comparison — published params applied to TEST:")

df_test["state"] = classify(df_test, THRESHOLD_S2, published["sigma"], published["size"], published["tx"])
tpr_pub_k, _ = detect_events(df_test, test_events)
fpr_pub_k, fpr_pub_n, fpr_pub = compute_fpr(df_test, test_events)
tpr_pub_ci = clopper_pearson(tpr_pub_k, tpr_test_n)
fpr_pub_ci = clopper_pearson(fpr_pub_k, fpr_pub_n)

print(f"    Published params on TEST :")
print(f"       TPR = {tpr_pub_k}/{tpr_test_n} = {tpr_pub_k/tpr_test_n:.0%}  "
      f"CI95% = [{tpr_pub_ci[0]:.4f}, {tpr_pub_ci[1]:.4f}]")
print(f"       FPR = {fpr_pub_k}/{fpr_pub_n} = {fpr_pub:.4%}  "
      f"CI95% = [{fpr_pub_ci[0]:.4f}, {fpr_pub_ci[1]:.4f}]")

# ─────────────────────────────────────────────
# 6. EXPORT
# ─────────────────────────────────────────────

out = {
    "train_window":  {"start": str(df_train["dt"].min().date()), "end": str(df_train["dt"].max().date())},
    "test_window":   {"start": str(df_test["dt"].min().date()),  "end": str(df_test["dt"].max().date())},
    "train_events":  [e["name"] for e in train_events],
    "test_events":   [e["name"] for e in test_events],
    "threshold_s2_fixed": THRESHOLD_S2,
    "caveat_s2":
        "threshold_s2 held fixed; no τ-type event exists in the train window "
        "(pre-2022-09), so threshold_s2 cannot be temporally cross-validated.",
    "best_on_train": best,
    "published_params": published,
    "test_results_train_selected": {
        "tpr": {"k": tpr_test_k, "n": tpr_test_n, "rate": tpr_test, "ci95": list(tpr_ci)},
        "fpr": {"k": fpr_test_k, "n": fpr_test_n, "rate": fpr_test, "ci95": list(fpr_ci)},
        "events": tpr_test_details,
    },
    "test_results_published_params": {
        "tpr": {"k": tpr_pub_k, "n": tpr_test_n, "rate": tpr_pub_k/tpr_test_n, "ci95": list(tpr_pub_ci)},
        "fpr": {"k": fpr_pub_k, "n": fpr_pub_n, "rate": fpr_pub, "ci95": list(fpr_pub_ci)},
    },
}
OUT_JSON.write_text(json.dumps(out, indent=2))
print(f"\n[6] Results written → {OUT_JSON}")
