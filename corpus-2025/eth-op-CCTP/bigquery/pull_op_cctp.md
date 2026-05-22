# BigQuery Queries for ETH-OP-CCTP V1 Event Extraction

This document records the SQL queries embedded in `scripts/pull_op_cctp.py` used to pull Optimism mainnet CCTP V1 events for 2025, split by calendar quarter. The same script handles authentication via Google application-default credentials and writes parquet output under `data/cctp_events/`.

## Source dataset

```
bigquery-public-data.goog_blockchain_optimism_mainnet_us.logs
```

A Google-maintained public BigQuery dataset for Optimism mainnet, equivalent to `bigquery-public-data.crypto_ethereum` for L1.

## Contract addresses (Optimism mainnet, CCTP V1)

| Contract | Address |
|---|---|
| TokenMessenger V1 (burn side) | `0x2B4069517957735bE00ceE0fadAE88a26365528f` |
| MessageTransmitter V1 (receive side) | `0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8` |

CCTP V1 domain id for Optimism: `2`. The corresponding ETH domain is `0`.

## Topic identifiers (event log topic[0])

| Event | Topic |
|---|---|
| `DepositForBurn` | `0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0` |
| `MessageReceived` | `0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d` |

## Quarterly windows

Each quarter is queried separately with a half-open time interval `[start, end)`:

| Label | Start (UTC) | End (UTC) |
|---|---|---|
| 2025-Q1 | 2025-01-01 00:00 | 2025-04-01 00:00 |
| 2025-Q2 | 2025-04-01 00:00 | 2025-07-01 00:00 |
| 2025-Q3 | 2025-07-01 00:00 | 2025-10-01 00:00 |
| 2025-Q4 | 2025-10-01 00:00 | 2026-01-01 00:00 |

## Query 1: DepositForBurn (OP burns)

```sql
SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  topics,
  data
FROM `bigquery-public-data.goog_blockchain_optimism_mainnet_us.logs`
WHERE block_timestamp >= @start_ts
  AND block_timestamp <  @end_ts
  AND LOWER(address) = LOWER(@addr)
  AND ARRAY_LENGTH(topics) >= 4
  AND topics[OFFSET(0)] = @topic0
ORDER BY block_timestamp, log_index
```

Parameters:
- `start_ts`, `end_ts`: quarter boundaries
- `addr`: `0x2B4069517957735bE00ceE0fadAE88a26365528f` (TokenMessenger V1 on OP)
- `topic0`: DepositForBurn topic

The `topics ARRAY_LENGTH >= 4` filter keeps only indexed DepositForBurn events, which expose nonce, burnToken, depositor, and mintRecipient as indexed parameters in topics 1 to 3.

## Query 2: MessageReceived (OP receives)

```sql
SELECT
  block_timestamp,
  block_number,
  transaction_hash,
  log_index,
  topics,
  data
FROM `bigquery-public-data.goog_blockchain_optimism_mainnet_us.logs`
WHERE block_timestamp >= @start_ts
  AND block_timestamp <  @end_ts
  AND LOWER(address) = LOWER(@addr)
  AND ARRAY_LENGTH(topics) >= 3
  AND topics[OFFSET(0)] = @topic0
ORDER BY block_timestamp, log_index
```

Parameters:
- `addr`: `0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8` (MessageTransmitter V1 on OP)
- `topic0`: MessageReceived topic

The `topics ARRAY_LENGTH >= 3` filter keeps MessageReceived events, where caller, sourceDomain, and nonce are indexed.

## Message pairing

The downstream pipeline (`scripts/build_op_pipeline.py`) decodes both event types, extracts the `(source_domain, destination_domain, nonce)` tuple, and matches:

- ETH-to-OP messages: `DepositForBurn` on Ethereum L1 paired with `MessageReceived` on Optimism, source_domain=0 and destination_domain=2.
- OP-to-ETH messages: `DepositForBurn` on Optimism paired with `MessageReceived` on Ethereum L1, source_domain=2 and destination_domain=0.

Per-message attestation latency is computed as the difference between burn and receive block timestamps. Hourly p50, p90, p99 are aggregated, then the BS1 threshold is calibrated as the P97 of attestation_latency_p90_s over the first 14 days of January 2025.

## BigQuery cost note

Each quarterly query scans approximately 25 GB of the OP logs table. Four quarters per side, two sides (burns + receives), four queries total: approximately 200 GB per full pull. This sits within the BigQuery 1 TB per month free quota.

## Output

Parquet files written under `data/cctp_events/`:

```
op_burns_2025-Q1.parquet      ... op_burns_2025-Q4.parquet
op_receives_2025-Q1.parquet   ... op_receives_2025-Q4.parquet
```

These are raw event logs (topics + data hex). Decoding into structured columns (nonce, sourceDomain, destinationDomain, latency_s) is done by `lib/decode_cctp.py` invoked from `scripts/build_op_pipeline.py`.
