#!/usr/bin/env python3
"""
Step 3 compute: hourly metrics, EMA, signed shifts, drift composites, regime codes,
CCTP V2 latency reconstruction, per-event sheets, baseline sheet.

Implements METHODOLOGY_STEP3_CONVENTIONS.md strictly.

Inputs (from Step 2 lock):
  data/eth_blocks_2025_raw.parquet
  data/pol_blocks_2025_raw.parquet
  data/cctp_v2_events_2025_raw.parquet
  INCIDENTS_2025.md (event inventory)

Outputs:
  results/per_event_sheets/{event_id}.parquet  (one per event)
  results/per_event_sheets/baseline.parquet
  results/REPORT_ETH_POL_CCTP_V2.md
"""

import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PUBLIABLE = Path(__file__).resolve().parent.parent
DATA = PUBLIABLE / "data"
RESULTS = PUBLIABLE / "results"
SHEETS = RESULTS / "per_event_sheets"
SHEETS.mkdir(parents=True, exist_ok=True)

# Production thresholds (METHODOLOGY.md §4)
THRESHOLDS = {
    "eth": {"s2": 1.12, "sigma_d2": 1.10, "size_d2": 1.20, "tx_d2": 1.10},
    "pol": {"s2": 1.04, "sigma_d2": 1.14, "size_d2": 1.18, "tx_d2": 1.23},
}

# Protocol targets (CONVENTIONS §1)
TARGET_BLOCK_TIME = {"eth": 12.0, "pol": 2.0}
EXPECTED_BLOCKS_PER_HOUR = {"eth": 300, "pol": 1800}

# EMA decay factor (CONVENTIONS §2)
EMA_HALF_LIFE_HOURS = 30 * 24
EMA_ALPHA = 1.0 - math.exp(-math.log(2) / EMA_HALF_LIFE_HOURS)
WARMUP_END = pd.Timestamp("2025-01-31 00:00:00", tz="UTC")

# CCTP V2 domain IDs
DOMAIN_ID = {"ethereum": 0, "polygon": 7}

# Corpus window
CORPUS_START = pd.Timestamp("2025-01-01 00:00:00", tz="UTC")
CORPUS_END = pd.Timestamp("2026-01-01 00:00:00", tz="UTC")
EPS = 1e-9


def ewma(series: pd.Series, alpha: float) -> pd.Series:
    """Standard EWMA recurrence, NaN-aware: skip NaN observations, carry previous EMA."""
    ema = np.empty(len(series))
    last = np.nan
    for i, x in enumerate(series.values):
        if np.isnan(x):
            ema[i] = last
        elif np.isnan(last):
            ema[i] = x
            last = x
        else:
            last = (1 - alpha) * last + alpha * x
            ema[i] = last
    return pd.Series(ema, index=series.index)


def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    """Division protecting against EMA divisor near zero."""
    den_safe = den.where(den.abs() > EPS, np.nan)
    return num / den_safe


def compute_chain_hourly(blocks_df: pd.DataFrame, chain: str) -> pd.DataFrame:
    """
    Aggregate raw blocks to hourly metrics per CONVENTIONS §1.

    Input columns: number, hash, parent_hash, timestamp, gas_used, gas_limit,
                   transaction_count, base_fee_per_gas, (size for ETH)

    Output index: hour_utc (timezone-aware hourly grid)
    Output columns: rhythm_ratio, continuity_ratio, sigma_demand_cv,
                    avg_tx_per_block, total_tx_per_hour, base_fee_per_gas_mean,
                    block_count
    """
    df = blocks_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("number").reset_index(drop=True)
    df["hour"] = df["timestamp"].dt.floor("h")

    target = TARGET_BLOCK_TIME[chain]
    expected = EXPECTED_BLOCKS_PER_HOUR[chain]

    # Per-block inter-block interval (vs previous block in time)
    df["prev_ts"] = df["timestamp"].shift(1)
    df["delta_s"] = (df["timestamp"] - df["prev_ts"]).dt.total_seconds()

    # Group by hour
    grouped = df.groupby("hour", sort=True)

    def hour_agg(g):
        return pd.Series({
            "block_count": len(g),
            "median_delta_s": g["delta_s"].median() if g["delta_s"].notna().any() else np.nan,
            "gas_used_mean": g["gas_used"].mean(),
            "gas_used_std": g["gas_used"].std(ddof=0),
            "avg_tx_per_block": g["transaction_count"].mean(),
            "total_tx_per_hour": g["transaction_count"].sum(),
            "base_fee_mean": g["base_fee_per_gas"].mean() if "base_fee_per_gas" in g else np.nan,
        })

    hourly = grouped.apply(hour_agg, include_groups=False)
    hourly = hourly.reindex(pd.date_range(CORPUS_START, CORPUS_END - pd.Timedelta(hours=1), freq="h", tz="UTC"))

    # Raw 5 metrics (CONVENTIONS §1)
    hourly["rhythm_ratio"] = hourly["median_delta_s"] / target
    hourly["continuity_ratio"] = hourly["block_count"] / expected

    cv_safe = hourly["gas_used_mean"].where(hourly["gas_used_mean"].abs() > EPS, np.nan)
    hourly["sigma_cv_raw"] = hourly["gas_used_std"] / cv_safe

    # EMA series (CONVENTIONS §2)
    for col in ["sigma_cv_raw", "avg_tx_per_block", "total_tx_per_hour"]:
        hourly[f"{col}_ema"] = ewma(hourly[col], EMA_ALPHA)

    # Ratio metrics against EMA (CONVENTIONS §1.3-1.5)
    hourly["sigma_demand"] = safe_div(hourly["sigma_cv_raw"], hourly["sigma_cv_raw_ema"])
    hourly["size_demand"] = safe_div(hourly["avg_tx_per_block"], hourly["avg_tx_per_block_ema"])
    hourly["tx_demand"] = safe_div(hourly["total_tx_per_hour"], hourly["total_tx_per_hour_ema"])

    # EMAs of the 5 metrics themselves (used for shifts CONVENTIONS §3)
    for col in ["rhythm_ratio", "continuity_ratio", "sigma_demand", "size_demand", "tx_demand"]:
        hourly[f"{col}_ema"] = ewma(hourly[col], EMA_ALPHA)

    # Signed shifts (CONVENTIONS §3)
    for col in ["rhythm_ratio", "continuity_ratio", "sigma_demand", "size_demand", "tx_demand"]:
        ema_col = f"{col}_ema"
        ema_safe = hourly[ema_col].where(hourly[ema_col].abs() > EPS, np.nan)
        hourly[f"{col}_shift"] = (hourly[col] - hourly[ema_col]) / ema_safe

    # Drift composites (CONVENTIONS §4)
    hourly["drift_structural"] = (hourly["rhythm_ratio_shift"] + hourly["continuity_ratio_shift"]) / 2
    hourly["drift_demand"] = (
        hourly["sigma_demand_shift"]
        + hourly["size_demand_shift"]
        + hourly["tx_demand_shift"]
    ) / 3

    # Regime code (CONVENTIONS §5)
    th = THRESHOLDS[chain]
    def classify_s(row):
        r = row["rhythm_ratio"]
        if pd.isna(r):
            return np.nan
        if r > th["s2"]:
            return "S2+"
        if r < 1.0 / th["s2"]:
            return "S2-"
        return "S1"

    def classify_d(row):
        n_above = 0
        n_below = 0
        for metric, key in [("sigma_demand", "sigma_d2"), ("size_demand", "size_d2"), ("tx_demand", "tx_d2")]:
            v = row[metric]
            if pd.isna(v):
                continue
            t = th[key]
            if v > t:
                n_above += 1
            elif v < 1.0 / t:
                n_below += 1
        n_trig = n_above + n_below
        if n_trig < 2:
            return "D1"
        if n_above >= 2 and n_below == 0:
            return "D2+"
        if n_below >= 2 and n_above == 0:
            return "D2-"
        return "D2±"

    hourly["s_axis"] = hourly.apply(classify_s, axis=1)
    hourly["d_axis"] = hourly.apply(classify_d, axis=1)
    hourly["regime_code"] = hourly["s_axis"].astype(str) + hourly["d_axis"].astype(str)

    # Warmup flag
    hourly["ema_warmup"] = hourly.index < WARMUP_END

    # Base fee
    hourly["base_fee_per_gas"] = hourly["base_fee_mean"]

    return hourly


def compute_cctp_hourly_latency(cctp_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pair MessageSent and MessageReceived by FIFO ordinal rank within each
    (source_domain, destination_domain, mode) bucket, then aggregate latency
    per hour per direction per mode (CONVENTIONS §6.1).

    Rationale: CCTP V2 fills the message nonce off-chain via Circle attestation
    after MessageSent emission, so byte-exact nonce matching is not feasible
    from BigQuery state alone. METHODOLOGY.md §2 forbids external API
    dependencies; FIFO pairing within domain-mode buckets is the deterministic
    reconstruction method.
    """
    sent = cctp_df[cctp_df["event_name"] == "MessageSent"].copy()
    received = cctp_df[cctp_df["event_name"] == "MessageReceived"].copy()
    sent["block_timestamp"] = pd.to_datetime(sent["block_timestamp"], utc=True)
    received["block_timestamp"] = pd.to_datetime(received["block_timestamp"], utc=True)

    def classify_mode(mft):
        if pd.isna(mft):
            return "Other"
        if mft <= 1000:
            return "Fast"
        if mft == 2000:
            return "Standard"
        return "Other"

    sent["mode"] = sent["min_finality_threshold"].apply(classify_mode)

    # Proximity-window matching per (source_domain, destination_domain, requested_mode):
    # for each Sent in chronological order, find the earliest unmatched Received within a
    # mode-specific plausible latency window. Fast: [t, t+2h]; Standard: [t, t+48h].
    # This avoids the FIFO-global cross-mode contamination problem where Fast and Standard
    # streams interleave in send order but cross-reorder in receive order due to their
    # different latency distributions. Mode is attributed from the source side.

    LATENCY_WINDOW_S = {"Fast": 2 * 3600, "Standard": 48 * 3600}

    corridor_pairs = [(0, 7), (7, 0)]
    pairs = []
    pairing_log = {}

    for sd, dd in corridor_pairs:
        s_grp = sent[(sent["source_domain"] == sd) & (sent["destination_domain"] == dd)]
        r_all = received[(received["source_domain"] == sd) & (received["destination_domain"] == dd)]
        r_sorted = r_all.sort_values("block_timestamp").reset_index(drop=True)
        r_ts_arr = r_sorted["block_timestamp"].values
        r_used = np.zeros(len(r_sorted), dtype=bool)

        for mode in ["Fast", "Standard"]:
            s_grp_mode = s_grp[s_grp["mode"] == mode].sort_values("block_timestamp").reset_index(drop=True)
            window = pd.Timedelta(seconds=LATENCY_WINDOW_S[mode])
            n_paired = 0
            n_unpaired = 0
            for _, sent_row in s_grp_mode.iterrows():
                sent_ts = sent_row["block_timestamp"]
                window_end = sent_ts + window
                # Find first unused recv with ts in [sent_ts, sent_ts+window]
                # Binary-search lower bound on sent_ts (first recv >= sent_ts)
                lo = np.searchsorted(r_ts_arr, np.datetime64(sent_ts, "ns"))
                # Linear scan from lo until ts > window_end or end
                paired_idx = -1
                for j in range(lo, len(r_sorted)):
                    if r_used[j]:
                        continue
                    rt = r_sorted.iloc[j]["block_timestamp"]
                    if rt > window_end:
                        break
                    paired_idx = j
                    break
                if paired_idx >= 0:
                    r_used[paired_idx] = True
                    pairs.append({
                        "source_domain": sd,
                        "destination_domain": dd,
                        "mode": mode,
                        "sent_ts": sent_ts,
                        "recv_ts": r_sorted.iloc[paired_idx]["block_timestamp"],
                        "latency_s": (r_sorted.iloc[paired_idx]["block_timestamp"] - sent_ts).total_seconds(),
                    })
                    n_paired += 1
                else:
                    n_unpaired += 1

            pairing_log[(sd, dd, mode)] = {
                "n_sent": len(s_grp_mode),
                "n_paired": n_paired,
                "n_unpaired_sent": n_unpaired,
            }
        pairing_log[(sd, dd, "_recv_unused")] = {"n_recv_unused": int((~r_used).sum()), "n_recv_total": len(r_sorted)}

    print("  CCTP V2 proximity-window pairing log (Fast<=2h, Standard<=48h, mode from requested side):")
    for key, stats in pairing_log.items():
        if len(key) == 3 and key[2] != "_recv_unused":
            sd, dd, mode = key
            direction = "eth_to_pol" if (sd, dd) == (0, 7) else "pol_to_eth"
            print(f"    {direction} {mode}: sent={stats['n_sent']:,}, paired={stats['n_paired']:,}, unpaired={stats['n_unpaired_sent']}")
        elif len(key) == 3 and key[2] == "_recv_unused":
            sd, dd, _ = key
            direction = "eth_to_pol" if (sd, dd) == (0, 7) else "pol_to_eth"
            print(f"    {direction} receives unused (no Sent matched within window): {stats['n_recv_unused']}/{stats['n_recv_total']}")

    matched = pd.DataFrame(pairs)
    if len(matched) == 0:
        out_idx = pd.date_range(CORPUS_START, CORPUS_END - pd.Timedelta(hours=1), freq="h", tz="UTC")
        return pd.DataFrame(index=out_idx)

    matched["direction"] = matched.apply(
        lambda r: "eth_to_pol" if (r["source_domain"], r["destination_domain"]) == (0, 7) else "pol_to_eth",
        axis=1,
    )
    matched["hour"] = matched["recv_ts"].dt.floor("h")

    # Hourly aggregation per (direction, mode)
    agg = matched.groupby(["hour", "direction", "mode"]).agg(
        n=("latency_s", "size"),
        p50=("latency_s", lambda x: x.quantile(0.50)),
        p90=("latency_s", lambda x: x.quantile(0.90)),
        p99=("latency_s", lambda x: x.quantile(0.99)),
    ).reset_index()

    # Pivot to wide format
    out_idx = pd.date_range(CORPUS_START, CORPUS_END - pd.Timedelta(hours=1), freq="h", tz="UTC")
    out = pd.DataFrame(index=out_idx)

    for direction in ["eth_to_pol", "pol_to_eth"]:
        for mode in ["Fast", "Standard"]:
            sub = agg[(agg["direction"] == direction) & (agg["mode"] == mode)].set_index("hour")
            prefix = f"cctp_v2_{direction}_{mode.lower()}"
            out[f"{prefix}_n"] = sub["n"]
            out[f"{prefix}_p50_s"] = sub["p50"]
            out[f"{prefix}_p90_s"] = sub["p90"]
            out[f"{prefix}_p99_s"] = sub["p99"]

    out = out.fillna({c: 0 for c in out.columns if c.endswith("_n")})
    return out


def parse_incidents_md(path: Path) -> pd.DataFrame:
    """Parse INCIDENTS_2025.md inventory table into a DataFrame of event windows."""
    content = path.read_text(encoding="utf-8")
    rows = []
    # Find the inventory table in section 2
    in_table = False
    headers = None
    for line in content.splitlines():
        if line.strip().startswith("| `") and not in_table:
            in_table = True
            # Find headers from a few lines before, but easier: hard-code the header order
            headers = [
                "event_id", "date_utc_start", "date_utc_end", "chain_scope",
                "incident_type", "tier_A_source_url",
                "hot_window_start_utc", "hot_window_end_utc", "notes",
            ]
        if in_table and line.strip().startswith("| `"):
            cells = [c.strip().strip("`") for c in line.split("|")[1:-1]]
            if len(cells) == len(headers):
                rows.append(dict(zip(headers, cells)))
        elif in_table and not line.strip().startswith("|"):
            if rows:
                break
            in_table = False
    df = pd.DataFrame(rows)
    df["hot_window_start_utc"] = pd.to_datetime(df["hot_window_start_utc"], utc=True)
    df["hot_window_end_utc"] = pd.to_datetime(df["hot_window_end_utc"], utc=True)
    df["extended_start"] = df["hot_window_start_utc"] - pd.Timedelta(hours=6)
    df["extended_end"] = df["hot_window_end_utc"] + pd.Timedelta(hours=6)
    return df


def assemble_combined(eth_hourly: pd.DataFrame, pol_hourly: pd.DataFrame, cctp_hourly: pd.DataFrame) -> pd.DataFrame:
    """Merge ETH, POL, CCTP hourly tables on hour_utc index. Add eth_/pol_ prefixes."""
    def prefix(df, p):
        keep = [
            "rhythm_ratio", "continuity_ratio", "sigma_demand", "size_demand", "tx_demand",
            "rhythm_ratio_ema", "continuity_ratio_ema", "sigma_demand_ema", "size_demand_ema", "tx_demand_ema",
            "rhythm_ratio_shift", "continuity_ratio_shift", "sigma_demand_shift", "size_demand_shift", "tx_demand_shift",
            "drift_structural", "drift_demand", "regime_code", "base_fee_per_gas",
            "ema_warmup",
        ]
        return df[keep].add_prefix(f"{p}_")

    eth_p = prefix(eth_hourly, "eth")
    pol_p = prefix(pol_hourly, "pol")

    out = eth_p.join(pol_p, how="outer").join(cctp_hourly, how="outer")
    # ema_warmup is the same for both chains (same time index); collapse
    out["ema_warmup"] = out["eth_ema_warmup"].fillna(out["pol_ema_warmup"]).astype("boolean")
    out = out.drop(columns=["eth_ema_warmup", "pol_ema_warmup"])
    out.index.name = "hour_utc"
    return out


def build_event_sheets(combined: pd.DataFrame, incidents: pd.DataFrame) -> dict:
    """For each event, slice the combined table to the extended window."""
    sheets = {}
    for _, ev in incidents.iterrows():
        ev_id = ev["event_id"]
        win = (combined.index >= ev["extended_start"]) & (combined.index <= ev["extended_end"])
        sheet = combined[win].copy().reset_index()
        sheet["event_id"] = ev_id
        sheet["in_hot_window"] = (sheet["hour_utc"] >= ev["hot_window_start_utc"]) & (sheet["hour_utc"] <= ev["hot_window_end_utc"])
        sheets[ev_id] = sheet
    return sheets


def build_baseline(combined: pd.DataFrame, incidents: pd.DataFrame) -> pd.DataFrame:
    """Hours of 2025 outside any extended event window."""
    in_any_window = pd.Series(False, index=combined.index)
    for _, ev in incidents.iterrows():
        in_window = (combined.index >= ev["extended_start"]) & (combined.index <= ev["extended_end"])
        in_any_window |= in_window
    baseline = combined[~in_any_window].copy().reset_index()
    return baseline


def write_report(combined: pd.DataFrame, incidents: pd.DataFrame, sheets: dict, baseline: pd.DataFrame, out_path: Path) -> None:
    lines = []
    lines.append("# Report, ETH-POL CCTP V2 Corpus, Step 3")
    lines.append("")
    lines.append("**Status.** Pre-lock draft.")
    lines.append("")
    lines.append("**Contract reference.** `METHODOLOGY.md` §3 Step 3 and `METHODOLOGY_STEP3_CONVENTIONS.md`.")
    lines.append("")
    lines.append("## 1. Corpus scope recap")
    lines.append("")
    lines.append(f"Events in inventory: {len(incidents)}.")
    lines.append(f"Per-event sheets produced: {len(sheets)}.")
    lines.append(f"Baseline hours: {len(baseline)} out of {len(combined)} corpus hours.")
    lines.append("")

    lines.append("## 2. Per-event narrative")
    lines.append("")
    incidents_sorted = incidents.sort_values("hot_window_start_utc")
    for _, ev in incidents_sorted.iterrows():
        ev_id = ev["event_id"]
        sheet = sheets[ev_id]
        hot = sheet[sheet["in_hot_window"]]
        lines.append(f"### {ev_id}")
        lines.append("")
        lines.append(f"Hot window: {ev['hot_window_start_utc']} to {ev['hot_window_end_utc']} UTC.")
        lines.append(f"Extended window hours: {len(sheet)}. Hot window hours: {len(hot)}.")
        lines.append(f"Chain scope: {ev['chain_scope']}. Type: {ev['incident_type']}.")
        lines.append("")
        if len(hot) > 0:
            for chain in ["eth", "pol"]:
                non_s1d1 = hot[hot[f"{chain}_regime_code"].notna() & (hot[f"{chain}_regime_code"] != "S1D1")]
                pct = 100 * len(non_s1d1) / len(hot) if len(hot) > 0 else 0
                lines.append(f"- {chain.upper()} non-S1D1 firing rate during hot window: {len(non_s1d1)}/{len(hot)} hours ({pct:.1f}%).")
                top_codes = hot[f"{chain}_regime_code"].value_counts().head(3)
                if len(top_codes) > 0:
                    lines.append(f"  Top regime codes: " + ", ".join([f"{k}={v}" for k, v in top_codes.items()]))
            corridor_n_eth_pol_fast = hot["cctp_v2_eth_to_pol_fast_n"].sum() if "cctp_v2_eth_to_pol_fast_n" in hot.columns else 0
            corridor_n_eth_pol_std = hot["cctp_v2_eth_to_pol_standard_n"].sum() if "cctp_v2_eth_to_pol_standard_n" in hot.columns else 0
            corridor_n_pol_eth_fast = hot["cctp_v2_pol_to_eth_fast_n"].sum() if "cctp_v2_pol_to_eth_fast_n" in hot.columns else 0
            corridor_n_pol_eth_std = hot["cctp_v2_pol_to_eth_standard_n"].sum() if "cctp_v2_pol_to_eth_standard_n" in hot.columns else 0
            lines.append(f"- CCTP V2 corridor activity during hot window: eth_to_pol Fast={int(corridor_n_eth_pol_fast)} Standard={int(corridor_n_eth_pol_std)}, pol_to_eth Fast={int(corridor_n_pol_eth_fast)} Standard={int(corridor_n_pol_eth_std)}.")
        lines.append("")

    lines.append("## 3. Baseline aggregate distribution")
    lines.append("")
    metric_cols = []
    for chain in ["eth", "pol"]:
        for m in ["rhythm_ratio", "continuity_ratio", "sigma_demand", "size_demand", "tx_demand"]:
            metric_cols.append(f"{chain}_{m}")
    agg = baseline[metric_cols].describe().T
    lines.append("```")
    lines.append(agg.to_string())
    lines.append("```")
    lines.append("")

    lines.append("## 4. Limitations applicable to Step 3")
    lines.append("")
    lines.append("- EMA warmup: January 2025 hours carry `ema_warmup=True`. Interpret with care.")
    lines.append("- POL substrate observation: `rho_ts` reported empirically.")
    lines.append("- Month-only event precision: `POL_HEIMDALL_CONSENSUS_2025_07` and `POL_BOR_RPC_2025_12` span entire months plus padding.")
    lines.append("- POL dataset selection: per MANIFEST.md §Step 2.")
    lines.append("- Convention transparency: formulas in METHODOLOGY_STEP3_CONVENTIONS.md.")
    lines.append("")
    lines.append("## 5. Outputs")
    lines.append("")
    lines.append(f"- {len(sheets)} per-event parquet files in `results/per_event_sheets/`.")
    lines.append(f"- `results/per_event_sheets/baseline.parquet` ({len(baseline)} rows).")
    lines.append("")
    lines.append("End of report.")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    import gc
    BLOCK_COLS = ["number", "timestamp", "gas_used", "transaction_count", "base_fee_per_gas"]

    print("Loading ETH blocks (selected columns)...")
    eth_blocks = pd.read_parquet(DATA / "eth_blocks_2025_raw.parquet", columns=BLOCK_COLS)
    print(f"ETH blocks: {len(eth_blocks):,}")
    print("Computing ETH hourly metrics...")
    eth_hourly = compute_chain_hourly(eth_blocks, "eth")
    print(f"ETH hourly rows: {len(eth_hourly):,}")
    del eth_blocks; gc.collect()

    print("\nLoading POL blocks (selected columns)...")
    pol_blocks = pd.read_parquet(DATA / "pol_blocks_2025_raw.parquet", columns=BLOCK_COLS)
    print(f"POL blocks: {len(pol_blocks):,}")
    print("Computing POL hourly metrics...")
    pol_hourly = compute_chain_hourly(pol_blocks, "pol")
    print(f"POL hourly rows: {len(pol_hourly):,}")
    del pol_blocks; gc.collect()

    print("\nLoading CCTP events...")
    cctp_events = pd.read_parquet(DATA / "cctp_v2_events_2025_raw.parquet")
    print(f"CCTP events: {len(cctp_events):,}")
    print("Computing CCTP V2 hourly latency...")
    cctp_hourly = compute_cctp_hourly_latency(cctp_events)
    print(f"CCTP hourly rows: {len(cctp_hourly):,}")
    del cctp_events; gc.collect()

    print("Assembling combined table...")
    combined = assemble_combined(eth_hourly, pol_hourly, cctp_hourly)
    print(f"Combined rows: {len(combined):,}, columns: {len(combined.columns)}")

    print("Parsing INCIDENTS_2025.md...")
    incidents = parse_incidents_md(PUBLIABLE / "INCIDENTS_2025.md")
    print(f"Incidents parsed: {len(incidents)}")
    for _, ev in incidents.iterrows():
        print(f"  - {ev['event_id']}: {ev['hot_window_start_utc']} to {ev['hot_window_end_utc']}")

    print("\nBuilding per-event sheets...")
    sheets = build_event_sheets(combined, incidents)
    for ev_id, sheet in sheets.items():
        out_path = SHEETS / f"{ev_id}.parquet"
        sheet.to_parquet(out_path, index=False)
        print(f"  {ev_id}.parquet: {len(sheet):,} rows")

    print("\nBuilding baseline sheet...")
    baseline = build_baseline(combined, incidents)
    baseline_path = SHEETS / "baseline.parquet"
    baseline.to_parquet(baseline_path, index=False)
    print(f"  baseline.parquet: {len(baseline):,} rows")

    print("\nWriting REPORT_ETH_POL_CCTP_V2.md...")
    report_path = RESULTS / "REPORT_ETH_POL_CCTP_V2.md"
    write_report(combined, incidents, sheets, baseline, report_path)
    print(f"  Report written to {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
