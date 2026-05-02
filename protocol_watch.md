# Invarians — Protocol Watch

**Format:** external protocol changes verified against primary sources, ranked by impact on Invarians calibration.
**Rule:** every entry must be sourced from ethereum.org, the GitHub EIP tracker, or the official project documentation. No third-party sources.

---

## EIP-4844 — Proto-Danksharding

**Status:** Final — deployed mainnet March 2024
**Source:** github.com/ethereum/EIPs/blob/master/EIPS/eip-4844.md

**Technical description:**
Introduces a new transaction type ("blob-carrying transaction") with a distinct gas market (blob gas) for L2 → L1 data posting. Blobs are temporary (approximately 18 days) and cheaper than calldata.

**Impact on Invarians:**

The economic pressure π on L1 was historically correlated with L2 activity via calldata posting. Since EIP-4844, L2s post their data as blobs at a structurally lower cost and on a distinct market. Consequence: π on L1 is partially decoupled from L2 activity.

The π baselines calculated on pre-March 2024 data incorporate a structurally higher level of L1 pressure than currently exists. Any backtest using pre-4844 data to calibrate S1D2/S2D2 thresholds must account for this.

**Required action:**
- Verify that ETH π baselines are calculated on post-March 2024 data only
- Explicitly document the break date in ETH backtests
- Flag in any pitch or publication that pre/post-4844 comparisons are not directly equivalent

**Priority:** High — directly impacts the reliability of ETH π baselines

---

## EIP-7702 — Account Abstraction for EOA (Pectra)

**Status:** Final — deployed mainnet May 2025
**Source:** github.com/ethereum/EIPs/blob/master/EIPS/eip-7702.md

**Technical description:**
Allows an EOA to temporarily delegate its execution to a smart contract via a SET_CODE transaction type. Used notably for session keys in agentic pipelines.

**Impact on Invarians:**

Structural increase in the volume of agentic transactions on L1 and L2. AI agents can now execute multi-step strategies in a non-custodial manner. The π pressure on chains supporting EIP-7702 will be progressively modified by this new type of traffic.

This is an accelerator of the Invarians thesis: more active agents = execution signal context more frequently solicited.

**Required action:**
- Monitor the evolution of ETH π baselines post-May 2025
- Identify whether UserOps (EIP-4337) and SET_CODE (EIP-7702) introduce distinct congestion patterns in σ metrics
- No immediate recalibration required — monitor over 90 days

**Priority:** Medium — opportunity, not a constraint

---

## EIP-7781 — Slot time reduction (under specification)

**Status:** Draft
**Source:** github.com/ethereum/EIPs/issues — to confirm on official EIP tracker before any public citation

**Technical description:**
Proposes reducing the Ethereum slot from 12 seconds to 8 seconds.

**Impact on Invarians:**

The Invarians structural window is expressed in number of blocks (~280 blocks for ETH ≈ 1h). If the slot moves to 8s, 280 blocks represent ~37 minutes instead of ~56 minutes. The time window compresses.

Options to evaluate at deployment time:
- Adjust the number of blocks to maintain a ~1h window (280 → 450 blocks)
- Or accept the shorter window and recalibrate the baselines

**Required action:**
- Monitor the status of this EIP — change nothing until it reaches "Last Call"
- Prepare the window recalibration script in advance

**Priority:** Low at this stage — to reactivate when status = Last Call

---

## Shared Sequencers — Espresso Systems, Astria

**Status:** Active testnets, L2 integrations in progress (April 2026)
**Sources:** docs.espressosys.com · astria.org

**Technical description:**
A shared sequencer handles transaction ordering for multiple L2s simultaneously, enabling inter-L2 interoperability without a bridge.

**Impact on Invarians:**

If multiple L2s monitored by Invarians share a common sequencer (e.g., Espresso), an incident on that sequencer produces a sudden correlation between chains that are normally independent. Risk of simultaneous multi-chain S2 false signal.

Without identification of the underlying sequencer, Invarians may interpret a third-party infrastructure failure as native network saturation.

**Required action:**
- Identify the underlying sequencer of each monitored L2 (native vs shared)
- Consider a `sequencer_type: native | shared` field in the regime matrix
- Document L2s on Espresso/Astria as soon as they go to mainnet

**Priority:** Medium — becomes high if a monitored L2 migrates to a shared sequencer

---

## EIP-4337 — Account Abstraction via Bundlers

**Status:** Final — deployed mainnet March 2023
**Source:** github.com/ethereum/EIPs/blob/master/EIPS/eip-4337.md

**Technical description:**
Introduces UserOperations processed by bundlers — an aggregation layer between smart contract wallets and the L1 mempool.

**Impact on Invarians:**

Bundlers add specific latency and competition that did not exist with classic EOA transactions. The π pressure may exhibit atypical patterns during UserOps volume spikes (e.g., NFT drops, DeFi liquidations via smart wallets).

**Required action:**
- Monitor whether ETH π baselines exhibit distinct signatures during known UserOps spikes
- No immediate recalibration required

**Priority:** Low — passive monitoring

---

## Invarians API v2.0 — internal protocol upgrade

**Status:** Live, deployed mainnet 2026-04-30
**Source:** `research/api/V2_SPEC.md`, `calibration_log.md` entries #033 to #036

**Technical description:**
API v2.0 unifies three primitives in a single signed payload: Attestation (HMAC-SHA256), Regime (12 signed codes per chain via the structural × demand grid with explicit direction suffixes S2±, D2±), Drift Signal (per-metric `MetricBlock` with `ratio`, `ratio_long`, `shift`, `shift_delta`, `shift_magnitude_delta` plus per-axis composite drift). Two new structural classifying observables ship with v2.0: `beacon_participation` on Ethereum L1 (validator participation rate, low-side trigger only) and `sequencer_publish_latency` on Arbitrum, Base, Optimism L2 rollups (batch posting cadence, high-side trigger).

**Impact on Invarians:**

The 12 signed codes are an additive extension of the legacy 4-state grid (S1D1, S1D2, S2D1, S2D2 remain valid as aliases when low thresholds are not yet calibrated). All historical backtests remain valid as the calibration of record; the signed codes further partition states without invalidating prior TPR/FPR figures.

The Drift Signal exposes soft slowdowns and slow drifts that do not flip the regime, addressing the gap between regime classification (calibrated halt-only on the structural axis) and operational decisions that require sub-halt timing buffers (RWA settlement, audit-grade SLAs).

**Required action:**
- v1.1.0 endpoints `/attestation/panel` and `/attestation/verify` remain live until 2026-06-30, then return `410 Gone`.
- Per-metric `shift_available: false` on `beacon_participation` and `sequencer_publish_latency` until the long-term EMA stabilizes (~30 days, target end-May 2026).
- Solana and Avalanche remain on the legacy 4-state grid until July 2026 calibration window.

**Priority:** High — spec of record for all new integrations.

---

*Last updated: 2026-05-02*
*Update rule: any new entry must cite a verified primary source.*
