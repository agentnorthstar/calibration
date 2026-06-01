---
title: "Invarians — Pre-Engagement, Substrate-Shift Precursors against BS_STRUCTURAL_v1.1 BS2 outcome (ETH-POL CCTP V2)"
version: "1.0-draft"
status: draft
audience: [ai-agents, developers, researchers, auditors]
---

# Pre-engagement protocol — substrate-shift precursors against `BS_STRUCTURAL_v1.1 BS2`

> **Protocol identifier.** `BS_STRUCTURAL_PRECURSORS_v1`.
>
> **Lock condition.** Three Ed25519 signatures in namespace `invarians_calibration_bs_structural_precursors_v1`, OpenTimestamps Bitcoin anchor on each, before any execution of `compute_bs_structural_precursors_v1.py` against the locked Step 3 corpus parquets.

## 1. Purpose

The substrate-matrix shift family defined in `bridge_state_methodology.md` and exposed through the production v3 API as `BridgeEntry.observed_fast_mode` and the per-chain `precursors[]` array is here evaluated empirically as a candidate predictor of bridge-state degradation under the `BRIDGE_STATE_STRUCTURAL_v1.1` definition. The hypothesis is:

```
H₀ (null)
  A substrate-shift configuration on Ethereum or Polygon does not anticipate
  BRIDGE_STATE_STRUCTURAL_v1.1 BS2 outcome on the ETH-POL CCTP V2 corridor
  at a future hour t + lead beyond its baseline rate.

H₁ (alternative, to be tested)
  At least one substrate-shift configuration fires at hour t with a measurable
  lift on the conditional probability P(BS2 at t+lead | configuration fires at t).
```

The protocol is the empirical validation of H₁ on the locked 2025 ETH-POL CCTP V2 corpus, under the per-engagement statistical discipline applied to prior substrate-shift exploration on this corridor.

## 2. Outcome definition

The outcome variable per hour `t` per triplet `(source, destination, mode_requested)` is:

```
BS_STRUCTURAL_v1.1 BS2(t, source, dest, mode) ≡ 1
  iff the 1-hour aggregation window ending at t satisfies
      [evaluateCctpV2Invariants(t, source, dest, mode)] = "BS2"
```

`evaluateCctpV2Invariants` is the rule fixed in `bridge_state_methodology.md` v1.1 §3, applied to the message-level rows of `ans_cctp_v2_message_attestations` reconstructed retroactively from the corpus parquets. Specifically, for an evaluation hour `t`:

```
n_eligible_t   = COUNT(messages with source_block_timestamp < t - SLA_mode
                       AND source_block_timestamp >= t - 1 hour)
n_attested_t   = COUNT(those eligible messages that have an attestation event)
success_rate_t = n_attested_t / n_eligible_t                 (NULL if n_eligible_t = 0)

n_resolved_fast_t  = COUNT(mode_requested='fast' AND
                            source_block_timestamp < t - SLA_fast
                            AND source_block_timestamp >= t - 1 hour
                            AND mode_executed IS NOT NULL)
n_escalated_fast_t = COUNT(within the above, mode_executed = 'standard')
mode_fallback_rate_t = n_escalated_fast_t / n_resolved_fast_t (NULL if n_resolved_fast_t = 0)

BS2(t) ≡ 1
  iff n_eligible_t >= 5
   AND (success_rate_t < 0.995 OR mode_fallback_rate_t > 0.05)
```

The two SLA values are inherited verbatim from `bridge_state_methodology.md` v1.1 §3.5:
`SLA_fast = 120 s`, `SLA_standard = 7200 s`.

### 2.1 Operational scope of the outcome

The 1-hour aggregation window is shorter than `SLA_standard`. Consequently, for Standard-mode triplets the eligible sample within any 1-hour window is structurally zero and the outcome is NULL on every hour. This is the expected behavior of `BRIDGE_STATE_STRUCTURAL_v1.1` documented in `bridge_state_methodology.md` v1.1 §3.5 and §5.

The protocol therefore restricts the outcome to the two **Fast-mode** triplets:

```
outcome_1  = bs2_eth_to_pol_fast
outcome_2  = bs2_pol_to_eth_fast
```

Standard-mode triplets are excluded from the configuration grid of §5 to avoid pre-engaging predictors against a structurally NULL outcome. A separate protocol may extend the aggregation window in a future version (`v1.1+`) to evaluate Standard.

### 2.2 Classifier semantics fixed in this protocol

The reconstruction of `mode_requested` and `mode_executed` on the corpus uses the v1.1 classifier (`calibration_log.md` Entry #045):

```
mode_requested
   = "other"      if min_finality_threshold_requested == 0
   = "fast"       if 1 <= min_finality_threshold_requested <= 1000
   = "standard"   if min_finality_threshold_requested == 2000
   = "other"      otherwise

mode_executed
   = same function applied to finality_threshold_executed read on the matched
     MessageReceived event of the destination chain.
```

Messages with `mode_requested = 'other'` are excluded from both numerators and denominators of `success_rate` and `mode_fallback_rate`. They contribute neither to `bs2_*_fast` nor to `bs2_*_standard`.

## 3. Input data

Three locked artefacts of the Step 3 corpus are consumed:

1. `data/cctp_v2_events_2025_raw.parquet` — source `DepositForBurn` + `MessageSent` events on Ethereum and `MessageReceived` events on the destination chains, together with their counterparts on Polygon. The reconstruction pairs source to destination via the on-chain `nonce` field (or `message_hash` where `nonce` is absent), restricted to the (source_domain, destination_domain) pairs `(0, 7)` and `(7, 0)` for ETH-POL.
2. `results/per_event_sheets/baseline.parquet` and the twelve per-event sheets — hourly substrate-shift series on Ethereum and Polygon, produced by `compute_step3.py` from the locked Step 2 parquets.
3. `MANIFEST.md` — root provenance, whose SHA-256 is recorded in the calibration output for trust-chain continuity.

No external data, no Iris API call, no production-database read. The full reconstruction is reproducible byte-for-byte from the locked parquets.

## 4. Predictor space

The predictor space is the substrate-shift family already used in the per-engaged exploration of the corridor's latency outcomes (cf. `corpus-2025/eth-pol-CCTP-v2/` blog publication on substrate-matrix shift detection). It is reproduced verbatim to preserve cross-protocol comparability:

**Ten substrate-shift axes** (locked Step 3 matrix columns):

| Chain | Axes |
|---|---|
| Ethereum | `eth_rhythm_ratio_shift`, `eth_continuity_ratio_shift`, `eth_sigma_demand_shift`, `eth_size_demand_shift`, `eth_tx_demand_shift` |
| Polygon | `pol_rhythm_ratio_shift`, `pol_continuity_ratio_shift`, `pol_sigma_demand_shift`, `pol_size_demand_shift`, `pol_tx_demand_shift` |

**Shift-magnitude delta** for each axis at hour `t`:

```
smd_axis(t) = |shift_axis(t)| − |shift_axis(t-1)|
```

**Instant alert per axis** triggers when `smd_axis(t)` exceeds the per-axis quantile threshold `pctl` of the non-January distribution of `smd_axis` over the calibration window (see §6 for the corridor-active window).

**Sustained alert** requires `K` consecutive instant alerts.

## 5. Configuration grid

Three families, identical in structure to the prior exploration but restricted to two outcomes (see §2.1):

```
F0 — single-axis
  10 axes × 3 pctl ∈ {0.85, 0.90, 0.95} × 2 K ∈ {1, 2} × 4 lead ∈ {3, 6, 12, 24} h × 2 outcomes
  = 480 configurations

F1 — multi-axis grouped
  8 group definitions (union variants by chain or by axis type, voting thresholds 2/3/4 axes)
  × 2 K × 4 lead × 2 outcomes at fixed pctl = 0.90
  = 128 configurations

F4 — cross-chain
  2 cross-chain group definitions (ETH-axes → pol_to_eth, POL-axes → eth_to_pol)
  × 5 axes × 2 K × 4 lead × 2 outcomes at fixed pctl = 0.90
  = 160 configurations

Total: 768 configurations
```

The eight F1 group definitions and the two F4 cross-chain group definitions are the same as those used in the prior exploration, listed verbatim in `scripts/compute_bs_structural_precursors_v1.py` as a constant dictionary, signed alongside the script.

## 6. Calibration window

The window is corridor-active, identical to `PRE_ENGAGEMENT_BS_CALIBRATION_v1.md` §3:

```
window_start = 2025-06-09 18:45 UTC   (Polygon CCTP V2 TokenMessengerV2 creation, block 72,566,047)
window_end   = 2025-12-31 23:59 UTC   (corpus year end)
```

Approximately 4 968 hours. The per-axis `pctl` thresholds of §4 are computed on the non-January 2025 substrate window (consistent with the prior exploration's warmup convention) to avoid pollution by the EMA initialization. The non-January window is therefore 2025-02-01 00:00 UTC to 2025-12-31 23:59 UTC for the percentile fit; the outcome evaluation uses the corridor-active window above.

## 7. Statistical machinery

For each of the 768 configurations:

1. **True positives, false positives, true negatives, false negatives** computed against the binary outcome `BS2(t + lead)` evaluated on the calibration window.
2. **Lift** = precision / base rate, where precision = TP / (TP + FP) and base rate = (TP + FN) / (TP + FP + FN + TN).
3. **Placebo p-value** from 500 random label-permutations of the outcome series, recomputing lift under random assignment. Empirical p = fraction of permutations whose lift ≥ observed lift.
4. **Benjamini-Hochberg FDR correction** applied at α = 0.05, computed separately within each family (F0, F1, F4) and combined across all 768 configurations.

The **survival criterion** is:

```
(BH-adjusted combined p < 0.05)  AND  (lift ≥ 1.5×)
```

A configuration that does not satisfy both is reported in the output JSON for transparency but is not retained as a candidate precursor.

## 8. Sample-size guards

If the outcome `BS2(t + lead)` is positive on fewer than 30 hours over the calibration window, the configuration's statistical test is reported but flagged `LOW_POWER`. Below 10 positive outcomes, the test is reported with `INSUFFICIENT_POWER` and excluded from the FDR family.

The empirical positive rate of `BS_STRUCTURAL_v1.1 BS2` on the corpus is, prior to execution of this protocol, **unknown**. The protocol explicitly accepts the case where the outcome is too sparse for statistical inference, and reports the empty survivor set rather than relaxing the criterion.

## 9. Output artefact

`scripts/compute_bs_structural_precursors_v1.py` produces a single output:

```
results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json
```

Schema (UTF-8 JSON, sorted keys, indent 2):

```json
{
  "protocol_version": "BS_STRUCTURAL_PRECURSORS_v1",
  "corpus_reference": "ETH-POL-CCTP-V2 publiable corpus, MANIFEST.md sha-256 <hash>",
  "calibration_window_start_utc": "2025-06-09T18:45:00Z",
  "calibration_window_end_utc":   "2025-12-31T23:59:00Z",
  "outcome_definition": "BRIDGE_STATE_STRUCTURAL_v1.1 BS2 (success_rate < 0.995 OR mode_fallback_rate > 0.05) gated by SLA_fast=120s, SLA_standard=7200s, restricted to mode_requested ∈ {fast}",
  "classifier_semantics": "min_finality_threshold_requested==0 → 'other' (excluded); 1..=1000 → 'fast'; ==2000 → 'standard'; else → 'other'",
  "outcomes_evaluated": ["bs2_eth_to_pol_fast", "bs2_pol_to_eth_fast"],
  "outcome_positive_rate_per_hour": {
    "bs2_eth_to_pol_fast": <float>,
    "bs2_pol_to_eth_fast": <float>
  },
  "n_configurations_total":           768,
  "n_configurations_raw_p_lt_005":    <int>,
  "n_configurations_fdr_within_family": <int>,
  "n_survivors_combined_fdr_and_lift": <int>,
  "survivors": [
    {
      "family":      "F0|F1|F4",
      "axis":        "<axis label or group label>",
      "k_consecutive_hours": <int>,
      "pctl":        <float>,
      "lead_hours":  <int>,
      "outcome":     "<bs2_eth_to_pol_fast|bs2_pol_to_eth_fast>",
      "lift":        <float>,
      "precision":   <float>,
      "alert_rate":  <float>,
      "placebo_p":   <float>,
      "bh_combined_p_adj": <float>,
      "n_positive_outcomes": <int>,
      "power_flag":  "OK|LOW_POWER|INSUFFICIENT_POWER"
    }
  ],
  "script_sha256":        "<SHA-256 of compute_bs_structural_precursors_v1.py>",
  "input_parquets_sha256": {
    "cctp_v2_events_2025_raw.parquet": "<hash>",
    "baseline.parquet": "<hash>"
  }
}
```

The JSON is hashed, Ed25519-signed in three namespaces, and OpenTimestamps-anchored on Bitcoin. The signed JSON is the source of truth for the survivor set under this protocol.

## 10. Stated limits

1. **Standard-mode outcome not evaluated.** As established in §2.1, the 1-hour aggregation window combined with `SLA_standard = 7200 s` produces a structurally zero eligible sample for Standard-mode evaluation on any single hour. The protocol restricts itself to the two Fast-mode outcomes and explicitly acknowledges this restriction. A future `v1.1+` may revisit Standard with a wider aggregation window.
2. **Outcome positive rate unknown at lock time.** The empirical positive rate of `BS_STRUCTURAL_v1.1 BS2` on the 2025 ETH-POL CCTP V2 corpus is not observed before the protocol is locked. If the rate is very low (well under 1 % of hours), the statistical power against `lift ≥ 1.5×` is intrinsically limited. The protocol accepts that the empty survivor set is a possible legitimate outcome.
3. **Per-corridor scope.** The 2025 corpus covers only the ETH-POL corridor. Transfer to ETH-ARB, ETH-BASE, ETH-OP, ETH-AVAX, ETH-SOL CCTP V2 corridors is not asserted by this protocol. Each corridor requires its own locked corpus and its own signed pre-engagement.
4. **Latency precursors not superseded.** Substrate-shift configurations that were validated under prior latency-outcome protocols (the nineteen configurations published in the eth-pol-CCTP-v2 matrix-and-drift article) remain valid under their original outcome. The present protocol introduces a separate evaluation against a distinct, structurally defined outcome. The two protocols co-exist; a configuration may survive one and not the other, or both.
5. **Reorg-tracking invariant not in scope.** Consistent with `bridge_state_methodology.md` v1.1 §3 note, the deferred fifth invariant (`messages_burned == messages_minted` cumulative) is not part of the outcome definition of `BS_STRUCTURAL_v1.1`. A future `BS_STRUCTURAL_v1.1.1` may add it, with a fresh pre-engagement for the precursor evaluation.

## 11. Verification protocol for external readers

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_bs_structural_precursors_v1_signer_<i> \
  -n invarians_calibration_bs_structural_precursors_v1 \
  -s signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md.sig.<i> \
  < PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md

ots verify signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md.sig.<i>.ots
```

Reproduction: any third party re-running `compute_bs_structural_precursors_v1.py` against the locked Step 3 parquets must obtain a JSON output whose `survivors[]` and `outcome_positive_rate_per_hour` fields match the signed output byte-for-byte. The pre-engagement signature is the cryptographic record that the methodological choices of Sections 2 to 10 are fixed prior to the script run.

## 12. Signing

The present document is locked, SHA-256 hashed, and signed with three independent Ed25519 keys under namespace `invarians_calibration_bs_structural_precursors_v1`. The hash is stamped on Bitcoin via OpenTimestamps. Signatures are stored under `signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md.sig.{1,2,3}` and their OpenTimestamps proofs at the corresponding `.ots` paths.

The Ed25519 signatures and the Bitcoin block anchor are the authoritative cryptographic record that the outcome definition (§2), the input data scope (§3), the predictor space (§4), the configuration grid (§5), the statistical machinery (§7), and the sample-size guards (§8) are fixed prior to execution of `compute_bs_structural_precursors_v1.py` against the corpus.

---

*v1.0-draft — pre-engagement for substrate-shift precursors against the `BRIDGE_STATE_STRUCTURAL_v1.1 BS2` outcome on the ETH-POL CCTP V2 corridor 2025 corpus. Successor protocols extend the methodology to other CCTP V2 corridors as their per-corpus pre-engagements are produced and signed.*
*Lock condition: three Ed25519 signatures + OpenTimestamps Bitcoin stamp, before any execution of `compute_bs_structural_precursors_v1.py`.*
