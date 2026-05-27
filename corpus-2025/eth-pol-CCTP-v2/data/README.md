# Step 2 raw parquets, reproduction protocol

The Step 2 raw BigQuery extracts are not stored in this repository due to their total size of approximately 2.8 GB across four files. They are reproducible byte-for-byte from public BigQuery datasets using the SQL queries documented in `../bigquery/queries.md` and the decoding script in `../scripts/decode_cctp_v2_events.py`.

## Expected files after reproduction

| File | Rows | Size | SHA-256 |
|---|---|---|---|
| `eth_blocks_2025_raw.parquet` | 2,610,162 | 405,027,246 bytes | `4bab509c27c4c9f0c33a919d5b5b13407acdadc0654318df836a9d0c6b07626a` |
| `pol_blocks_2025_raw.parquet` | 14,894,253 | 2,200,685,480 bytes | `6fa3440f80ba4dc53fc1ab17cd17fd05d0aec4eec2885d685d780d77d1e8b4b5` |
| `cctp_v2_events_2025_raw.parquet` (decoded) | 936,005 | 123,083,348 bytes | `6da1efe76086d7fbb5c6492760283a985c0f0d8bc06d1b61893e4746ca853871` |
| `cctp_v2_events_2025_bigquery_extract.parquet` (raw BigQuery output, retained for traceability) | 936,005 | 230,983,949 bytes | `42f3fd5e58519f4a89a8a086d534dee1fc7833f62f9ab3313cb57fda0e679f4f` |

## Procedure

1. Authenticate to BigQuery (`gcloud auth application-default login` or service account credentials).
2. Run each query in `../bigquery/queries.md` against the indicated dataset. Three queries produce raw parquets directly; the CCTP V2 events query produces an undecoded parquet whose ABI is then parsed by `../scripts/decode_cctp_v2_events.py` to produce the final decoded parquet.
3. Verify each produced file against the SHA-256 hash above. The four hashes are the same as those recorded in `../MANIFEST.md` §Step 2 (Ed25519 signed payload `../signatures/STEP2_PAYLOAD.txt`).
4. The decoded `cctp_v2_events_2025_raw.parquet` is the canonical Step 2 artefact bound by the Step 2 signature; the auxiliary `cctp_v2_events_2025_bigquery_extract.parquet` is retained for traceability of the raw BigQuery output prior to decoding.

## Reproduction cost

Approximately 9 TB total bytes processed across the three BigQuery extraction runs (Polygon blocks plus the two CCTP V2 events extraction passes documented in the Step 2 amendment history of `../MANIFEST.md`). Reproduction is billable at the BigQuery scan rate of the executing project.

## Downstream pipeline

The Step 3 hourly panel and per-event sheets in `../results/per_event_sheets/` are deterministic outputs of `../scripts/compute_step3.py` applied to the four parquets reproduced from this protocol. Reproducing the Step 2 parquets and running the Step 3 script reproduces every artefact under `../results/` and matches the Ed25519 signatures in `../signatures/`.
