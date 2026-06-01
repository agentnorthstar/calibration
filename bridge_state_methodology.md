---
title: "Invarians — Bridge State Methodology (CCTP V2 and CCIP V1.5 / V1.6)"
version: "1.0-draft"
status: draft
audience: [ai-agents, developers, researchers, auditors]
---

# Bridge State methodology — structural invariants approach

> **Status.** Draft of protocol `BRIDGE_STATE_STRUCTURAL_v1`. Supersedes the statistical P97-on-latency approach documented in `methodology.md` §13 for the CCTP V2 and CCIP V1.5 / V1.6 surfaces.
>
> The protocol is locked when the present document is hashed, Ed25519-signed in three namespaces, and stamped on Bitcoin via OpenTimestamps. Tolerances stated in §3 and §4 are pre-engaged and may not be adjusted to match observed false-positive / true-positive rates: any adjustment requires rotation to a successor protocol with its own pre-engagement signature.

---

## 1. Why structural over statistical

Calibrating a P97 quantile on attestation latency and calling the resulting binary classification a *bridge state* produces an instrument whose `BS2` label is, by construction, the assertion *"latency lies in the upper tail of the 2025 distribution of latencies"*. It does not assert *"the cross-chain transfer will not settle"*, *"funds are stuck"*, or *"the protocol contract is broken"* — which are the propositions an autonomous agent acting on the bridge needs.

The internal lessons document `event-agent/LESSONS_LEARNED_2026_05_15.md` (§Erreur 1, §Erreur 2) records this point as a methodological error from the May 2025 sprint. The sourced needs analysis `event-agent/SOURCED_NEEDS_BY_AUDIENCE.md` (§4) names the externally testable outcomes attached to *Element 2 — BS1/BS2 stability* as *attestation failure rate, fast-mode fallback rate, stuck-funds events* — not latency in any quantile.

The protocol below defines `BS1` and `BS2` directly on the contractual invariants of the underlying cross-chain protocols. The P97 calibration of latency, computed on the 2025 ETH-POL CCTP V2 corpus and Ed25519-signed under protocol identifier `BS_CALIBRATION_v1`, is retained as a separate object: a candidate **latency precursor**, to be validated by independent empirical lift against the structural `BS2` outcome defined here.

## 2. Definition of the state on a variable-latency cross-chain protocol

For every entry of `panel.bridges[]` of type `cctp` or `ccip`, the state on the most recent aggregation window is one of three values:

```
BS1            all invariants of the underlying protocol contract hold
BS2            at least one invariant of the underlying protocol contract is broken
UNAVAILABLE    observation is invalid (instrument degraded or sample too small)
```

The classification is computed by direct rule evaluation on the observables present in `ans_cctp_v2_route_signals` (for CCTP V2) and `ans_ccip_messages` (for CCIP V1.5 / V1.6). There is no fitted threshold in the chain `observable → state`. The cutoffs that separate *invariant holds* from *invariant broken* are pre-engaged tolerances on each invariant individually, stated in §3 and §4.

## 3. CCTP V2 — invariants and pre-engaged tolerances

Circle's CCTP V2 protocol commits the following contractual properties on each cross-chain USDC transfer: a `MessageSent` event is emitted on the source domain, an ECDSA attestation is delivered by Iris within the requested `finality_threshold` (Fast or Standard), the executed `finality_threshold` matches the requested one, and a `MessageReceived` event is emitted on the destination domain within a bounded settlement window.

The four invariants below capture this contract on the 1-hour aggregation window already produced by `bridge/cctp-v2-collector/src/aggregator.rs` into `ans_cctp_v2_route_signals`:

| # | Invariant | Observable on the row | Pre-engaged tolerance |
|---|---|---|---|
| I1 | Attestation delivered | `attestation_success_rate` | `>= 0.995` |
| I2 | Requested mode honored | `mode_fallback_rate` | `<= 0.05` |
| I3 | Instrument valid | `confounded_by_iris_downtime` | `== false` |
| I4 | Sample sufficient | `n_observations` | `>= 5` |

State transition rules:

```
n_observations  < 5                     ⇒ UNAVAILABLE  (rule blocks before any other check)
confounded_by_iris_downtime == true     ⇒ UNAVAILABLE  (instrument degraded)
attestation_success_rate >= 0.995
  AND mode_fallback_rate  <= 0.05       ⇒ BS1
otherwise                               ⇒ BS2
```

### Justification of each tolerance (mechanical, not data-derived)

**I1, `attestation_success_rate >= 0.995`.** Institutional infrastructure SLA tier-1 convention is four nines or higher on settlement success. Three nines (0.999) is the strict target; 0.995 is the operational tolerance that admits one delayed attestation in 200 within the 1-hour window without firing `BS2`. Below 0.995, the Circle attestation pipeline is failing to honor its contract at a rate that an RWA workflow cannot ignore.

**I2, `mode_fallback_rate <= 0.05`.** Circle CCTP V2 documentation frames the Fast-to-Standard fallback as the response to *"unusually high finality risk"* on the source chain, conceptualized as a rare event. A 5% tolerance on the 1-hour window admits one fallback per twenty Fast requests as normal operational noise. Above 5%, Circle is escalating the requested mode for a non-negligible fraction of users — operationally this is a `BS2` condition that an agent requesting Fast settlement must observe.

**I3, `confounded_by_iris_downtime == false`.** The flag is raised by the collector when Iris consecutive failures during the aggregation window exceed an upstream threshold. A raised flag means the latency distribution observed in the window is not a valid measurement of the protocol's behavior, only of the instrument's. The state is `UNAVAILABLE`, not `BS2`: an unavailable instrument is distinct from a broken protocol.

**I4, `n_observations >= 5`.** Below five attested messages in the window, a single failure pushes `attestation_success_rate` to 0.8, which is statistically meaningless as a signal but would mechanically trigger `BS2` under I1. The minimum sample size of 5 is chosen as the smallest value at which a single failure ratio (1/5 = 0.20) is large enough to be a real signal rather than noise from low traffic. Below 5 messages, the state is `UNAVAILABLE`.

### Note on a reorg-tracking invariant

A fifth invariant — `messages_burned == messages_minted` over a cumulative window — would close the burn-to-mint settlement loop and is the natural test for the *stuck-funds* outcome named in `SOURCED_NEEDS_BY_AUDIENCE.md` §4. It requires a join between source-side `DepositForBurn` rows and destination-side `MessageReceived` rows over a settlement-bounded window (2 h for Fast, 48 h for Standard, per the pairing convention of `compute_step3.py` §6.1). The capture pipeline already records both events; the join is a forthcoming SQL view, not new instrumentation. The fifth invariant is therefore deferred to `BRIDGE_STATE_STRUCTURAL_v1.1`, which will add it as an additional `BS2` trigger once the view is in production.

## 4. CCIP V1.5 / V1.6 — invariants and pre-engaged tolerances

Chainlink CCIP commits, for each cross-chain message, that the DON Risk Management Network is not cursed, that the message identified by its `bytes32 messageId` is committed by the Committing DON and subsequently executed on the destination, and that the destination `ExecutionStateChanged` event records `executionState = 2` (Success) for the message. The collector `bridge/ccip-collector` records both source and destination events into `ans_ccip_messages` keyed by `messageId`.

| # | Invariant | Observable on the row | Pre-engaged tolerance |
|---|---|---|---|
| J1 | Message executed | `execution_success_rate_1h` | `>= 0.995` |
| J2 | RMN not cursed | `rmn_cursed` | `== false` |
| J3 | Instrument valid | `confounded_by_collector_downtime` | `== false` |
| J4 | Sample sufficient | `n_observations` | `>= 5` |

State transition rules are analogous to CCTP V2.

### Justification

**J1.** Same convention as I1. CCIP `executionState = 2` is the success path; `executionState = 3` (Failure) plus pending messages past the SLA constitute the failure subset. Tolerance 0.995.

**J2.** RMN-cursed is an absolute fault: a single cursed observation in the window means the lane is frozen by Chainlink protocol. The tolerance is binary (`false`), not statistical. A cursed lane is `BS2`.

**J3.** Same logic as I3 transposed to the CCIP collector. `UNAVAILABLE` when the instrument cannot validly observe.

**J4.** Same logic as I4.

### Sequence gap

CCIP exposes `sequence_gap` (current sequence number minus last advanced sequence number). On lanes with sustained throughput, a positive `sequence_gap` indicates that the destination is falling behind the source — a partial congestion signal. The mapping `sequence_gap → invariant` is not pre-engaged in v1: existing CCIP throughput across the ten monitored lanes is too sparse to commit a tolerance mechanically. A future `BRIDGE_STATE_STRUCTURAL_v1.2` may add a fifth invariant on `sequence_gap` once a sustained traffic profile is established and a mechanical tolerance can be justified.

## 5. Status field in the API payload

The Edge Function `attestation/index.ts` exposes the state on each `BridgeEntry` as the existing `state` field (`BS1` / `BS2` / `null`) combined with the existing `status` field (`OK` / `STALE` / `UNAVAILABLE` / `UNCALIBRATED`). The mapping:

| Computed | `state` | `status` |
|---|---|---|
| All invariants hold | `BS1` | `OK` |
| At least one invariant broken | `BS2` | `OK` |
| Sample insufficient or instrument confounded | `null` | `UNAVAILABLE` |
| Window data older than freshness bound | `null` | `STALE` |
| Bridge present but no methodology applicable (legacy, future protocol) | `null` | `UNCALIBRATED` |

The `BridgeEntry` does not need a per-row threshold in `bridge_thresholds` to classify under the present protocol: the rules above are evaluated directly on the most recent `ans_cctp_v2_route_signals` row. The legacy `threshold_bs1_s` column remains in the schema but is no longer the source of truth for CCTP V2 routes calibrated under `BRIDGE_STATE_STRUCTURAL_v1`; instead the `calibration_method` field records the protocol identifier and `calibrated` is set to `true` for any corridor where the methodology applies.

## 6. Recycling the latency calibration as a precursor

The output of protocol `BS_CALIBRATION_v1` on the ETH-POL CCTP V2 corpus 2025 — four pre-engaged P97 latency thresholds per (direction, mode) triplet, Ed25519-signed and OpenTimestamps-anchored on Bitcoin — is retained as a **candidate latency precursor** under a separate protocol `LATENCY_PRECURSOR_v1`. The precursor hypothesis is:

```
H_lat:  attestation_latency_p90_s (hour t) > P97_corpus_2025 (triplet)
        →  P(BS2 in [t+1, t+N hours] under BRIDGE_STATE_STRUCTURAL_v1)
           > P(BS2 baseline under BRIDGE_STATE_STRUCTURAL_v1)
```

The precursor is operationally separate from the state: a firing precursor on latency does not flip `state` from `BS1` to `BS2`. It is exposed in the API on the `BridgeEntry` under a distinct field (to be specified in `LATENCY_PRECURSOR_v1`), with its own pre-engagement and its own empirical validation pass (BH FDR, lift threshold, placebo permutations) following the pattern already established for the nineteen ETH-POL CCTP V2 substrate-shift precursors published in *eth-pol-cctp-v2-2025-matrix-and-drift*.

Until `LATENCY_PRECURSOR_v1` is locked and the empirical validation is completed, the four P97 values remain in the corpus output `BS_CALIBRATION_ETH_POL_CCTP_V2.json` as a signed pre-validation artefact, not as a production-deployed signal.

## 7. Schema implications and migration

The transition from `BS_CALIBRATION_v1` (statistical P97 on latency, four mode-suffixed rows seeded in production) to `BRIDGE_STATE_STRUCTURAL_v1` (rule-based on invariants, no per-row threshold needed) requires the following changes in production:

1. The four mode-suffixed rows in `bridge_thresholds` (`ethereum-polygon/cctp/fast`, `ethereum-polygon/cctp/standard`, `polygon-ethereum/cctp/fast`, `polygon-ethereum/cctp/standard`) are replaced by two mode-agnostic rows (`ethereum-polygon/cctp`, `polygon-ethereum/cctp`) carrying `calibration_method = 'BRIDGE_STATE_STRUCTURAL_v1'`, `calibrated = true`, `threshold_bs1_s = NULL`, `confidence = NULL`, `calibration_source = NULL`.
2. The Edge Function `attestation/index.ts` evaluates the four invariants of §3 on the latest `ans_cctp_v2_route_signals` row for each direction. `BridgeEntry.id` remains `<source>-<dest>/cctp` (mode-agnostic), preserving SDK contract stability. The mode-specific evaluation is collapsed: if either mode (Fast or Standard) of a direction violates an invariant on its 1-hour window, the direction is `BS2`.
3. Other CCTP V2 corridors (ARB / BASE / OP rollup, AVAX / SOL L1-to-L1) are upgraded to `BRIDGE_STATE_STRUCTURAL_v1` immediately, since the methodology applies universally to any CCTP V2 corridor without requiring a per-corridor corpus.
4. CCIP V1.5 / V1.6 lanes are upgraded to the analogous J1-J4 evaluation, lifting them out of the deferred state described in `methodology.md` §13.4 *CCIP deferred calibration*.

The migration is documented in a fresh entry of `calibration_log.md` chained against the lock signature of the present document.

## 8. What this protocol does not do

The protocol classifies the state of a bridge against its own contractual invariants on the most recent aggregation window. It does not, by itself:

- Predict future state from present state (that is the role of precursors, including `LATENCY_PRECURSOR_v1` under separate validation).
- Detect application-layer exploits of the bridge that respect the protocol invariants while draining contracts via flaws in adjacent components (Balancer rounding bug in `INCIDENTS_2025_RWA_SUBSTRATE.md` §B12 is an example: the bridge contract worked correctly while the application logic above it was being exploited).
- Capture settlement-asset risk (de-pegging of USDC, escalation events on USDe), which is downstream of the bridge contract.
- Capture substrate stress on the host chains (sequencer outage, finality lag), which is observed by the L1 / L2 regime signals (S/D codes), not by the bridge state.

These propositions are testable by distinct elements of the Invarians framework documented in `event-agent/SOURCED_NEEDS_BY_AUDIENCE.md` §1.4. They are not replacements for, and are not replaced by, the present protocol.

## 9. Pre-engagement and signing

The present document is locked, SHA-256 hashed, signed in three independent Ed25519 namespaces (`invarians_calibration_bridge_state_structural_v1_key{1,2,3}`), and OpenTimestamps-anchored on Bitcoin before the production migration described in §7 is applied to `bridge_thresholds` or to `attestation/index.ts`.

The signing acts and the Bitcoin block anchor are the authoritative cryptographic record that the four invariants of §3, the four invariants of §4, the four tolerances of each set, and the migration plan of §7 are fixed prior to deployment.

---

*Draft 1.0 — successor to methodology.md §13 (statistical P97-on-latency, retired for CCTP V2 and CCIP V1.5 / V1.6 active scope).*
*Lock condition: three Ed25519 signatures + OpenTimestamps Bitcoin stamp, before any production migration referencing `BRIDGE_STATE_STRUCTURAL_v1` is applied.*
