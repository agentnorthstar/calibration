"""Pull OP CCTP DepositForBurn + MessageReceived events for 2025, split by quarter.

Outputs parquet files under data/cctp_events/ mirroring the ARB convention :
  op_burns_2025-Q{1-4}.parquet
  op_receives_2025-Q{1-4}.parquet

Uses the BigQuery Python client (no UI export limit). Authenticated via
gcloud application-default credentials. Each query is parametrized; address
literals are passed as ScalarQueryParameter to avoid injection.

Run:
  python scripts/pull_op_cctp.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "cctp_events"
DATA.mkdir(parents=True, exist_ok=True)

# OP CCTP V1 mainnet
OP_TOKEN_MESSENGER_V1     = "0x2B4069517957735bE00ceE0fadAE88a26365528f"
OP_MESSAGE_TRANSMITTER_V1 = "0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8"

TOPIC_DEPOSIT_FOR_BURN  = "0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0"
TOPIC_MESSAGE_RECEIVED  = "0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d"

OP_LOGS_TABLE = "`bigquery-public-data.goog_blockchain_optimism_mainnet_us.logs`"


QUARTERS = [
    ("2025-Q1", datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 4, 1, tzinfo=timezone.utc)),
    ("2025-Q2", datetime(2025, 4, 1, tzinfo=timezone.utc), datetime(2025, 7, 1, tzinfo=timezone.utc)),
    ("2025-Q3", datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2025, 10, 1, tzinfo=timezone.utc)),
    ("2025-Q4", datetime(2025, 10, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
]


SQL_BURNS = f"""
SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  topics,
  data
FROM {OP_LOGS_TABLE}
WHERE block_timestamp >= @start_ts
  AND block_timestamp <  @end_ts
  AND LOWER(address) = LOWER(@addr)
  AND ARRAY_LENGTH(topics) >= 4
  AND topics[OFFSET(0)] = @topic0
ORDER BY block_timestamp, log_index
"""

SQL_RECEIVES = f"""
SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  topics,
  data
FROM {OP_LOGS_TABLE}
WHERE block_timestamp >= @start_ts
  AND block_timestamp <  @end_ts
  AND LOWER(address) = LOWER(@addr)
  AND ARRAY_LENGTH(topics) >= 3
  AND topics[OFFSET(0)] = @topic0
ORDER BY block_timestamp, log_index
"""


def pull(client: bigquery.Client, sql: str, addr: str, topic0: str,
         start_ts: datetime, end_ts: datetime) -> pd.DataFrame:
    config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("start_ts", "TIMESTAMP", start_ts),
        bigquery.ScalarQueryParameter("end_ts",   "TIMESTAMP", end_ts),
        bigquery.ScalarQueryParameter("addr",     "STRING",    addr),
        bigquery.ScalarQueryParameter("topic0",   "STRING",    topic0),
    ])
    return client.query(sql, job_config=config).result().to_dataframe(
        create_bqstorage_client=False,
    )


def main():
    client = bigquery.Client()
    print(f"Project: {client.project}")

    for label, start_ts, end_ts in QUARTERS:
        print(f"\n=== {label} : {start_ts.date()} -> {end_ts.date()} ===")

        burns_path = DATA / f"op_burns_{label}.parquet"
        if burns_path.exists():
            print(f"  burns: cached at {burns_path.name}")
        else:
            print(f"  burns: pulling…")
            df = pull(client, SQL_BURNS, OP_TOKEN_MESSENGER_V1,
                      TOPIC_DEPOSIT_FOR_BURN, start_ts, end_ts)
            df.to_parquet(burns_path)
            print(f"  burns: {len(df)} rows -> {burns_path.name}")

        receives_path = DATA / f"op_receives_{label}.parquet"
        if receives_path.exists():
            print(f"  receives: cached at {receives_path.name}")
        else:
            print(f"  receives: pulling…")
            df = pull(client, SQL_RECEIVES, OP_MESSAGE_TRANSMITTER_V1,
                      TOPIC_MESSAGE_RECEIVED, start_ts, end_ts)
            df.to_parquet(receives_path)
            print(f"  receives: {len(df)} rows -> {receives_path.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
