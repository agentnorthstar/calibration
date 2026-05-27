# Methodology Step 3 Conventions

**Status.** Pre-execution conventions document. Hashed and listed in `MANIFEST.md` §Step 3 at lock time alongside the report and per-event parquets.

**Date drafted.** 2026-05-26.

**Contract reference.** `METHODOLOGY.md` §3 Step 3 specifies the outputs and the general framework. This document fixes the explicit formulas, threshold tables, and decision trees used by `scripts/compute_step3.py` to produce those outputs. It is intended to allow byte-for-byte reproduction by any external reviewer.

---

## 1. Hourly metrics, per chain

Hourly buckets are defined on UTC, half-open intervals `[h, h+1)` where `h` is the integer hour expressed in UTC. A block belongs to the bucket containing its `block_timestamp`.

### 1.1 rhythm_ratio

For each hour `h`, let `B(h)` be the set of blocks whose timestamp falls in `[h, h+1)`, indexed in ascending order. For each consecutive pair of blocks `(b_{i-1}, b_i)` in `B(h)`, compute the inter-block interval:

```
delta_i = timestamp(b_i) − timestamp(b_{i-1})
```

The hourly rhythm metric is the median of `{delta_i}` divided by the protocol target block time:

```
rhythm_ratio(h) = median({delta_i : i in B(h)}) / target_block_time
```

Protocol target block times:
- Ethereum mainnet: `target_block_time = 12.0 seconds` (slot duration since the Merge, EIP-3675)
- Polygon PoS mainnet: `target_block_time = 2.0 seconds` (Bor block production target)

The median is used instead of the mean to be robust to single-block jitter (occasional re-org repositioning, occasional 24 second gaps after a missed ETH proposal). For a strictly nominal hour, `rhythm_ratio = 1.000`. For an hour where slots are systematically missed, `rhythm_ratio > 1.0`. For an hour with abnormally fast block production (rare), `rhythm_ratio < 1.0`.

### 1.2 continuity_ratio

```
continuity_ratio(h) = |B(h)| / expected_blocks_per_hour
```

Expected blocks per hour:
- Ethereum mainnet: `expected_blocks_per_hour = 3600 / 12.0 = 300`
- Polygon PoS mainnet: `expected_blocks_per_hour = 3600 / 2.0 = 1800`

For a nominal hour, `continuity_ratio ≈ 1.000`. For a halt or RPC degradation, `continuity_ratio < 1.0`. Values above 1.0 are theoretically possible if block production exceeds nominal cadence.

### 1.3 sigma_demand

`sigma_demand` is the ratio of the current hour coefficient of variation on `gas_used` to its 30-day exponentially weighted moving average.

```
CV(h) = std(gas_used over B(h)) / mean(gas_used over B(h))
```

If `mean(gas_used over B(h)) = 0` (degenerate case), `CV(h) = NaN` and the row is flagged.

```
sigma_demand(h) = CV(h) / EMA_30d(CV)(h)
```

For a nominal hour, `sigma_demand ≈ 1.000`. For a hot window with abnormal gas variance, `sigma_demand` diverges in either direction.

### 1.4 size_demand

```
avg_tx_per_block(h) = mean(transaction_count over B(h))
size_demand(h) = avg_tx_per_block(h) / EMA_30d(avg_tx_per_block)(h)
```

### 1.5 tx_demand

```
total_tx_per_hour(h) = sum(transaction_count over B(h))
tx_demand(h) = total_tx_per_hour(h) / EMA_30d(total_tx_per_hour)(h)
```

---

## 2. EMA convention

Each EMA series uses the same hourly cadence and the same half-life.

Half-life: 30 calendar days = 720 hours.

EWMA decay factor (per hour):

```
alpha = 1 − exp(−ln(2) / 720) ≈ 9.6244e-4
```

Recurrence (for any series `x` of hourly observations):

```
EMA[0] = x[0]
EMA[t] = (1 − alpha) * EMA[t − 1] + alpha * x[t]
```

Warmup. The first 30 days of the corpus window (1 January 2025 00:00 UTC to 30 January 2025 23:59 UTC, equivalently the first 720 hourly observations) are flagged `ema_warmup = True` in the per-event sheets and in the baseline. During warmup, the EMA value is mathematically defined but is sensitive to the initial seed. Regime classifications and signed shifts are still reported during warmup, accompanied by the flag, and are not interpretable as calibrated signals against a stable baseline.

NaN handling. If a metric value is `NaN` at hour `t` (degenerate case, missing data), the EMA propagation skips that observation: `EMA[t] = EMA[t − 1]`. This is documented at the row level by an additional `metric_nan_at_t` flag.

---

## 3. Signed shifts

For each metric `M ∈ {rhythm_ratio, continuity_ratio, sigma_demand, size_demand, tx_demand}` and each chain `c ∈ {eth, pol}`:

```
shift_{c}_{M}(h) = (M(h) − EMA_30d(M)(h)) / EMA_30d(M)(h)
```

Sign is preserved. Positive shift means the metric is above its 30-day reference, negative means below. A small `EMA_30d(M)(h)` near zero would make the shift diverge; this is protected by clipping the divisor at a small epsilon (1e-9) and flagging the row.

---

## 4. Drift composite

Two composites per chain.

```
drift_structural(c)(h) = (shift_{c}_rhythm_ratio(h) + shift_{c}_continuity_ratio(h)) / 2
drift_demand(c)(h) = (shift_{c}_sigma_demand(h) + shift_{c}_size_demand(h) + shift_{c}_tx_demand(h)) / 3
```

Unweighted means by axis. Sign preserved.

---

## 5. Regime code decision tree

Production thresholds (from `METHODOLOGY.md` §4, applied without recalibration):

| Chain | `threshold_s2` | `sigma_d2` | `size_d2` | `tx_d2` |
|---|---|---|---|---|
| Ethereum | 1.12 | 1.10 | 1.20 | 1.10 |
| Polygon | 1.04 | 1.14 | 1.18 | 1.23 |

### 5.1 S axis (structural)

For each chain `c`:

```
if rhythm_ratio(c)(h) > threshold_s2(c):
    S = "S2+"
elif rhythm_ratio(c)(h) < 1.0 / threshold_s2(c):
    S = "S2-"
else:
    S = "S1"
```

The lower band uses the multiplicative inverse of the threshold to preserve geometric symmetry around 1.0.

### 5.2 D axis (demand)

For each demand metric `M ∈ {sigma_demand, size_demand, tx_demand}`, classify:

```
if M(h) > threshold_d2_M(c):
    state(M) = "ABOVE"
elif M(h) < 1.0 / threshold_d2_M(c):
    state(M) = "BELOW"
else:
    state(M) = "NEUTRAL"
```

Then count:

```
n_above = number of M with state(M) == "ABOVE"
n_below = number of M with state(M) == "BELOW"
n_triggered = n_above + n_below
```

Decision:

```
if n_triggered < 2:
    D = "D1"
elif n_above >= 2 and n_below == 0:
    D = "D2+"
elif n_below >= 2 and n_above == 0:
    D = "D2-"
elif n_above >= 1 and n_below >= 1:
    D = "D2±"
else:
    D = "D1"  # defensive fallback, should not occur
```

### 5.3 Composite code

The 12 signed codes are the Cartesian product `S × D`:

`S1D1, S1D2+, S1D2-, S1D2±, S2+D1, S2-D1, S2+D2+, S2+D2-, S2+D2±, S2-D2+, S2-D2-, S2-D2±`

---

## 6. CCTP V2 latency reconstruction

### 6.1 Source-side to destination-side matching

In CCTP V2, the message `nonce` is not assigned by the source contract at `MessageSent` emission. The 32-byte nonce field at offset `[12:44]` of the message header is set to `bytes32(0)` by `MessageTransmitterV2.sendMessage`. The nonce is generated off-chain by Circle's attestation service after observation of the source-side burn, then inserted into the message body before the user invokes `receiveMessage` on the destination chain. The `MessageReceived` event's indexed `nonce` field (topic2) is therefore the Circle-attributed identifier, available only after attestation. The 2025 corpus parquet confirms this empirically: 266,263 of 266,263 `MessageSent V2` rows carry `nonce = 0x000...000`. Byte-exact identification of the `MessageSent` paired with each `MessageReceived` is therefore not feasible from public on-chain state alone, and `METHODOLOGY.md` §2 excludes dependence on Circle's Iris attestation API or any other off-chain source.

The reconstruction method specified for this corpus is **greedy proximity-window matching, stratified by mode requested on the source side**.

The mode dimension is taken from the source-side field `MessageSent.min_finality_threshold` (the user-requested finality threshold). The destination-side equivalent field on `MessageReceived` reports `finalityThresholdExecuted` (the finality level actually applied by Circle), which can differ from the requested mode when Circle's risk pipeline escalates a Fast request to Standard finality. Stratifying both sides by their respective `min_finality_threshold` fields therefore creates a stratification mismatch that breaks the rank correspondence between source and destination. The retained algorithm stratifies the source side by requested mode and does not stratify the destination side, attributing the requested mode to each successful pair.

**Algorithm.**

```
For each (source_domain, destination_domain) ∈ {(0, 7), (7, 0)}:
    R := MessageReceived rows with the matching (source_domain, destination_domain),
         sorted ascending by block_timestamp.
    used[r] := False for all r in R.

    For mode ∈ {Fast, Standard}:
        S_mode := MessageSent rows with the matching (source_domain, destination_domain)
                  and min_finality_threshold classifying as `mode` per §6.3,
                  sorted ascending by block_timestamp.
        W := plausibility_window(mode)

        For each sent in S_mode (chronological order):
            j := smallest index in R such that
                 used[j] is False
                 AND R[j].block_timestamp ∈ [sent.block_timestamp, sent.block_timestamp + W].
            If j exists:
                Pair (sent, R[j]); used[j] := True.
                latency_s := R[j].block_timestamp − sent.block_timestamp.
                Attribute mode = source-side requested mode to the pair.
            Else:
                Increment unpaired_sent[mode].

        recv_unused[direction] := count of j with used[j] = False.
```

**Plausibility windows.**

| Mode | Window | Rationale |
|---|---|---|
| Fast | 2 hours | CCTP V2 Fast transfers complete in 5 to 30 seconds under nominal conditions. The 2-hour window accommodates stress events where Circle's attestation pipeline is throttled, while excluding pairings to messages whose timing is implausibly long for the Fast settlement category. |
| Standard | 48 hours | CCTP V2 Standard transfers complete after the destination chain's hard-finality interval (Ethereum approximately 13 minutes; Polygon approximately 5 seconds Heimdall) plus attestation latency. The empirical p99 over 2025 is approximately 1 to 3 hours; the 48-hour window accommodates outliers from chain incidents documented in `INCIDENTS_2025.md`. |

**Reproducibility and contract compliance.**

- The algorithm is deterministic: any reviewer applying the same procedure to the Step 2 parquets obtains an identical set of pairs and an identical pairing log.
- All inputs are the public BigQuery-derived parquets locked at Step 2. No external API call is invoked.
- The matching is not a cryptographic byte-exact identity assignment, an outcome that is structurally infeasible in CCTP V2 from on-chain state. The matching is a documented heuristic with explicit window parameters. The pairing log committed in `MANIFEST.md` §Step 3 records `n_sent`, `n_paired`, `n_unpaired_sent`, and `n_recv_unused` per direction and mode, allowing independent verification of coverage.
- Mode is attributed from the source side (requested), corresponding to the user-observable transit category of the corridor.

**Edge cases.**

- Unpaired `Sent` at the corpus boundary: messages emitted late in 2025 whose receive falls in 2026 are counted as unpaired and excluded from latency computation.
- Unused `Received` rows: messages whose Sent counterpart was emitted in 2024 (outside the corpus window) or whose plausible Sent slot in 2025 was claimed by a more recent Sent under the greedy rule. The pairing log records the count.
- `mode = Other` (atypical `min_finality_threshold` outside the canonical set `{≤1000, =2000}`) is excluded from the corridor latency computation and recorded in the pairing log residuals.

### 6.2 Per-message latency

```
latency_seconds(message) = MessageReceived.block_timestamp − MessageSent.block_timestamp
```

`block_timestamp` is the destination chain block timestamp at the `MessageReceived` event, and the source chain block timestamp at the `MessageSent` event. Both are recorded as UTC timestamps by BigQuery, comparable across chains.

This proxies the end-to-end transit latency requested by the contract §3 Step 3, with `MessageSent.block_timestamp ≈ DepositForBurn.block_timestamp` (the two events are emitted in the same transaction).

### 6.3 Mode classification

Each message carries a `min_finality_threshold` (from `MessageSent` header or `MessageReceived` indexed topic). Classification:

```
if min_finality_threshold <= 1000:
    mode = "Fast"
elif min_finality_threshold == 2000:
    mode = "Standard"
else:
    mode = "Other"  # flagged as anomaly
```

### 6.4 Hourly aggregation

Bucket each matched message by `MessageReceived.block_timestamp` floored to the hour. Group by `(source_domain, destination_domain, mode, hour)`. Compute:

```
messages_observed_1h
attestation_latency_p50_s = quantile(latencies, 0.50)
attestation_latency_p90_s = quantile(latencies, 0.90)
attestation_latency_p99_s = quantile(latencies, 0.99)
```

For the ETH-POL corridor specifically, two directions are tracked:
- `direction = "eth_to_pol"`: `source_domain = 0`, `destination_domain = 7`
- `direction = "pol_to_eth"`: `source_domain = 7`, `destination_domain = 0`

Messages with other domain pairs (for example messages from Avalanche to Ethereum that pass through the corpus) are excluded from the corpus latency report. They remain in the parquet for completeness.

---

## 7. Hot window selection

For each `event_id` in `INCIDENTS_2025.md`:

```
extended_window = [hot_window_start_utc − 6 hours, hot_window_end_utc + 6 hours]
```

The per-event sheet covers all hours in `extended_window`. For events with month-only precision (`POL_HEIMDALL_CONSENSUS_2025_07`, `POL_BOR_RPC_2025_12`), the extended window spans the entire documented month plus 6 hours of padding on each side. This is documented in `LIMITATIONS.md`.

For `ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09` (hot window from 2025-09-09 to 2025-09-26), the extended window is approximately 17 days plus 12 hours.

---

## 8. Baseline computation

The baseline is the set of all hours in 2025 that fall **outside** any extended event window (hot window ± 6 hours, for all events in the inventory). For each metric and each chain, the baseline parquet reports the hour-by-hour values with the same column schema as the per-event sheets, plus an aggregate row at the end that contains:

```
mean, median, std, min, p25, p75, max, count
```

over the baseline hours, per metric per chain. This aggregate provides the reference distribution against which per-event observations are visually compared in the report.

---

## 9. Per-event sheet schema

For each event, one parquet file `results/per_event_sheets/{event_id}.parquet` with columns:

```
event_id                        string
hour_utc                        timestamp
in_hot_window                   bool
ema_warmup                      bool
# ETH metrics (raw)
eth_rhythm_ratio                float64
eth_continuity_ratio            float64
eth_sigma_demand                float64
eth_size_demand                 float64
eth_tx_demand                   float64
# ETH EMAs
eth_rhythm_ratio_ema            float64
eth_continuity_ratio_ema        float64
eth_sigma_demand_ema            float64
eth_size_demand_ema             float64
eth_tx_demand_ema               float64
# ETH signed shifts
eth_rhythm_ratio_shift          float64
eth_continuity_ratio_shift      float64
eth_sigma_demand_shift          float64
eth_size_demand_shift           float64
eth_tx_demand_shift             float64
# ETH drift composite
eth_drift_structural            float64
eth_drift_demand                float64
# ETH regime
eth_regime_code                 string
# POL metrics (raw)
pol_rhythm_ratio                float64
pol_continuity_ratio            float64
pol_sigma_demand                float64
pol_size_demand                 float64
pol_tx_demand                   float64
# POL EMAs
pol_rhythm_ratio_ema            float64
pol_continuity_ratio_ema        float64
pol_sigma_demand_ema            float64
pol_size_demand_ema             float64
pol_tx_demand_ema               float64
# POL signed shifts
pol_rhythm_ratio_shift          float64
pol_continuity_ratio_shift      float64
pol_sigma_demand_shift          float64
pol_size_demand_shift           float64
pol_tx_demand_shift             float64
# POL drift composite
pol_drift_structural            float64
pol_drift_demand                float64
# POL regime
pol_regime_code                 string
# CCTP V2 latency (per hour, per direction, per mode)
cctp_v2_messages_observed_1h_eth_to_pol_fast        int64
cctp_v2_p50_eth_to_pol_fast_s                       float64
cctp_v2_p90_eth_to_pol_fast_s                       float64
cctp_v2_p99_eth_to_pol_fast_s                       float64
cctp_v2_messages_observed_1h_eth_to_pol_standard    int64
cctp_v2_p50_eth_to_pol_standard_s                   float64
cctp_v2_p90_eth_to_pol_standard_s                   float64
cctp_v2_p99_eth_to_pol_standard_s                   float64
cctp_v2_messages_observed_1h_pol_to_eth_fast        int64
cctp_v2_p50_pol_to_eth_fast_s                       float64
cctp_v2_p90_pol_to_eth_fast_s                       float64
cctp_v2_p99_pol_to_eth_fast_s                       float64
cctp_v2_messages_observed_1h_pol_to_eth_standard    int64
cctp_v2_p50_pol_to_eth_standard_s                   float64
cctp_v2_p90_pol_to_eth_standard_s                   float64
cctp_v2_p99_pol_to_eth_standard_s                   float64
# Base fee
base_fee_per_gas_eth            int64
base_fee_per_gas_pol            int64
```

`NULL` is used where a quantile cannot be computed (zero messages in the bucket).

---

## 10. Report structure

`results/REPORT_ETH_POL_CCTP_V2.md` contains:

- Section 1: scope and corpus inventory recap (event count, distribution by chain).
- Section 2: per-event narrative. One subsection per event_id in chronological order. Each subsection summarizes what the matrix reports during the extended window in plain prose: which regime codes the chains transit through, which shifts diverge from zero, which CCTP V2 latency percentiles spike or stay nominal. The report does not interpret, predict, or claim causation. It describes.
- Section 3: baseline summary. Aggregate distribution of metrics over the 2025 baseline hours.
- Section 4: limitations recap, mirroring `LIMITATIONS.md` (EMA warmup, POL substrate observation status, month-only event precision, dataset substitution notice on POL).

The report contains no inferential claim. No p-value, no lift, no PASS or FAIL verdict.

---

## 11. Limitations applicable to Step 3

Recorded in `LIMITATIONS.md` at lock time:

- EMA warmup: regimes and shifts for January 2025 are flagged `ema_warmup = True` and are sensitive to the EMA seed. Interpretation requires caution.
- POL substrate observation: `rho_ts` on POL is reported empirically. The production methodology notes a 0.011 second amplitude on 90 days of nominal operation; the matrix output for POL during the documented POL events is part of what the report records, not a pre-judgement.
- Month-only event precision: two POL events (`POL_HEIMDALL_CONSENSUS_2025_07`, `POL_BOR_RPC_2025_12`) have their extended window spanning an entire month plus 6 hours. The per-event sheet for these events contains hundreds of hours rather than tens.
- POL dataset selection: per `MANIFEST.md` §Step 2.
- Convention transparency: the formulas in this document are best-documented effort. The production Invarians stack may compute equivalent metrics with marginal numerical differences (rounding, edge cases). Where differences are detectable, they are flagged in the report.

---

End of conventions document.
