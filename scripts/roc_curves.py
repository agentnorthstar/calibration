"""
Invarians — ROC curves per chain
=================================

Builds ROC curves (FPR on X, TPR on Y) from the per-chain threshold sweeps
already produced by the production backtesting pipeline.

Inputs (local CSVs produced by the per-chain sweep scripts):
  - eth_sweep_results.csv    (1D τ sweep, 2 τ-events tracked)
  - sol_sweep_results.csv    (1D τ sweep, 4 outages tracked, phase A)
  - pol_sweep_d2_results_phi720.csv (3D D2 sweep, 4 events tracked, production-aligned Φ=720)

Outputs:
  - scripts/roc_eth.png
  - scripts/roc_sol.png
  - scripts/roc_pol.png
  - scripts/roc_results.json  (AUC per chain + operating point)

Methodology
-----------
- ETH, SOL: 1D sweep over a single τ threshold → direct ROC curve sorted by FPR.
- POL: 3D sweep (σ × size × tx) over D2 logic. Every combo maps to one (FPR, TPR)
  point. The ROC curve is the upper-left Pareto frontier of the point cloud.
- AUC is computed by trapezoidal integration on the sorted ROC points, with the
  axis anchored at (0, 0) and (1, 1).
- The published operating point (production threshold) is overlaid on each plot.

Honest caveats
--------------
- With n_events ≤ 4, the ROC curve is a step function; point estimates of TPR
  only take values in {0, 1/n, 2/n, ..., 1}. AUC is therefore coarse.
- A ROC curve does not resolve the in-sample optimization concern on its own.
  That is addressed separately by the temporal cross-validation (ETH §6).
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Convention: place sweep CSV outputs next to this script.
# See scripts/README.md for reproduction instructions.
DATA_DIR = Path(__file__).parent
OUT_DIR  = Path(__file__).parent
OUT_JSON = OUT_DIR / "roc_results.json"

# ─────────────────────────────────────────────
# PUBLISHED OPERATING POINTS (from backtest_*.md frontmatter)
# ─────────────────────────────────────────────
PUBLISHED = {
    "ETH": {"threshold_s2": 1.12, "fpr_published": 0.0123, "tpr_published": 1.00,
            "n_events_used_for_roc": 2, "note": "Full-chain FPR=1.23% uses 2-of-3 D2; τ-only ROC below isolates the τ axis."},
    "SOL": {"threshold_s2": 1.12, "fpr_published": 0.0177, "tpr_published": 1.00,
            "n_events_used_for_roc": 4, "note": "τ-only (π pending calibration July 2026)."},
    "POL": {"threshold_s2": 1.04, "fpr_published": 0.1457, "tpr_published": 1.00,
            "n_events_used_for_roc": 4, "phi": 720,
            "note": "ROC below is D2-axis projection (σ × size × tx). Production-aligned Φ=720 since v2.0 (2026-04-19)."},
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def trapz_auc(fpr, tpr):
    """Trapezoidal AUC, anchored at (0,0) and (1,1)."""
    pts = sorted(zip(fpr, tpr))
    xs = [0.0] + [p[0] for p in pts] + [1.0]
    ys = [0.0] + [p[1] for p in pts] + [1.0]
    xs, ys = zip(*sorted(zip(xs, ys)))
    return float(np.trapezoid(ys, xs))

def pareto_frontier(fpr_arr, tpr_arr):
    """Upper-left Pareto frontier of 2D points (maximize TPR, minimize FPR)."""
    pts = sorted(zip(fpr_arr, tpr_arr), key=lambda x: (x[0], -x[1]))
    frontier = []
    best_tpr = -1.0
    for f, t in pts:
        if t > best_tpr:
            frontier.append((f, t))
            best_tpr = t
    return frontier

def plot_roc(ax, fpr, tpr, frontier_fpr=None, frontier_tpr=None,
             operating=None, title="", auc=None):
    """Invarians dark theme ROC plot."""
    ax.set_facecolor("#0d0d0d")
    ax.tick_params(colors="#888", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#222")

    # Reference diagonal (random classifier)
    ax.plot([0, 1], [0, 1], color="#333", linewidth=0.7, linestyle="--", label="random")

    # All sweep points
    ax.scatter(fpr, tpr, s=18, color="#5b9bd5", alpha=0.55, edgecolor="none", label="sweep points")

    # Pareto frontier (if supplied) or direct ROC line
    if frontier_fpr is not None:
        ax.plot(frontier_fpr, frontier_tpr, color="#3ECF8E", linewidth=1.6, label="ROC frontier")
    else:
        order = np.argsort(fpr)
        ax.plot(np.array(fpr)[order], np.array(tpr)[order], color="#3ECF8E", linewidth=1.4, label="ROC")

    # Published operating point
    if operating:
        ax.scatter([operating["fpr"]], [operating["tpr"]], s=110, color="#e8a020",
                   edgecolor="white", linewidth=1.2, zorder=10, label="published threshold")
        ax.annotate(operating["label"],
                    xy=(operating["fpr"], operating["tpr"]),
                    xytext=(operating["fpr"] + 0.06, operating["tpr"] - 0.1),
                    color="#e8a020", fontsize=8,
                    arrowprops=dict(arrowstyle="->", color="#e8a020", lw=0.6))

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlabel("FPR (false alarms / normal windows)", color="#888", fontsize=9)
    ax.set_ylabel("TPR (events detected / events)", color="#888", fontsize=9)
    ttl = title + (f"  —  AUC = {auc:.3f}" if auc is not None else "")
    ax.set_title(ttl, color="white", fontsize=10)
    ax.legend(fontsize=7, loc="lower right", facecolor="#111", labelcolor="white", frameon=False)

# ─────────────────────────────────────────────
# 1. ETH — τ sweep
# ─────────────────────────────────────────────
print("[1] ETH τ ROC ...")
eth = pd.read_csv(DATA_DIR / "eth_sweep_results.csv")
# TPR over τ-dominant events (Merge + Shanghai)
eth["tpr"] = (eth["merge_detected"].astype(int) + eth["shanghai_detected"].astype(int)) / 2
eth_auc = trapz_auc(eth["fpr"].tolist(), eth["tpr"].tolist())

fig, ax = plt.subplots(figsize=(7, 6), facecolor="#080A09")
plot_roc(ax, eth["fpr"], eth["tpr"],
         operating={"fpr": 0.0123, "tpr": 1.00,
                    "label": f"threshold_s2 = {PUBLISHED['ETH']['threshold_s2']}\nFPR = 1.23% · TPR = 100%"},
         title=f"ETH — τ-axis ROC  (n_events = 2: Merge, Shanghai)",
         auc=eth_auc)
plt.tight_layout()
plt.savefig(OUT_DIR / "roc_eth.png", dpi=150, facecolor="#080A09")
plt.close()
print(f"    AUC = {eth_auc:.3f} — roc_eth.png")

# ─────────────────────────────────────────────
# 2. SOL — τ sweep (Phase A = τ only)
# ─────────────────────────────────────────────
print("[2] SOL τ ROC ...")
sol = pd.read_csv(DATA_DIR / "sol_sweep_results.csv")
sol = sol[sol["phase"] == "A_s2"].copy()
sol["param"] = sol["param"].astype(float)
event_cols = [c for c in sol.columns if c.startswith("Outage") and "latency" not in c]
sol["tpr"] = sol[event_cols].astype(int).sum(axis=1) / len(event_cols)
sol_auc = trapz_auc(sol["fpr"].tolist(), sol["tpr"].tolist())

fig, ax = plt.subplots(figsize=(7, 6), facecolor="#080A09")
plot_roc(ax, sol["fpr"], sol["tpr"],
         operating={"fpr": 0.0177, "tpr": 1.00,
                    "label": f"threshold_s2 = {PUBLISHED['SOL']['threshold_s2']}\nFPR = 1.77% · TPR = 100%"},
         title=f"SOL — τ-axis ROC  (n_events = 4 outages)",
         auc=sol_auc)
plt.tight_layout()
plt.savefig(OUT_DIR / "roc_sol.png", dpi=150, facecolor="#080A09")
plt.close()
print(f"    AUC = {sol_auc:.3f} — roc_sol.png")

# ─────────────────────────────────────────────
# 3. POL — D2 sweep (3D → Pareto frontier)
# ─────────────────────────────────────────────
print("[3] POL D2 ROC (Pareto frontier of 3D sweep) ...")
pol = pd.read_csv(DATA_DIR / "pol_sweep_d2_results_phi720.csv")
event_cols = ["halt", "gas", "heimdall", "reorg"]
pol["tpr"] = pol[event_cols].astype(int).sum(axis=1) / len(event_cols)
frontier = pareto_frontier(pol["fpr"].tolist(), pol["tpr"].tolist())
f_fpr = [p[0] for p in frontier]
f_tpr = [p[1] for p in frontier]
pol_auc = trapz_auc(f_fpr, f_tpr)

fig, ax = plt.subplots(figsize=(7, 6), facecolor="#080A09")
plot_roc(ax, pol["fpr"], pol["tpr"], frontier_fpr=f_fpr, frontier_tpr=f_tpr,
         operating={"fpr": 0.1457, "tpr": 1.00,
                    "label": f"published D2 triplet (Φ=720)\nFPR = 14.57% · TPR = 100%"},
         title=f"POL — D2 ROC  (3D sweep Φ=720, n_events = 4)",
         auc=pol_auc)
plt.tight_layout()
plt.savefig(OUT_DIR / "roc_pol.png", dpi=150, facecolor="#080A09")
plt.close()
print(f"    AUC = {pol_auc:.3f} — roc_pol.png")

# ─────────────────────────────────────────────
# 4. EXPORT JSON
# ─────────────────────────────────────────────
out = {
    "ETH": {
        "axis": "tau", "n_events": 2, "n_sweep_points": int(len(eth)),
        "auc": round(eth_auc, 4),
        "published": PUBLISHED["ETH"],
        "sweep": eth[["threshold_s2", "fpr", "tpr"]].round(4).to_dict(orient="records"),
    },
    "SOL": {
        "axis": "tau", "n_events": 4, "n_sweep_points": int(len(sol)),
        "auc": round(sol_auc, 4),
        "published": PUBLISHED["SOL"],
        "sweep": sol[["param", "fpr", "tpr"]].round(4).to_dict(orient="records"),
    },
    "POL": {
        "axis": "D2 (3D projection → Pareto frontier)", "n_events": 4,
        "n_sweep_points": int(len(pol)),
        "n_pareto_points": len(frontier),
        "auc": round(pol_auc, 4),
        "published": PUBLISHED["POL"],
        "pareto_frontier": [{"fpr": round(f, 4), "tpr": round(t, 4)} for f, t in frontier],
    },
}
OUT_JSON.write_text(json.dumps(out, indent=2))
print(f"\n[4] Results → {OUT_JSON}")
print(f"\nSummary (AUC, higher is better, 0.5 = random, 1.0 = perfect):")
print(f"  ETH τ : AUC = {eth_auc:.3f}  (n=2 events)")
print(f"  SOL τ : AUC = {sol_auc:.3f}  (n=4 events)")
print(f"  POL D2: AUC = {pol_auc:.3f}  (n=4 events, Pareto of 3D sweep)")
