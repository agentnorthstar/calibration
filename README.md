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

### 5. Known limitations — `limitations_and_plans.md`

Public accountability document: every limitation we know about (statistical, methodological, security, coverage), with dated corrections and a public changelog. Read this before opening issues.

---

## Index

| File | Status | Date | Description |
|---------|--------|------|-------------|
| `methodology.md` | 🟡 draft | 2026-04-19 | Complete method — pipeline, signals, calibration, M1 (§10.5 bootstrap 95% CI + P99 variant) · §9.3b L2 forensic event detection protocol (batch_gap on `ans_l2_adapter_signals`, archive node replay Q3 2026) |
| `backtest_ethereum.md` | ✅ validated | 2026-04-19 | ETH backtest 2020–2024 — TPR=100% (4/4) IC95% [39.76% ; 100%], FPR=1.23% IC95% [1.11% ; 1.36%] · §6 Temporal CV: TPR_test=100% (2/2), FPR_test=0.65% with published D2 params · §9 α_fast sensitivity sweep (knee confirmed at α=2/11) |
| `backtest_solana.md` | ✅ validated | 2026-03-16 | SOL τ backtest 2021–2024 — TPR_τ=100% (4/4) IC95% [39.76% ; 100%], FPR_τ=1.77% IC95% [1.70% ; 1.84%] · π pending |
| `calibration_log.md` | 🟡 active | 2026-04-22 | Incident log + decisions — 27 entries (incl. #027 native bridge thresholds P97/30d, ARB=180s · BASE=60s · OP=396s) |
| `limitations_and_plans.md` | 🟡 living | 2026-04-19 | Known limitations + dated roadmap of corrections — public accountability |
| `protocol_watch.md` | 🟡 active | 2026-04-11 | EIP and upgrade tracking — 5 entries |
| `composite_signal_arbitrum_june2024.md` | ✅ validated | 2026-04-03 | ARB case study June 20, 2024 — L2:S1D2 + Bridge:BS2 invisible to fee monitors |
| `scripts/` | ✅ reproducible | 2026-04-19 | Python + SQL BigQuery scripts — ETH, POL, SOL + h5_composite_demo.py + ci_binomial.py (Clopper-Pearson IC95%) + cv_eth.py (temporal cross-validation) + roc_curves.py (ROC per chain, AUC, POL Φ=720) + POL Φ=720 pipeline (extract_pol_phi720.sql, backtest_pol_phi720.py, sweep_pol_d2_phi720.py, m1_pol_phi720.py) + sensitivity_alpha_eth.py (α_fast sweep ETH) + M1 bootstrap 95% CI & P99 variant in m1_{eth,pol,pol_phi720}.py. See `scripts/README.md` for full reproduction. |
| `backtest_polygon.md` | ✅ validated v2.0 | 2026-04-19 | POL backtest 2020–2024 **production-aligned Φ=720** — TPR=100% (4/4) IC95% [39.76% ; 100%], FPR=14.57% IC95% [14.30% ; 14.83%] (elevated, documented), M1 τ=12.60 / π=3.59 (formula v0.1), mean latency 3.95h. See `calibration_log.md #023` for v1→v2 decision. |
| `chain_profile_ethereum.md` | ⏳ pending | — | Complete ETH profile (pending formalized M1) |
| `chain_profile_solana.md` | ⏳ pending | — | SOL profile (pending π calibration July 2026) |
| `chain_profile_polygon.md` | ⏳ pending | — | POL profile (pending backtest execution) |

**Statuses:**
- ✅ validated — published, data validated by backtest
- 🟡 active/draft — in progress, partially published
- ⏳ pending — content available, publication pending

---

## What is NOT here

- Source code → attestation service repository
- API documentation → docs.invarianslabs.com
- Real-time M1 values → AgentNorthStar.com

---

*Invarians measures which structural regime a blockchain is operating in.*
*These publications allow the method to be audited independently.*

*Created April 17, 2026*
