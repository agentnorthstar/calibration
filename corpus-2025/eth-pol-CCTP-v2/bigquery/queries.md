# BigQuery Extracts, Step 2

**Status.** Draft, pre-execution. Awaiting query runs by the corpus author.

**Date drafted.** 2026-05-25.

**Contract reference.** This file documents the raw BigQuery extracts required by `METHODOLOGY.md` §3 Step 2, locked 2026-05-25, SHA-256 `1b0ef577733d1bb05b372547e26f0c633b6a1e4873fa2d67e1c640c2f51c67e7`.

**Datasets used.**
- `bigquery-public-data.crypto_ethereum` (blocks + logs). Verified active as of 2026-05-25.
- `bigquery-public-data.goog_blockchain_polygon_mainnet_us` (blocks + logs + transactions). Verified active as of 2026-05-25 with coverage through 2026-05-25 20:39 UTC, 87M blocks total.

**Polygon dataset selection.** POL queries source from `bigquery-public-data.goog_blockchain_polygon_mainnet_us` (Google Blockchain Analytics, actively maintained, coverage through 2026-05-25). The `bigquery-public-data.crypto_polygon` dataset is not used: its coverage ends at block timestamp 2024-09-01 23:59:58 UTC and does not include the 2025 corpus window. The `goog_blockchain_*` schema names block-related columns `block_number`, `block_hash`, `block_timestamp`; the POL queries apply aliases (`AS number`, `AS hash`, `AS timestamp`) to match the canonical column names used by the ETH parquet. The `transaction_count` column is not exposed directly on the `goog_blockchain_*` blocks table and is computed via LEFT JOIN on the `transactions` table over the same time window.

---

## 1. Phase 0 inputs (verified 2026-05-25)

### Contract addresses, CCTP V2

| Chain | Contract | Proxy address | Implementation | Creation block | Creation UTC |
|---|---|---|---|---|---|
| Ethereum mainnet | TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `0x555E2725506c06e7e559d57418563742afe363ec8` | 21,819,733 | 2025-02-11 00:35:11 |
| Ethereum mainnet | MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | `0xa30c41865729c248067704d4db9f38385cbe1186` | 21,819,729 | 2025-02-11 00:34:23 |
| Polygon PoS mainnet | TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `0x555e272506c06e7e559d57418563742afe363ec8` | 72,566,047 | 2025-06-09 18:45:11 |
| Polygon PoS mainnet | MessageTransmitterV2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | `0xd40518c1a3139e8f1f73f83e5de74e05c88f5ad3` | 72,566,046 | 2025-06-09 18:45:09 |

Common deployer: `0xadb384f7fa7486422051d2a896417eaab9e5a9d1`.

CCTP domain IDs: Ethereum = 0, Polygon = 7.

Sources verified at draft time:
- Circle official docs: https://developers.circle.com/cctp/evm-smart-contracts
- Etherscan: https://etherscan.io/address/0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
- Etherscan: https://etherscan.io/address/0x81D40F21F12A8F0E3252Bccb954D722d4c464B64
- PolygonScan: https://polygonscan.com/address/0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d
- PolygonScan: https://polygonscan.com/address/0x81D40F21F12A8F0E3252Bccb954D722d4c464B64

### Event ABIs, CCTP V2

Source: `https://raw.githubusercontent.com/circlefin/evm-cctp-contracts/master/src/v2/TokenMessengerV2.sol` and `MessageTransmitterV2.sol`.

```solidity
// Emitted on source chain by TokenMessengerV2
event DepositForBurn(
    address indexed burnToken,            // topic1
    uint256 amount,                       // data
    address indexed depositor,            // topic2
    bytes32 mintRecipient,                // data
    uint32 destinationDomain,             // data
    bytes32 destinationTokenMessenger,    // data
    bytes32 destinationCaller,            // data
    uint256 maxFee,                       // data
    uint32 indexed minFinalityThreshold,  // topic3
    bytes hookData                        // data
);

// Emitted on source chain by MessageTransmitterV2 (companion of DepositForBurn)
event MessageSent(
    bytes message                         // data: the full cross-chain message
);

// CCTP V2 message header layout (bytes inside MessageSent.message and MessageReceived.messageBody):
//   [0:4]     version              (uint32)
//   [4:8]     sourceDomain         (uint32)
//   [8:12]    destinationDomain    (uint32)
//   [12:44]   nonce                (bytes32)
//   [44:76]   sender               (bytes32)
//   [76:108]  recipient            (bytes32)
//   [108:140] destinationCaller    (bytes32)
//   [140:144] minFinalityThreshold (uint32)
//   [144:148] finalityThresholdExecuted (uint32)
//   [148:]    messageBody          (variable bytes)

// Emitted on destination chain by MessageTransmitterV2
event MessageReceived(
    address indexed caller,                       // topic1
    uint32 sourceDomain,                          // data
    bytes32 indexed nonce,                        // topic2
    bytes32 sender,                               // data
    uint32 indexed finalityThresholdExecuted,     // topic3
    bytes messageBody                             // data
);
```

**Why MessageSent is extracted.** The `nonce` field is not present in the `DepositForBurn V2` ABI. It is carried by the companion `MessageSent` event, in the bytes header of the `message` field. Matching source-side burn activity to destination-side receive activity by nonce therefore requires extracting `MessageSent` events from the source chain. `DepositForBurn` and `MessageSent` are emitted in the same transaction; their `block_number` and `transaction_hash` are identical, which allows joining the two source-side events post-extraction.

### Topic hashes (keccak256 of event signature)

Computed locally with pycryptodome at draft time.

| Event | Signature | topic0 |
|---|---|---|
| DepositForBurn V2 | `DepositForBurn(address,uint256,address,bytes32,uint32,bytes32,bytes32,uint256,uint32,bytes)` | `0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5` |
| MessageSent V2 | `MessageSent(bytes)` | `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036` |
| MessageReceived V2 | `MessageReceived(address,uint32,bytes32,bytes32,uint32,bytes)` | `0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c` |

All three events are extracted into the CCTP V2 events parquet.

### Effective extraction windows

| Extraction | Window | Justification |
|---|---|---|
| ETH blocks | 2025-01-01 → 2025-12-31 | Independent of CCTP V2 |
| POL blocks | 2025-01-01 → 2025-12-31 | Independent of CCTP V2 |
| CCTP V2 events ETH | 2025-02-11 → 2025-12-31 | Earliest contract creation on ETH |
| CCTP V2 events POL | 2025-06-09 → 2025-12-31 | Earliest contract creation on POL |
| ETH↔POL corridor effective | 2025-06-09 → 2025-12-31 | Intersection. Documented in LIMITATIONS.md |

---

## 2. Query 1, ETH blocks 2025

**Output target:** `data/eth_blocks_2025_raw.parquet`

```sql
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
```

The identifiers `hash`, `parent_hash`, `timestamp` are backtick-quoted because `hash` is a reserved keyword in BigQuery Standard SQL; the others are quoted for consistency.

Expected row count order: approximately 2.6 million Ethereum blocks for the year.

---

## 3. Query 2, POL blocks 2025

**Output target:** `data/pol_blocks_2025_raw.parquet`

```sql
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
```

The aliases `\`hash\`` and `\`timestamp\`` are backtick-quoted because `hash` and `timestamp` are reserved keywords in BigQuery Standard SQL, including when used as aliases.

Schema aliases (`block_number AS number`, `block_hash AS hash`, `block_timestamp AS timestamp`) restore the canonical column names used by the corpus, matching the schema of the ETH blocks parquet.

The LEFT JOIN on the `transactions` table computes `transaction_count` per block, since the `goog_blockchain_polygon_mainnet_us.blocks` table does not expose this column directly. The subquery scans the transactions table within the same time window. Approximate scan cost is documented in the execution procedure (§6).

Expected row count order: approximately 14 to 16 million Polygon blocks for the year.

Note: the `size` column is intentionally omitted per the contract §3 Step 2. The `crypto_polygon.blocks` table does not expose a stable `size` column with the same semantics as `crypto_ethereum.blocks`.

---

## 4. Query 3, CCTP V2 raw events ETH + POL

**Output target:** `data/cctp_v2_events_2025_raw.parquet`

Raw extraction joining both chains via UNION ALL. The `chain` column identifies the source. The two event types (DepositForBurn V2 on source side and MessageReceived V2 on destination side) are extracted in the same parquet; downstream decoding distinguishes them by `topics[0]`.

```sql
SELECT
  'ethereum'             AS chain,
  block_number,
  block_timestamp,
  transaction_hash,
  log_index,
  address                AS contract_address,
  topics,
  data
FROM `bigquery-public-data.crypto_ethereum.logs`
WHERE block_timestamp >= TIMESTAMP('2025-02-11 00:00:00 UTC')
  AND block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
  AND LOWER(address) IN (
    '0x28b5a0e9c621a5badaa536219b3a228c8168cf5d',
    '0x81d40f21f12a8f0e3252bccb954d722d4c464b64'
  )
  AND ARRAY_LENGTH(topics) >= 1
  AND topics[OFFSET(0)] IN (
    '0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5',
    '0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c',
    '0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'
  )

UNION ALL

SELECT
  'polygon'              AS chain,
  block_number,
  block_timestamp,
  transaction_hash,
  log_index,
  address                AS contract_address,
  topics,
  data
FROM `bigquery-public-data.goog_blockchain_polygon_mainnet_us.logs`
WHERE block_timestamp >= TIMESTAMP('2025-06-09 00:00:00 UTC')
  AND block_timestamp <  TIMESTAMP('2026-01-01 00:00:00 UTC')
  AND LOWER(address) IN (
    '0x28b5a0e9c621a5badaa536219b3a228c8168cf5d',
    '0x81d40f21f12a8f0e3252bccb954d722d4c464b64'
  )
  AND ARRAY_LENGTH(topics) >= 1
  AND topics[OFFSET(0)] IN (
    '0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5',
    '0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c',
    '0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'
  )

ORDER BY chain, block_number ASC, log_index ASC
```

The POL part of the UNION uses `bigquery-public-data.goog_blockchain_polygon_mainnet_us.logs` per §1 (Polygon dataset selection). The columns `block_number`, `block_timestamp`, `transaction_hash`, `log_index`, `address`, `topics`, `data` exist with the same names and types on both `crypto_ethereum.logs` and `goog_blockchain_polygon_mainnet_us.logs`, so the union is type-compatible without further aliasing.

Expected row count order: low thousands to low tens of thousands, depending on CCTP V2 traffic on the corridor over the period.

---

## 5. Post-extraction ABI decoding

The BigQuery output is raw `(topics, data)` per log. The decoded fields required by the corpus schema are derived from the ABI documented in §1 above. Decoding is performed by the script `scripts/decode_cctp_v2_events.py` (to be committed under `publiable/scripts/`).

The decoded parquet `data/cctp_v2_events_2025_raw.parquet` exposes the following columns post-decoding:

```
chain                       string  (ethereum | polygon)
contract_address            string
event_name                  string  (DepositForBurn | MessageReceived)
block_number                int64
block_timestamp             timestamp
transaction_hash            string
log_index                   int64
# DepositForBurn-specific (NULL on MessageReceived rows)
burn_token                  string  (topic1, address)
depositor                   string  (topic2, address)
min_finality_threshold      int64   (topic3, uint32)
amount                      string  (data, uint256, as decimal string)
mint_recipient              string  (data, bytes32)
destination_domain          int64   (data, uint32)
destination_token_messenger string  (data, bytes32)
destination_caller          string  (data, bytes32)
max_fee                     string  (data, uint256, as decimal string)
hook_data                   string  (data, bytes, hex)
# MessageReceived-specific (NULL on DepositForBurn rows)
caller                      string  (topic1, address)
nonce                       string  (topic2, bytes32)
finality_threshold_executed int64   (topic3, uint32)
source_domain               int64   (data, uint32)
sender                      string  (data, bytes32)
message_body                string  (data, bytes, hex)
```

The decoding logic strictly follows the indexed/non-indexed flags of §1. The `amount` and `max_fee` `uint256` values are stored as decimal strings to preserve precision (parquet does not natively support 256-bit integers).

---

## 6. Execution procedure

1. Each query is executed in the BigQuery console (or via `bq query --use_legacy_sql=false`) by the corpus author.
2. For each query, the result is exported to a parquet file in the target path under `publiable/data/`.
3. Row count and SHA-256 hash of each parquet are recorded in `publiable/MANIFEST.md` §Step 2.
4. The raw CCTP V2 events parquet is then passed through `scripts/decode_cctp_v2_events.py` to produce the decoded `cctp_v2_events_2025_raw.parquet`. The raw and decoded files are both retained.

Alternative orchestration: the three queries are independent and can be executed in parallel.

---

## 7. Nonce uniqueness check, pre-lock

Before Step 2 is signed, the decoded CCTP V2 events parquet is checked for `nonce` uniqueness per `(source_domain, destination_domain)` pair on the MessageReceived rows. Each MessageReceived row must correspond to at most one DepositForBurn row under the same nonce and domain pair.

Procedure:

```python
import pandas as pd
df = pd.read_parquet('data/cctp_v2_events_2025_raw.parquet')
received = df[df.event_name == 'MessageReceived']
duplicates = received.groupby(['source_domain', 'nonce']).size()
duplicates = duplicates[duplicates > 1]
if not duplicates.empty:
    print("Duplicate nonces detected:")
    print(duplicates)
```

If duplicates exist, they are enumerated in `MANIFEST.md` §Step 2 with their root cause (replay, retry, contract migration, missing receive event) before the lock signature is applied.

---

## 8. Lock procedure

Once the three parquets and this `queries.md` are produced and the nonce uniqueness check is recorded:

1. Compute SHA-256 of each artefact:
   - `data/eth_blocks_2025_raw.parquet`
   - `data/pol_blocks_2025_raw.parquet`
   - `data/cctp_v2_events_2025_raw.parquet`
   - `bigquery/queries.md`
2. Record the four hashes in `MANIFEST.md` §Step 2.
3. Ed25519 signature with key 1 from the contract Step 0 set, namespace `invarians_corpus_eth_pol_cctp_v2_step2`.
4. Step 2 is locked. Step 3 may begin.

End of queries.md.
