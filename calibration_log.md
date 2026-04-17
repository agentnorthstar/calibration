# Invarians — Calibration Log

**Format:** chronological entries, immutable.
Each EMA reset, incident, or parameter change is documented here with its rationale.

---

## Entry #001 — March 14, 2026 — L2 production start

**Type:** Initialization
**Chains:** arbitrum, base, optimism
**Action:** First L2 invariants produced. EMA baselines initialized from the first invariant.
**Initial parameters:**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30d)
- S2 threshold: rhythm_ratio > 1.15
- D2 threshold: sigma_ratio > 1.20
**Baseline status:** not calibrated — arbitrary initial values
**Confidence:** LOW

---

## Entry #002 — March 15, 2026 — Arbitrum incident: race condition

**Type:** Incident → Deployment fix
**Chain:** arbitrum
**Symptom:** buffer frozen at 2/14400, no invariant produced after seq=10.
**Root cause:** 30s throttle with beta=120 → advance rate 4 blocks/s > chain rate 3.8 blocks/s.
**Fix:** throttle 30s → 38s. Advance rate 3.16 blocks/s < 3.8 blocks/s.
**EMA impact:** baselines partially contaminated by the few invariants produced before the incident.
**Corrective action:** no reset required (little contaminated data, short sequence).
**Post-fix confidence:** LOW → to reassess after 30d

---

## Entry #003 — March 16, 2026 — BASE/OPTIMISM incident: rho_ts/c_s mirror

**Type:** Structural incident → Deployment fix
**Chains:** base, optimism
**Symptom:** rhythm_ratio=4.62, continuity_ratio=0.21 → permanently classified S2. Strict mirror evolution of both signals.
**Root cause:**
1. Race condition: 100s throttle with beta=50 → advance rate 0.5 blocks/s = exact chain rate.
2. Physical insight: for chains with fixed 2s block time, `rho_ts × c_s/100 ≈ 2s = constant` → mathematically inverse signals.
**Fix:** throttle 100s → 110s. Advance rate 0.4545 blocks/s < 0.5 blocks/s.
**EMA impact:** 2 weeks of contaminated baselines (c_s≈58%, rho_ts≈5s instead of c_s≈100%, rho_ts≈2s).
**Required corrective action:** DELETE FROM ans_l2_rollup_signals WHERE chain IN ('base','optimism') after first clean invariant.
**Validation criterion:** c_s > 90% AND rho_ts < 2.5s on the most recent row.
**Status:** ⏳ Pending validation of first clean invariant.
**Design note:** c_s is a redundant signal for Base and Optimism. In the long run, use only rho_ts or rho_s for these chains.

---

## Entry #004 — March 16, 2026 — EMA reset BASE/OPTIMISM

**Type:** EMA Reset
**Chains:** base, optimism
**Trigger:** First post-fix invariant — criterion validated:
- base: seq=20, c_s=100, rho_ts=1.9989s ✅
- optimism: seq=21, c_s=100, rho_ts=1.9989s ✅
**Action:** `DELETE FROM ans_l2_rollup_signals WHERE chain IN ('base','optimism')`
**Effect:** Baselines re-initialized on clean data. Fast EMA convergence in ~5 invariants (~5h).
**Expected result:** Divergence ANOMALY/ELEVATED → NOMINAL within ~5h.
**Status:** ✅ Executed — March 16, 2026

---

---

## Entry #005 — March 16, 2026 — ETH τ calibration (threshold_s2)

**Type:** Parameter calibration
**Chain:** ethereum (L1)
**Method:** Event-detection backtest on BigQuery `bigquery-public-data.crypto_ethereum.blocks`, window 2020-01-01 → 2024-01-01, 34,697 invariants, Φ=280 blocks (~1h).
**Previous value:** `rhythm_p90 = 1.0073` (empirical P90 percentile — arbitrary)
**New value:** `rhythm_p90 = 1.12` (event-detection validated)
**Rationale:**
- FPR = 2.50% at threshold_s2=1.12 (vs 10.56% at 1.05)
- Detects The Merge (Sept 15, 2022, latency +18.3h) ✅ and Shanghai Upgrade (April 12, 2023) ✅
- Non-detection of DeFi Summer / NFT Mania: **correct** — τ stress absent, nominal infrastructure
- FPR floor at 2.12% beyond 1.18: caused by D2 noise, not by τ
**Signal:** rho_ts / EMA(rho_ts), alpha=2/11 (~10h)
**TPR:** 100% on known structural events (n=2)
**FPR τ only:** 2.50%
**Confidence:** MEDIUM
**Deployed:** Supabase project `sdpilypwumxsyyipceew`, March 16, 2026
**Script:** BIGDATA/sweep_eth.py

---

## Entry #006 — March 16, 2026 — ETH π calibration (D2 thresholds)

**Type:** Parameter calibration
**Chain:** ethereum (L1)
**Method:** Sigma-only sweep (sweep_eth_d2.py) then full D2 sweep size × tx (sweep_eth_d2_full.py). Production logic: D2 if 2 dims out of 3 (sigma, size, tx) above their threshold.
**Previous values:** `sigma_demand=1.0154`, `size_demand=1.2002`, `tx_demand=1.1430` (empirical P95 percentiles)
**New values:**
- `sigma_demand = 1.10` (sigma-only sweep, FPR π = 0.99%)
- `size_demand = 1.20` (full D2 sweep, combined FPR τ+π = 1.23%)
- `tx_demand = 1.10` (full D2 sweep, gains DeFi Summer S1D2 + NFT Mania S1D2)
**Rationale:**
- Combined FPR (τ+π) = 1.23% — objective < 1.5% achieved
- TPR 4/4 events: The Merge ✅, Shanghai ✅, DeFi Summer ✅ (S1D2), NFT Mania ✅ (S1D2)
- DeFi Summer / NFT Mania detectable via size+tx multi-signal even if sigma is stable (EIP-1559 stabilizes rho_s): **S1D2 = healthy infrastructure, elevated demand** — correct behavior
- c_s excluded (100% constant on ETH, no exploitable variance)
**Insight:** EIP-1559 stabilizes sigma_ratio → sigma alone insufficient to detect economic overloads. The size+tx combination captures real demand.
**D2 logic:** 2 of 3 dims ≥ respective threshold
**TPR:** 100% (4/4 ground truth events)
**Combined FPR:** 1.23%
**Confidence:** MEDIUM
**Deployed:** Supabase project `sdpilypwumxsyyipceew`, March 16, 2026
**Script:** BIGDATA/sweep_eth_d2.py + BIGDATA/sweep_eth_d2_full.py

---

---

## Entry #007 — March 16, 2026 — Solana τ calibration (rhythm_p90 + continuity_p10)

**Type:** Parameter calibration
**Chain:** solana (L1)
**Method:** Event-detection backtest on BigQuery `bigquery-public-data.crypto_solana_mainnet_us.Blocks`, window 2021-01-01 → 2024-01-01, 128,365 windows, Φ=800 slots (~5.3 min).
**Available BigQuery schema:** slot, block_hash, block_timestamp, height — no transaction_count.

**rhythm_p90:**
- Previous value: `1.0340` (empirical P90 — 90d production)
- New value: `1.12` (event-detection validated)
- Sweep 1.01→1.20: 1.12 = last threshold detecting all 4 outages. Beyond that: Outage May 2022 lost at 1.15.
- TPR τ: 100% (4/4 structural outages)
- FPR τ: 1.77% — slightly > 1.5% target, inherent to Solana volatility
- Latencies: Outage Sept 2021 +6.7h, Jan 2022 +1.4h, May 2022 +15.9h, Oct 2022 +12.5h

**continuity_p10:**
- Previous value: `0.9530` (P10 production — catastrophically too high)
- New value: `null` (disabled)
- Rationale: c_s follows a very wide distribution on Solana (p10=0.775, p50=0.911, p90=0.972). The skip rate is inherent to the protocol — even under normal conditions, c_s regularly drops to 77%. The value 0.9530 exceeded the natural p50 → 75% FPR. Signal non-discriminating as an alarm trigger.
- Note: rhythm_ratio=1.12 already covers complete outage cases (very low c_s → rho_ts spike → rhythm_ratio >> 1.12).

**π (demand):** ⚠️ TECHNICAL DEBT — not calibrated.
- BigQuery `crypto_solana_mainnet_us.Blocks` does not contain `transaction_count`.
- sigma/size/tx remain at initial P90 values (confidence: LOW).
- Planned source: internal data `ans_invariants_v3`, sensor `size_avg` fixed March 14, 2026.
- **Target: July 2026** (after 90 days of clean production, ~mid-June 2026 → processing July).
- Blocker: to address before any commercial approach on Solana.

**Confidence τ:** MEDIUM
**Deployed:** Supabase project `sdpilypwumxsyyipceew`, March 16, 2026
**Scripts:** BIGDATA/backtest_sol.py + BIGDATA/sweep_sol.py

---

---

## Entry #008 — March 17, 2026 — Polygon τ calibration (rhythm_p90)

**Type:** Parameter calibration
**Chain:** polygon (L1)
**Method:** Event-detection backtest on BigQuery `bigquery-public-data.crypto_polygon.blocks`,
  window 2020-10-01 → 2023-12-31, 25,906 invariants, Φ=1800 blocks (~1h).
  Early Polygon data (June–Sept 2020, gas/tx=0) excluded — clean start from 2020-10-01.
**Previous value:** `rhythm_p90 = 1.04034` (empirical P90 — arbitrary)
**New value:** `rhythm_p90 = 1.12` (event-detection validated)
**Rationale:**
- Pure FPR τ = 0.78% at threshold_s2=1.12
- Detects Reorg Storm Feb 2023 (rho_ts peak=1.2509, latency +20.1h) ✅
- Network Halt March 2021 not captured via τ (rho_ts max ~1.08 — weak signal), but captured via π ✅
- Heimdall/Bor Jan 2023: no measurable τ or π signal (consensus/finality incident, out of instrument scope)
- c_s p10=1.000 → continuity_p10 = null confirmed
**Signal:** rho_ts / EMA(rho_ts), alpha=2/11 (~10h)
**Canonical τ event:** Reorg Storm Feb 2023 — 157-block reorg, clear rho_ts disruption
**TPR τ:** 1/1 detectable τ events
**FPR τ:** 0.78%
**Confidence:** MEDIUM
**Deployed:** Supabase project `sdpilypwumxsyyipceew`, March 17, 2026
**Script:** BIGDATA/sweep_pol.py

---

## Entry #009 — March 17, 2026 — Polygon π calibration (D2 thresholds)

**Type:** Parameter calibration
**Chain:** polygon (L1)
**Method:** Full D2 sweep sigma × size × tx (7×7×7 grid + targeted balanced candidates).
  Production logic: D2 if 2 dims out of 3 (sigma, size, tx) above their threshold.
**Previous values:** `sigma_demand=1.13594`, `size_demand=1.17667`, `tx_demand=1.23474` (empirical P95)
**New values:**
- `sigma_demand = 1.50` (p99 σ=1.394 → ratio +7.6%)
- `size_demand  = 1.40` (p99 sz=1.318 → ratio +6.2%)
- `tx_demand    = 1.60` (p99 tx=1.457 → ratio +9.8%)
**Rationale:**
- Combined FPR (τ+π) = 1.20% — objective < 1.5% achieved
- TPR 3/3 events:
  - Network Halt March 2021 ✅ (S1D2 via π, σ=1.764 post-halt backlog, latency +17.0h)
  - Gas Crisis May 2021 ✅ (S1D2, σ=1.896/sz=1.945/tx=1.889, latency +3.5h from onset)
  - Reorg Storm Feb 2023 ✅ (S2D1 via τ already, latency +20.1h)
- Thresholds calibrated proportionally to the p99 of each dimension (balanced)
- Heimdall/Bor Jan 2023: removed from ground truth — consensus/finality incident without measurable on-chain signal
**Insight:** Polygon Gas Crisis (May 2021) = massive multi-dim overload (σ×2, size×2, tx×2).
  Network Halt = post-recovery demand (accumulated gas backlog). Two distinct signatures, both captured.
**D2 logic:** 2 of 3 dims ≥ respective threshold
**TPR:** 100% (3/3 events)
**Combined FPR:** 1.20%
**Confidence:** MEDIUM
**Deployed:** Supabase project `sdpilypwumxsyyipceew`, March 17, 2026
**Script:** BIGDATA/sweep_pol_d2.py

---

---

## Entry #010 — March 17, 2026 — Avalanche technical debt: no BigQuery dataset

**Type:** Technical debt — Data blocker
**Chain:** avalanche (L1)
**Action:** Attempted τ+π calibration via BigQuery backtest — blocked.
**Diagnosis:**
- `bigquery-public-data.crypto_avalanche`: Access Denied / non-existent
- `bigquery-public-data.goog_blockchain_avalanche_c_chain_us`: Access Denied / non-existent
- No public BigQuery dataset available for Avalanche C-Chain at this time.
**Current status:** Empirical P90 thresholds in production (not calibrated by event-detection)
- `rhythm_p90 = 1.0282` (P90 — LOW)
- `sigma_demand = 1.2322`, `size_demand = 1.2143`, `tx_demand = 1.2399` (P90 — LOW)
- `m1_validated = false` (median rho_s ~7% — under-saturated chain)
**Corrective action:** Backtest on production data `ans_invariants_v3`
- Sensor active since March 14, 2026, Φ=720 blocks (~24 inv/day)
- 90 days required for stabilized EMA + detectable events
- **Target: July 2026** (after mid-June 2026 → processing July)
**Scripts ready:** BIGDATA/extract_avax.sql + backtest_avax.py + sweep_avax.py + sweep_avax_d2.py
**Blocker:** To address before any commercial approach on Avalanche.
**Confidence:** LOW

---

## Entry #011 — March 17, 2026 — complexity_ratio L2 deployment (Phase A)

**Type:** New signal — production deployment
**Chains:** arbitrum, base, optimism
**Signal:** `complexity_ratio = (size_avg / tx_count_avg) / EMA(size_avg / tx_count_avg)`
**Physics:** bytes per transaction — measures average data complexity per tx, independent of volume.
**Motivation:** τ (rhythm_ratio) unusable on L2 by design (regular sequencer). σ Arbitrum dead (incompatible gas model). complexity_ratio = first L2 structural signal derivable without L1 monitoring.

**Initial baselines (March 17, 2026, first measurement):**
- arbitrum: complexity_baseline = 589.7 bytes/tx
- base: complexity_baseline = 564.5 bytes/tx
- optimism: complexity_baseline = 302.9 bytes/tx

**EMA parameters:**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30d)
- Clamp ratio: [0.01, 20.0]

**Signature domain:** `v2-l2` (new domain — incompatible with old `v1-l2`)
**DB Reset:** `DELETE FROM ans_l2_chain_signals` executed before deployment
**Baseline status:** not calibrated — initial values, 1 invariant only
**Confidence:** LOW — event-detection calibration to be done via Dune (Phase D, Q2-Q3 2026)

**Required corrective action:** none — signal operational, baselines will converge in ~10 invariants (~10h)
**Calibration blocker:** Dune historical data ARB/BASE/OP to identify reference events

---

## Entry #012 — March 17, 2026 — gas_complexity_ratio L2 deployment (Phase B)

**Type:** New signal — production deployment
**Chains:** arbitrum, base, optimism, zksync, polygon-zkevm
**Signal:** `gas_complexity_ratio = (gas_used_avg / tx_count_avg) / EMA(gas_used_avg / tx_count_avg)`
**Physics:** gas per transaction — measures average computational complexity per tx. Unlike `complexity_ratio` (bytes/tx = data), `gas_complexity_ratio` captures the actual computational load imposed on the sequencer.

**Phase B architecture:**
- `ans-core` frozen (L1 cryptographic chain preserved)
- `gas_used_avg` computed in `invarians-l2-collector`: `mean(load)` over Φ blocks of the buffer, stored as nullable column in `ans_invariants_v3`
- `load` = raw `gas_used` as provided by the RPC sensor via `L0Signal.load`
- NULL safety: if `gas_used_avg IS NULL` or `tx_count_avg = 0`, ratio = 1.0 (neutral), baseline preserved

**SQL migration:**
```sql
ALTER TABLE ans_invariants_v3
    ADD COLUMN IF NOT EXISTS gas_used_avg DOUBLE PRECISION;
ALTER TABLE ans_l2_chain_signals
    ADD COLUMN IF NOT EXISTS gas_complexity_ratio          DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_baseline       DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_baseline_slow  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_ratio_slow     DOUBLE PRECISION;
```

**Signature domain:** `v3-l2` (breaks with `v2-l2` Phase A — DB reset required)
**DB Reset:** `DELETE FROM ans_l2_chain_signals` executed before service restart

**EMA parameters:**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30d)
- Clamp ratio: [0.01, 20.0]

**Initial baselines:** to observe on first post-deployment cycle (evening March 17, 2026)
**Baseline status:** not calibrated — initial values, cold start EMA
**Confidence:** LOW — event-detection calibration to be done via Dune (Phase D, Q2-Q3 2026)

**Note Arbitrum:** `gas_used_avg` expected to be very high (Nitro model, gas limit ≈ 2^50). `rho_s` ≈ 0 confirms incompatibility of gasUsed/gasLimit ratio. `gas_complexity_ratio` measures absolute complexity (gas/tx), not relative to the limit — physically relevant signal for Arbitrum unlike sigma_ratio.

---

---

## Entry #013 — March 17, 2026 — invarians-l2-adapter deployment (Phase C)

**Type:** New service — production deployment
**Chains:** base, optimism, arbitrum
**Signals:** `publish_latency_seconds`, `calldata_bytes`, `blob_count`, `blob_usage`, `calldata_per_tx`
**Physics:** σ layer (Adaptation) — sequencer reaction to demand. L1 signals crossed with L2 data.

**Architecture:**
- Independent Rust service: `invarians-l2-adapter` (new repo)
- Source: L1 Ethereum via `ETH_L1_RPC_URL` (Alchemy mainnet)
- Method: **Option A** (approximation without batch encoding decoding)
- Scan: 25 L1 block window / 5 min, 200ms/block throttle
- Estimated CU budget: ~3.5M CU/month (115,000 CU/day)
- Target table: `ans_l2_adapter_signals` + `ans_l2_adapter_state`

**Monitored addresses:**
| Chain | Contract | Address |
|--------|---------|---------|
| Base | BatchInbox | `0xff00...8453` |
| Optimism | BatchInbox | `0xff00...0010` |
| Arbitrum | SequencerInbox | `0x1c47...82B6` |

**First observed values (March 17, 2026, 21:35 UTC, L1 blocks #24679924–#24679929):**
- `blob_usage` Base = 0.833 (5/6 blobs), Optimism = 0.833 (5/6 blobs)
- `calldata_bytes` = 655,360b (5 × 131,072b per blob)
- `publish_latency` ≈ 4,830–4,878s (~80min) — Option A approximation artifact
- Base + Optimism submit in the same L1 block (shared OP Stack infrastructure)
- Arbitrum: no batch in the initial window (reduced on-chain frequency due to AnyTrust)

**Note on publish_latency:** the ~80min value reflects the gap between `t_L1_block` and the `last_timestamp` of the most recent L2 invariant (~1h window). This is a relative measure, adapted to the EMA. The absolute value is not directly interpretable — only variations vs baseline are significant.

**Note on blob_usage = 0.833:** high signal on first reading. May indicate heavy blob market usage this evening, or be the normal baseline for Base/OP. EMA convergence needed (~10 cycles = ~50 min of L1 scan) before interpretation.

**EMA parameters:** to be defined during Dune calibration (Phase D). No EMA implemented in Phase C — signals are stored raw. EMA will be added in an enriched `invarians-l2-chain` service or in a new `invarians-l2-adapter-chain`.

**Baseline status:** not calibrated — first data, cold start
**Confidence:** LOW — Dune event-detection calibration pending (Phase D, Q2-Q3 2026)

---

---

## Entry #014 — March 22, 2026 — L2 threshold calibration v2 (ARB · BASE · OP)

**Type:** Parameter calibration — first statistical L2 calibration
**Chains:** arbitrum, base, optimism
**Method:** Statistical P90-P95 calibration on 7 days of production (March 15–22, 2026).
  No event-based backtest at this stage — insufficient data (n≈105-126/chain).
  Event-based validation planned Phase D (Q2-Q3 2026 on Dune data).

**Data source:**
- `ans_l2_rollup_signals`: n=126/chain (τ — rhythm_ratio)
- `ans_l2_chain_signals`: n=91-105/chain (π — sigma_ratio)

**Per-chain diagnosis:**

| Chain | τ (rhythm_ratio) | π (sigma_ratio) | Discriminating signal |
|--------|-----------------|-----------------|---------------------|
| Arbitrum | DEAD — range 0.9278-1.0135, p95=1.0018 | DEAD — constant 1.0000 | None. Always S1D1. |
| Base | DEAD — constant 1.0000 | ACTIVE — p90=1.0866, p95=1.1444, max=1.3068 | π only |
| Optimism | DEAD — constant 1.0000 | ACTIVE — p90=1.0500, p95=1.0749, max=1.1368 | π only |

**Note on τ L2:** τ (rhythm_ratio) is dead by design on Base and Optimism — the sequencer imposes
a perfectly regular cadence (fixed 2s block time). Confirmed empirically: all observed
values = 1.0000 exactly. Consistent with the architectural pivot of March 17, 2026.

**Note on Arbitrum cold-start EMA (March 16, 2026, 00:03 → 07:44):** Post-calibration analysis of
126 observations reveals 7 consecutive entries with τ < 0.97 (min=0.9278) only during
this 7h window. Cause: EMA not converged after startup (α=0.1818, N≈10 — convergence
~10 observations = ~10h). Initial baseline was too high → τ < 1.0 during convergence.
This is not a structural event. Operational impact: **zero** — τ < 1.0 never crosses
the S2 threshold (1.15). The cold start produces low τ values (system perceived as faster than baseline),
never S2 false positives. After March 16 08:00: τ stable in the 0.998–1.014 band.

**Note on π Arbitrum:** sigma_ratio constant = 1.0000 over 91 observations. Confirmed: Arbitrum Nitro
gasLimit ≈ 2^50 → rho_s ≈ 0 systematically → non-discriminating signal. Arbitrum will
always be S1D1 until complexity_ratio calibration (Phase A — ROADMAP 1-bis).

**Previous values (v1 — provisional since March 15, 2026):**
- `TAU_THRESHOLD = 1.15` (global)
- `PI_THRESHOLD  = 1.20` (global)

**New values (v2 — per chain):**

| Chain | τ (was 1.15) | π (was 1.20) | Rationale |
|--------|---------------|---------------|--------------|
| Arbitrum | 1.15 (dormant) | 1.20 (dormant) | Dead signals — thresholds have no effect |
| Base | 1.05 (τ dead) | **1.10** | Between p90 (1.0866) and p95 (1.1444) — ~p92 |
| Optimism | 1.05 (τ dead) | **1.06** | Between p90 (1.0500) and p95 (1.0749) — ~p93 |

**Distribution validation (query 1C with v2 thresholds):**

| Chain | S1D1 | S1D2 | Verdict |
|--------|------|------|---------|
| Arbitrum | 100% | 0% | Expected — dead signals |
| Base | 92.4% | 7.6% | ✅ Within target 3-8% |
| Optimism | 92.4% | 7.6% | ✅ Within target 3-8% |

**Modified files:**
- `invarians-oracle/supabase/functions/attestation/index.ts` — `L2_THRESHOLDS` Record per chain · `classifyL2State` chain-aware · calibration version `"v2"`
- `invarians-oracle/supabase/migration_l2_states.sql` — CASE per chain in `v_l2_states`

**Deployments:**
- Oracle Edge Function redeployed: `supabase functions deploy attestation` ✅
- View `v_l2_states` recreated in production (Supabase SQL Editor) ✅

**Confidence:** MEDIUM (statistical over 7d) — no event-based backtest
**Next L2 calibration:** Phase D, Q2-Q3 2026 on Dune historical data ARB/BASE/OP
**Blocker:** event-based calibration required before commercial approach on L2

---

---

## Entry #015 — March 22, 2026 — invarians-bridge-collector deployment (Phase 2A)

**Type:** New service — production deployment
**Chains:** arbitrum, base, optimism
**Signal:** `last_batch_age_seconds` — time since the last batch published on L1
**Physics:** sequencer → L1 batch posting liveness. Detects absences (interrupted flow), not presences.

**Architecture:**
- Independent Rust service: `BRIDGE/invarians-bridge-collector/`
- Source: L1 Ethereum mainnet via `ETH_L1_RPC_URL` (same Alchemy key as invarians-l2-adapter)
- Method: `eth_getLogs` on BatchDelivered events (Arbitrum) + BatchInbox txs (Base/OP)
- Polling: 10 min
- Tables created: `ans_bridge_signals` + `bridge_collector_state`

**First observed values (March 22–23, 2026, 131 cycles/chain):**
- arbitrum: avg=57s, max=192s
- base:     avg=23s, max=108s
- optimism: avg=132s, max=360s

**Status:** Phase 2A ✅ active — Phase 2B in progress (30d observation, ~April 22, 2026)
**Next step:** Phase 2B — P90 calibration `threshold_rupture` + `threshold_P90` per chain
**BS1/BS2 confidence:** not applicable — classifier not deployed (Phase 2C, post-calibration)
**Oracle impact:** `bridge_state` remains hardcoded BS1 in `attestation/index.ts` until Phase 2C

---

## Entry #016 — April 16, 2026 — 30d L2 distribution analysis + BASE/OP threshold recalibration

**Type:** Distribution analysis + Parameter recalibration
**Chains:** base, optimism (arbitrum not affected — dormant signals)
**Trigger:** H2 condition lifted — 30d post-EMA reset BASE/OP (2026-03-16 → 2026-04-16)

---

**Validation query executed (April 16, 2026):**

```sql
SELECT chain, COUNT(*) as n_samples,
  ROUND(100.0 * SUM(CASE WHEN sigma_ratio >= CASE WHEN chain='base' THEN 1.10
    WHEN chain='optimism' THEN 1.06 ELSE 1.20 END THEN 1 ELSE 0 END) / COUNT(*), 2) as percent_d2,
  ROUND(AVG(sigma_ratio)::numeric, 4) as avg_sigma_ratio,
  ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY sigma_ratio)::numeric, 4) as p90,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY sigma_ratio)::numeric, 4) as p95
FROM ans_l2_chain_signals
WHERE computed_at >= '2026-03-22'::timestamptz
GROUP BY chain ORDER BY chain;
```

**Results with v2 thresholds (calibration_log #014):**

| Chain | n | D2% | avg_sigma | p90 | p95 |
|--------|---|-----|-----------|-----|-----|
| arbitrum | 555 | 0.00% | 1.0000 | 1.0000 | 1.0000 |
| base | 558 | 12.37% | 1.0007 | 1.1127 | 1.1671 |
| optimism | 558 | 11.29% | 1.0010 | 1.0675 | 1.1018 |

**Diagnosis:**
- v2 thresholds (BASE=1.10, OP=1.06) produce D2%=12-11% — outside target 3-8%.
- Cause: calibration #014 performed on 7 days (calm window). 30d distribution reveals higher real activity.
- **Inconsistency detected with L1:** L1 FPR = 1.20-1.23% (ETH, POL) via 2-of-3 multi-signal logic. L2 uses sigma alone (mono-signal) with the same numerical threshold values → 10x higher FPR. Thresholds are not comparable cross-layer without adjustment.

**Extended percentile query (p97-p99):**

| Chain | p97 | p98 | p99 |
|--------|-----|-----|-----|
| base | 1.1933 | 1.2441 | 1.3110 |
| optimism | 1.1216 | 1.1415 | 1.2273 |

**Recalibration logic:**

L1 targets FPR ~1.2% with 2-of-3 logic (multi-signal consensus).
L2 uses sigma alone (mono-signal, more sensitive) — for equivalent FPR, the threshold must be positioned higher in the distribution.
Selected target: **~3% D2 (P97 over 30d)** — consistent with L1 FPR accounting for mono/multi-signal asymmetry.

**Proposed new values (v3):**

| Chain | v2 threshold | v3 threshold | Percentile | Estimated D2% | Rationale |
|--------|----------|----------|------------|------------|---------------|
| BASE | 1.10 | **1.20** | ~p97 (1.1933) | ~3% | Round number, just above p97 |
| OP | 1.06 | **1.12** | p97 (1.1216) | ~3% | Exactly p97 |
| ARB | 1.20 | 1.20 (unchanged) | dormant | ~0% | sigma_ratio constant 1.0000 — ARB gasLimit incompatible |

**Status:** ✅ Deployed — April 16, 2026 · `supabase functions deploy attestation` · project sdpilypwumxsyyipceew
**Confidence:** MEDIUM — statistical P97 calibration over 30d. No event-based validation.
**Next step:** Phase D (Q2-Q3 2026) — Dune backtest on historical L2 events ARB/BASE/OP to validate TPR/FPR on real incidents.
**Blocker:** event-based validation required before commercial approach on L2 (unchanged since #014).

---

*Log maintained and updated with each intervention on calibration baselines or parameters.*
*Format: immutable. No modification of past entries — additions at end of file only.*
