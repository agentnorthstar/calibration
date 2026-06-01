#!/usr/bin/env python3
"""
BS V2 calibration for the ETH-POL CCTP V2 corridor.

Implements PRE_ENGAGEMENT_BS_CALIBRATION_v1.md strictly. Reads the locked
corpus parquets, computes the empirical P97 of the non-null hourly p90
attestation latency per (source, destination, mode) triplet over the
corridor-active calibration window, applies the confidence partition, and
writes a single signable JSON output.

Inputs (from Step 3 lock):
  results/per_event_sheets/baseline.parquet
  results/per_event_sheets/*.parquet  (12 per-event sheets, hot windows)
  data/cctp_v2_events_2025_bigquery_extract.parquet  (provenance only)

Output:
  results/BS_CALIBRATION_ETH_POL_CCTP_V2.json
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PUBLIABLE = Path(__file__).resolve().parent.parent
DATA = PUBLIABLE / "data"
RESULTS = PUBLIABLE / "results"
SHEETS = RESULTS / "per_event_sheets"

PROTOCOL_VERSION = "BS_CALIBRATION_v1"

# Calibration window (PRE_ENGAGEMENT §3)
WINDOW_START = pd.Timestamp("2025-06-09 18:45:00", tz="UTC")
WINDOW_END = pd.Timestamp("2025-12-31 23:59:00", tz="UTC")

# Quantile (PRE_ENGAGEMENT §4)
QUANTILE = 0.97
INTERPOLATION = "linear"

# Confidence partition (PRE_ENGAGEMENT §4)
CONFIDENCE_HIGH_MIN = 200
CONFIDENCE_MEDIUM_MIN = 50

# Triplet definitions (PRE_ENGAGEMENT §1, §6)
TRIPLETS = [
    {
        "bridge_id":   "ethereum-polygon/cctp/fast",
        "source":      "ethereum",
        "destination": "polygon",
        "mode":        "Fast",
        "col_prefix":  "cctp_v2_eth_to_pol_fast",
    },
    {
        "bridge_id":   "ethereum-polygon/cctp/standard",
        "source":      "ethereum",
        "destination": "polygon",
        "mode":        "Standard",
        "col_prefix":  "cctp_v2_eth_to_pol_standard",
    },
    {
        "bridge_id":   "polygon-ethereum/cctp/fast",
        "source":      "polygon",
        "destination": "ethereum",
        "mode":        "Fast",
        "col_prefix":  "cctp_v2_pol_to_eth_fast",
    },
    {
        "bridge_id":   "polygon-ethereum/cctp/standard",
        "source":      "polygon",
        "destination": "ethereum",
        "mode":        "Standard",
        "col_prefix":  "cctp_v2_pol_to_eth_standard",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def assign_confidence(n_buckets_non_null: int) -> str:
    if n_buckets_non_null >= CONFIDENCE_HIGH_MIN:
        return "HIGH"
    if n_buckets_non_null >= CONFIDENCE_MEDIUM_MIN:
        return "MEDIUM"
    return "LOW"


def load_corpus_matrix() -> tuple[pd.DataFrame, list[Path]]:
    """
    Reconstitute the hourly corpus matrix by concatenating baseline.parquet
    and the per-event sheets. compute_step3.build_baseline excludes extended
    event windows from baseline, so the union partitions the corpus year.
    Overlapping extended windows between adjacent events are deduplicated on
    hour_utc by keeping the first occurrence.
    """
    baseline_path = SHEETS / "baseline.parquet"
    per_event_paths = sorted(
        p for p in SHEETS.glob("*.parquet") if p.name != "baseline.parquet"
    )

    frames = [pd.read_parquet(baseline_path)]
    frames.extend(pd.read_parquet(p) for p in per_event_paths)

    df = pd.concat(frames, ignore_index=True)
    df["hour_utc"] = pd.to_datetime(df["hour_utc"], utc=True)
    df = df.drop_duplicates(subset=["hour_utc"], keep="first")
    df = df.sort_values("hour_utc").reset_index(drop=True)

    return df, [baseline_path, *per_event_paths]


def calibrate_triplets(df: pd.DataFrame) -> tuple[list[dict], int]:
    win_mask = (df["hour_utc"] >= WINDOW_START) & (df["hour_utc"] <= WINDOW_END)
    df_win = df.loc[win_mask]
    n_buckets_total = int(len(df_win))

    out: list[dict] = []
    for triplet in TRIPLETS:
        p90_col = f"{triplet['col_prefix']}_p90_s"
        n_col = f"{triplet['col_prefix']}_n"

        if p90_col not in df_win.columns or n_col not in df_win.columns:
            raise KeyError(
                f"Expected columns missing from corpus matrix: {p90_col}, {n_col}"
            )

        n_attested = df_win[n_col].fillna(0)
        p90_series = df_win[p90_col]
        included = (n_attested >= 1) & p90_series.notna()
        p90_values = p90_series.loc[included].to_numpy(dtype=float)

        n_buckets_non_null = int(included.sum())

        if n_buckets_non_null == 0:
            threshold = None
        else:
            threshold = float(np.quantile(p90_values, QUANTILE, method=INTERPOLATION))

        out.append({
            "bridge_id":                 triplet["bridge_id"],
            "source":                    triplet["source"],
            "destination":               triplet["destination"],
            "mode":                      triplet["mode"],
            "threshold_bs1_s":           threshold,
            "n_buckets_non_null":        n_buckets_non_null,
            "n_buckets_total_in_window": n_buckets_total,
            "confidence":                assign_confidence(n_buckets_non_null),
        })

    return out, n_buckets_total


def main() -> None:
    df_corpus, parquet_paths = load_corpus_matrix()
    thresholds, n_buckets_total = calibrate_triplets(df_corpus)

    parquets_sha256: dict[str, str] = {
        p.name: sha256_file(p) for p in parquet_paths
    }
    raw_extract = DATA / "cctp_v2_events_2025_bigquery_extract.parquet"
    if raw_extract.exists():
        parquets_sha256[raw_extract.name] = sha256_file(raw_extract)

    manifest_path = PUBLIABLE / "MANIFEST.md"
    manifest_sha256 = sha256_file(manifest_path) if manifest_path.exists() else None

    output = {
        "protocol_version": PROTOCOL_VERSION,
        "corpus_reference": (
            f"ETH-POL-CCTP-V2 publiable corpus, MANIFEST.md sha-256 {manifest_sha256}"
        ),
        "calibration_window_start_utc": WINDOW_START.isoformat().replace("+00:00", "Z"),
        "calibration_window_end_utc":   WINDOW_END.isoformat().replace("+00:00", "Z"),
        "method": (
            "P97 of non-null hourly p90 latency, per (source, destination, mode), "
            "linear interpolation"
        ),
        "thresholds": thresholds,
        "script_sha256": sha256_file(Path(__file__)),
        "input_parquets_sha256": parquets_sha256,
    }

    out_path = RESULTS / "BS_CALIBRATION_ETH_POL_CCTP_V2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote {out_path}")
    print(f"Calibration window total buckets: {n_buckets_total}")
    for t in thresholds:
        thr = (
            f"{t['threshold_bs1_s']:.3f}s"
            if t["threshold_bs1_s"] is not None
            else "n/a"
        )
        print(
            f"  {t['bridge_id']}: threshold_bs1_s={thr} "
            f"(n_non_null={t['n_buckets_non_null']}, confidence={t['confidence']})"
        )


if __name__ == "__main__":
    main()
