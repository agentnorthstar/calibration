#!/usr/bin/env python3
"""
Step 2 BigQuery extraction for the ETH-POL CCTP V2 corpus.

Produces three raw parquet artefacts in publiable/data/:
  - eth_blocks_2025_raw.parquet
  - pol_blocks_2025_raw.parquet
  - cctp_v2_events_2025_raw.parquet

Datasets:
  - bigquery-public-data.crypto_ethereum            (ETH, active)
  - bigquery-public-data.goog_blockchain_polygon_mainnet_us  (POL, active; crypto_polygon is frozen 2024-09)

Contract reference: METHODOLOGY.md §3 Step 2.
Pre-requisites: gcloud auth login + gcloud auth application-default login.
"""
from pathlib import Path
import hashlib
import sys

from google.cloud import bigquery

CLIENT = bigquery.Client()
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CCTP_V2_ADDRESSES = (
    "'0x28b5a0e9c621a5badaa536219b3a228c8168cf5d'",  # TokenMessengerV2
    "'0x81d40f21f12a8f0e3252bccb954d722d4c464b64'",  # MessageTransmitterV2
)
CCTP_V2_TOPICS = (
    "'0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5'",  # DepositForBurn V2
    "'0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c'",  # MessageReceived V2
    "'0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'",  # MessageSent V2
)

QUERIES = {
    "eth_blocks_2025_raw.parquet": f"""
        SELECT
          number,
          `hash`,
          `parent_hash`,
          `timestamp`,
          gas_used,
          gas_limit,
          transaction_count,
          base_fee_per_gas,
          size
        FROM `bigquery-public-data.crypto_ethereum.blocks`
        WHERE `timestamp` >= TIMESTAMP('2025-01-01 00:00:00 UTC')
          AND `timestamp` <  TIMESTAMP('2026-01-01 00:00:00 UTC')
        ORDER BY number ASC
    """,
    "pol_blocks_2025_raw.parquet": f"""
        SELECT
          b.block_number       AS number,
          b.block_hash         AS `hash`,
          b.parent_hash,
          b.block_timestamp    AS `timestamp`,
          b.gas_used,
          b.gas_limit,
          COALESCE(tx.tx_count, 0) AS transaction_count,
          b.base_fee_per_gas
        FROM `bigquery-public-data.goog_blockchain_polygon_mainnet_us.blocks` b
        LEFT JOIN (
          SELECT block_hash, COUNT(*) AS tx_count
          FROM `bigquery-public-data.goog_blockchain_polygon_mainnet_us.transactions`
          WHERE block_timestamp >= TIMESTAMP('2025-01-01 00:00:00 UTC')
            AND block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
          GROUP BY block_hash
        ) tx ON tx.block_hash = b.block_hash
        WHERE b.block_timestamp >= TIMESTAMP('2025-01-01 00:00:00 UTC')
          AND b.block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
        ORDER BY b.block_number ASC
    """,
    "cctp_v2_events_2025_raw.parquet": f"""
        SELECT
          'ethereum' AS chain,
          block_number,
          block_timestamp,
          transaction_hash,
          log_index,
          address AS contract_address,
          topics,
          data
        FROM `bigquery-public-data.crypto_ethereum.logs`
        WHERE block_timestamp >= TIMESTAMP('2025-02-11 00:00:00 UTC')
          AND block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
          AND LOWER(address) IN ({", ".join(CCTP_V2_ADDRESSES)})
          AND ARRAY_LENGTH(topics) >= 1
          AND topics[OFFSET(0)] IN ({", ".join(CCTP_V2_TOPICS)})

        UNION ALL

        SELECT
          'polygon' AS chain,
          block_number,
          block_timestamp,
          transaction_hash,
          log_index,
          address AS contract_address,
          topics,
          data
        FROM `bigquery-public-data.goog_blockchain_polygon_mainnet_us.logs`
        WHERE block_timestamp >= TIMESTAMP('2025-06-09 00:00:00 UTC')
          AND block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
          AND LOWER(address) IN ({", ".join(CCTP_V2_ADDRESSES)})
          AND ARRAY_LENGTH(topics) >= 1
          AND topics[OFFSET(0)] IN ({", ".join(CCTP_V2_TOPICS)})

        ORDER BY chain, block_number ASC, log_index ASC
    """,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    print(f"Output dir: {OUT_DIR}")
    results = []
    import pyarrow.parquet as pq

    for filename, sql in QUERIES.items():
        out_path = OUT_DIR / filename
        print(f"\n=== {filename} ===")
        print("Submitting query to BigQuery...")
        job = CLIENT.query(sql)
        rows = job.result()
        print(f"Query state            : {job.state}")
        print(f"Bytes processed (billed): {job.total_bytes_processed:,}")
        print(f"Total rows in result   : {rows.total_rows:,}")
        print("Downloading via BQ Storage API and streaming to parquet...")
        arrow_table = rows.to_arrow(create_bqstorage_client=True)
        pq.write_table(arrow_table, out_path, compression="snappy")
        size = out_path.stat().st_size
        sha = sha256_file(out_path)
        print(f"Path  : {out_path}")
        print(f"Size  : {size:,} bytes")
        print(f"SHA256: {sha}")
        results.append((filename, rows.total_rows, size, sha))

    print("\n=== Summary ===")
    for filename, rows, size, sha in results:
        print(f"{filename:40s} {rows:>12,} rows  {size:>14,} bytes  sha256={sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
