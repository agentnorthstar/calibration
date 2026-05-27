#!/usr/bin/env python3
"""
Step 2 — Decode raw CCTP V2 events parquet according to METHODOLOGY.md §3 Step 2.

Input
-----
data/cctp_v2_events_2025_raw.parquet
    BigQuery raw extract with columns:
        chain, block_number, block_timestamp, transaction_hash,
        log_index, contract_address, topics (array<string>), data (string)

Output
------
data/cctp_v2_events_2025_bigquery_extract.parquet
    The input file renamed in place, kept as traceability of the raw BigQuery extract.

data/cctp_v2_events_2025_raw.parquet
    Decoded parquet with the 15 columns named by the contract:
        chain, contract_address, event_name,
        block_number, block_timestamp, transaction_hash, log_index,
        nonce, source_domain, destination_domain, amount,
        mint_recipient, burn_token, min_finality_threshold, message_hash

Decoding rules
--------------
DepositForBurn V2 (emitted on source chain by TokenMessengerV2):
    topics[1] -> burn_token (address indexed)
    topics[2] -> depositor (address indexed)  (not in contract spec, skipped)
    topics[3] -> min_finality_threshold (uint32 indexed)
    data      -> amount (uint256), mint_recipient (bytes32),
                 destination_domain (uint32), destination_token_messenger (bytes32, skipped),
                 destination_caller (bytes32, skipped), max_fee (uint256, skipped),
                 hook_data (bytes, skipped)
    source_domain      = DOMAIN_ID[chain]   (derived from emitting chain)
    nonce              = NULL               (not present in DepositForBurn V2 ABI)
    message_hash       = NULL               (would require MessageSent companion; out of scope)

MessageReceived V2 (emitted on destination chain by MessageTransmitterV2):
    topics[1] -> caller (address indexed)  (not in contract spec, skipped)
    topics[2] -> nonce (bytes32 indexed)
    topics[3] -> finality_threshold_executed (uint32 indexed). Stored in
                 min_finality_threshold to reuse the contract column.
    data      -> source_domain (uint32), sender (bytes32, skipped),
                 message_body (bytes)
    destination_domain = DOMAIN_ID[chain]   (derived from receiving chain)
    amount, mint_recipient, burn_token = NULL (carried by message_body header, not parsed here)
    message_hash       = keccak256(message_body)

Limitations recorded for LIMITATIONS.md
---------------------------------------
1. Nonce is only available on MessageReceived rows. DepositForBurn nonce is not in the
   V2 event ABI and is not recovered here. Matching DepositForBurn <-> MessageReceived
   per nonce is therefore not implemented at this step.
2. amount / mint_recipient / burn_token are populated on DepositForBurn rows and NULL on
   MessageReceived rows. They live in MessageReceived.message_body header but are not
   decoded here to keep this step strictly aligned with the columns named by the contract.
3. min_finality_threshold stores the requested threshold for DepositForBurn rows and the
   executed threshold for MessageReceived rows. The two are not the same field but share
   the column for compactness; the event_name column allows disambiguation.
"""
from pathlib import Path
import hashlib
import sys

import pandas as pd
from eth_abi import decode as abi_decode
from Crypto.Hash import keccak

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INPUT_PATH = DATA_DIR / "cctp_v2_events_2025_raw.parquet"
RAW_BACKUP_PATH = DATA_DIR / "cctp_v2_events_2025_bigquery_extract.parquet"
OUTPUT_PATH = DATA_DIR / "cctp_v2_events_2025_raw.parquet"

TOPIC_DEPOSIT_FOR_BURN = "0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5"
TOPIC_MESSAGE_RECEIVED = "0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c"
TOPIC_MESSAGE_SENT = "0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036"

DOMAIN_ID = {"ethereum": 0, "polygon": 7}


def k256(b: bytes) -> str:
    h = keccak.new(digest_bits=256)
    h.update(b)
    return "0x" + h.hexdigest()


def addr_from_topic(topic_hex):
    if topic_hex is None:
        return None
    return "0x" + topic_hex[-40:].lower()


def uint_from_topic(topic_hex):
    return int(topic_hex, 16)


def hex_to_bytes(hex_str):
    if hex_str.startswith("0x"):
        return bytes.fromhex(hex_str[2:])
    return bytes.fromhex(hex_str)


def decode_deposit_for_burn(row):
    topics = row["topics"]
    burn_token = addr_from_topic(topics[1])
    min_finality_threshold = uint_from_topic(topics[3])

    data = hex_to_bytes(row["data"])
    decoded = abi_decode(
        ["uint256", "bytes32", "uint32", "bytes32", "bytes32", "uint256", "bytes"],
        data,
    )
    amount = str(decoded[0])
    mint_recipient = "0x" + decoded[1].hex()
    destination_domain = int(decoded[2])

    chain = row["chain"]
    source_domain = DOMAIN_ID.get(chain)

    return {
        "chain": chain,
        "contract_address": row["contract_address"],
        "event_name": "DepositForBurn",
        "block_number": int(row["block_number"]),
        "block_timestamp": row["block_timestamp"],
        "transaction_hash": row["transaction_hash"],
        "log_index": int(row["log_index"]),
        "nonce": None,
        "source_domain": source_domain,
        "destination_domain": destination_domain,
        "amount": amount,
        "mint_recipient": mint_recipient,
        "burn_token": burn_token,
        "min_finality_threshold": min_finality_threshold,
        "message_hash": None,
    }


def decode_message_sent(row):
    """
    MessageSent V2:
      data: bytes message (the full cross-chain message ABI-encoded)

    Message format (CCTP V2 header + body):
      [0:4]    version (uint32)
      [4:8]    sourceDomain (uint32)
      [8:12]   destinationDomain (uint32)
      [12:44]  nonce (bytes32)
      [44:76]  sender (bytes32)
      [76:108] recipient (bytes32)
      [108:140] destinationCaller (bytes32)
      [140:144] minFinalityThreshold (uint32)
      [144:148] finalityThresholdExecuted (uint32)
      [148:]   messageBody (variable)
    """
    data = hex_to_bytes(row["data"])
    (message_bytes,) = abi_decode(["bytes"], data)

    source_domain = int.from_bytes(message_bytes[4:8], "big")
    destination_domain = int.from_bytes(message_bytes[8:12], "big")
    nonce = "0x" + message_bytes[12:44].hex()
    min_finality_threshold = int.from_bytes(message_bytes[140:144], "big")
    message_hash = k256(message_bytes)

    chain = row["chain"]

    return {
        "chain": chain,
        "contract_address": row["contract_address"],
        "event_name": "MessageSent",
        "block_number": int(row["block_number"]),
        "block_timestamp": row["block_timestamp"],
        "transaction_hash": row["transaction_hash"],
        "log_index": int(row["log_index"]),
        "nonce": nonce,
        "source_domain": source_domain,
        "destination_domain": destination_domain,
        "amount": None,
        "mint_recipient": None,
        "burn_token": None,
        "min_finality_threshold": min_finality_threshold,
        "message_hash": message_hash,
    }


def decode_message_received(row):
    topics = row["topics"]
    nonce = topics[2]
    finality_threshold_executed = uint_from_topic(topics[3])

    data = hex_to_bytes(row["data"])
    decoded = abi_decode(["uint32", "bytes32", "bytes"], data)
    source_domain = int(decoded[0])
    message_body = decoded[2]
    message_hash = k256(message_body)

    chain = row["chain"]
    destination_domain = DOMAIN_ID.get(chain)

    return {
        "chain": chain,
        "contract_address": row["contract_address"],
        "event_name": "MessageReceived",
        "block_number": int(row["block_number"]),
        "block_timestamp": row["block_timestamp"],
        "transaction_hash": row["transaction_hash"],
        "log_index": int(row["log_index"]),
        "nonce": nonce,
        "source_domain": source_domain,
        "destination_domain": destination_domain,
        "amount": None,
        "mint_recipient": None,
        "burn_token": None,
        "min_finality_threshold": finality_threshold_executed,
        "message_hash": message_hash,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not INPUT_PATH.exists():
        print(f"Error: input {INPUT_PATH} not found", file=sys.stderr)
        return 1

    print(f"Reading {INPUT_PATH}...")
    df = pd.read_parquet(INPUT_PATH)
    print(f"Input rows: {len(df):,}")

    print(f"Renaming {INPUT_PATH.name} -> {RAW_BACKUP_PATH.name} for traceability...")
    INPUT_PATH.rename(RAW_BACKUP_PATH)

    print("Decoding ABI...")
    decoded_rows = []
    by_event = {"DepositForBurn": 0, "MessageSent": 0, "MessageReceived": 0, "Unknown": 0}
    for _, row in df.iterrows():
        topic0 = row["topics"][0]
        if topic0 == TOPIC_DEPOSIT_FOR_BURN:
            decoded_rows.append(decode_deposit_for_burn(row))
            by_event["DepositForBurn"] += 1
        elif topic0 == TOPIC_MESSAGE_SENT:
            decoded_rows.append(decode_message_sent(row))
            by_event["MessageSent"] += 1
        elif topic0 == TOPIC_MESSAGE_RECEIVED:
            decoded_rows.append(decode_message_received(row))
            by_event["MessageReceived"] += 1
        else:
            by_event["Unknown"] += 1

    print(f"Event counts: {by_event}")

    decoded_df = pd.DataFrame(decoded_rows)
    print(f"Decoded rows: {len(decoded_df):,}")
    print(f"Columns: {list(decoded_df.columns)}")

    print(f"Writing decoded parquet to {OUTPUT_PATH}...")
    decoded_df.to_parquet(OUTPUT_PATH, index=False, compression="snappy")

    print()
    print("=== Output artefacts ===")
    for p in [RAW_BACKUP_PATH, OUTPUT_PATH]:
        print(f"{p.name:50s} {p.stat().st_size:>14,} bytes  sha256={sha256_file(p)}")

    print()
    print("=== Nonce uniqueness check (MessageReceived rows, key=(source_domain, nonce)) ===")
    mr = decoded_df[decoded_df["event_name"] == "MessageReceived"]
    print(f"MessageReceived rows: {len(mr):,}")
    grouped = mr.groupby(["source_domain", "nonce"]).size().reset_index(name="count")
    duplicates = grouped[grouped["count"] > 1]
    if duplicates.empty:
        print("Clean: no duplicate (source_domain, nonce) pair on MessageReceived events.")
    else:
        print(f"WARNING: {len(duplicates):,} duplicate nonce groups detected.")
        print("Sample (up to 20):")
        print(duplicates.head(20).to_string())
        print()
        print("These must be enumerated in MANIFEST.md §Step 2 with their root cause before lock.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
