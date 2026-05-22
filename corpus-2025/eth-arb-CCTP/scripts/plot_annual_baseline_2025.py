"""Annual 2025 baseline view, hot windows of the 5 infra-critical events masked.

Same 7-panel layout as the per-incident plots, applied to the full year. Hot windows
+/- 6h around each event start are blanked (no data shown) to give a clean visual
of nominal substrate behavior across 2025 on ETH, ARB, and CCTP eth-arb and arb-eth.

Output:
  plots/annual_baseline_2025.png
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent / "plots"
OUT_DIR.mkdir(exist_ok=True)

INCIDENT_WINDOWS = [
    ("2025-05-07 10:05", "2025-05-07 18:00"),   # S03 Pectra
    ("2025-06-12 19:05", "2025-06-12 21:40"),   # L02 ARB sequencer
    ("2025-10-10 20:30", "2025-10-11 06:00"),   # D01 USDe cascade
    ("2025-12-03 21:49", "2025-12-04 05:00"),   # S04 Fusaka
    ("2025-12-09 14:21", "2025-12-09 22:00"),   # S05 BPO1
]
BUFFER_H = 6

REGIME_COLORS = {
    "S1D1": "#dcdcdc",
    "S1D2+": "#ffd166",
    "S1D2-": "#a8c7e0",
    "S1D2±": "#ffeb99",
    "S2+D1": "#f08c69",
    "S2-D1": "#7fb069",
    "S2+D2+": "#d93636",
    "S2+D2-": "#b370c7",
    "S2+D2±": "#e07ac0",
    "S2-D2+": "#5a9fbf",
    "S2-D2-": "#3d7c47",
    "S2-D2±": "#9bc3a3",
}
BS_COLORS = {"BS1": "#dcdcdc", "BS2": "#d93636"}


def load_chain_2025(chain):
    frames = []
    for q in ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        path = DATA_DIR / "metrics" / f"{chain}_{q}-application_with_regime.parquet"
        if path.exists():
            frames.append(pd.read_parquet(path))
    return pd.concat(frames).sort_index() if frames else pd.DataFrame()


def load_bridge_state_2025():
    return pd.read_parquet(DATA_DIR / "bridge_state_eth_arb_cctp_2025.parquet")


def build_panel():
    # Strict alignment with v2.0 API contract (developers.html):
    # ETH L1: structural = rhythm, continuity (+ beacon_participation, unavailable in historical parquets)
    #         demand = sigma, size, tx
    # ARB L2: structural = rhythm, continuity, sequencer_publish_latency
    #         demand = sigma (blindspot), size, tx, complexity, gas_complexity
    eth = load_chain_2025("ethereum")
    arb = load_chain_2025("arbitrum")
    bs = load_bridge_state_2025().reset_index()

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

    return eth_keep.join(arb_keep, how="inner").join(bs_e2a, how="inner").join(bs_a2e, how="inner").sort_index()


def mask_incident_windows(panel, buffer_h=BUFFER_H):
    """Set values in incident +/- buffer to NaN (so plot shows gap)."""
    masked = panel.copy()
    for start, end in INCIDENT_WINDOWS:
        s = pd.Timestamp(start, tz="UTC") - pd.Timedelta(hours=buffer_h)
        e = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=buffer_h)
        in_mask = (masked.index >= s) & (masked.index <= e)
        for col in masked.columns:
            masked.loc[in_mask, col] = np.nan
    return masked


def draw_strip(ax, series, color_map, title, default_color="#f5f5f5"):
    if series.empty:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
        return
    times = series.index
    times_num = mdates.date2num(times.to_pydatetime() if hasattr(times, "to_pydatetime") else times)
    dt = 1.0 / 24
    for t_num, val in zip(times_num, series):
        if pd.isna(val):
            continue
        color = color_map.get(val, default_color)
        ax.add_patch(plt.Rectangle((t_num - dt / 2, 0), dt, 1, color=color, linewidth=0))
    ax.set_xlim(times_num[0] - dt / 2, times_num[-1] + dt / 2)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.5])
    ax.set_yticklabels([title])
    ax.tick_params(left=False, labelleft=True)


def main():
    print("Building panel...")
    panel = build_panel()
    print(f"Shape: {panel.shape}, range {panel.index.min()} -> {panel.index.max()}")

    print("Masking incident windows +/- 6h...")
    baseline = mask_incident_windows(panel)
    n_nan = baseline["regime_eth"].isna().sum()
    print(f"Masked hours: {n_nan} (events {len(INCIDENT_WINDOWS)} x window each)")

    print("Plotting annual baseline view...")
    fig, axes = plt.subplots(
        7, 1, figsize=(18, 12), sharex=True,
        gridspec_kw={"height_ratios": [0.35, 0.35, 0.35, 0.35, 1.4, 1.4, 1.8]},
    )

    ax_eth_reg, ax_arb_reg, ax_bs1, ax_bs2, ax_eth_sh, ax_arb_sh, ax_atte = axes

    draw_strip(ax_eth_reg, baseline["regime_eth"], REGIME_COLORS, "ETH regime")
    draw_strip(ax_arb_reg, baseline["regime_arb"], REGIME_COLORS, "ARB regime")
    draw_strip(ax_bs1, baseline["bs_e2a"], BS_COLORS, "BS eth-arb")
    draw_strip(ax_bs2, baseline["bs_a2e"], BS_COLORS, "BS arb-eth")

    # ETH shifts: 2 structural (rhythm, continuity) + 3 demand (sigma, size, tx)
    ax_eth_sh.plot(baseline.index, baseline["eth_struct_rhythm"], label="struct.rhythm", color="#1f77b4", linewidth=0.6)
    ax_eth_sh.plot(baseline.index, baseline["eth_struct_continuity"], label="struct.continuity", color="#17becf", linewidth=0.6)
    ax_eth_sh.plot(baseline.index, baseline["eth_demand_sigma"], label="demand.sigma", color="#2ca02c", linewidth=0.6)
    ax_eth_sh.plot(baseline.index, baseline["eth_demand_size"], label="demand.size", color="#9467bd", linewidth=0.6)
    ax_eth_sh.plot(baseline.index, baseline["eth_demand_tx"], label="demand.tx", color="#e377c2", linewidth=0.6)
    ax_eth_sh.axhline(0, color="grey", linestyle=":", linewidth=0.5)
    ax_eth_sh.set_ylabel("ETH signed shifts (API)")
    ax_eth_sh.legend(loc="upper right", fontsize=7, ncol=5)
    ax_eth_sh.grid(True, alpha=0.3)

    # ARB shifts: 3 structural (rhythm, continuity, sequencer_publish_latency)
    #          + 5 demand (sigma blindspot, size, tx, complexity, gas_complexity)
    ax_arb_sh.plot(baseline.index, baseline["arb_struct_rhythm"], label="struct.rhythm", color="#1f77b4", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_struct_continuity"], label="struct.continuity", color="#17becf", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_struct_seq_lat"], label="struct.sequencer_publish_latency", color="#d62728", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_demand_sigma"], label="demand.sigma (blindspot)", color="#2ca02c", linewidth=0.5, alpha=0.4)
    ax_arb_sh.plot(baseline.index, baseline["arb_demand_size"], label="demand.size", color="#9467bd", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_demand_tx"], label="demand.tx", color="#e377c2", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_demand_complexity"], label="demand.complexity", color="#bcbd22", linewidth=0.6)
    ax_arb_sh.plot(baseline.index, baseline["arb_demand_gas_complexity"], label="demand.gas_complexity", color="#8c564b", linewidth=0.6)
    ax_arb_sh.axhline(0, color="grey", linestyle=":", linewidth=0.5)
    ax_arb_sh.set_ylabel("ARB signed shifts (API)")
    ax_arb_sh.legend(loc="upper right", fontsize=7, ncol=4)
    ax_arb_sh.grid(True, alpha=0.3)

    ax_atte.plot(baseline.index, baseline["p50_e2a"], label="p50 eth-arb", color="#1f77b4", linewidth=0.5, linestyle="-")
    ax_atte.plot(baseline.index, baseline["p90_e2a"], label="p90 eth-arb", color="#1f77b4", linewidth=0.8, linestyle="--")
    ax_atte.plot(baseline.index, baseline["p99_e2a"], label="p99 eth-arb", color="#1f77b4", linewidth=1.0, linestyle=":")
    ax_atte.plot(baseline.index, baseline["p50_a2e"], label="p50 arb-eth", color="#d62728", linewidth=0.5, linestyle="-")
    ax_atte.plot(baseline.index, baseline["p90_a2e"], label="p90 arb-eth", color="#d62728", linewidth=0.8, linestyle="--")
    ax_atte.plot(baseline.index, baseline["p99_a2e"], label="p99 arb-eth", color="#d62728", linewidth=1.0, linestyle=":")
    ax_atte.set_yscale("log")
    ax_atte.set_ylabel("CCTP attestation latency (s, log)")
    ax_atte.legend(loc="upper right", fontsize=7, ncol=2)
    ax_atte.grid(True, alpha=0.3, which="both")

    axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()

    fig.suptitle(
        "Annual baseline view 2025 ETH-ARB-CCTP, infra-critical event windows masked (+/- 6h)\n"
        f"Masked events: {len(INCIDENT_WINDOWS)} (S03 Pectra, L02 ARB sequencer, D01 USDe, S04 Fusaka, S05 BPO1)",
        fontsize=12, y=0.995,
    )

    caveats = (
        "Caveats: Research calibration (event-agent BigQuery-derived parquets). ARB sigma_demand_shift blindspot.\n"
        "BS1/BS2 prod calibration pending; research P97/14d reconstruction shown.\n"
        "CCTP V1 only; V2 launched ARB 2025-05-02."
    )
    fig.text(0.01, 0.005, caveats, fontsize=7, color="grey", ha="left", va="bottom")

    plt.tight_layout(rect=[0, 0.02, 1, 0.97])
    out_path = OUT_DIR / "annual_baseline_2025.png"
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")

    # Bonus: aggregate stats over baseline
    bcounts = Counter()
    base_clean = baseline.dropna()
    for _, row in base_clean.iterrows():
        cell = (f"ETH:{row['regime_eth']}|ARB:{row['regime_arb']}"
                f"|BS_e2a:{row['bs_e2a']}|BS_a2e:{row['bs_a2e']}")
        bcounts[cell] += 1
    n_clean = len(base_clean)
    print(f"\nBaseline 2025 (excluding events) summary:")
    print(f"  Total hours: {n_clean}")
    print(f"  Unique cells: {len(bcounts)}")
    print(f"  Top 10 cells:")
    for cell, n in bcounts.most_common(10):
        print(f"    {cell}: {n}h ({n/n_clean*100:.2f}%)")


if __name__ == "__main__":
    main()
