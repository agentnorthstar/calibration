---
title: "Invarians, Calibration Publications"
version: "0.4"
date: "2026-05-12"
audience: [ai-agents, developers, researchers]
---

# Invarians, Calibration Publications

> **AgentNorthStar.com** is the Invarians public calibration registry.
> These documents constitute the verifiable technical specification of the measurement system.

---

## Read in this order

### 1. Understand the method, `methodology.md`

Entry point for all readers. Covers:
- Core principle: structural regime vs instantaneous signal
- Signal architecture (τ structure, π demand)
- Complete OFFLINE/ONLINE pipeline (section 4.5)
- Per-chain parameters and calibration status
- M1 Metric Stability Score (section 10)
- L2 Rollups: why signals differ
- Complete metrics by layer (L1, L2 π/μ/σ, Bridge)
- 12 signed regime codes per chain (S2±, D2±) since 2026-04-29

**Audience:** developers integrating the API, AI agents consuming attestations, researchers auditing the method.

### 2. Validation results, `backtest_ethereum.md`

BigQuery backtest 2020 to 2024 on 34,697 Ethereum windows.
- threshold_s2 and threshold_d2 sweeps
- Ground truth events: The Merge, Shanghai Upgrade, DeFi Summer, NFT Mania
- TPR=100% (4/4), FPR τ+π=1.23%
- Final validated ETH parameters (confidence: MEDIUM)

### 3. Incident log, `calibration_log.md`

Immutable history of all calibration decisions (EMA resets, bug fixes, methodological choices). Audit reference. 40 entries through 2026-05-12.

### 4. Protocol watch, `protocol_watch.md`

Impact of blockchain upgrades (EIP-4844, EIP-7702, EIP-7781, Shared Sequencers) on Invarians calibration. Updated with each significant protocol change.

### 5. Known limitations, `limitations_and_plans.md`

Public accountability document: every limitation that is known (statistical, methodological, security, coverage), with dated corrections and a public changelog. Read this before opening issues.

---

## API v2.0 (since 2026-04-30)

API v2.0 unifies three primitives in a single signed payload:

| Primitive | Purpose |
|---|---|
| **Attestation** | HMAC-SHA256 over the canonical payload, independently verifiable via `/attestation/v2/verify`. |
| **Regime** | 12 signed codes per chain (S1, S2+, S2-, D1, D2+, D2-, D2±) on L1 and L2, plus bridge state. Drift Signal applies to L1 and L2 substrate observables only. |
| **Drift Signal** | Per-metric `MetricBlock` (`ratio`, `ratio_long`, `shift`, `shift_delta`, `shift_magnitude_delta`) and per-axis composite drift. Substrate-physics concept: tracks 10 h / 30 d EMA deviation on L1 and L2 entries. Bridges, as operational pipelines rather than substrates, expose their fitness-for-action via current metrics + crypto pointer, without a drift block. |

Live chains (12 signed codes calibrated):
- L1: Ethereum, Polygon
- L2: Arbitrum, Base, Optimism (since 2026-05-01)

Pending (legacy 4-state until further calibration):
- L1: Solana, Avalanche (calibration scheduled July 2026)

**Per-message capture across CCTP and CCIP.** Both variable-latency bridge families now expose `capability_level: per_message_attested`. CCTP (since 2026-05-11): the collector captures the Circle ECDSA secp256k1 signature for each attested message, retrievable via `GET /attestation/v2/cctp/attestation/{message_hash}` and independently verifiable against Circle's published attester public key. CCIP (since 2026-05-12): the collector matches each `CCIPSendRequested` event on the source OnRamp against the corresponding `ExecutionStateChanged` event on the destination OffRamp via the bytes32 `messageId`, retrievable via `GET /attestation/v2/ccip/message/{message_id}`. CCIP `crypto.anchor` is `null` today; capture of CCIP `CommitReport` DON multi-sig and per-message Merkle inclusion proofs is the next step. See `calibration_log.md` Entries #039 (CCTP) and #040 (CCIP), and `limitations_and_plans.md §2.4`.

Surveillance topology:
- L1 substrates with structural and demand axes
- L2 rollups (Ethereum-anchored) with rhythm, continuity, sequencer_publish_latency, plus 5-observable demand axis
- CCIP routes (Chainlink), bidirectional, L1 to L1 and L1 to L2, capability level `per_message_attested` with source-to-execute matched by bytes32 `messageId` (`crypto.anchor` remains `null` until DON multi-sig `CommitReport` capture)
- CCTP routes (Circle), bidirectional, L1 to L1 and L1 to L2 — capability level `per_message_attested` with Circle ECDSA signature captured per message

---

## Index

| File | Status | Date | Description |
|---------|--------|------|-------------|
| `methodology.md` | 🟡 active | 2026-04-29 | Complete method, pipeline, signals, calibration, M1 (§10.5 bootstrap 95% CI plus P99 variant), §9.3b L2 archive-replay event detection protocol (batch_gap on `ans_l2_adapter_signals`, archive node replay Q3 2026). |
| `backtest_ethereum.md` | ✅ validated | 2026-04-19 | ETH backtest 2020 to 2024, TPR=100% (4/4) IC95% [39.76% ; 100%], FPR=1.23% IC95% [1.11% ; 1.36%], §6 Temporal CV: TPR_test=100% (2/2), FPR_test=0.65% with published D2 params, §9 α_fast sensitivity sweep (knee confirmed at α=2/11). |
| `backtest_solana.md` | ✅ validated | 2026-03-16 | SOL τ backtest 2021 to 2024, TPR_τ=100% (4/4) IC95% [39.76% ; 100%], FPR_τ=1.77% IC95% [1.70% ; 1.84%], π pending. |
| `calibration_log.md` | 🟡 active | 2026-05-12 | Incident log and decisions, 40 entries through entry #040 (CCIP per-message capture via messageId matching, source-to-execute end-to-end latency derived from per-message data). |
| `limitations_and_plans.md` | 🟡 living | 2026-05-12 | Known limitations and dated roadmap of corrections. Public accountability. Per-message capture live on both CCTP (2026-05-11) and CCIP (2026-05-12). |
| `protocol_watch.md` | 🟡 active | 2026-05-02 | EIP and upgrade tracking, 6 entries (latest: API v2.0 deployment). |
| `composite_signal_arbitrum_june2024.md` | ✅ validated | 2026-04-03 | ARB case study June 20, 2024, L2:S1D2 plus Bridge:BS2 invisible to fee monitors. |
| `backtest_polygon.md` | ✅ validated v2.0 | 2026-04-19 | POL backtest 2020 to 2024, production-aligned Φ=720, TPR=100% (4/4) IC95% [39.76% ; 100%], FPR=14.57% IC95% [14.30% ; 14.83%] (elevated, documented), M1 τ=12.60 / π=3.59 (formula v0.1), mean latency 3.95h. See `calibration_log.md` entry #023 for v1 to v2 decision. |
| `SHIFT_PREDICTIVE_VALIDATION.md` | 🟡 in progress | 2026-05-02 | Drift Signal validation against indexed event cases, post-launch follow-up to API v2.0. |
| `scripts/` | ✅ reproducible | 2026-04-19 | Python and SQL BigQuery scripts, ETH, POL, SOL, plus h5_composite_demo.py, ci_binomial.py (Clopper-Pearson IC95%), cv_eth.py (temporal cross-validation), roc_curves.py (ROC per chain, AUC, POL Φ=720), POL Φ=720 pipeline (extract_pol_phi720.sql, backtest_pol_phi720.py, sweep_pol_d2_phi720.py, m1_pol_phi720.py), sensitivity_alpha_eth.py (α_fast sweep ETH), M1 bootstrap 95% CI and P99 variant in m1_{eth,pol,pol_phi720}.py. See `scripts/README.md` for full reproduction. |
| `chain_profile_ethereum.md` | ⏳ pending | — | Complete ETH profile (pending formalized M1). |
| `chain_profile_solana.md` | ⏳ pending | — | SOL profile (pending π calibration July 2026). |
| `chain_profile_polygon.md` | ⏳ pending | — | POL profile (pending backtest execution). |

**Statuses:**
- ✅ validated: published, data validated by backtest
- 🟡 active/draft: in progress, partially published
- 📐 spec: API specification document
- ⏳ pending: content available, publication pending

---

## Honest gaps

The following limitations are publicly acknowledged and documented in `limitations_and_plans.md`:

1. P(tx revert | regime), no conditional failure rate published.
2. Regime criticality per action type, matrix action × regime not yet mapped publicly.
3. Drift across months, rolling 30d absorbs it operationally; cross-month empirical drift not yet published.
4. Nominal-only is a heuristic, not a rule.
5. Native canonical bridges (L2 to L1) explicitly removed from the active calibration scope on 2026-05-04 (Entry #038). Variable-latency bridges (CCTP, CCIP) are the active scope because they are the surface on which Invarians provides a measurable value lever for autonomous agents.
6. CCIP cryptographic anchor remains `null` today. CCIP `capability_level` is `per_message_attested` since 2026-05-12 (send-to-execute matched by `messageId`), but the DON threshold-signed `CommitReport` (CCIP's native crypto anchor, structurally different from CCTP's single-attester ECDSA) is the next capture step. Resolution target: late May / early June 2026.

---

## What is NOT here

- Source code: attestation service repository.
- API v2.0 reference and worked examples: `invarians.com/developers` (panel schema, MetricBlock fields, signed regime codes, signature verification flow).
- Live M1 values: AgentNorthStar.com.

---

*Invarians measures which structural regime a blockchain is operating in.*
*These publications allow the method to be audited independently.*

*Created 2026-04-17. Last revision 2026-05-12.*
