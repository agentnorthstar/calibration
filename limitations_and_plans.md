---
title: "Invarians — Known Limitations and Planned Corrections"
version: "0.1"
date: "2026-04-19"
status: "living document"
audience: [auditors, researchers, integrators]
---

# Invarians — Known Limitations and Planned Corrections

> This document exists so an auditor does not have to guess what we know is imperfect.
> What is listed here is already acknowledged internally — publishing it closes the gap.

---

## 1. Why this document exists

An external technical review on 2026-04-19 correctly identified weaknesses in what was publicly documented. Several of those weaknesses are already addressed in internal plans or deployed workarounds, but had not yet been written down publicly. This document is the fix for that publication gap.

It is a **living document**: revised whenever a new limitation is identified, a planned correction ships, or an external reviewer flags something worth acknowledging.

**Three maturity states are distinguished throughout:**

| State | Meaning |
|---|---|
| **Shipped** | Deployed and operational today (e.g. multi-RPC collector, 2-of-2 Arbitrum rule, REST API, MCP/A2A discovery schemas at `agentic.invarians.com`, CRE reference implementation at `invarians.com/cre.html`). §4 lists what is shipped but not yet documented in the methodology proper. |
| **In development** | Design complete, code written or prototyped, rollout pending (e.g. `InvariansAnchor` contract for May 2026, MCP `/mcp` endpoint activation, Calibration Agent). §3 dates these. |
| **Pending** | Requires data that does not yet exist or a design decision still open (e.g. Solana π calibration awaiting sensor data mid-June 2026; additional τ ground-truth events for ETH cross-validation of `threshold_s2`). §3 and §2 mark these. |

An auditor should read "planned" in this document as "in development" unless the item is explicitly marked pending on external data.

---

## 1.1 Scope of this document — and what sits upstream / downstream

This repository documents the **calibration** of the two primitives Invarians exposes through the public API:

- **#01 On-Chain Execution Context** — the certified regime of L1, L2 and bridge at query time (HMAC-signed, timestamped, independently verifiable).
- **#02 Pattern Reference** — the historical record of those regimes across the matrix (S1D1 / S1D2 / S2D1 / S2D2) × L1 × L2 × Bridge (BS1 / BS2).

What we publish here — thresholds, EMA windows, Φ, TPR / FPR, confidence intervals, calibration log, cross-validation — governs the quality of those two primitives.

**Downstream of this calibration: Invarians Labs.** Labs (`labs.invarians.com`, `labs/` folders) operates on top of the regime labels produced by calibrated primitives. Labs is where the hypothesis *"Blockchains deform under sustained agentic pressure"* is tested empirically — by accumulating regime baselines across L1 × L2 × Bridge since 2026-03-30 and watching for systematic drift in regime distributions over time. The rheology framing (material science applied to infrastructure) is Labs' own framing; the calibration repo remains neutral on causal claims.

**ε(t) — the deformation metric.** ε(t) is Labs' composite deformation signal. It is built from regime trajectories — i.e. from the outputs of the primitives calibrated here. The *formula* of ε(t) is not published (see §5). Its *inputs* are fully public: anyone can reproduce the L1/L2/bridge regime series from the API + the published thresholds and recompute regime-distribution statistics identical to Labs' visible aggregations. Only the final weighting that collapses trajectories into a single ε(t) scalar is private.

**Consequence — calibration is upstream of Labs.** Any change to a threshold, EMA, Φ, or D2 logic in this repo propagates to Labs' regime counts. This is not a defect; it is the expected dependency order. It does impose a constraint: calibration stability during Labs' baseline-building phase (started 2026-03-30) is treated as an operating priority. Any recalibration ships with dated annotations in `calibration_log.md` so that Labs can distinguish **regime shift (real)** from **label shift (recalibration-induced)** when analyzing its time series. See §2.6.

---

## 2. Known limitations (today)

### 2.1 Statistical

**Small number of ground truth events per chain.**
ETH, POL, SOL τ are each validated on **n = 4 events**. The exact Clopper-Pearson IC95% for TPR = 4/4 is **[39.76% ; 100.00%]**. The "100%" point estimate alone is not a predictive guarantee — a TPR as low as ~40% is statistically compatible with what we have observed. Enlarging n is the only way to tighten the interval, and n only grows when real blockchain events happen. The FPR intervals, by contrast, are narrow (n_normal > 10,000 per chain) and are statistically robust. See `methodology.md` §4.4.1.

**In-sample threshold optimization.**
Thresholds (`threshold_s2 = 1.12` for ETH, etc.) were swept across candidate values and selected on the same time period that contains the ground truth events. This is in-sample optimization — the reported TPR is partly an artifact of fitting the threshold to the events we knew about.

**Status 2026-04-19 — partially closed for ETH D2.** A temporal cross-validation was published (see `backtest_ethereum.md §6`, `calibration_log.md` Entry #021): D2 thresholds (σ, size, tx) refit on train 2020–2022 (DeFi Summer, NFT Mania) generalize out-of-sample to test 2022-09 → 2023-12 (The Merge, Shanghai Upgrade) at TPR_test = 100% (2/2), FPR_test = 0.65% with the published triplet — **lower** than the full-period FPR, arguing against over-fitting. **Remaining gap:** `threshold_s2` (τ) itself is still not temporally validated because no τ-type event exists before The Merge. Reopens if/when a second τ-dominant event occurs on ETH. Same CV protocol planned for POL and SOL (Q3 2026) once script is generalized.

**FPR is an upper bound on true noise.**
FPR is computed as "alarms outside labeled events / normal windows". But "normal" means "not in our ground truth list" — and our ground truth is not exhaustive. Some false alarms are probably undocumented incidents. The published FPR is therefore an **upper bound** on real noise, not a lower bound. See §3, Q3 2026 (near-miss protocol).

### 2.2 Methodological

**EMA window α not empirically studied.**
`α_fast = 2/11 (~10h)` and `α_slow = 2/721 (~30d)` were chosen by convention. A sensitivity analysis across `α ∈ {2/7, 2/11, 2/15, 2/21}` has not been published. See `methodology.md §4.5` (acknowledged) and §3 below (Q3 2026).

**Φ window size not yet sensitivity-studied.**
Production values: `Φ = 280` blocks for ETH, `Φ = 720` for POL, `Φ = 800` slots for SOL, `Φ = 720` for AVAX, `Φ = 1800` for L2 rollups. All production values produce a ~1h sampling cadence across chains. No published Φ sensitivity sweep yet — same status as α.

> **POL backtest/production alignment — resolved 2026-04-19.** The v1.0 POL backtest used Φ=1800 while production runs with Φ=720. This gap was closed by re-extracting at Φ=720 and republishing `backtest_polygon.md` v2.0. See `calibration_log.md #023`. TPR preserved at 100% (4/4), FPR shifts from 11.75% → 14.57%, mean detection latency drops from 16.8h → 3.95h. ETH, SOL, and L2 backtests were already production-aligned.

**M1 formula v0.1 is provisional.**
The Metric Stability Score formula (§10 of `methodology.md`) is version 0.1, documented as provisional in `calibration_log.md` Entry #018. Known theoretical weaknesses: `max_event` is an extreme order statistic, not robust to outliers; no bootstrap CI on M1 itself; cross-chain comparisons are not z-score normalized. A v0.2 with quantile-based numerator and bootstrap CI is planned.

### 2.3 Security & trust

**Single-node attestation signer.**
Today, one node computes invariants and signs attestations with Ed25519. The chain of custody (SHA-256 → Ed25519 → HMAC-SHA256) is cryptographically sound but **centralized on trust**. A malicious or compromised node could sign false attestations. There is no multi-witness signature yet.

**In active development, not a future abstraction:** the Chainlink CRE integration that moves attestation consensus to a Decentralized Oracle Network is already scaffolded at [invarians.com/cre.html](https://invarians.com/cre.html) — the documented TypeScript workflow uses `runInNodeMode` with mode aggregation so that all DON nodes reach BFT consensus on the regime value before downstream code acts. The remaining work is production deployment, not design. See §3 (Q3–Q4 2026).

**No on-chain tamper-evidence yet.**
Historical attestations live in Supabase. They are auditable but not anchored on-chain. A future rewrite of historical records by the operator is, cryptographically, currently indistinguishable from the original signing. `InvariansAnchor` (Arbitrum contract, May 2026) fixes this by periodically anchoring batched attestation hashes on-chain. In parallel, every attestation consumed through a CRE workflow is already bound to the DON's BFT round, which provides independent tamper-evidence at consumption time.

**No published threat model section.**
`methodology.md` §5 covers the cryptographic primitives but does not enumerate attack vectors: mempool flooding to force S2D2 on ETH, timestamp post-dating, key compromise, eclipse attacks on the observing node. A formal threat model section is planned for Q2 2026.

### 2.4 Coverage

**Arbitrum τ signal uses a non-standard rule.**
Arbitrum Nitro has `rho_s ≈ 0` structurally (gasLimit ≈ ∞ → near-zero variance in block size in nominal regime). The standard τ classifier does not work. A **2-of-2 rule on `size_ratio` and `tx_ratio`** is deployed in production and operates correctly (AGENT internal Rule 10), but this workaround is not yet documented publicly. Documentation will be added to `composite_signal_arbitrum_june2024.md` or a dedicated `chain_profile_arbitrum.md` (Q2 2026).

**Bridge signal in observation phase.**
BS1 / BS2 are described in `methodology.md §9.5` but are in **Phase 2B observation mode** (hard-coded BS1 until switchover date 2026-04-22). They are not yet part of the classified production signal. Sections describing Bridge and ω behaviors should be read as specifications, not validated measurements.

**Solana π not yet calibrated.**
BigQuery Solana Blocks does not contain `transaction_count`. π calibration is pending until mid-June 2026 when the sensor data becomes usable. Current production π on SOL is `confidence: LOW` (P90 proxy).

**L2 signals differ from L1 by design.**
Rollups with centralized sequencers (Arbitrum, Base, Optimism) cannot reproduce the τ signal that works on L1s with decentralized consensus. This is correct and documented in `methodology.md §7.4`. The L2 framework (π, μ, σ) is separate from the L1 framework (S/D).

### 2.5 Ground truth quality

**Ground truth is manually curated.**
The lists of events (Merge, Shanghai, Solana outages, Polygon Reorg Storm, etc.) come from public blockchain incident reports. There is no automated ingestion from status pages or agent feedback. Some real incidents are likely missing from the list; they register as "false alarms" and inflate the measured FPR. See §3 (agent feedback protocol).

### 2.6 Downstream dependency — Labs baseline integrity

Invarians Labs began accumulating regime-distribution baselines across L1 × L2 × Bridge pairs on **2026-03-30**. This baseline is the instrument Labs uses to test its central hypothesis (agentic load → structural deformation). The baseline has three properties that interact with calibration:

1. **It cannot be reconstructed retroactively.** Regime labels assigned in real time by the current threshold set are the object of study. Recomputing them later with a different threshold set creates a different baseline, not a corrected one.
2. **It is sensitive to calibration changes.** A revised `threshold_s2` or a D2 logic update shifts the fraction of windows labeled S2 / D2, independently of any underlying structural change on the chain. To Labs this shows up as a level shift in the aggregated series.
3. **It must distinguish two causes of regime-frequency movement.** Labs' measurement of interest is *"regime distribution changed because agentic load deformed the chain"*. The measurement error to avoid is *"regime distribution changed because we moved the threshold"*. The two are cryptographically indistinguishable in the attestation record alone.

**Operating rule.** Every calibration change shipped during Labs' baseline phase is logged in `calibration_log.md` with (a) UTC timestamp of the cut-over, (b) per-chain parameter diff, (c) an explicit flag `baseline_impact: yes|no`. Labs' analyses segment their time series on these cut-over dates rather than treating the baseline as homogeneous. Entries #019 and #021 in the log are the current reference format.

**Stability commitment.** During the stated Labs baseline phase (started 2026-03-30, planned window through at least Q3 2026), published thresholds will be changed only when a genuine calibration problem is detected — not for incremental improvement. Improvements that do not fix a demonstrated defect are deferred to a batched revision at the end of the phase.

---

## 3. Planned corrections — timeline

Dates are targets. Slippage is disclosed in `calibration_log.md`.

### Q2 2026 (April–June)

- **✅ Done 2026-04-19** — Exact Clopper-Pearson IC95% added to all published TPR / FPR (Entry #019, `scripts/ci_binomial.py`).
- **✅ Done 2026-04-19** — Temporal cross-validation ETH D2 (Entry #021, `scripts/cv_eth.py`, `backtest_ethereum.md §6`). Train 2020–2022 / test 2022-09 → 2023-12. TPR_test = 2/2 with IC95% [15.81% ; 100%]; FPR_test = 0.65% with published triplet, IC95% [0.51% ; 0.81%]. Caveat: `threshold_s2` not CV'd (no τ-event pre-Merge).
- **In progress** — Threat model section in `methodology.md` (mempool flooding, post-dating, key compromise, eclipse, vectors against the single-node signer).
- **May 2026** — `InvariansAnchor` contract deployed on Arbitrum. Periodically anchors batched attestation hashes on-chain for public tamper-evidence. Historical Supabase records become cryptographically comparable to their on-chain commitment.
- **Q2 2026** — MCP server activation at `agentic.invarians.com/mcp`. Schema stable and published at [`agentic.invarians.com/.well-known/mcp.json`](https://agentic.invarians.com/.well-known/mcp.json); A2A discovery at `.well-known/agent.json`. Tools `invarians_get_scope()` and `invarians_get_execution_context(from, to)` documented in [`agentic.invarians.com/llms.txt`](https://agentic.invarians.com/llms.txt). Multi-RPC collector architecture is already operational in production behind the REST API — the MCP layer exposes the same multi-source context to agents.
- **May 2026** — AgentNorthStar Calibration Agent exposed via MCP. Autonomously monitors drift (FPR out of bounds, missed TPR, M1 instability) and proposes recalibration candidates per chain.

### Q3 2026 (July–September)

- **July 2026** — Solana π calibration with full backtest (sensor data ready mid-June). SOL π moves from `LOW` to `MEDIUM event-based`.
- **July 2026** — Avalanche event-based calibration begins.
- **Q3 2026** — Agent feedback protocol: integrating agents can report incidents they lived through, enriching ground truth retroactively. Reduces near-miss bias in FPR.
- **Q3 2026** — Arbitrum 2-of-2 workaround documented publicly.
- **Q3 2026** — α and Φ sensitivity analyses published (FPR × α × Φ matrix per chain).
- **Q3 2026** — Generalize `cv_eth.py` to POL and SOL once events allow (SOL has 4 outages concentrated 2021-09 → 2022-10, POL events span 2020 → 2024).

### Q4 2026 (October–December)

- **✅ Done 2026-04-19** — ROC curves per chain published (Entry #022, `scripts/roc_curves.py`). AUC: ETH τ = 0.978 (n=2 events), SOL τ = 0.994 (n=4), POL D2 = 0.930 (n=4, Pareto of 3D sweep, Φ=720 production-aligned — see Entry #023). Item moved forward from Q4 2026 to Q2 2026 because all sweep CSVs were already produced and derivation was mechanical.
- **✅ Done 2026-04-19** — POL backtest production-alignment. v1.0 used Φ=1800; v2.0 at Φ=720 matches the deployed collector configuration. `backtest_polygon.md` rewritten, 71,860 invariants re-extracted from BigQuery, full sweep + M1 + ROC re-run. FPR 11.75% → 14.57%, mean detection latency 16.8h → 3.95h (−76%), TPR 100% preserved. See `calibration_log.md #023`.
- **Q3–Q4 2026** — Chainlink CRE integration in production. The attestation flow becomes decentralized via a Chainlink Decentralized Oracle Network: `runInNodeMode` aggregation reaches BFT consensus on the regime value across DON nodes, so no single operator can forge attestations alone. Full integration guide already published at [invarians.com/cre.html](https://invarians.com/cre.html). Target surface: CCIP EVM lanes (ETH → ARB / BASE / OP / POL / AVAX) with Invarians pre-flight sensing.
- **Q4 2026** — M1 formula v0.2: quantile-based numerator (P99 instead of max), bootstrap CI, cross-chain z-score normalization.

### 2027

- **2027** — Native Invarians network: attestation signing becomes a permissionless layer, no longer dependent on Chainlink. Target architecture announced separately.

---

## 4. Corrections already deployed but not yet publicly documented

These are implemented and operational, but the public methodology does not (yet) describe them. Listed here so auditors know they exist.

**Arbitrum 2-of-2 rule on size and tx ratios.**
Production code on Arbitrum substitutes the standard τ classifier with a 2-of-2 rule on `size_ratio` and `tx_ratio` (both must exceed their respective thresholds to trigger S2). Reason: `rho_s ≈ 0` makes the classic sigma-based rule degenerate. Documentation scheduled for Q3 2026.

**Calibration Drift Protocol (5 steps).**
Internal operating procedure when a per-chain signal drifts out of calibration:

1. Detect drift (FPR / TPR / M1 outside published bounds)
2. Analyze cause (protocol upgrade, regime change, sensor bug)
3. Propose new parameters via sweep scripts
4. Validate on backtest + ground truth
5. Publish in `calibration_log.md` with version bump

This protocol is currently exercised manually by operators. It will be automated by the AgentNorthStar Calibration Agent (MCP, May 2026).

**Multi-RPC collector architecture.**
The collector that feeds the invariant computation does not rely on a single RPC per chain. Per-chain diversity is operational today: multiple RPC endpoints per network with failover, source-level agreement checks on block height, and rejection of inconsistent responses. This is what the REST API at `sdpilypwumxsyyipceew.supabase.co/functions/v1/attestation/` has been serving since before this document was published. Public architectural documentation scheduled Q3 2026 alongside the MCP server release notes.

**MCP server and A2A discovery — schema published.**
The MCP server at [`agentic.invarians.com`](https://agentic.invarians.com) is deployed with stable discovery endpoints:
- [`/.well-known/mcp.json`](https://agentic.invarians.com/.well-known/mcp.json) — MCP tool discovery
- `/.well-known/agent.json` — A2A agent discovery
- [`/llms.txt`](https://agentic.invarians.com/llms.txt) — agent-readable integration guide

Tools (`invarians_get_scope`, `invarians_get_execution_context`) are documented, signatures stable. Activation of the `/mcp` endpoint is the Q2 2026 target. The design — including the `actionable` / `calibrated` field semantics agents rely on — is shipped.

**Chainlink CRE integration — reference implementation published.**
A complete TypeScript integration pattern showing Invarians sensing inside a CRE workflow is public at [invarians.com/cre.html](https://invarians.com/cre.html). This is not a design sketch: the code uses `@chainlink/cre-sdk` with `runInNodeMode`, demonstrates BFT consensus on the regime string across DON nodes, and is the template targeted at CCIP EVM lanes (ETH → ARB / BASE / OP / POL / AVAX). What is "planned" is production rollout and customer workflows; the integration architecture itself is documented.

---

## 5. What will not be published

We are transparent about what we keep private.

**The ε(t) / deformation_score formula (Invarians Labs).**
ε(t) is the deformation metric operated by Invarians Labs (`labs.invarians.com`). It is built from regime trajectories produced by the calibrated primitives #01 and #02 documented in this repository — that is, from publicly reproducible inputs. Specifically:

- **Inputs of ε(t) are public.** The regime labels (S1D1 / S1D2 / S2D1 / S2D2 × L1 × L2 × BS1 / BS2) that feed ε(t) are served by the API, and their calibration is audited here. An auditor can reproduce the regime-distribution aggregations that Labs displays (rolling 30-day frequencies per L1 × L2 pair) from the attestation feed + the thresholds published in this repo.
- **The formula that collapses those trajectories into a single ε(t) scalar is not published.** Weight coefficients, bandwidth choices, and the composition of the deformation kernel remain private. Two reasons: (1) ε(t) is still in active empirical validation against the Labs baseline (started 2026-03-30) — publishing a provisional formula as if finalized would be premature; (2) the weighting is the point at which Labs' hypothesis (agentic pressure produces a characteristic deformation signature) is tested, and keeping the test instrument insulated from the population under observation is methodological hygiene.

In short: what is private is the *scoring*, not the *inputs*. The inputs remain subject to the calibration standards in this document; the scoring is Labs' research artifact, published on its own schedule at `labs.invarians.com`.

**Production operational details.**
VPS configuration, systemd service topology, key management specifics, internal service URLs. These are standard operational security and do not affect auditability of the published method.

**Session keys and HMAC secrets.**
Obvious.

---

## 6. How to report a problem or contribute

- **Found a bug in a script**: open an issue on [`agentnorthstar/calibration`](https://github.com/agentnorthstar/calibration/issues) with `bug/` prefix.
- **Disagree with a published number**: open an issue with `statistical-review/` prefix — include the metric, chain, and your own IC / recomputation.
- **Think we missed a ground truth event**: issue with `ground-truth/` prefix — include event name, approximate onset, sources, and the chain.
- **Spot a limitation not listed here**: issue with `limitation/` prefix. We prefer discovering these before our users do.

---

## 7. What is NOT a limitation (to avoid a class of confusion)

Certain properties of the Invarians signal have been framed as defects in prior reviews but are **by design**:

- **~18h detection latency on The Merge**: Invarians is a slow structural regime indicator (EMA `α_fast = 2/11` → ~10h integrated window), not a real-time alarm. For minute-level signals, a different product is required.
- **DeFi Summer not detected on ETH**: infrastructure handled the load; this is correct non-detection (healthy infrastructure, elevated demand). See `backtest_ethereum.md` §4.
- **L1/L2 asymmetry**: rollup sequencers are deterministic, so τ is structurally flat on L2s. Applying L1 models to L2s would be wrong; we use a distinct L2 framework (π, μ, σ).
- **Dormant Arbitrum τ**: see §2.4 for the 2-of-2 workaround that replaces it.

---

*Maintained 2026-04-19. This document is versioned.*
*Next review planned: end of Q2 2026.*
