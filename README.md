---
title: "Invarians — Calibration Publications"
version: "0.1"
date: "2026-04-17"
audience: [ai-agents, developers, researchers]
---

# Invarians — Calibration Publications

> **AgentNorthStar.com** — Invarians public calibration registry
> These documents constitute the verifiable technical specification of the measurement system.

---

## Read in this order

### 1. Understand the method — `methodology.md`

Entry point for all readers. Covers:
- Core principle: structural regime vs instantaneous signal
- Signal architecture (τ structure, π demand)
- Complete OFFLINE/ONLINE pipeline (section 4.5)
- Per-chain parameters + calibration status
- M1 Metric Stability Score (section 10)
- L2 Rollups: why signals differ
- Complete metrics by layer (L1, L2 π/μ/σ, Bridge)

**Audience:** developers integrating the API, AI agents consuming attestations, researchers auditing the method.

### 2. Validation results — `backtest_ethereum.md`

BigQuery backtest 2020–2024 on 34,697 Ethereum windows.
- threshold_s2 and threshold_d2 sweeps
- Ground truth events: The Merge, Shanghai Upgrade, DeFi Summer, NFT Mania
- TPR=100% (4/4), FPR τ+π=1.23%
- Final validated ETH parameters (confidence: MEDIUM)

### 3. Incident log — `calibration_log.md`

Immutable history of all calibration decisions (EMA resets, bug fixes, methodological choices). Audit reference.

### 4. Protocol watch — `protocol_watch.md`

Impact of blockchain upgrades (EIP-4844, EIP-7702, EIP-7781, Shared Sequencers) on Invarians calibration. Updated with each significant protocol change.

---

## Index

| File | Status | Date | Description |
|---------|--------|------|-------------|
| `methodology.md` | 🟡 draft | 2026-04-17 | Complete method — pipeline, signals, calibration, M1 |
| `backtest_ethereum.md` | ✅ validated | 2026-03-16 | ETH backtest 2020–2024 — TPR=100%, FPR τ+π=1.23% (4/4 events) |
| `backtest_solana.md` | ✅ validated | 2026-03-16 | SOL τ backtest 2021–2024 — TPR=100%, FPR_τ=1.77% (4/4 outages) · π pending |
| `calibration_log.md` | 🟡 active | 2026-04-16 | Incident log + decisions — 16 entries |
| `protocol_watch.md` | 🟡 active | 2026-04-11 | EIP and upgrade tracking — 5 entries |
| `composite_signal_arbitrum_june2024.md` | ✅ validated | 2026-04-03 | ARB case study June 20, 2024 — L2:S1D2 + Bridge:BS2 invisible to fee monitors |
| `scripts/` | ✅ reproducible | 2026-03-16 | Python + SQL BigQuery scripts — ETH, POL, SOL + h5_composite_demo.py (independently reproducible) |
| `backtest_polygon.md` | ✅ validated | 2026-04-17 | POL backtest 2020–2024 — TPR=100% (4/4), FPR=11.75% (elevated, documented), M1 τ=10.66 / π=4.55 (formula v0.1) |
| `chain_profile_ethereum.md` | ⏳ pending | — | Complete ETH profile (pending formalized M1) |
| `chain_profile_solana.md` | ⏳ pending | — | SOL profile (pending π calibration July 2026) |
| `chain_profile_polygon.md` | ⏳ pending | — | POL profile (pending backtest execution) |

**Statuses:**
- ✅ validated — published, data validated by backtest
- 🟡 active/draft — in progress, partially published
- ⏳ pending — content available, publication pending

---

## What is NOT here

- Source code → GitHub [invarians-oracle]
- API documentation → docs.invarianslabs.com
- Real-time M1 values → AgentNorthStar.com

---

*Invarians measures which structural regime a blockchain is operating in.*
*These publications allow the method to be audited independently.*

*Created April 17, 2026*
