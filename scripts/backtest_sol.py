"""
Invarians — Backtest Solana τ (Φ=800 slots, 2021–2024)

τ calibration only — BigQuery Blocks does not contain transaction_count.
π (execution_profile) stays at P90 confidence:LOW (m1_validated:false, proxy_v1).

τ signals (structure) — source BigQuery:
  rhythm_ratio  = rho_ts / EMA(rho_ts)   → spike = spaced blocks / outage
  c_s           = raw value (0→1)        → drop  = high skip rate
  struct_stress = rhythm_ratio > THRESHOLD_S2  OR  c_s < CONTINUITY_P10

Input  : sol_invariants_2021_2024_phi800.csv  (BigQuery export — columns: inv_idx, window_id,
         block_count, window_start, window_end, rho_ts, c_s)
Output : sol_backtest_results.csv + sol_backtest_chart.png
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR   = Path(__file__).parent
INPUT_FILE = DATA_DIR / "sol_invariants_2021_2024_phi800.csv"
OUT_CHART  = DATA_DIR / "sol_backtest_chart.png"
OUT_CSV    = DATA_DIR / "sol_backtest_results.csv"

# ── Current production thresholds (P90 — τ to calibrate, π unchanged) ────────
THRESHOLD_S2    = 1.034    # current rhythm_p90 — will be refined by sweep
CONTINUITY_P10  = 0.9530   # current c_s P10 — will be refined by sweep
# π: not calibrated in this backtest (no tx data in BQ)
SIGMA_DEMAND    = 1.1279
SIZE_DEMAND     = 1.0375
TX_DEMAND       = 1.1279

ALPHA_FAST = 2 / 11        # ~10h (800 slots × 5.3min/window ≈ compatible)
WARMUP_INV = 50

# ── τ ground truth events (structural only) ──────────────────────────────────
# π not tested here — no tx_count in BigQuery Blocks
GROUND_TRUTH = [
    {"name": "Outage Sept 2021",  "onset": "2021-09-14", "window_end": "2021-09-17",
     "expected": ["S2D1", "S2D2"], "type": "structural"},
    {"name": "Outage Jan 2022",   "onset": "2022-01-21", "window_end": "2022-01-22",
     "expected": ["S2D1", "S2D2"], "type": "structural"},
    {"name": "Outage May 2022",   "onset": "2022-05-31", "window_end": "2022-06-01",
     "expected": ["S2D1", "S2D2"], "type": "structural"},
    {"name": "Outage Oct 2022",   "onset": "2022-10-01", "window_end": "2022-10-02",
     "expected": ["S2D1", "S2D2"], "type": "structural"},
]

# ── Utilities ─────────────────────────────────────────────────────────────────
def ema_seq(series, alpha):
    result = np.empty(len(series))
    result[0] = series.iloc[0] if not pd.isna(series.iloc[0]) else 1.0
    arr = series.to_numpy()
    for i in range(1, len(arr)):
        v = arr[i]
        if pd.isna(v):
            result[i] = result[i - 1]
        else:
            result[i] = alpha * v + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=series.index)


def classify_state(row, threshold_s2, continuity_p10, sigma_d, size_d, tx_d):
    rhythm_stressed     = row["rhythm_ratio"]   > threshold_s2
    continuity_stressed = (continuity_p10 is not None
                           and pd.notna(row["c_s"])
                           and row["c_s"] < continuity_p10)
    struct_stress = rhythm_stressed or continuity_stressed

    dims = sum([
        1 if row["sigma_ratio"] > sigma_d else 0,
        1 if row["size_ratio"]  > size_d  else 0,
        1 if row["tx_ratio"]    > tx_d    else 0,
    ])
    demand_elevated = dims >= 1
    demand_stress   = dims >= 2

    if struct_stress and demand_stress:    return "S2D2"
    if struct_stress and not demand_elevated: return "S2D1"
    if demand_elevated:                    return "S1D2"
    return "S1D1"


# ── 1. Loading + filling outage gaps ─────────────────────────────────────────
print("[1] Loading data ...")
if not INPUT_FILE.exists():
    print(f"ERROR: file not found → {INPUT_FILE}")
    print("Run extract_sol.sql on BigQuery first, export as CSV.")
    raise SystemExit(1)

df = pd.read_csv(INPUT_FILE).sort_values("window_id").reset_index(drop=True)
df["dt"] = pd.to_datetime(df["window_start"], unit="s", utc=True)
n_raw = len(df)

# Fill complete outage gaps (windows absent from BQ = 0 blocks)
print(f"   {n_raw} windows in the CSV.")
all_win = pd.DataFrame({"window_id": range(df["window_id"].min(),
                                           df["window_id"].max() + 1)})
df = all_win.merge(df, on="window_id", how="left")
n_filled = len(df) - n_raw
print(f"   {n_filled} complete-outage windows injected (c_s=0, rho_ts=999s).")

# Synthetic values for full-outage windows
df["block_count"]   = df["block_count"].fillna(0)
df["rho_ts"]        = df["rho_ts"].fillna(999.0)    # 999s → rhythm_ratio >> threshold
df["c_s"]           = df["c_s"].fillna(0.0)          # 0% continuity
df["dt"]            = pd.to_datetime(
    df["window_start"].fillna(
        df["window_id"] * 800 * 0.4   # estimate: 400ms/slot
    ), unit="s", utc=True
)
df["inv_idx"] = np.arange(len(df))

# ── 2. Compute EMA ────────────────────────────────────────────────────────────
print("[2] Computing EMA rho_ts ...")

# Cap at 5s for the EMA — complete-outage windows (999s) do not bias the baseline
rho_ts_capped  = df["rho_ts"].clip(upper=5.0)
df["ema_rho_ts"]   = ema_seq(rho_ts_capped, ALPHA_FAST)
df["rhythm_ratio"] = df["rho_ts"].clip(upper=20.0) / df["ema_rho_ts"]

# π ratios: placeholders (no BQ data) — classification will be S1D1 or S2D1 only
df["sigma_ratio"] = 1.0
df["size_ratio"]  = 1.0
df["tx_ratio"]    = 1.0

df.loc[:WARMUP_INV, "rhythm_ratio"] = np.nan

# ── 3. Classification ─────────────────────────────────────────────────────────
print("[3] State classification ...")
valid = df.index > WARMUP_INV

df["state"] = "S1D1"
df.loc[valid, "state"] = df[valid].apply(
    lambda r: classify_state(r, THRESHOLD_S2, CONTINUITY_P10,
                             SIGMA_DEMAND, SIZE_DEMAND, TX_DEMAND),
    axis=1
)

# ── 4. FPR (outside event windows) ───────────────────────────────────────────
print("[4] Computing FPR ...")
mask_event = pd.Series(False, index=df.index)
for evt in GROUND_TRUTH:
    mask_event |= (df["dt"] >= pd.Timestamp(evt["onset"],      tz="UTC")) & \
                  (df["dt"] <= pd.Timestamp(evt["window_end"], tz="UTC"))

normal_idx = df[~mask_event & valid].index
fpr_total  = df.loc[normal_idx, "state"].isin(["S2D1","S2D2","S1D2"]).mean()
fpr_tau    = df.loc[normal_idx, "state"].isin(["S2D1","S2D2"]).mean()
fpr_pi     = df.loc[normal_idx, "state"].isin(["S1D2"]).mean()

print(f"   FPR total   : {fpr_total:.2%}")
print(f"   FPR τ only  : {fpr_tau:.2%}")
print(f"   FPR π only  : {fpr_pi:.2%}")

# ── 5. State distribution ─────────────────────────────────────────────────────
print("\n[5] State distribution:")
state_counts = df[valid]["state"].value_counts()
total = state_counts.sum()
for s, c in state_counts.items():
    print(f"   {s:6s} : {c:6d} ({c/total:.1%})")

# ── 6. Event detection ────────────────────────────────────────────────────────
print("\n[6] Ground truth event detection:")
for evt in GROUND_TRUTH:
    onset   = pd.Timestamp(evt["onset"],      tz="UTC")
    win_end = pd.Timestamp(evt["window_end"], tz="UTC")
    window  = df[(df["dt"] >= onset) & (df["dt"] <= win_end)]
    det     = window[window["state"].isin(evt["expected"])]

    # Latency: first detection after onset
    if len(det) > 0:
        first_det = det["dt"].min()
        latency_h = (first_det - onset).total_seconds() / 3600
        print(f"   ✅ {evt['name']:25s} — detected  (latency +{latency_h:.1f}h)")
    else:
        print(f"   ❌ {evt['name']:25s} — not detected")
        if len(window) > 0:
            print(f"      → max rhythm_ratio={window['rhythm_ratio'].max():.4f}  "
                  f"min c_s={window['c_s'].min():.4f}  "
                  f"max tx_ratio={window['tx_ratio'].max():.4f}")

# ── 7. Sauvegarde CSV ─────────────────────────────────────────────────────────
df[valid].to_csv(OUT_CSV, index=False)
print(f"\nCSV → {OUT_CSV.name}")

# ── 8. Graphique ──────────────────────────────────────────────────────────────
print("[7] Generation graphique ...")
fig, axes = plt.subplots(4, 1, figsize=(16, 12), facecolor="#080A09",
                         sharex=True)
fig.suptitle("Solana — Backtest Invarians 2021–2024 (thresholds production P90)",
             color="white", fontsize=11)

colors_state = {"S1D1":"#2a7a4b","S1D2":"#e8a030","S2D1":"#e05050","S2D2":"#9b30e0"}

for ax in axes:
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=7)
    for s in ax.spines.values(): s.set_edgecolor("#222")
    for evt in GROUND_TRUTH:
        ax.axvspan(pd.Timestamp(evt["onset"], tz="UTC"),
                   pd.Timestamp(evt["window_end"], tz="UTC"),
                   alpha=0.15,
                   color="#ff6b6b" if evt["type"] == "structural" else "#6bc5ff")

axes[0].plot(df["dt"], df["rhythm_ratio"], color="#55aaff", lw=0.4, alpha=0.8)
axes[0].axhline(THRESHOLD_S2, color="#ff5555", lw=0.8, ls="--", label=f"threshold_s2={THRESHOLD_S2}")
axes[0].set_ylabel("rhythm_ratio", color="#888", fontsize=8)
axes[0].legend(fontsize=7, facecolor="#222", labelcolor="white")
axes[0].set_ylim(0, min(df["rhythm_ratio"].quantile(0.999) * 1.5, 5))

axes[1].plot(df["dt"], df["c_s"], color="#55ffaa", lw=0.4, alpha=0.8)
axes[1].axhline(CONTINUITY_P10, color="#ff5555", lw=0.8, ls="--", label=f"continuity_p10={CONTINUITY_P10}")
axes[1].set_ylabel("c_s (continuity)", color="#888", fontsize=8)
axes[1].legend(fontsize=7, facecolor="#222", labelcolor="white")
axes[1].set_ylim(0, 1.05)

axes[2].text(0.5, 0.5, "tx_ratio — non available\n(BigQuery Blocks without transaction_count)",
             transform=axes[2].transAxes, ha="center", va="center",
             color="#666", fontsize=9)
axes[2].set_ylabel("tx_ratio", color="#888", fontsize=8)

state_colors = df[valid]["state"].map(colors_state)
axes[3].scatter(df.loc[valid, "dt"], np.ones(valid.sum()),
                c=state_colors, s=0.3, marker="|")
axes[3].set_yticks([])
axes[3].set_ylabel("Etat", color="#888", fontsize=8)
# Legende state
for s, c in colors_state.items():
    axes[3].scatter([], [], c=c, label=s, s=20)
axes[3].legend(fontsize=7, facecolor="#222", labelcolor="white", ncol=4)

# Annotations events
for evt in GROUND_TRUTH:
    axes[0].annotate(
        evt["name"].split()[0],
        xy=(pd.Timestamp(evt["onset"], tz="UTC"), THRESHOLD_S2 * 1.05),
        fontsize=5, color="#aaa", rotation=90, va="bottom"
    )

axes[-1].set_xlabel("Date", color="#888", fontsize=8)
plt.tight_layout()
plt.savefig(OUT_CHART, dpi=150, bbox_inches="tight", facecolor="#080A09")
plt.close()
print(f"Chart → {OUT_CHART.name}")
print("\nBaseline backtest termine. Lance sweep_sol.py for calibrer τ.")
