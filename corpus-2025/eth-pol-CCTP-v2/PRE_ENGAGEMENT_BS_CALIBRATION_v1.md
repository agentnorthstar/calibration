# Pre-Engagement, ETH-POL CCTP V2 Bridge State Calibration

**Protocol identifier.** `BS_CALIBRATION_v1`.

**Contract reference.** `METHODOLOGY.md` §3 Step 3 excludes any threshold-based bridge state classification within the corpus itself. The protocol below is a downstream calibration applied **ex-ante** to the frozen corpus, producing thresholds that are subsequently applied to **live** production observables. The Step 3 exclusion stands: thresholds derived under the present protocol are written to a separate output artefact and are not inserted into the per-event sheets, the baseline parquet, or any object covered by the Step 3 manifest.

**Lock and signing.** The present document is locked (SHA-256), Ed25519-signed in three independent namespaces, and stamped on Bitcoin via OpenTimestamps. The Ed25519 signatures and the Bitcoin block anchor constitute the cryptographic record that the methodological choices below are fixed prior to execution of `scripts/compute_bs_calibration_v2.py` against the corpus parquets. No timestamp internal to the document is required for this purpose: the signing acts and the Bitcoin block height are the authoritative provenance.

---

## 1. Scope

The protocol produces **four bridge state thresholds** for the ETH-POL CCTP V2 corridor:

```
(ethereum, polygon, Fast)
(ethereum, polygon, Standard)
(polygon, ethereum, Fast)
(polygon, ethereum, Standard)
```

Each threshold is a single scalar in seconds, denoted `threshold_bs1_s`. A live message attested with `attestation_latency_s <= threshold_bs1_s` for its triplet is classified `BS1`. A live message with `attestation_latency_s > threshold_bs1_s` is classified `BS2`.

The column `threshold_bs2_s` is not produced under this protocol. It remains NULL in the production seed, reserved for a possible future tri-class extension governed by a separate pre-engagement.

## 2. Input data

The four thresholds are computed from the locked Step 2 parquets in `data/`:

- `cctp_v2_events_2025_bigquery_extract.parquet` (raw CCTP V2 events, ABI-decoded)
- per-event sheets in `results/per_event_sheets/*.parquet` (hourly aggregates)
- `baseline.parquet` (8760 hourly rows over the corpus year)

The decoded fields required per message are:

- `source_domain` ∈ {0 (ETH), 7 (POL)}
- `destination_domain` ∈ {0 (ETH), 7 (POL)}
- `mode_executed` ∈ {`Fast`, `Standard`}, derived from `finality_threshold_executed` per the convention encoded in `routes.rs` (≤ 1000 ⇒ `Fast`, = 2000 ⇒ `Standard`)
- `attestation_latency_s` = attestation timestamp − MessageSent timestamp (seconds)

## 3. Calibration window

The window is corridor-active:

```
window_start = 2025-06-09 18:45 UTC   (Polygon CCTP V2 TokenMessengerV2 creation, block 72,566,047)
window_end   = 2025-12-31 23:59 UTC   (corpus year end)
```

Total length: approximately 4,968 hours. The pre-corridor segment of the corpus year (2025-01-01 → 2025-06-09) is excluded by construction: with Polygon V2 contracts not yet deployed, no corridor observable exists to calibrate on.

No additional warmup is applied within the window. The 30-day EMA warmup of Step 3 applies to substrate metrics and does not propagate to corridor latency, which carries no EMA dependency.

## 4. Calibration method

For each hour `h` in the calibration window and for each triplet `(source, destination, mode)`:

```
n_attested(h) = number of attested messages observed in [h, h+1) on the triplet
p90_latency(h) = 90th percentile of attestation_latency_s over those messages, if n_attested(h) ≥ 1
              = NULL,                                                            if n_attested(h) = 0
```

The hourly p90 is consistent with the convention established in `aggregator.rs` (`attestation_latency_p90_s`).

For each triplet, the threshold is the empirical P97 of the non-null hourly p90 distribution over the calibration window, computed with linear interpolation:

```
threshold_bs1_s(source, destination, mode) = P97({ p90_latency(h) : h in window, n_attested(h) ≥ 1 })
```

P97 is the quantile of record for bridge state calibration, retained for continuity with the V1 convention seeded in `migration_bridge_thresholds.sql`. Under a stationary distribution it corresponds to a 3% nominal BS2 rate per triplet.

For each triplet, let `n_buckets_non_null` denote the count of hours with `n_attested ≥ 1` within the window. The threshold carries a confidence tag derived from this count:

```
confidence = "HIGH"   if n_buckets_non_null ≥ 200
confidence = "MEDIUM" if 50 ≤ n_buckets_non_null < 200
confidence = "LOW"    if n_buckets_non_null < 50
```

A `LOW` confidence threshold is seeded into production with the tag exposed in the row of `bridge_thresholds` and surfaced verbatim by the production API in the bridge state response. The threshold is not suppressed.

## 5. Methodological choices fixed prior to execution

The following choices are part of the present pre-engagement and are not amended after signing. Any amendment requires rotation to a successor protocol with its own pre-engagement signature.

1. Calibration window: 2025-06-09 18:45 UTC to 2025-12-31 23:59 UTC. Corridor-active, not full corpus year, not post-warmup year.
2. Aggregation granularity: hourly p90 per `(source, destination, mode)`.
3. Quantile: P97, linear interpolation, on the distribution of non-null hourly p90s.
4. Bucket inclusion rule: `n_attested ≥ 1` required.
5. No outlier filtering: no Tukey fence, no Hampel filter, no IQR clipping. The empirical P97 is the threshold.
6. No retroactive resampling: the window is fixed; the calibration is not iterated on sub-windows.
7. No cross-triplet pooling: the four thresholds are independent, each computed on its own triplet's distribution.
8. Confidence partition: 200 and 50 buckets, in that order, for HIGH, MEDIUM, LOW.

## 6. Schema convention for production seeding

The production table `bridge_thresholds` keys rows by `bridge_id` as a single column. CCTP V2 introduces a mode dimension that this key does not natively express.

The convention retained encodes the mode as a suffix of `bridge_id`:

```
ethereum-polygon/cctp/fast
ethereum-polygon/cctp/standard
polygon-ethereum/cctp/fast
polygon-ethereum/cctp/standard
```

This preserves the single-column primary key shape, requires no `ALTER TABLE` to the existing schema, and is resolved at lookup time by reconstructing the suffix from `(source, destination, mode_executed)` on each row of `ans_cctp_v2_route_signals`.

Two columns are added to `bridge_thresholds` to carry calibration provenance:

```
confidence            text NULL  (values: 'HIGH', 'MEDIUM', 'LOW')
calibration_source    text NULL  (value: 'corpus_2025_ex_ante' for rows produced under the present protocol)
```

Nullability preserves compatibility with pre-existing V1 and CCIP rows that do not carry calibration metadata at this granularity.

## 7. Output artefact

`scripts/compute_bs_calibration_v2.py` produces a single output:

```
results/BS_CALIBRATION_ETH_POL_CCTP_V2.json
```

Schema (UTF-8 JSON, sorted keys, indent 2):

```json
{
  "protocol_version": "BS_CALIBRATION_v1",
  "corpus_reference": "ETH-POL-CCTP-V2 publiable corpus, MANIFEST.md sha-256 <hash>",
  "calibration_window_start_utc": "2025-06-09T18:45:00Z",
  "calibration_window_end_utc":   "2025-12-31T23:59:00Z",
  "method": "P97 of non-null hourly p90 latency, per (source, destination, mode), linear interpolation",
  "thresholds": [
    {
      "bridge_id": "ethereum-polygon/cctp/fast",
      "source": "ethereum",
      "destination": "polygon",
      "mode": "Fast",
      "threshold_bs1_s": <float>,
      "n_buckets_non_null": <int>,
      "n_buckets_total_in_window": <int>,
      "confidence": "<HIGH|MEDIUM|LOW>"
    },
    { "bridge_id": "ethereum-polygon/cctp/standard", ... },
    { "bridge_id": "polygon-ethereum/cctp/fast",     ... },
    { "bridge_id": "polygon-ethereum/cctp/standard", ... }
  ],
  "script_sha256":              "<SHA-256 of compute_bs_calibration_v2.py>",
  "input_parquets_sha256": {
    "baseline.parquet":                                 "<hash>",
    "cctp_v2_events_2025_bigquery_extract.parquet":     "<hash>"
  }
}
```

The JSON output is hashed (SHA-256), Ed25519-signed in three namespaces, and stamped on Bitcoin via OpenTimestamps. The four threshold rows are then seeded into the production `bridge_thresholds` table via `migration_cctp_v2_bs_calibration_eth_pol.sql`.

## 8. Live confirmation protocol

A confirmation pass is part of the present protocol. It is executed once the production collector `ans_cctp_v2_route_signals` has accumulated a live observation window of at least 4,000 hours per triplet since CCTP V2 production deployment, on the same corridor and the same triplet decomposition.

The confirmation script `scripts/confirm_bs_calibration_v2_live.py` is written and locked under a separate pre-engagement prior to execution. The confirmation method is identical to Section 4, applied to the live `ans_cctp_v2_route_signals` rows within the live window.

Per triplet, the confirmation decision rule compares the live threshold to the ex-ante threshold of the present protocol:

```
ratio = | threshold_live - threshold_ex_ante | / threshold_ex_ante

ratio ≤ 0.20            ⇒ LIVE_CONFIRMED
                          ex-ante threshold retained; row note appended

0.20 < ratio, explained ⇒ DRIFT
                          ex-ante threshold updated to live value;
                          successor protocol signed with documentation of the discrepancy
                          (volume profile, fee market, externally documented event)

0.20 < ratio, unexplained ⇒ REJECTED
                            calibrated flag set to false on the triplet;
                            API surfaces raw p50, p90, p99 for that triplet,
                            without BS1/BS2 classification
```

The confirmation result is published as `eth-pol-cctp-v2-bs-calibration-confirmation.html` on the public site, Ed25519-signed, OpenTimestamps-anchored on Bitcoin.

## 9. Stated limits of the calibration

The four thresholds carry five explicit limits, declared as part of the present pre-engagement.

1. **Per-corridor only.** The thresholds calibrate the ETH-POL corridor exclusively. Transferability to ETH-ARB, ETH-BASE, ETH-OP, ETH-AVAX, or ETH-SOL CCTP V2 corridors is not asserted and is not testable within the 2025 corpus universe in the absence of a sibling L1-to-L1 CCTP V2 corpus.
2. **Mode asymmetry not modeled.** The Fast and Standard modes have different operational meanings and physical floors. P97 is applied identically to both; a Fast `threshold_bs1_s` and a Standard `threshold_bs1_s` carry different operational severities of equal nominal BS2 rate. The API consumer is expected to interpret BS2 in mode context.
3. **Sparse triplets retain LOW confidence.** Three of four triplets exhibit fewer than 50 non-null hourly buckets in the corridor-active window (see `REPORT_ETH_POL_CCTP_V2.md` for the underlying event-window counts). Their `threshold_bs1_s` is computed but flagged LOW. Live confirmation is the natural mitigation.
4. **Direction-mode independence is asserted, not tested.** The four thresholds are computed independently per triplet. No formal test of independence between triplets is performed under the present protocol.
5. **Quantile choice is pre-engaged, not optimized.** P97 is fixed for V1 continuity. No multi-quantile sweep is performed. If the live confirmation suggests the quantile is mis-tuned, the protocol rotates to a successor with explicit justification, recorded in a fresh pre-engagement; the rotation does not silently re-tune.

## 10. Signing procedure

The present document, once frozen, is hashed (SHA-256) and signed with three independent Ed25519 keys using the same namespace convention as the corpus Step 0, Step 2, and Step 3 artefacts. The signatures are stored in `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.sig.{1,2,3}` with the corresponding public keys in `signatures/public_keys/`. The hash is stamped on Bitcoin via OpenTimestamps; the proof file is stored in `signatures/PRE_ENGAGEMENT_BS_CALIBRATION_v1.md.ots` and upgraded to a Bitcoin block anchor after calendar attestation.

The Ed25519 signatures and the Bitcoin block anchor are the authoritative cryptographic record that the methodological choices of Sections 4, 5, 6, 7, 8 are fixed prior to execution of `compute_bs_calibration_v2.py` against the corpus parquets.

---

**End of pre-engagement.**
