# Manifest, ETH-POL CCTP V2 Descriptive Corpus

**Project.** Invarians substrate matrix and CCTP V2 latency observation, ETH-POL corridor, calendar year 2025.

**Methodology of record.** `METHODOLOGY.md` (in this folder).

**Manifest version.** 1, 2026-05-25.

This manifest records the SHA-256 hash and signature status of each artefact produced by the corpus protocol. Artefacts are produced in sequence. Each artefact is locked (hashed and signed) before the next artefact is produced. Any modification after lock is recorded as a dated amendment that preserves the prior hash chain.

---

## Step 0, Methodology contract

The methodology document is locked before any data extraction begins. It is the contract against which every downstream artefact is verified.

| Field | Value |
|---|---|
| Artefact | `METHODOLOGY.md` |
| SHA-256 | `1b0ef577733d1bb05b372547e26f0c633b6a1e4873fa2d67e1c640c2f51c67e7` |
| Byte length at hash | 19243 bytes |
| Line count at hash | 195 lines |
| Hash date UTC | 2026-05-25 |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step0` |
| Ed25519 signature 1 (primary) | `signatures/signature_1.sig`, key fingerprint `SHA256:oY1c0cRsZBtSxYhZf5tun6cZg2RUmLjHiD0B09CmwAw`, public key `signatures/public_keys/ed25519_1.pub`, verified Good |
| Ed25519 signature 2 (secondary) | `signatures/signature_2.sig`, key fingerprint `SHA256:3WJMmeJbZ8DasTCwagVSQBIaaKE/OKew54GfGspsFSI`, public key `signatures/public_keys/ed25519_2.pub`, verified Good |
| Ed25519 signature 3 (tertiary) | `signatures/signature_3.sig`, key fingerprint `SHA256:QkopZBWjd2xTJQRAe6y7WPO2r8R5x9ui3/BwOeRmIWQ`, public key `signatures/public_keys/ed25519_3.pub`, verified Good |
| OpenTimestamps Bitcoin proof file | `signatures/METHODOLOGY.md.ots`, 805 bytes, 4 calendar attestations (alice.btc.calendar.opentimestamps.org, bob.btc.calendar.opentimestamps.org, btc.calendar.catallaxy.com, finney.calendar.eternitywall.com), pending Bitcoin block confirmation |
| OpenTimestamps upgrade scheduled | within 1 to 6 hours after `ots stamp`, command `ots upgrade signatures/METHODOLOGY.md.ots` |
| Status | locked, three signatures verified, OpenTimestamps stamped, awaiting Bitcoin block confirmation for full anchor proof |

**Verification protocol for external readers.** Any third party can independently verify Step 0 by running:

```
ssh-keygen -Y verify -f <allowed_signers> -I <signer_id> -n invarians_corpus_eth_pol_cctp_v2_step0 -s signatures/signature_<i>.sig < METHODOLOGY.md
```

with `<allowed_signers>` constructed from the three public keys in `signatures/public_keys/`. Each signature should yield `Good "invarians_corpus_eth_pol_cctp_v2_step0" signature` for its corresponding signer. The OpenTimestamps anchor can be verified with `ots verify signatures/METHODOLOGY.md.ots` once Bitcoin block confirmation has been recorded by the upgrade.

**Lock condition.** Step 0 is locked. Step 1 may begin.

---

## Step 1, Incident sourcing

| Field | Value |
|---|---|
| Artefact | `INCIDENTS_2025.md` |
| SHA-256 | `11e776d0b68265e2f9da2843909c3b92667fffe6eca4444f257a208471344d01` |
| Byte length at hash | 19870 bytes |
| Hash date UTC | 2026-05-25 |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step1` |
| Ed25519 signature 1 (primary) | `signatures/INCIDENTS_2025.md.sig.1`, key fingerprint `SHA256:oY1c0cRsZBtSxYhZf5tun6cZg2RUmLjHiD0B09CmwAw`, public key `signatures/public_keys/ed25519_1.pub`, verified Good |
| Inventory composition | 12 events in §2 (5 ETH only, 4 POL only, 2 CCTP V2 corridor only, 1 cross-chain ETH+POL+CCTP V2), 14 events excluded by rule in §3, 5 out-of-corridor events documented for transparency in §4, 1 event pending Phase 0 reconfirmation in §5 |
| Status | locked, signature verified |

**Lock condition.** Step 1 is locked. Step 2 may begin.

---

## Step 2, Raw BigQuery extraction

| Field | Value |
|---|---|
| Artefact 1 | `data/eth_blocks_2025_raw.parquet` |
| Rows | 2,610,162 |
| Size | 405,027,246 bytes |
| SHA-256 | `4bab509c27c4c9f0c33a919d5b5b13407acdadc0654318df836a9d0c6b07626a` |
| Artefact 2 | `data/pol_blocks_2025_raw.parquet` |
| Rows | 14,894,253 |
| Size | 2,200,685,480 bytes |
| SHA-256 | `6fa3440f80ba4dc53fc1ab17cd17fd05d0aec4eec2885d685d780d77d1e8b4b5` |
| Artefact 3 | `data/cctp_v2_events_2025_raw.parquet` (ABI-decoded, 15 columns per contract; three event types) |
| Rows | 936,005 (266,244 DepositForBurn + 266,263 MessageSent + 403,498 MessageReceived + 0 Unknown) |
| Size | 123,083,348 bytes |
| SHA-256 | `6da1efe76086d7fbb5c6492760283a985c0f0d8bc06d1b61893e4746ca853871` |
| Artefact 4 | `bigquery/queries.md` |
| Lines | 325 |
| Size | 15,654 bytes |
| SHA-256 | `227a111ed852125b6a0e53fbd1e7d88cb95bf438de3ea776eef38194827c4b57` |
| Auxiliary artefact (not in contract spec, retained for traceability) | `data/cctp_v2_events_2025_bigquery_extract.parquet` (raw BigQuery output, topics+data unparsed, three event types) |
| Auxiliary SHA-256 | `42f3fd5e58519f4a89a8a086d534dee1fc7833f62f9ab3313cb57fda0e679f4f`, 230,983,949 bytes |
| Nonce uniqueness check | Clean. No duplicate `(source_domain, nonce)` pair on the 403,498 MessageReceived rows. Reported by `scripts/decode_cctp_v2_events.py` at extraction time. |
| Polygon dataset selection | `bigquery-public-data.goog_blockchain_polygon_mainnet_us` (Google Blockchain Analytics, coverage through 2026-05-26, 87M+ blocks total). The `bigquery-public-data.crypto_polygon` dataset is not used (coverage ends 2024-09-01 23:59:58 UTC, prior to the corpus window). `transaction_count` computed via LEFT JOIN on `transactions.block_hash` since `transactions.block_number` is not exposed in the schema. Recorded in `queries.md` §1 and `LIMITATIONS.md`. |
| Effective CCTP V2 corridor window | 2025-06-09 to 2025-12-31 (Polygon mainnet CCTP V2 deployment date is 2025-06-09 18:45:11 UTC; events prior to that on Polygon do not exist) |
| Event types extracted | `DepositForBurn V2` (source-side, no nonce in its ABI), `MessageSent V2` (source-side, carries nonce inside the bytes header of the emitted message), `MessageReceived V2` (destination-side, carries nonce as indexed topic). Joint extraction of all three is required to support per-nonce matching of source-side burns to destination-side receives, as the matching key (nonce) is not present in `DepositForBurn V2` itself. |
| BigQuery total bytes processed (billed) | approximately 9 TB cumulative across the two extraction runs (4.5 TB initial + 4.5 TB amendment) |
| Hash date UTC | 2026-05-26 |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step2` |
| Aggregate payload | `signatures/STEP2_PAYLOAD.txt` (lists the four SHA-256 hashes named above, one per line) |
| Ed25519 signature 1 (primary) | `signatures/STEP2_PAYLOAD.sig.1`, key fingerprint `SHA256:oY1c0cRsZBtSxYhZf5tun6cZg2RUmLjHiD0B09CmwAw`, public key `signatures/public_keys/ed25519_1.pub`, verified Good on 2026-05-26 |
| Status | locked, signature verified |

**Verification protocol for external readers.** Any third party can independently verify Step 2 by running:

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_step0_signer_1 -n invarians_corpus_eth_pol_cctp_v2_step2 -s signatures/STEP2_PAYLOAD.sig.1 < signatures/STEP2_PAYLOAD.txt
```

The signed payload binds the four SHA-256 hashes named in §Step 2 to the public key. Recomputing the four hashes from the parquets and the `queries.md` file and confirming a byte-for-byte match against the payload completes the verification chain.

**Lock condition.** Step 2 is locked when the Ed25519 signature on the amended payload is filled. The four SHA-256 hashes above are recorded, the nonce uniqueness check is clean, the event-type set covers source-side and destination-side nonce sources.

### Step 2 amendment history

This subsection records prior locks of Step 2 that have been superseded by a re-signature, with their hashes preserved for verification of the prior state.

**Lock 1 (superseded 2026-05-26).** Initial Step 2 lock with two CCTP V2 event types only (`DepositForBurn V2` and `MessageReceived V2`). The matching key `nonce` was found absent from `DepositForBurn V2` and present in `MessageReceived V2` only, preventing per-nonce reconstruction of end-to-end latency required by §3 Step 3 of the contract. Lock 1 hashes:
- `data/eth_blocks_2025_raw.parquet` SHA-256 `4bab509c27c4c9f0c33a919d5b5b13407acdadc0654318df836a9d0c6b07626a`
- `data/pol_blocks_2025_raw.parquet` SHA-256 `a4491191f03e5438c0a7bcd1cc2526ddd3f915de169146ba113a7d7cd454c341`
- `data/cctp_v2_events_2025_raw.parquet` SHA-256 `2ab796e73dfe17fe7377694406ad671bb525f34fd5ffc86f2cac0131d032579f`
- `bigquery/queries.md` SHA-256 `7a160c4bfc23c39ee0a8f6bfe28c7718f528587b23bdd430ef13b1596ced8a1f`
- Lock 1 payload signature: `signatures/STEP2_PAYLOAD.sig.1_lock1` (preserved), payload `signatures/STEP2_PAYLOAD.txt_lock1` (preserved). Key fingerprint `SHA256:oY1c0cRsZBtSxYhZf5tun6cZg2RUmLjHiD0B09CmwAw`.

**Amendment 1 (current, 2026-05-26).** Adds `MessageSent V2` extraction to the CCTP V2 events parquet, restoring per-nonce matching capability for Step 3. The Polygon blocks parquet hash changed during the re-extraction window because the `goog_blockchain_polygon_mainnet_us` dataset received a minor backfill between the two runs (5,153 bytes delta, approximately 0.0002 percent of the parquet size, consistent with a few additional latest blocks). `queries.md` was updated to document the third event type and its ABI. Current hashes are listed in the table above.

---

## Step 3, Matrix and Delta application

| Field | Value |
|---|---|
| Artefact 1 | `METHODOLOGY_STEP3_CONVENTIONS.md` |
| SHA-256 | `7b9f3e7125150ffd5ac5b4a76efe035efc362be03229df6fc053eef41ed02603` |
| Artefact 2 | `results/REPORT_ETH_POL_CCTP_V2.md` |
| SHA-256 | `e9387165a1dca26ad7e675b4ecb57bd7c30a7db17a818aa084676709f64243b3` |
| Artefact 3 | `results/per_event_sheets/CCTP_V2_MAINNET_LAUNCH_2025_03_11.parquet` |
| SHA-256 | `07f8fa74995ebb2e77d78f0af8a27714f40ea92f9656e67f3fafac650cb38ab8` |
| Artefact 4 | `results/per_event_sheets/CCTP_V2_POLYGON_DEPLOYMENT_2025_06.parquet` |
| SHA-256 | `41ca40d8f931ec74bc44515180a353b1fe4cf41f731bdd200614b8bb305698db` |
| Artefact 5 | `results/per_event_sheets/ETH_BPO1_MAINNET_2025_12_09.parquet` |
| SHA-256 | `d3c259e7df6f35b9f2902d445ca00753e5137a63a8a223b163e50a90215eda5e` |
| Artefact 6 | `results/per_event_sheets/ETH_FUSAKA_MAINNET_2025_12_03.parquet` |
| SHA-256 | `1c1884e0d42c84ed801391eabbe1a1d01532ad527f0a1dbeec918e6b2c816940` |
| Artefact 7 | `results/per_event_sheets/ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09.parquet` |
| SHA-256 | `4ae9c05d141ddd29a77ea0cec2704fadc696fd81fd1c5884a8983ec7a4cf86aa` |
| Artefact 8 | `results/per_event_sheets/ETH_PECTRA_MAINNET_2025_05_07.parquet` |
| SHA-256 | `0c5acf44c587cc46c97f2e96a24a44dbd092df4f020259d75a4766e113c34f4e` |
| Artefact 9 | `results/per_event_sheets/ETH_SSV_MASS_SLASHING_2025_09_10.parquet` |
| SHA-256 | `2cf77d221f0275eca6a55864c88c8851b5f29a644412532490acce1252d82ec7` |
| Artefact 10 | `results/per_event_sheets/POL_BOR_RPC_2025_12.parquet` |
| SHA-256 | `99039c456c163073efe2361964a5338a299248c8d9d3e91ef9a8b16ec7e5f178` |
| Artefact 11 | `results/per_event_sheets/POL_HEIMDALL_CONSENSUS_2025_07_30.parquet` |
| SHA-256 | `3fc9305937667a0df1de07d5badd2f570fe4976c7a5294c476c73714aa67abfa` |
| Artefact 12 | `results/per_event_sheets/POL_HEIMDALL_MILESTONE_2025_09_10.parquet` |
| SHA-256 | `88e64bd1916cb8c30645930faa607af990c6c9191f9a559430657ac4271de5d1` |
| Artefact 13 | `results/per_event_sheets/POL_HEIMDALL_V2_HARD_FORK_2025_09_16.parquet` |
| SHA-256 | `e178c9530cc175e8b42c12a522ae86d7159cd202007f8c264cf5654639dcab67` |
| Artefact 14 | `results/per_event_sheets/USDE_DEPEG_CASCADE_2025_10_10.parquet` |
| SHA-256 | `cee12bae571fa900fe94dc6ea12d6dc0c47661435ce5c7e5b772d7925e2a87d3` |
| Artefact 15 | `results/per_event_sheets/baseline.parquet` |
| SHA-256 | `85d15a681fe57e603d66aea353b75637a290dbe545f16109c0d244659a62b3d5` |
| Hash date UTC | 2026-05-26 |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step3` |
| Aggregate payload | `signatures/STEP3_PAYLOAD.txt`, SHA-256 `f9139320654a0fc874d13f201a705009ae82df37d16ab1c03c7a5fe8096ff0a0`, lists the fifteen artefact hashes named above, one per line. |
| Ed25519 signature 1 (primary) | `signatures/STEP3_PAYLOAD.sig.1`, key fingerprint `SHA256:oY1c0cRsZBtSxYhZf5tun6cZg2RUmLjHiD0B09CmwAw`, public key `signatures/public_keys/ed25519_1.pub`, verified Good on 2026-05-26 |
| Ed25519 signature 2 (secondary) | `signatures/STEP3_PAYLOAD.sig.2`, key fingerprint `SHA256:3WJMmeJbZ8DasTCwagVSQBIaaKE/OKew54GfGspsFSI`, public key `signatures/public_keys/ed25519_2.pub`, verified Good on 2026-05-26 |
| Ed25519 signature 3 (tertiary) | `signatures/STEP3_PAYLOAD.sig.3`, key fingerprint `SHA256:QkopZBWjd2xTJQRAe6y7WPO2r8R5x9ui3/BwOeRmIWQ`, public key `signatures/public_keys/ed25519_3.pub`, verified Good on 2026-05-26 |
| OpenTimestamps Bitcoin proof file | `signatures/STEP3_PAYLOAD.txt.ots`, 759 bytes, 4 calendar attestations (a.pool.opentimestamps.org, b.pool.opentimestamps.org, a.pool.eternitywall.com, ots.btc.catallaxy.com), pending Bitcoin block confirmation |
| OpenTimestamps upgrade scheduled | within 1 to 6 hours after `ots stamp`, command `ots upgrade signatures/STEP3_PAYLOAD.txt.ots` |
| CCTP V2 pairing log | eth_to_pol Fast: n_sent=2,063, n_paired=2,056, n_unpaired_sent=7; eth_to_pol Standard: n_sent=2,063, n_paired=2,060, n_unpaired_sent=3; eth_to_pol receives unused (no Sent matched within mode-specific window): 3 of 4,119. pol_to_eth Fast: n_sent=1,358, n_paired=1,336, n_unpaired_sent=22; pol_to_eth Standard: n_sent=1,099, n_paired=1,096, n_unpaired_sent=3; pol_to_eth receives unused: 12 of 2,444. Total corridor pairs: 6,548 of 6,583 messages (99.5% coverage). Pairing algorithm per `METHODOLOGY_STEP3_CONVENTIONS.md` §6.1 (greedy proximity-window matching, Fast window 2h, Standard window 48h, mode attributed from the source-side requested finality threshold). |
| Status | locked, three signatures verified, OpenTimestamps stamped, awaiting Bitcoin block confirmation for full anchor proof |

**Verification protocol for external readers.** Any third party can independently verify Step 3 by running, for each signature `i ∈ {1, 2, 3}`:

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_step0_signer_<i> -n invarians_corpus_eth_pol_cctp_v2_step3 -s signatures/STEP3_PAYLOAD.sig.<i> < signatures/STEP3_PAYLOAD.txt
```

Each signature must yield `Good "invarians_corpus_eth_pol_cctp_v2_step3" signature` for its corresponding signer. The signed payload binds the fifteen SHA-256 hashes of §Step 3 to the three public keys. Recomputing the fifteen hashes from the artefacts and confirming byte-for-byte match against the payload completes the verification chain. The OpenTimestamps anchor can be verified with `ots verify signatures/STEP3_PAYLOAD.txt.ots` once Bitcoin block confirmation has been recorded by the upgrade.

**Lock condition.** Step 3 is locked. The corpus is published, subject to Bitcoin block confirmation of the OpenTimestamps anchor pending in calendar attestations.

---

## Step 4-bis, Bridge State Calibration (ex-ante)

Step 4-bis is a downstream calibration applied to the locked Step 3 corpus. It produces the four ETH-POL CCTP V2 bridge state thresholds intended for seeding the production `bridge_thresholds` table. The protocol is signed independently of Step 3 and does not modify any Step 0 to Step 3 artefact.

### Pre-engagement contract

The pre-engagement document fixes the calibration window, the quantile, the bucket inclusion rule, the confidence partition, the schema convention, and the live confirmation protocol. It is locked before execution of the calibration script.

| Field | Value |
|---|---|
| Artefact | `PRE_ENGAGEMENT_BS_CALIBRATION_v1.md` |
| SHA-256 | `8418e6d7437baf0fc7a4561f59318bbc095387319a19ab5e26cf8da2bc54bd61` |
| Byte length at hash | 12 520 bytes |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step4bis_pre_engagement` |
| Ed25519 signature 1 (primary) | `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.1`, 367 bytes, public key `signatures/public_keys/ed25519_step4bis_1.pub`, key fingerprint `SHA256:t0HLiUzQmfaxeFGUxFB7/eGcTO6nMaEZWomsbnpHNKU`, verified Good |
| Ed25519 signature 2 (secondary) | `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.2`, 367 bytes, public key `signatures/public_keys/ed25519_step4bis_2.pub`, key fingerprint `SHA256:T58pqVuMRW2E8NtaxKpKpjoPutw3TtAkpDtNcw8cHT0`, verified Good |
| Ed25519 signature 3 (tertiary) | `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.3`, 367 bytes, public key `signatures/public_keys/ed25519_step4bis_3.pub`, key fingerprint `SHA256:Yq4jTD7AzTwSgD/TPDgNCT+Yk7Prn60mBbAmXAk6lUo`, verified Good |
| OpenTimestamps Bitcoin proof files | `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.{1,2,3}.ots` |
| Bitcoin block confirmation height | `<pending until ots upgrade>` |
| Status | `<locked / pending signing>` |

### Calibration script

The script implements the pre-engagement strictly. Its SHA-256 is self-reported in the calibration output for byte-for-byte reproducibility.

| Field | Value |
|---|---|
| Artefact | `scripts/compute_bs_calibration_v2.py` |
| SHA-256 | `f34feda79287d85419218f59c5e26e436918e87557ba3c34ac209af63f7dc761` |
| Byte length at hash | 7 079 bytes |

### Calibration output

The output JSON encodes the four threshold rows, the input parquet hashes, the script hash, the calibration window bounds, and the protocol identifier.

| Field | Value |
|---|---|
| Artefact | `results/BS_CALIBRATION_ETH_POL_CCTP_V2.json` |
| SHA-256 | `97198ee0f65c1121118eaf25525e365e7b2f86f83f736073ddd86115dc6bf041` |
| Byte length at hash | 3 298 bytes |
| Signature namespace | `invarians_corpus_eth_pol_cctp_v2_step4bis_output` |
| Ed25519 signature 1 (primary) | `signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.1`, public key `signatures/public_keys/ed25519_step4bis_1.pub`, key fingerprint `SHA256:t0HLiUzQmfaxeFGUxFB7/eGcTO6nMaEZWomsbnpHNKU` |
| Ed25519 signature 2 (secondary) | `signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.2`, public key `signatures/public_keys/ed25519_step4bis_2.pub`, key fingerprint `SHA256:T58pqVuMRW2E8NtaxKpKpjoPutw3TtAkpDtNcw8cHT0` |
| Ed25519 signature 3 (tertiary) | `signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.3`, public key `signatures/public_keys/ed25519_step4bis_3.pub`, key fingerprint `SHA256:Yq4jTD7AzTwSgD/TPDgNCT+Yk7Prn60mBbAmXAk6lUo` |
| OpenTimestamps Bitcoin proof files | `signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.{1,2,3}.ots` |
| Bitcoin block confirmation height | `<pending until ots upgrade>` |
| Status | `<locked / pending signing>` |

### Inputs consumed

The script consumes the locked Step 3 parquets (their SHA-256 are listed in Step 3 above and are re-recorded by the script in the output JSON for self-contained provenance):

- `results/per_event_sheets/baseline.parquet`
- `results/per_event_sheets/*.parquet` (twelve per-event sheets, hot windows)

The locked Step 2 raw extract `data/cctp_v2_events_2025_bigquery_extract.parquet` is hashed for provenance but is not read by the script.

### Verification protocol for external readers

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_step4bis_signer_<i> \
  -n invarians_corpus_eth_pol_cctp_v2_step4bis_pre_engagement \
  -s signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.<i> < PRE_ENGAGEMENT_BS_CALIBRATION_v1.md

ssh-keygen -Y verify -f <allowed_signers> -I invarians_step4bis_signer_<i> \
  -n invarians_corpus_eth_pol_cctp_v2_step4bis_output \
  -s signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.<i> < results/BS_CALIBRATION_ETH_POL_CCTP_V2.json

ots verify signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.<i>.ots
ots verify signatures/BS_CALIBRATION_ETH_POL_CCTP_V2.json.sig.<i>.ots
```

The Step 4-bis signers are independent of the Step 0/2/3 signers. The three public keys are recorded in `signatures/public_keys/ed25519_step4bis_{1,2,3}.pub` and their fingerprints are listed in the signature tables of this section.

Reproduction of the calibration: any third party re-running `compute_bs_calibration_v2.py` against the Step 3 parquets must obtain a JSON output whose `thresholds[]` and `n_buckets_*` fields match the signed output byte-for-byte. The pre-engagement signature is the cryptographic record that the methodology of Sections 4 to 8 of `PRE_ENGAGEMENT_BS_CALIBRATION_v1.md` was fixed prior to the script run.

### Lock condition

Step 4-bis is locked when both the pre-engagement document and the JSON output carry three Ed25519 signatures and at least calendar-attested OpenTimestamps proofs, with the JSON output's `script_sha256` matching the script SHA-256 recorded in this section.

---

## Final manifest hash

The SHA-256 of this `MANIFEST.md` is computed at the instant Step 3 is sealed, with all Step 0 through Step 3 entries filled and this Final manifest hash section showing `pending`. The hash anchors the manifest state at that exact moment on Bitcoin via OpenTimestamps. After the stamp is created, this section is updated to record the hash and the OTS proof location; the update post-dates the cryptographic anchor and does not alter the OTS-attested state. The OTS proof file is therefore the cryptographic source of truth for the manifest hash; recomputing SHA-256 of `MANIFEST.md` after this section is filled will not match the recorded value, by self-reference design.

| Field | Value |
|---|---|
| Final manifest SHA-256 (state at OTS stamping) | `70bded33332d2a116613bf16c81b303dcbb0c0b9d868d303829d4265308ebe85` |
| Byte length at stamping | 16,067 bytes |
| Stamp date UTC | 2026-05-26 |
| OpenTimestamps proof file | `signatures/MANIFEST_final.ots`, 619 bytes, 4 calendar attestations (a.pool.opentimestamps.org, b.pool.opentimestamps.org, a.pool.eternitywall.com, ots.btc.catallaxy.com), pending Bitcoin block confirmation |
| OpenTimestamps upgrade scheduled | within 1 to 6 hours after `ots stamp`, command `ots upgrade signatures/MANIFEST_final.ots` |
| Bitcoin block confirmation height | pending |
| Status | manifest hash stamped, awaiting Bitcoin block confirmation for full anchor proof |

---

## Amendment log

Any modification of a locked artefact after its lock signature is recorded here, with the date, the modified artefact, the prior SHA-256, the new SHA-256, the new signature, and a brief description of the modification. The prior signature and hash are preserved so the chain of trust remains verifiable across amendments.

### Amendment, manifest version 2: Step 4-bis Bridge State Calibration

| Field | Value |
|---|---|
| Modified artefact | `MANIFEST.md` |
| Prior SHA-256 (Step 3 lock) | `70bded33332d2a116613bf16c81b303dcbb0c0b9d868d303829d4265308ebe85` (16,067 bytes, version 1, ancré OTS) |
| New SHA-256 (Step 4-bis lock) | `<MANIFEST.md SHA-256 version 2>` |
| New byte length | `<bytes>` |
| Modification | addition of section "Step 4-bis, Bridge State Calibration (ex-ante)" between Step 3 and Final manifest hash, plus this Amendment entry. No prior section is altered. The Final manifest hash version 1 remains the OTS anchor for the Step 3 state of the manifest. |
| OpenTimestamps proof file (manifest version 2) | `signatures/MANIFEST_v2.ots` |
| Bitcoin block confirmation height | `<pending>` |
| Status | `<locked / pending signing>` |
