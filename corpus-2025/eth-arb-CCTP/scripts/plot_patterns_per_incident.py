"""Plot pre / during / post substrate pattern for each ETH-ARB infra-critical 2025 event.

For each of the 5 events (S03 Pectra, L02 ARB sequencer, D01 USDe cascade, S04 Fusaka,
S05 BPO1), produce a 5-panel figure on +/-24h window around hot:

  P1 strips: regime ETH, regime ARB, BS eth-arb, BS arb-eth
  P2 ETH continuous shifts (rhythm, continuity, sigma_demand, size_demand)
  P3 ARB continuous shifts (rhythm, continuity, sigma_demand, sequencer_publish_latency)
  P4 CCTP attestation latency p50/p90/p99 both routes, log scale
  P5 hourly combined cell lift = P(observed_cell | hour) / P(observed_cell | baseline)

Caveats embedded in figure footer:
- Research calibration (event-agent BigQuery-derived), distinct from prod Iris probe
- ARB sigma blindspot (Nitro gas constraint, sigma_demand permanently ~1.0)
- BS1/BS2 prod calibration pending post-2026-05-20; this is research reconstruction
- CCTP V1 only; V2 launched ARB 2025-05-02

Outputs:
  plots/<incident_id>_pattern.png
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "plots"
OUT_DIR.mkdir(exist_ok=True)


@dataclass
class Incident:
    incident_id: str
    label: str
    start_utc: str
    end_utc: str
    incident_type: str


INCIDENTS = [
    Incident("S03", "Pectra mainnet activation",
             "2025-05-07 10:05", "2025-05-07 18:00", "Hard fork ETH"),
    Incident("L02", "ARB One sequencer connectivity 2h35",
             "2025-06-12 19:05", "2025-06-12 21:40", "L2 sequencer (sub-RWA-critical)"),
    Incident("D01", "USDe Binance cascade $19B liquidations",
             "2025-10-10 20:30", "2025-10-11 06:00", "Settlement asset cascade"),
    Incident("S04", "Fusaka mainnet activation (PeerDAS)",
             "2025-12-03 21:49", "2025-12-04 05:00", "Hard fork ETH"),
    Incident("S05", "BPO1 mainnet activation (blob target)",
             "2025-12-09 14:21", "2025-12-09 22:00", "Hard fork BPO minor"),
]

# Regime color mapping
REGIME_COLORS = {
    "S1D1": "#dcdcdc",       # neutral light grey
    "S1D2+": "#ffd166",      # warm yellow
    "S1D2-": "#a8c7e0",      # cool blue
    "S1D2±": "#ffeb99", # pale yellow
    "S2+D1": "#f08c69",      # orange-red
    "S2-D1": "#7fb069",      # green
    "S2+D2+": "#d93636",     # red
    "S2+D2-": "#b370c7",     # purple
    "S2+D2±": "#e07ac0",# pink
    "S2-D2+": "#5a9fbf",     # teal
    "S2-D2-": "#3d7c47",     # dark green
    "S2-D2±": "#9bc3a3",# pale green
}
BS_COLORS = {"BS1": "#dcdcdc", "BS2": "#d93636"}


def load_chain_2025(chain: str) -> pd.DataFrame:
    frames = []
    for q in ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        path = DATA_DIR / "metrics" / f"{chain}_{q}-application_with_regime.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    return pd.concat(frames).sort_index() if frames else pd.DataFrame()


def load_bridge_state_2025() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "bridge_state_eth_arb_cctp_2025.parquet")


def build_panel():
    eth = load_chain_2025("ethereum")
    arb = load_chain_2025("arbitrum")
    bs = load_bridge_state_2025().reset_index()

    # Strict alignment with v2.0 API contract (developers.html):
    # ETH L1: structural = rhythm, continuity (+ beacon_participation, unavailable in historical parquets)
    #         demand = sigma, size, tx
    # ARB L2: structural = rhythm, continuity, sequencer_publish_latency
    #         demand = sigma (blindspot), size, tx, complexity, gas_complexity
    eth_keep = eth[["regime",
                    "rhythm_ratio_shift", "continuity_ratio_shift",
                    "sigma_demand_shift", "size_demand_shift", "tx_demand_shift"]].copy()
    eth_keep.columns = ["regime_eth",
                        "eth_struct_rhythm", "eth_struct_continuity",
                        "eth_demand_sigma", "eth_demand_size", "eth_demand_tx"]
    arb_keep = arb[["regime",
                    "rhythm_ratio_shift", "continuity_ratio_shift", "sequencer_publish_latency_shift",
                    "sigma_demand_shift", "size_demand_shift", "tx_demand_shift",
                    "complexity_value_shift", "gas_complexity_ratio_shift"]].copy()
    arb_keep.columns = ["regime_arb",
                        "arb_struct_rhythm", "arb_struct_continuity", "arb_struct_seq_lat",
                        "arb_demand_sigma", "arb_demand_size", "arb_demand_tx",
                        "arb_demand_complexity", "arb_demand_gas_complexity"]

    bs_e2a = bs[bs["route_id"] == "eth-arb"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s"]
    ].rename(columns={
        "state": "bs_e2a",
        "attestation_latency_p50_s": "p50_e2a",
        "attestation_latency_p90_s": "p90_e2a",
        "attestation_latency_p99_s": "p99_e2a",
    })
    bs_a2e = bs[bs["route_id"] == "arb-eth"].set_index("hour_utc")[
        ["state", "attestation_latency_p50_s",
         "attestation_latency_p90_s", "attestation_latency_p99_s"]
    ].rename(columns={
        "state": "bs_a2e",
        "attestation_latency_p50_s": "p50_a2e",
        "attestation_latency_p90_s": "p90_a2e",
        "attestation_latency_p99_s": "p99_a2e",
    })

    panel = eth_keep.join(arb_keep, how="inner").join(bs_e2a, how="inner").join(bs_a2e, how="inner")
    return panel.sort_index()


def joint_cell(row):
    return (f"ETH:{row['regime_eth']}|ARB:{row['regime_arb']}"
            f"|BS_e2a:{row['bs_e2a']}|BS_a2e:{row['bs_a2e']}")


def in_any_incident(ts, buffer_h=6):
    for inc in INCIDENTS:
        s = pd.Timestamp(inc.start_utc, tz="UTC") - pd.Timedelta(hours=buffer_h)
        e = pd.Timestamp(inc.end_utc, tz="UTC") + pd.Timedelta(hours=buffer_h)
        if s <= ts <= e:
            return True
    return False


def compute_baseline_cells(panel):
    mask = panel.index.to_series().apply(lambda ts: not in_any_incident(ts))
    base = panel[mask.values].copy()
    base["cell"] = base.apply(joint_cell, axis=1)
    counts = Counter(base["cell"])
    n = len(base)
    return counts, n


def draw_strip(ax, series, color_map, title, default_color="#f5f5f5"):
    """Draw a categorical strip on ax. series is a pandas Series indexed by datetime."""
    if series.empty:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        return
    times = series.index
    if len(times) < 2:
        return
    # Convert to matplotlib date numbers
    times_num = mdates.date2num(times.to_pydatetime() if hasattr(times, "to_pydatetime") else times)
    # Estimate width per hour
    dt = (times_num[1] - times_num[0]) if len(times_num) > 1 else 1.0 / 24
    for t_num, val in zip(times_num, series):
        color = color_map.get(val, default_color)
        ax.add_patch(plt.Rectangle((t_num - dt / 2, 0), dt, 1, color=color, linewidth=0))
    ax.set_xlim(times_num[0] - dt / 2, times_num[-1] + dt / 2)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.5])
    ax.set_yticklabels([title])
    ax.tick_params(left=False, labelleft=True)


def plot_incident(incident, panel, baseline_counts, baseline_n):
    ts_start = pd.Timestamp(incident.start_utc, tz="UTC")
    ts_end = pd.Timestamp(incident.end_utc, tz="UTC")
    win_start = ts_start - pd.Timedelta(hours=24)
    win_end = ts_end + pd.Timedelta(hours=24)

    win = panel.loc[win_start:win_end].copy()
    if win.empty:
        print(f"  {incident.incident_id}: empty window, skipping")
        return

    win["cell"] = win.apply(joint_cell, axis=1)
    win["lift"] = win["cell"].apply(
        lambda c: (1.0 / (baseline_counts.get(c, 0) / baseline_n))
        if baseline_counts.get(c, 0) > 0 else np.nan  # inf if unseen, mark as nan for log plot
    )

    fig, axes = plt.subplots(
        7, 1, figsize=(14, 14), sharex=True,
        gridspec_kw={"height_ratios": [0.4, 0.4, 0.4, 0.4, 1.4, 1.4, 1.6, 1.6][:7]},
    )

    # P1 strips: 4 sub-strips actually, but combine into 4 axes
    # Reorganize: ax 0,1,2,3 = strips ; 4 = ETH shifts ; 5 = ARB shifts ; 6 = attestation + lift overlay?
    # Better: 7 axes total
    # axes[0] regime ETH, [1] regime ARB, [2] BS e2a, [3] BS a2e, [4] ETH shifts, [5] ARB shifts, [6] attestation + lift twin
    ax_eth_reg, ax_arb_reg, ax_bs1, ax_bs2, ax_eth_sh, ax_arb_sh, ax_atte = axes

    draw_strip(ax_eth_reg, win["regime_eth"], REGIME_COLORS, "ETH regime")
    draw_strip(ax_arb_reg, win["regime_arb"], REGIME_COLORS, "ARB regime")
    draw_strip(ax_bs1, win["bs_e2a"], BS_COLORS, "BS eth-arb")
    draw_strip(ax_bs2, win["bs_a2e"], BS_COLORS, "BS arb-eth")

    # ETH shifts: 2 structural (rhythm, continuity) + 3 demand (sigma, size, tx)
    ax_eth_sh.plot(win.index, win["eth_struct_rhythm"], label="struct.rhythm", color="#1f77b4", linewidth=1.4)
    ax_eth_sh.plot(win.index, win["eth_struct_continuity"], label="struct.continuity", color="#17becf", linewidth=1.4)
    ax_eth_sh.plot(win.index, win["eth_demand_sigma"], label="demand.sigma", color="#2ca02c", linewidth=1.4)
    ax_eth_sh.plot(win.index, win["eth_demand_size"], label="demand.size", color="#9467bd", linewidth=1.4)
    ax_eth_sh.plot(win.index, win["eth_demand_tx"], label="demand.tx", color="#e377c2", linewidth=1.4)
    ax_eth_sh.axhline(0, color="grey", linestyle=":", linewidth=0.5)
    ax_eth_sh.set_ylabel("ETH signed shifts (API)")
    ax_eth_sh.legend(loc="upper right", fontsize=7, ncol=5)
    ax_eth_sh.grid(True, alpha=0.3)

    # ARB shifts: 3 structural (rhythm, continuity, sequencer_publish_latency)
    #          + 5 demand (sigma blindspot, size, tx, complexity, gas_complexity)
    ax_arb_sh.plot(win.index, win["arb_struct_rhythm"], label="struct.rhythm", color="#1f77b4", linewidth=1.2)
    ax_arb_sh.plot(win.index, win["arb_struct_continuity"], label="struct.continuity", color="#17becf", linewidth=1.2)
    ax_arb_sh.plot(win.index, win["arb_struct_seq_lat"], label="struct.sequencer_publish_latency", color="#d62728", linewidth=1.4)
    ax_arb_sh.plot(win.index, win["arb_demand_sigma"], label="demand.sigma (blindspot)", color="#2ca02c", linewidth=1.0, alpha=0.4)
    ax_arb_sh.plot(win.index, win["arb_demand_size"], label="demand.size", color="#9467bd", linewidth=1.2)
    ax_arb_sh.plot(win.index, win["arb_demand_tx"], label="demand.tx", color="#e377c2", linewidth=1.2)
    ax_arb_sh.plot(win.index, win["arb_demand_complexity"], label="demand.complexity", color="#bcbd22", linewidth=1.2)
    ax_arb_sh.plot(win.index, win["arb_demand_gas_complexity"], label="demand.gas_complexity", color="#8c564b", linewidth=1.2)
    ax_arb_sh.axhline(0, color="grey", linestyle=":", linewidth=0.5)
    ax_arb_sh.set_ylabel("ARB signed shifts (API)")
    ax_arb_sh.legend(loc="upper right", fontsize=6, ncol=4)
    ax_arb_sh.grid(True, alpha=0.3)

    # P7 attestation latency p50/p90/p99 both routes, log scale, + lift overlay on twin axis
    ax_atte.plot(win.index, win["p50_e2a"], label="p50 eth-arb", color="#1f77b4", linewidth=1.0, linestyle="-")
    ax_atte.plot(win.index, win["p90_e2a"], label="p90 eth-arb", color="#1f77b4", linewidth=1.5, linestyle="--")
    ax_atte.plot(win.index, win["p99_e2a"], label="p99 eth-arb", color="#1f77b4", linewidth=2.0, linestyle=":")
    ax_atte.plot(win.index, win["p50_a2e"], label="p50 arb-eth", color="#d62728", linewidth=1.0, linestyle="-")
    ax_atte.plot(win.index, win["p90_a2e"], label="p90 arb-eth", color="#d62728", linewidth=1.5, linestyle="--")
    ax_atte.plot(win.index, win["p99_a2e"], label="p99 arb-eth", color="#d62728", linewidth=2.0, linestyle=":")
    ax_atte.set_yscale("log")
    ax_atte.set_ylabel("CCTP attestation latency (s, log)")
    ax_atte.legend(loc="upper right", fontsize=7, ncol=2)
    ax_atte.grid(True, alpha=0.3, which="both")

    # Twin axis for lift
    ax_lift = ax_atte.twinx()
    lift_vals = win["lift"].copy()
    # cap inf for plot
    cap = 1000
    lift_plot = lift_vals.clip(upper=cap)
    ax_lift.plot(win.index, lift_plot, color="black", linewidth=1.5, marker="o", markersize=3,
                 label="combined cell lift (right axis)")
    ax_lift.set_yscale("log")
    ax_lift.set_ylabel("Lift (log)", color="black")
    ax_lift.axhline(1, color="grey", linestyle="-", linewidth=0.5)
    ax_lift.axhline(3, color="red", linestyle=":", linewidth=0.8)
    ax_lift.set_ylim(0.1, cap * 1.5)
    ax_lift.legend(loc="upper left", fontsize=8)

    # Mark hot window vertically across all axes
    for ax in axes:
        ax.axvline(ts_start, color="red", linestyle="-", linewidth=1.0, alpha=0.9)
        ax.axvline(ts_end, color="red", linestyle="-", linewidth=1.0, alpha=0.9)
        ax.axvspan(ts_start, ts_end, color="red", alpha=0.05)

    # X axis formatting
    axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    fig.autofmt_xdate()

    # Title + caveats
    fig.suptitle(
        f"{incident.incident_id} | {incident.label}\n"
        f"Type: {incident.incident_type}\n"
        f"Hot: {incident.start_utc} -> {incident.end_utc} UTC (red shading)",
        fontsize=11, y=0.995,
    )

    caveats = (
        "Caveats: Research calibration (event-agent BigQuery-derived parquets), distinct from prod Iris probe.\n"
        "ARB sigma_demand_shift blindspot known (Nitro gas constraint, rho_s permanently near 1.0).\n"
        "BS1/BS2 prod calibration pending post-2026-05-20; states shown are research P97/14d reconstruction.\n"
        "CCTP V1 only; V2 launched ARB 2025-05-02. Lift = P(observed cell | hour) / P(observed cell | baseline 2025 hors incidents +/-6h)."
    )
    fig.text(0.01, 0.005, caveats, fontsize=7, color="grey", ha="left", va="bottom")

    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    out_path = OUT_DIR / f"{incident.incident_id}_pattern.png"
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {out_path}")


def main():
    print("Building panel...")
    panel = build_panel()
    print(f"Panel shape: {panel.shape}, range {panel.index.min()} -> {panel.index.max()}")

    print("Computing baseline cell counts...")
    counts, n = compute_baseline_cells(panel)
    print(f"Baseline: {n} hours, {len(counts)} unique cells, top cell {counts.most_common(1)[0]}")

    print("Generating plots...")
    for inc in INCIDENTS:
        plot_incident(inc, panel, counts, n)

    print("Done.")


if __name__ == "__main__":
    main()
