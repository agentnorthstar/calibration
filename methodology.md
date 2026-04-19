---
title: "Invarians — Methodology"
version: "0.4"
status: draft
date: "2026-04-17"
audience: [ai-agents, developers, researchers]
---

# Invarians — Structural measurement method for blockchains

> **Status:** v0.4 — ETH/SOL/POL event-based calibrations validated. M1 scripts available (`m1_eth.py` ✅, `m1_pol_phi720.py` ✅ production-aligned — see note §10.3). Complete M1 script implementation planned for v0.5.

---

## 1. Core principle

Invarians does not measure *what is happening right now* on a blockchain.
It measures *which structural regime the chain is operating in*.

```
INSTANT SIGNAL     →  MEV noise, arb, liquidations, mempool games
STRUCTURAL REGIME  →  state of the underlying infrastructure
```

The distinction is critical for AI agents: an instant signal can be
manipulated or noisy. A structural regime is computed on finalized data,
aggregated over ~1 hour, and independent of short-term market games.

---

## 2. Signal architecture

### 2.1 The two measured dimensions

**τ — Structure (Block/Slot layer)** *(valid on L1 only — structurally non-discriminating on L2, see section 7.1)*
Measures the physical behavior of the consensus protocol: cadence, temporal inertia,
production continuity, slot saturation.

**π — Pressure + Composition (Chain layer)**
Measures the economic pressure on the chain: block saturation by transactions,
evolution of average block size, transaction volume.
On L2, π extends to transaction **composition** (Phase A/B) — bytes/tx and gas/tx —
which form a μ sub-layer (see section 7.4). Pure π = volumetric pressure; μ = compositional pressure.

### 2.2 The two EMA speeds

Each signal is expressed as a current/baseline ratio:
```
ratio = signal_current / EMA_baseline
```

Two EMA baselines are maintained in parallel:
- **Fast EMA**: captures recent deviations (~10h by default, per-chain)
- **Slow EMA**: long-term structural baseline (~30 days by default, per-chain)

The fast ratio detects stress episodes. The slow ratio measures structural drift.

### 2.3 State classification

```
τ (structure):
  S1 : rhythm_ratio < threshold_s2     → nominal structure
  S2 : rhythm_ratio ≥ threshold_s2     → structural drift

π (demand):
  D1 : sigma_ratio < threshold_d2      → nominal demand
  D2 : sigma_ratio ≥ threshold_d2      → demand overload

Composite states:
  S1D1 → healthy infrastructure, nominal load
  S1D2 → healthy infrastructure, high demand (expensive gas)
  S2D1 → structural drift WITHOUT visible economic signature ← critical case
  S2D2 → structural drift + simultaneous overload
```

**S2D1 is the most important state.** It represents structural stress without a visible
economic signature. No fee monitor, no gas tracker detects it. This is Invarians'
fundamental competitive differentiator.

> ⚠️ This classification (SxDx) applies to **L1 only**. On L2, τ is dead by design
> (section 7.1) — the S2Dx classification does not exist. L2 uses a distinct framework (π, μ, σ),
> see section 7.4.

---

## 3. Computation pipeline

```
BLOCKCHAIN
  → L0Signal(block_index, timestamp, load, capacity, size, tx_count)
  → SHA256(chain:index:timestamp:load:capacity:size:tx_count) = l0_hash

L1INVARIANT (Φ aggregated blocks)
  → rho_st  : average cadence (blocks/s)
  → rho_ts  : temporal inertia (s/block = duration/count)
  → c_s     : continuity (valid blocks / total slot range × 100)
  → rho_s   : saturation (load/capacity × 100)
  → size_avg, tx_count_avg
  → l0_batch_hash = SHA256(l0_hash_1 || l0_hash_2 || ... || l0_hash_Φ)
  → l1_hash = SHA256(all L1 fields)

CLASSIFIER
  → EMA_fast(rho_ts) = baseline_fast
  → EMA_slow(rho_ts) = baseline_slow
  → rhythm_ratio = rho_ts / baseline_fast
  → continuity_ratio = c_s / baseline_continuity
  → EMA_fast(sigma%) = baseline_sigma
  → sigma_ratio = sigma% / baseline_sigma
  → Classification: S1D1 | S1D2 | S2D1 | S2D2

ATTESTATION
  → Ed25519 signature(classified state + baselines + hashes)  ← asymmetric integrity, verifiable without a shared key
  → HMAC-SHA256(payload, service_key) + TTL 1h                ← transport authenticity between node and consumer
  → Independently verifiable attestation
```

---

## 4. Per-chain parameters

> ⚠️ The parameters below are **theoretical estimates**.
> They will be progressively replaced by backtest-validated values.
> See `backtest_{chain}.md` for definitive values.

### 4.1 Integration windows Φ

Across all supported chains, Φ is chosen so that the collector produces approximately one invariant per hour. This uniform ~1h sampling cadence is a design invariance of the system: API consumers see the same temporal resolution (~24 invariants/day/chain) regardless of the chain's native block speed.

| Chain | Block time | Φ | β | ~1h sampling cadence |
|--------|-----------|---|---|---|
| Solana | ~0.4s | 800 | 10 | ✅ |
| Ethereum | 12s | 280 | 1 | ✅ |
| Polygon | 2s | 720 | 5 | ✅ |
| Avalanche | 2s | 720 | 5 | ✅ |
| Arbitrum | ~0.25s | 1800 | 50 | ✅ |
| Base | 2s | 1800 | 50 | ✅ |
| Optimism | 2s | 1800 | 50 | ✅ |

### 4.2 Valid signals per chain

> **Update 16 March 2026 — empirically validated on Supabase data.**
> L1 (Solana, Ethereum, Polygon, Avalanche): 90d of data, n≥338 invariants per chain.
> L2 (Arbitrum, Base, Optimism): insufficient data (n=14–19) — production start 14 March 2026.

| Chain | Valid τ signals | Valid π signals | Excluded signals | Empirical justification |
|--------|------------------|------------------|----------------|------------------------|
| Solana | rho_ts | sigma_ratio, tx_ratio | c_s (99.85%±0.33%), size_ratio (historical size_avg=0) | c_s quasi-constant — extreme detector only |
| Ethereum | rho_ts (low var.) | sigma_ratio, size_ratio, tx_ratio | c_s (100.00%±0.00%), rho_s (50.76%±0.81%) | rho_s ultra-stable EIP-1559 — sigma_ratio weakly discriminating |
| Polygon | rho_s (dual τ+π) | sigma_ratio, size_ratio, tx_ratio | rho_ts (2.000s±0.005s), c_s (99.99%±0.06%) | rho_ts: 0.011s of amplitude over 90d → unusable |
| Avalanche | rho_ts (~1s, variable) | sigma_ratio, size_ratio, tx_ratio | c_s (99.99%±0.06%) | Actual block time ~1-1.3s (not 2s). c_s quasi-constant. |
| Arbitrum | rho_ts | ❌ sigma_ratio BROKEN | c_s (insufficient data), rho_s (0.00% — measurement error) | rho_s = 0: capacity = protocol_gas_limit (1.125e15) instead of effective (~32M) |
| Base | rho_ts (post-reset) | sigma_ratio, size_ratio, tx_ratio | c_s (contaminated + mirror of rho_ts) | Awaiting EMA reset. Current data contaminated (c_s min=14.17%) |
| Optimism | rho_ts (post-reset) | sigma_ratio, size_ratio, tx_ratio | c_s (contaminated + mirror of rho_ts) | Awaiting EMA reset. Current data contaminated (c_s min=13.97%) |

> "Excluded" signals = not used for classification, still computed and stored.
> c_s remains computed: useful for detecting extreme outages (drop > 10%), not for early drift.

#### Empirical rho_s data (90d)

| Chain | n | avg_rho_s | std_rho_s | p50 | p85 | p95 | CV | Verdict |
|--------|---|-----------|-----------|-----|-----|-----|----|---------|
| Solana | 338 | 72.93% | 11.49% | 71.16% | 86.87% | 93.94% | 15.8% | ✅ Strong |
| Polygon | 354 | 62.44% | 6.10% | 64.11% | 67.75% | 70.08% | 9.8% | ✅ Good |
| Optimism | 15 | 44.21% | 2.23% | 45.16% | 45.96% | 47.53% | 5.0% | ✅ Moderate (contaminated) |
| Ethereum | 349 | 50.76% | 0.81% | 50.74% | 51.42% | 52.14% | 1.6% | ⚠️ Weak (EIP-1559) |
| Avalanche | 354 | 12.94% | 2.83% | 11.74% | 16.42% | 18.80% | 21.9% | ✅ Good (high CV) |
| Base | 14 | 13.92% | 1.12% | 13.71% | 14.99% | 15.58% | 8.0% | ⚠️ Moderate (contaminated) |
| Arbitrum | 19 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | — | ❌ Broken measurement |

### 4.3 Empirical rho_ts data (90d)

| Chain | n | avg_rho_ts | std_rho_ts | p50 | p90 | p95 | p99 | p99/p50 |
|--------|---|------------|------------|-----|-----|-----|-----|---------|
| Polygon | 354 | 1.9974s | 0.0013s | 1.9972s | 1.9972s | 1.9972s | 2.0068s | **1.005** |
| Ethereum | 349 | 12.0155s | 0.0548s | 12.000s | 12.086s | 12.129s | 12.171s | **1.014** |
| Solana | 339 | 0.3937s | 0.0044s | 0.3938s | 0.3988s | 0.4007s | 0.4081s | **1.036** |
| Arbitrum | 19 | 0.2521s | 0.0058s | 0.2500s | 0.2550s | 0.2572s | 0.2715s | **1.086** |
| Avalanche | 354 | 1.0719s | 0.0660s | 1.0403s | 1.1774s | 1.2060s | 1.2446s | **1.197** |
| Base | 14 | 4.679s | 4.135s | 2.950s | 11.622s | 14.024s | 14.098s | **4.78** |
| Optimism | 15 | 4.564s | 4.070s | 2.885s | 10.900s | 14.055s | 14.263s | **4.94** |

> Base and Optimism: contaminated data (race condition). p50 ~3s instead of 2s. EMA reset pending.
> Avalanche: actual block time ~1.04s (p50), not 2s as initially documented.

### 4.4 Classification thresholds — calibration state per chain

**Confidence levels:**
- `MEDIUM event-based` — BigQuery backtest validated, TPR+FPR measured on real ground truth events → **publishable**
- `MEDIUM statistical` — P97 over ≥30d of production, without ground truth events → operational in production, event-based calibration pending
- `LOW` — empirical estimate only, no backtest → not publishable
- `HIGH` — TPR ≥ 0.80, FPR ≤ 0.10, n ≥ 3 events, deployed >30d → target Q3-Q4 2026

> ⚠️ Only `MEDIUM event-based` parameters are published here.
> Thresholds in production on other chains are available in the API but
> are not publicly certified before complete event-based validation.

#### τ — Structural thresholds (threshold_s2) — published

| Chain | threshold_s2 | Validated events | FPR_τ | IC95% FPR_τ | Confidence | Status |
|--------|-------------|-------------------|-------|-------------|------------|--------|
| **Ethereum** | **1.12** | The Merge (Sept 2022) · Shanghai Upgrade (April 2023) | 0.38% | — | **MEDIUM event-based** | ✅ published |
| **Polygon** | **1.04** | Network Halt · Gas Crisis · Heimdall/Bor · Reorg Storm (2021–2023) | 14.57% | [14.30% ; 14.83%] | **MEDIUM event-based** | ✅ published v2.0 (Φ=720) |
| **Solana** | **1.12** | 4 major outages (Sept 2021 · Jan 2022 · May 2022 · Oct 2022) | 1.77% | [1.70% ; 1.84%] | **MEDIUM event-based** | ✅ published |
| Avalanche τ | in progress | Event-based calibration July 2026 | — | — | pending | ⏳ |
| Arbitrum τ | Dormant | Regular sequencer by design — non-discriminating signal | — | — | Dormant | — |
| Base τ | Dormant | Regular sequencer by design | — | — | Dormant | — |
| Optimism τ | Dormant | Regular sequencer by design | — | — | Dormant | — |

#### π — Demand thresholds — published

| Chain | D2 logic | sigma | size | tx | Combined FPR (τ+π) | IC95% FPR | Confidence | Status |
|--------|----------|-------|------|----|-------------------|-----------|------------|--------|
| **Ethereum** | **2 of 3** | **1.10** | **1.20** | **1.10** | **1.23%** | [1.11% ; 1.36%] | **MEDIUM event-based** | ✅ published |
| **Polygon** | **2 of 3** | **1.14** | **1.18** | **1.23** | **14.57%** | [14.30% ; 14.83%] | **MEDIUM event-based** | ✅ published v2.0 (Φ=720) |
| Solana π | in progress | Usable data mid-June 2026 | — | — | — | pending | ⏳ |
| Avalanche π | in progress | Event-based calibration July 2026 | — | — | — | pending | ⏳ |
| Base π | MEDIUM statistical in prod | Event-based calibration Phase D (Q2-Q3 2026) | — | — | — | pending | ⏳ |
| Optimism π | MEDIUM statistical in prod | Event-based calibration Phase D (Q2-Q3 2026) | — | — | — | pending | ⏳ |
| Arbitrum π | signal absent by construction | gasLimit Nitro ≈ ∞ — rho_s structurally null | — | — | — | fix pending | ⏳ |

#### Validated ETH ground truth events (BigQuery backtest 2020–2024)

| Event | Type | Expected state | Detected | Latency |
|-----------|------|-------------|---------|---------|
| DeFi Summer (June–Sept 2020) | Pre-EIP-1559 demand surge | S1D2 | ✅ | — |
| NFT Mania (March–May 2021) | Demand surge | S1D2 | ✅ | — |
| The Merge (15 Sept 2022) | PoW→PoS transition | S2D1 | ✅ | +18.3h |
| Shanghai Upgrade (12 April 2023) | Withdrawals activation | S2D1 | ✅ | +22.8h |

#### 4.4.1 Exact confidence interval — reading TPR at small n

All published TPR and FPR values are accompanied by an **exact Clopper-Pearson 95% confidence interval** (binomial method, without normal approximation — appropriate when n is small or when the rate is close to 0% or 100%).

**Why this matters**: a `TPR = 100% (4/4)` is misleading when read alone. The Clopper-Pearson IC95% for k=4, n=4 is **[39.76% ; 100.00%]**. In other words, with 4 successes out of 4, one cannot statistically reject the hypothesis that the true detection rate is about 40%. The observed 100% is the **best point estimator** given the available events, not a strong predictive guarantee.

**Evolution with n**:

| k/n | Point | Clopper-Pearson IC95% |
|-----|-------|----------------------|
| 4/4 | 100% | [39.76% ; 100.00%] |
| 10/10 | 100% | [69.15% ; 100.00%] |
| 20/20 | 100% | [83.16% ; 100.00%] |

**Only the growth of n tightens the IC** — and n = number of real, non-reproducible blockchain events. Hence the event-based strategy plus a near-miss pipeline (flagging sub-threshold windows that approach the operating point) to progressively enrich the ground truth.

**FPR**: n_normal ≫ 10,000 on the 3 chains → tight ICs (<0.5% on ETH, <0.3% on POL, <0.1% on SOL). The noise measurement is statistically robust, even at high FPR (POL 14.57% ± 0.27%).

**Reproduction**:

```bash
python scripts/ci_binomial.py             # all published Invarians cases
python scripts/ci_binomial.py --k 4 --n 4 # custom case
```

Reference: Clopper, C. J. & Pearson, E. S. (1934). *Biometrika* 26(4), 404–413.

---

### 4.5 Complete calibration pipeline — OFFLINE → ONLINE

```
╔══════════════════════════════════════════════════════════════╗
║  OFFLINE  (calibration — once per threshold version)         ║
╚══════════════════════════════════════════════════════════════╝

  Historical distribution of EMA ratios (4 years BigQuery)
    + ground truth events (Merge, outages, upgrades…)
              ↓
    METHOD A — Event-based (mature L1: ETH, POL, SOL)
      → Sweep candidate thresholds (1.01 → 1.25)
      → Choose the highest that detects 100% of events
      → P90/P95/P97 bounds the search zone, not the result
              ↓
    METHOD B — Statistical (L2 without historical events: BASE, OP)
      → 30d of clean production
      → Threshold = P97 of the distribution
      → Confidence: MEDIUM statistical (vs MEDIUM event-based for L1)
              ↓
    Fixed versioned threshold (e.g.: threshold_s2=1.12 for ETH τ)
    stored in AgentNorthStar.com registry
              ↓
    M1 — Metric Stability Score computed on the calibrating distribution
    (see section 10)


╔══════════════════════════════════════════════════════════════╗
║  ONLINE  (production — at each Φ window of blocks)           ║
╚══════════════════════════════════════════════════════════════╝

  Raw signal (rho_ts, sigma, size, tx) from the blockchain
              ↓
    Fast EMA (α=2/11, ~10h)    ← "recent behavior"
    Slow EMA (α=2/721, ~30d)   ← "long-term structural baseline"
              ↓
    ratio = current_signal / Fast_EMA
    → dimensionless: 1.0 = nominal, 1.15 = 15% above baseline
    → comparable between ETH (12s/block) and SOL (0.4s/block)
              ↓
    ratio ≥ threshold_τ ?         → S2 (structural drift)  / S1 (nominal)
    ≥2 of 3 dims ≥ threshold_π ?  → D2 (high demand)       / D1 (nominal)
              ↓
    State: S1D1 | S1D2 | S2D1 | S2D2
              ↓
    PoEC signed Ed25519 + HMAC-SHA256
```

**Key architectural property:** the threshold is stable and versioned (auditable),
but the reference (EMA) continuously adapts to the chain. If ETH becomes
naturally slower after an upgrade, the EMA adjusts in ~10h and the system
does not sound permanently. Alarm stability + baseline adaptability.

---

## 5. Cryptographic trust chain

```
L0Signal  →  SHA256  →  L1Invariant  →  SHA256  →  L2Signal  →  Ed25519  →  Attestation  →  Agent
```

What Invarians **attests**:
> "Node X observed Y at time T via methods M on block B."

What Invarians **does NOT attest**:
- That Y is universally true
- That another node would see the same thing
- That the observation is reproducible tomorrow

The integrity of the observation is guaranteed. Universal truth is not.

---

## 5.1 Threat model

This section enumerates what an attacker would have to do to make Invarians lie — and what protects against it today vs in planned future work. Listed here so auditors do not have to guess.

### Trust model today

- **Who signs:** a single operational node computes invariants from an RPC feed and signs attestations with an Ed25519 private key.
- **Custody:** the signing key is on one VPS. Rotation is manual.
- **TTL:** attestations expire 1h after signing time.
- **HMAC-SHA256:** wrapper for the API transport layer (service → clients).
- **Record store:** historical attestations in Supabase (not yet anchored on-chain — see Attack 6 below).

### Attack 1 — Signer key compromise

**Scenario:** an attacker gains shell access to the signing node and exfiltrates the Ed25519 private key. They can now sign arbitrary false attestations bearing a valid signature.

**Current mitigation:**
- Short TTL (1h) bounds the window during which a stolen key can be used — if detected, revocation invalidates all attestations signed after the breach timestamp.
- Integrators SHOULD verify attestation timestamps against their own clock (±5 min skew tolerance) to reject obviously replayed signatures.

**Planned mitigation (Q4 2026):**
- **Chainlink DON threshold signing** — multiple independent signers required to produce an attestation. A single compromised key cannot forge signatures. Reduces this attack from *"total fabrication"* to *"delayed fabrication contingent on t-of-n collusion"*.
- Until then, key rotation every 90 days (manual, tracked in `calibration_log.md`).

### Attack 2 — Observing node eclipse / malicious RPC

**Scenario:** the observing node reads the blockchain through an RPC provider (or self-hosted node). If an attacker controls that feed, they can feed the node fabricated blocks (wrong timestamps, inflated sizes, tampered tx counts). Invarians will then sign attestations based on false data.

**Current mitigation:**
- RPC diversity: the node reads from multiple independent RPC endpoints and cross-checks block headers.
- For self-hosted nodes: peer diversity at the P2P layer.

**Planned mitigation (Q3 2026):**
- Multi-node observation: invariants computed independently on 3+ geographically separated nodes, only attestations agreed by a majority are signed. Dovetails with the Chainlink DON roadmap.

### Attack 3 — Timestamp post-dating / replay

**Scenario:** an attacker replays an old valid attestation as if it were current, or signs with a manipulated timestamp to make a past regime appear present.

**Current mitigation:**
- TTL 1h: attestations older than 1h are rejected by clients verifying signatures.
- Timestamp is part of the signed payload — cannot be altered without invalidating the Ed25519 signature.
- Integrators SHOULD reject timestamps more than 5 min in the future (signing-clock skew protection).

**Residual risk:** within the 1h TTL window, a malicious integrator could present the same valid attestation to multiple consumers as if generated freshly. This is not forgery — it is stale data. Consumers are expected to request fresh attestations per call.

### Attack 4 — Single-node trust (pre-DON)

**Scenario:** not an attack per se, but a structural limitation: today, a single operator can produce silently biased attestations if they chose to. Integrity is not cryptographic — it is *operational honesty*.

**Current mitigation:**
- Public `calibration_log.md` and BigQuery reproducibility: anyone can replay historical backtests and flag discrepancies.
- Published thresholds, scripts, and M1 formulas — bias would be statistically visible.

**Planned mitigation:**
- Q4 2026 — Chainlink DON threshold signing (see Attack 1).
- 2027 — native Invarians network (permissionless signing layer).

### Attack 5 — Block-space monopolization to force false S2D2

**Scenario:** an attacker with significant capital attempts to force a chain into a false S2D2 regime by:
- Buying enough block space (via priority fees / MEV-Boost bids) to inflate `size_avg` and `tx_count_avg` above their EMA baselines.
- Sustaining this over multiple hours (α_fast ≈ 10h — short spikes are absorbed).

**Cost floor (order of magnitude):** on ETH, sustained monopolization requires competitive priority fees across ~10h windows. At typical 2026 gas prices, this is a six-figure USD/day expenditure to maintain a sustained false stress signal.

**Why this is a feature, not a vulnerability:**
Invarians does not observe the mempool. Mempool flooding — the classic cheap DoS against block analytics systems — has **zero impact** on τ and π. This is a direct consequence of the post-PBS design choice documented in *Post-PBS blockchains need infrastructure metrics. Not mempool illusions* (Invarians, February 2026): what is not landed in a block does not exist for Invarians. The cost of forging a false stress signal is therefore proportional to actual on-chain block space, not to mempool spam bandwidth. This makes the attack **economically prohibitive** on high-volume chains (ETH, POL) and degrades gracefully on low-volume chains (where low volume itself is a signal).

**Planned mitigation:** none needed at signal level. Cross-referencing with independent fee trackers (by consumers of the attestation) provides defense-in-depth.

### Attack 6 — Supabase record rewrite

**Scenario:** an attacker (or a malicious operator) with Supabase write access modifies historical attestation records to retroactively present a different blockchain history.

**Current mitigation:**
- Supabase row-level security and audit logs.
- Attestations are cryptographically signed — any modification invalidates the Ed25519 signature. The attacker could only *delete* records, not silently alter them.

**Planned mitigation (May 2026):**
- **InvariansAnchor** contract on Arbitrum: periodically (daily or per-session) commits the Merkle root of attestations produced into an on-chain transaction. Historical Supabase records become cryptographically comparable against the on-chain commitment. Any rewrite would produce a mismatch immediately detectable by any auditor.

### Attack 7 — Ground truth poisoning via agent feedback

**Scenario (anticipatory, protocol not yet deployed):** the Q3 2026 agent feedback protocol allows integrating agents to report incidents they experienced, enriching the ground truth. A malicious agent could invent fake incidents to poison the FPR denominator (making FPR appear lower) or to create fake TPR events.

**Planned mitigation (Q3 2026, design-phase):**
- Agent feedback REQUIRES a signed attestation of the agent's own state during the claimed incident window — must be consistent with block-level observables.
- Multi-source confirmation: a "ground truth event" requires N independent agent reports + correlation with public incident feeds (chain status pages, block explorer anomalies, protocol announcements).
- Quarantine: new ground truth events enter a 30-day review period before affecting published TPR/FPR.

### Attack 8 — Long-range denial via upstream protocol changes

**Scenario:** a blockchain upgrade (EIP) changes the distribution of a signal without ground-truth notification, making calibration drift silently. Not an attacker-driven scenario, but a *class-of-failure* analogous to attacks.

**Current mitigation:**
- `protocol_watch.md` tracks major EIPs and documents calibration impact.
- EMA_slow (30d) adapts baselines over time.
- `calibration_log.md` documents explicit EMA resets.

**Planned mitigation (May 2026):**
- AgentNorthStar Calibration Agent (MCP) monitors drift metrics autonomously and opens `drift/` issues on `agentnorthstar/calibration` when FPR or M1 move out of published bounds.

### Summary table — threats × defenses

| # | Attack | Cost / difficulty | Current defense | Planned defense | Target date |
|---|--------|-------------------|-----------------|-----------------|-------------|
| 1 | Signer key theft | Shell access to the signing host | TTL 1h + manual rotation | Chainlink DON | Q4 2026 |
| 2 | RPC eclipse | Control of RPC feed | RPC diversity | Multi-node observation | Q3 2026 |
| 3 | Replay / post-dating | Trivial but short-lived | Signed timestamp + TTL 1h | Unchanged | — |
| 4 | Single-node operator trust | Structural | Public reproducibility | Chainlink DON then native net | Q4 2026 / 2027 |
| 5 | Block-space monopolization | $100k+/day sustained | Post-PBS design (by construction) | Not needed | — |
| 6 | Supabase record rewrite | DB access | Signed records (no silent alteration) | InvariansAnchor on-chain | May 2026 |
| 7 | Agent feedback poisoning | Protocol not yet deployed | N/A | Multi-source + signed state + quarantine | Q3 2026 |
| 8 | Silent protocol-upgrade drift | Passive | `protocol_watch.md` + EMA_slow | Calibration Agent MCP | May 2026 |

### What Invarians does NOT claim

- **Byzantine fault tolerance** on the signing layer — today the signing layer is one node. BFT comes with Chainlink DON (Q4 2026) and natively in 2027.
- **Perfect threat enumeration** — this section is a best-effort snapshot. Attack vectors omitted here should be reported via GitHub issues with prefix `threat/`.

---

## 6. Known instrumental limits

| Chain | Limitation | Impact | Compensated by |
|--------|-----------|--------|-------------|
| Ethereum | c_s=100% by construction (EVM sensor, not slot-by-slot) | c_s non-informative | Separate beacon chain monitoring |
| Ethereum | rho_s 50.76%±0.81% (EIP-1559 target 50%) | sigma_ratio very weakly discriminating — D2 threshold will need to be very close to 1.0 | Combination of size_ratio + tx_ratio |
| Polygon | rho_ts 2.000s±0.005s (governed block time fixed at 2s) | rho_ts unusable — total amplitude 0.011s over 90d | rho_s = main τ AND π signal |
| Avalanche | Documented block time 2s, actual ~1-1.3s | Incorrect documentation, Φ parameters to be recalibrated | Φ based on measured actual block time |
| Arbitrum | rho_s = 0.00% systematic | σ signal totally absent — π classification impossible | Fix required: use gas_used / effective block_gas_limit (~32M) |
| Base, OP | rho_ts and c_s mathematically inverse (block time fixed at 2s) | c_s redundant, not an independent signal | Use only rho_ts |
| Base, OP | Contaminated EMA baselines (race condition 16 March 2026) | c_s min=14.17/13.97%, rho_ts max=14s — distorted baselines | EMA reset after first clean invariant |
| All L2 | Post-seal sync: ~60% of time not covered | Discontinuous coverage | Intentional design — fresh window |
| All chains | c_s ≈ 100% in nominal operation (except extreme outage) | Low discriminating power for early drift | c_s kept as extreme outage detector (drop > 10%) |
| Polygon, Arbitrum (τ) | A single operational τ signal | Fragility: if the single signal is noisy, no redundancy for S1/S2 | To be documented — future improvement |

### 6.1 Mathematical property of the EMA ratio

The signal `rhythm_ratio = rho_ts / EMA(rho_ts)` has an important property to understand:

```
Phase 1 — surge:   rho_ts rises, EMA lags      → high ratio → S2 detected         ✅
Phase 2 — return: rho_ts drops, EMA still high → ratio < 1  → return to S1        ✅
Phase 3 — shadow: EMA still high (~10h)        → temporarily reduced sensitivity  ⚠️
```

After an S2 event, there is a **temporary insensitivity window** (~10h, duration of the fast EMA) during which a second event would need a stronger deviation to be detected. This is not a bug — it is a mechanical property of ratios with a lagged denominator. The slow EMA (30d) does not undergo this compression and maintains a stable baseline over the long term.

**EMA reset rule:** a reset is legitimate only during a change of instrumentation regime (sensor fix, corrected race condition, modified Φ parameter). A reset cannot be motivated by disagreement with the produced classification — that would be falsification of history.

---

---

## 7. L2 Rollups — Why the signals differ

### 7.1 The fundamental physical constraint

On L1, the consensus protocol produces blocks. A cadence deviation → real structural stress.

On L2, a **centralized sequencer** produces blocks at a regular cadence by design:

```
L1 (Ethereum, Solana, Polygon…)   → distributed consensus → variable cadence → τ measurable
L2 (Arbitrum, Base, Optimism…)    → single sequencer       → fixed cadence    → τ dead by design
```

Direct consequence: `rhythm_ratio ≈ 1.0` permanently on L2. This is not a measurement bug — it is a structural property of rollups. **τ is not a discriminating signal on L2.**

### 7.2 The Arbitrum case — broken rho_s

On Ethereum, `rho_s = gasUsed / gasLimit`. The effective gasLimit (~30M) is close to gasUsed (~15-25M), which gives an informative ratio.

On Arbitrum Nitro, the protocol gasLimit is `2^50 ≈ 1.125×10¹⁵`. gasUsed is ~2-3 billion.
```
rho_s(Arbitrum) = 2×10⁹ / 1.125×10¹⁵ ≈ 0.000001 → rounded to 0.00%
```

**Standard σ is structurally absent on Arbitrum.** The chain always operates at near-zero saturation by construction of the Nitro gas model.

### 7.3 What is operational on L2

| Signal | Arbitrum | Base | Optimism | Reason |
|--------|----------|------|----------|--------|
| `rhythm_ratio` (τ) | ❌ dead | ❌ dead | ❌ dead | Regular sequencer by design |
| `sigma_ratio` (π) | ❌ broken | ✅ | ✅ | gasLimit Nitro ≈ ∞ on Arbitrum |
| `size_ratio` (π) | ✅ | ✅ | ✅ | Block size measurable on all |
| `tx_ratio` (π) | ✅ | ✅ | ✅ | Tx volume measurable on all |
| `complexity_ratio` (π) | ✅ | ✅ | ✅ | Derived from size_avg/tx_count_avg |
| `gas_complexity_ratio` (π) | ✅ | ✅ | ✅ | Derived from gas_used_avg/tx_count_avg |

### 7.4 New comparison architecture — L1 cause / L2 response

**Why (SxDx)L1 vs (SxDx)L2 does not work:**

The initial intent was a symmetry:
```
L1: S (structure) + D (demand)
L2: S (structure) + D (demand)
```

This symmetry is physically incorrect. On L2, S ≈ constant (sequencer).
The τ dimension degenerates into a constant → useless classifier → loss of information.

**The actual finding:**
```
L1 = physical system      → directly observable   → direct sensing
L2 = transformation layer → indirectly observable → indirect sensing
```

L2 is not a "mini L1". It is a **response** layer to the L1 state.

**New architecture:**

```
L1 → (S, D)                          Bridge → (BS*)            L2 → (π, μ, σ)
  S = structure (τ)                     operational state           π = pressure (tx, size, sigma)
  D = demand    (π)                     (latency, backlog)          μ = composition (complexity_ratio, gas_complexity_ratio)
                                                                    σ = adaptation (publish_latency, blob_usage)
```

**Causal logic:**
```
L1 = CAUSE  → global structural state of the system
Bridge      → transmission channel — conditions propagation
L2 = EFFECT → local response to that state
```

Invarians no longer compares chains to each other symmetrically.
It reads layers of a single system: **Invarians = cross-layer interpreter**.

**Causal reading grid:**

| L1 state | Bridge | Typical L2 response | Interpretation |
|---------|--------|-------------------|----------------|
| S1D1 | BS1L1 | π↓ μ↓ σ↓ | Global calm — healthy infrastructure |
| S1D2 | BS1L1 | π↑ μ stable σ stable | Healthy adoption — L2 absorbs demand normally |
| S2D1 | BS1L1 | π↓ μ↑ σ↑ | Structural stress invisible on the price side — L2 adapts with no apparent demand |
| S2D2 | BS1L1 | π↑ μ↑ σ↑ | Systemic congestion — stress at all layers |
| * | BS2L* | σ↑ | Congested bridge — transmission broken, L2 responds alone |

> The S2D1 + π↓ μ↑ σ↑ case is particularly interesting for AI agents:
> it signals real infrastructure stress **before** it becomes visible in the fee markets.

**What this changes for the product:**

Before: dashboard + monitoring
Now: **execution context attestation** — input for agents, smart routing, multi-layer decisions.

---

## 8. L2 signal extension — Phases A, B, C (deployed 17 March 2026)

### 8.1 Phase A — complexity_ratio: bytes/tx (data complexity proxy)

**Motivation:** on L2, τ is dead and Arbitrum σ is broken. The first useful derivation from existing data is data complexity per transaction.

```
complexity = size_avg / tx_count_avg   (bytes per transaction)
complexity_ratio = complexity / EMA(complexity)
```

**Physics:** a high complexity_ratio indicates that transactions are becoming heavier in data — signature of complex smart contracts, massive NFT transfers, or dense calldata. Useful signal even when rho_s is absent.

**Implementation:** derived directly in `invarians-l2-chain/src/lib.rs` from the existing fields `DemandSnapshot.size_avg` and `DemandSnapshot.tx_count_avg`. **No change on the collector side.**

**EMA:** same alpha as other signals (2/11 fast, 2/721 slow). Temporal consistency with π.

**Initial baselines (17 March 2026):**
- Arbitrum: 589.7 bytes/tx
- Base: 564.5 bytes/tx
- Optimism: 302.9 bytes/tx

---

### 8.2 Phase B — gas_complexity_ratio: gas/tx (computational complexity)

**Motivation:** complexity_ratio measures the weight of *data*. What is missing is a measure of *computational* weight — what the chain actually computes per transaction. This is the σ signal for Arbitrum.

```
gas_complexity = gas_used_avg / tx_count_avg   (gas per transaction)
gas_complexity_ratio = gas_complexity / EMA(gas_complexity)
```

**Physics:** a high gas_complexity_ratio indicates that transactions are computationally heavier — complex DeFi, intensive smart contracts. On Arbitrum in particular, this is the only proxy for computational overload available (rho_s being structurally null).

**Technical constraint:** `ans-core` is **frozen** — `L0Signal` and `InvariantL1` are immutable (integrity of the L1 cryptographic chain). `gas_used_avg` is computed in `invarians-l2-collector` from the buffer: `mean(load)` over Φ blocks, stored as a nullable column in `ans_invariants_v3`.

```
Implementation:
invarians-l2-collector  → gas_used_avg = sum(s.load) / buffer.len()   [outside ans-core]
ans_invariants_v3       → ADD COLUMN gas_used_avg DOUBLE PRECISION
invarians-l2-chain      → gas_complexity_ratio from gas_used_avg/tx_count_avg
```

**NULL safety:** if `gas_used_avg IS NULL` or `tx_count_avg = 0`, the ratio returns to 1.0 (neutral) and the baseline is preserved. Expected cold start: 1 collector cycle (~1h) before first non-NULL value.

---

### 8.3 Phase C — invarians-l2-adapter: the σ layer (Adaptation)

**Motivation:** τ is dead on L2. π measures demand on the chain. One unmeasured dimension remains: **how the sequencer reacts to demand** — this is the σ layer (Adaptation).

The source of these signals is not L2 but **L1 Ethereum**: the sequencer materializes its adaptation by submitting batches to L1. These batches are observable on-chain.

```
DEMAND (L2)    →  sequencer reacts  →  BATCH SUBMISSION (L1)
     π measures here                          σ measures here
```

**Three σ signals produced:**

| Signal | Computation | Physics |
|--------|--------|----------|
| `publish_latency_seconds` | `t_L1_inclusion − last_timestamp_L2` (approx) | Batch publication delay. Increases under extreme load or L1 congestion. |
| `calldata_bytes` | `input.len()` (calldata tx) or `blob_count × 131 072` (blob tx) | Total size of submitted batch. Proxy for the compressed L2 data volume. |
| `blob_usage` | `blob_count / 6` | Saturation of the EIP-4844 market. Resource shared among ALL L2s — cross-L2 systemic signal. |
| `calldata_per_tx` | `calldata_bytes / tx_count_ref` (approx) | Data compression efficiency per L2 transaction. |

**Why blob_usage is strategic:** EIP-4844 allocates 6 blobs per L1 block. Base and Optimism compete for these blobs with all other L2s. A blob stress simultaneously affects all OP Stack chains. This is a shared-infrastructure signal invisible in per-chain metrics.

**Method — Option A (approximation):** no decoding of the batch encoding (OP Span Batch / Arbitrum Nitro). `publish_latency` is approximated by `t_L1_block − last_timestamp` of the last L2 invariant. Relative value, suited to EMA. Absolute precision is not required to detect regimes.

**Monitored L1 addresses:**
| Chain | Contract | Address |
|--------|---------|---------|
| Base | BatchInbox | `0xff00000000000000000000000000000000008453` |
| Optimism | BatchInbox | `0xff00000000000000000000000000000000000010` |
| Arbitrum | SequencerInbox | `0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6` |

**Infrastructure:** L1 scan every 5 minutes, 25-block window (~5 min L1 = 12s/block). Source: Ethereum L1 RPC endpoint.

**First observations (17 March 2026):**
- Base + Optimism submit in the **same L1 block** (shared OP Stack infrastructure)
- `blob_usage = 0.833` (5/6 blobs) — blob market under high utilization
- Arbitrum: reduced on-chain frequency (AnyTrust reduces on-chain submissions)

---

## 9. Complete synthesis of Invarians metrics

### 9.1 L1 — τ and π layers

| Metric | Computation | Layer | Active chains | Signal |
|---------|--------|--------|----------------|--------|
| `rho_ts` | window_duration / block_count | τ | ETH, SOL, AVAX, ARB | Temporal inertia — cadence in s/block |
| `rhythm_ratio` | rho_ts / EMA(rho_ts) | τ | ETH, SOL, AVAX, ARB | Cadence drift vs baseline |
| `c_s` | valid_blocks / slot_range × 100 | τ | all | Continuity — extreme outage detector |
| `rho_s` | gasUsed / gasLimit × 100 | π | ETH, SOL, POL, AVAX | Computational saturation |
| `sigma_ratio` | rho_s / EMA(rho_s) | π | ETH, SOL, POL, AVAX | Computational overload vs baseline |
| `size_avg` | average bytes per block | π | all | Data volume |
| `size_ratio` | size_avg / EMA(size_avg) | π | all | Data pressure vs baseline |
| `tx_count_avg` | average transactions per block | π | all | Operational volume |
| `tx_ratio` | tx_count_avg / EMA(tx_count_avg) | π | all | Operational pressure vs baseline |

### 9.2 L2 — π layer (Volumetric pressure)

| Metric | Computation | Phase | Chains | Signal |
|---------|--------|-------|---------|--------|
| `sigma_ratio` | rho_s / EMA(rho_s) | baseline | BASE, OP | Saturation (❌ Arbitrum: incompatible gas model) |
| `size_ratio` | size_avg / EMA(size_avg) | baseline | ARB, BASE, OP | L2 data volume |
| `tx_ratio` | tx_count_avg / EMA(tx_count_avg) | baseline | ARB, BASE, OP | L2 transaction volume |

> Note: `rhythm_ratio` is computed and stored on L2 but structurally ≈ 1.0 — non-discriminating.

**Why L2 calibration differs structurally from L1:**

1. **Mono-signal vs multi-signal.** On L1, D2 requires 2 of 3 dims (sigma + size + tx) — multi-signal consensus, combined FPR ~1.2%. On L2, `sigma_ratio` is the only reliable signal on BASE/OP (size and tx not event-calibrated). A mono-signal threshold placed at the same percentile as L1 produces a structurally higher FPR. L2 thresholds are not numerically comparable to L1 thresholds.

2. **Statistical vs event-based.** L1 thresholds are derived by event-detection (BigQuery — The Merge, Solana outages, Polygon Reorg Storm). L2 thresholds are statistical (percentile on production distribution) — no calibrating L2 event available before Phase D (Dune, Q2-Q3 2026).

**L2 calibration status:**
- Thresholds in production (operational), derived by statistical P97 method on ≥30d
- Event-based calibration (Phase D — Dune): Q2-Q3 2026
- Numerical thresholds published in `ans_registry` only after Phase D validation

### 9.2b L2 — μ layer (Composition — Phases A/B)

μ is a sub-layer of π that measures the **internal structure** of transactions,
not their volume. A stable tx_ratio with a rising μ signals a recomposition
of activity (more complex transactions, not necessarily more numerous).

| Metric | Computation | Phase | Chains | Signal |
|---------|--------|-------|---------|--------|
| `complexity_ratio` | (size_avg/tx_count_avg) / EMA | **Phase A** | ARB, BASE, OP | Data complexity per tx (bytes/tx) — calldata weight proxy |
| `gas_complexity_ratio` | (gas_used_avg/tx_count_avg) / EMA | **Phase B** | ARB, BASE, OP | Computational complexity per tx (gas/tx) — DeFi load proxy |

### 9.3 L2 Adapter — σ layer (Adaptation)

| Metric | Computation | Phase | Chains | Signal |
|---------|--------|-------|---------|--------|
| `publish_latency_seconds` | t_L1_block − last_timestamp_L2 | **Phase C** | ARB, BASE, OP | L1 batch publication delay |
| `calldata_bytes` | input.len() or blob_count×131072 | **Phase C** | ARB, BASE, OP | Batch size submitted to L1 |
| `calldata_per_tx` | calldata_bytes / tx_count_ref | **Phase C** | ARB, BASE, OP | Compression efficiency per tx (approx) |
| `blob_count` | len(blobVersionedHashes) | **Phase C** | BASE, OP | Number of EIP-4844 blobs used |
| `blob_usage` | blob_count / 6 | **Phase C** | BASE, OP | Blob market saturation (cross-L2 resource) |

### 9.4 Synthesis by layer and state framework

```
L1 → (S, D) states
  S1D1 | S1D2 | S2D1 | S2D2

L2 → (π, μ, σ) states  [framework under construction — Phase D]
  π = volumetric pressure (tx, size, sigma)
  μ = composition (complexity_ratio, gas_complexity_ratio)
  σ = adaptation via L1 (publish_latency, blob_usage)
```

Target L2 classification (post Phase D):

| π | μ | σ | Interpretation |
|---|---|---|----------------|
| ↓ | ↓ | ↓ | Low activity — calm regime |
| ↑ | stable | stable | Healthy adoption — rising volume, stable complexity |
| stable | ↑ | stable | Recomposition — more complex transactions without volume |
| ↑ | ↑ | stable | Complex adoption — intensive DeFi |
| ↑ | ↑ | ↑ | Real stress — congestion at all layers |

> This grid will be calibrated by Dune backtest on historical L2 events (Phase D).

### 9.5 Bridge — Transmission layer

The bridge is the **membrane between L1 and L2**. It does not measure the state of L1 or L2 —
it measures whether the **transmission channel between the two layers is operational**.

**Systemic role:**
```
L1 (global state)
  → Bridge (transmission)
    → L2 (execution)
```

The bridge conditions the propagation of stress between layers. An L1 stress can remain
contained (low bridge activity) or propagate massively (high bridge flow). A congested
bridge breaks the transmission — L2 ends up isolated.

**Operational dimension — BS* (Phase 2, Q3 2026):**

| Metric | Nature | Signal |
|---------|--------|--------|
| `latency_ratio` | t_relay / expected | L1↔L2 message relay delay |
| `backlog_ratio` | pending / throughput | Message queue saturation |

BS* classification:

| State | Condition | Meaning |
|------|-----------|---------------|
| **BS1L1** | Latency normal, backlog normal | Healthy bridge |
| **BS1L2** | Latency normal, high backlog | Queue buildup |
| **BS2L2** | High latency + backlog | Bridge stress |
| **BS2L1** | High latency, nominal backlog | Relayer instability |

> No hysteresis on bridges — polling 5-15 min (direct measurement, no ~1h window).
> A bridge can go from healthy to congested in 5-15 minutes.

**Flow dimension — ω (Phase 3, prospective):**

A future extension will introduce **ω** (inter-layer flow) as an economic
propagation signal — distinct from the BS* operational state.

> ⚠️ Note: β is already used in section 4.1 as an internal batch parameter.
> The bridge flow is noted ω to avoid collision.

| ω signal (future) | Nature | Interpretation |
|-----------------|--------|----------------|
| Bridged volume (ETH→L2) | Economic flow | Activity migration L1→L2 |
| Deposits / Withdrawals | Flow direction | Panic/risk-off if massive withdrawals |
| L1↔L2 imbalance | Asymmetry | Arbitrage or liquidity flight |

```
ω = economic propagation signal
BS* = operational state of the channel
```

> ω is not yet implemented — no data collected. To be evaluated post Phase D.

### 9.6 EMA availability by layer

| Layer | Fast EMA | Slow EMA | Calibrated baselines |
|--------|-----------|-----------|-------------------|
| L1 τ+π | ✅ (2/11, ~10h) | ✅ (2/721, ~30d) | ETH: MEDIUM. Others: LOW or pending |
| L2 π+μ | ✅ (2/11, ~10h) | ✅ (2/721, ~30d) | all LOW — Dune calibration pending |
| L2 σ (adapter) | ⏳ not yet | ⏳ not yet | To be implemented post Phase D |

> Phase C signals are currently stored **raw** (no EMA). The σ EMA will be added after Dune calibration (Phase D, Q2-Q3 2026).

---

## 10. M1 — Metric Stability Score

> **Status:** formula v0.1 validated — calibration session 17 April 2026. Dedicated script implementation pending (`m1_*.py` — see scripts/README.md).

M1 quantifies the **calibratory reliability** of a signal on a given chain.
It answers the question: *is this signal sufficiently discriminating to produce
a reliable alarm, or is it too noisy / too flat to be useful?*

### 10.1 Formula (validated — calibration session 17 April 2026)

```
M1 = dynamic_amplitude / baseline_noise

dynamic_amplitude  = (max_event − p50) / p50
                     max_event = maximum of the EMA ratio observed during the best ground truth event
                     p50       = median of the EMA ratio over the full backtest

baseline_noise     = std(signal) / mean(signal)
                     computed on windows where ratio < 1.05 (strict nominal regime)
```

**Property:** M1 measures how many times the signal amplitude during a real event
exceeds the structural noise of the nominal regime. M1 ≥ 1.0 means the signal
discriminates better than it noises — usable calibration. M1 < 0.5 means
noise dominates amplitude — non-discriminating signal.

**ETH numerical verification (session 17 April 2026):**
```
Signal       : rhythm_ratio (rho_ts / EMA_fast)
max_event    : 1.1548  (The Merge, 15 Sept 2022)
p50          : 0.9993
amplitude    : (1.1548 − 0.9993) / 0.9993 = 0.1556
noise        : std/mean of signal < 1.05 = 0.0307
M1_computed  : 0.1556 / 0.0307 = 5.07  ✅  (published value: 5.05)
```

### 10.2 Interpretation

| M1 score | Level | Meaning |
|----------|--------|---------------|
| ≥ 2.0 | Excellent | Strongly discriminating signal |
| ≥ 1.0 | Certified | Event-based calibration validated |
| ≥ 0.5 | Operational | Acceptable statistical calibration |
| < 0.5 | Provisional | Weak signal — use with caution |

**Special statuses:**
- **Dormant**: signal constant by design (e.g.: ARB τ — regular sequencer). M1 not computable.
- **Observational**: insufficient data for calibration (e.g.: Bridge BS2 pre-Phase 2C).

### 10.3 Published values — formula v0.1 (scripts/m1_*.py)

| Chain | Signal | Event | M1 | Script | Confidence |
|--------|--------|-----------|----|--------|------------|
| **Ethereum** | τ (rhythm_ratio) | The Merge (2022-09) | **5.07** | `m1_eth.py` ✅ | **MEDIUM event-based** |
| **Polygon** | τ (rhythm_ratio) | Reorg Storm (2023-02) | **12.60** | `m1_pol_phi720.py` ✅ | **MEDIUM event-based (Φ=720)** |
| **Polygon** | π (sigma_ratio) | Gas Crisis (2021-05) | **3.59** | `m1_pol_phi720.py` ✅ | **MEDIUM event-based (Φ=720)** |
| Solana | τ | — | — | Script pending | LOW — not published |
| Avalanche | τ | — | — | Event-based calibration pending (July 2026) | LOW — not published |
| Arbitrum | τ/π | — | — | Dormant (regular sequencer by design) | Dormant |
| Base | π | — | — | Phase D pending (Q2-Q3 2026) | Observational |
| Optimism | π | — | — | Phase D pending (Q2-Q3 2026) | Observational |

> All M1 values above are produced by the `m1_*.py` scripts (formula v0.1).
> Independently reproducible from BigQuery.
>
> **Historical note:** the values previously published on AgentNorthStar.com (ETH=5.05, POL=8.06)
> were manual estimates prior to the formalization of the formula.
> The value POL=7.37 (calibration_log #017) was also a session estimate —
> it is not reproducible by formula v0.1. The traceable values are those in the table above.
> ANS registry updated on 17 April 2026 (see Entry #018).

### 10.4 Recomputation protocol

M1 is recomputed only when:
- A ground truth event is added to the backtest
- A threshold changes (new version)
- EMA is reset after a sensor incident

M1 does not fluctuate in production — it is a property of calibration, not of runtime.

### 10.5 Confidence intervals and tail resistance (bootstrap + P99)

The formula in §10.1 uses `max_event`, which is by construction the single most
extreme observation during the best ground truth event. This yields the
**peak discrimination** of the signal but is, by definition, a one-point
statistic — it can overstate reliability if the peak is an artifact.

Two complementary metrics are reported alongside the published M1:

**Bootstrap 95% CI (n=1000, seed=42).** Full-signal windows and event-window
values are independently resampled with replacement. For each resample, p50,
noise (CV on nominal windows) and `max_event` are recomputed, yielding a
distribution over M1. The 2.5th and 97.5th percentiles form the 95% CI.
The published max-based M1 typically sits at the upper edge of this CI —
consistent with `max` being an order statistic.

**P99 variant.** Replace `max_event` with the 99th percentile of the event
window. This is a **tail-resistant** estimate that answers the question
"what is M1 if we ignore the single most extreme sample?" — useful as a
conservative floor.

| Chain / Signal | Event | M1 (published) | 95% CI | Bootstrap mean | M1 (P99) |
|---|---|---|---|---|---|
| ETH τ rhythm_ratio | The Merge | **5.07** | [2.23, 5.12] | 4.32 | 3.90 |
| POL τ rhythm_ratio (Φ=1800) | Reorg Storm | 10.66 | [4.00, 10.82] | 9.17 | 4.96 |
| POL π sigma_ratio (Φ=1800) | Gas Crisis | 4.55 | [2.66, 4.65] | 4.08 | 2.08 |
| POL τ rhythm_ratio (Φ=720) | Reorg Storm | **12.60** | [4.04, 12.74] | 10.68 | 3.01 |
| POL π sigma_ratio (Φ=720) | **Gas Crisis** | **3.59** | [3.27, 3.64] | 3.49 | 1.94 |

Events above match the canonical anchors declared in §10.3. For POL π, the canonical anchor is **Gas Crisis** (a pure-demand event), even though the Network Halt event produces a larger amplitude (M1=8.85 / 8.66 at Φ=1800 / 720). Network Halt is a composite halt+backlog incident and is intentionally not used as the π calibration anchor — keeping Gas Crisis preserves methodological consistency with the formula-v0.1 publication.

**Interpretation:**
- All published M1 values sit inside their bootstrap CI — sampling is not
  pathological.
- The P99 variant is typically 40–75% of the max-based M1. This is the
  expected separation between "peak signal" and "broad signal" under a
  short ground-truth window. Both remain well above the M1 ≥ 1.0
  certification threshold (§10.2) for all chains.
- The CI lower bound is the **publishable floor** — below it, the calibration
  would be downgraded from *Certified* to *Operational*. As of this release,
  no chain falls below 1.0 even at the CI lower bound.

**Scripts:** `scripts/m1_eth.py`, `scripts/m1_pol.py`, `scripts/m1_pol_phi720.py`
— the `bootstrap_m1()` and P99 helpers output the additional columns
`m1_ci95_low`, `m1_ci95_high`, `m1_bootstrap_mean`, `p99_event`, `m1_p99`
in the `*_m1_results.csv` files.

---

## 11. Next steps

- [x] Phase A: complexity_ratio L2 (17 March 2026)
- [x] Phase B: gas_complexity_ratio L2 (17 March 2026)
- [x] Phase C: invarians-l2-adapter — publish_latency, calldata_per_tx, blob_usage (17 March 2026)
- [ ] Phase D: Dune calibration — Phase A+C thresholds on historical L2 events (Q2-Q3 2026)
- [ ] EMA σ: add fast/slow EMA on Phase C signals (after Phase D) — `σ_ratio = σ / EMA(σ)`
- [ ] L2 classifier (π, μ, σ): implement the states (see section 9.4) after Phase D calibration
- [ ] **Phase 2 — Bridge BS*** : invarians-bridge module (ARB · OP/BASE · Across · LayerZero · CCTP) — latency_ratio, backlog_ratio, BS1/BS2 states (Q3 2026)
- [ ] **Phase 3 — ω (inter-layer flow)**: bridged volume, deposits/withdrawals, L1↔L2 imbalances — economic propagation signal (post Phase D, 2027 evaluation)
- [ ] Validation of remaining L1 thresholds via backtest (Solana π, Avalanche τ+π)
- [ ] Fix Arbitrum rho_s: use gas_used / effective_block_gas_limit (~32M)

---

*Version 0.4 — Draft — 17 March 2026*
*v0.3: architectural pivot L1 cause / L2 response, introduction of the μ layer (composition),*
*section 7.4 causal grid, section 9.2b μ distinct from π, section 9.4 target (π,μ,σ) classifier*
*v0.4: integration of the bridge as transmission layer — causal framework L1→Bridge→L2,*
*section 9.5 operational BS* (Phase 2) + ω inter-layer flow (Phase 3, prospective),*
*causal grid extended with Bridge column, section 10 planned phases 2+3*
*Effective publication after minimum backtest validation on 2 chains*
