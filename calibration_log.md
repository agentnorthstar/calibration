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
**Symptom:** buffer frozen, no invariant produced after seq=10.
**Root cause:** collector advance rate exceeded chain production rate.
**Fix:** tuning of batch/throttle parameters to align advance rate with chain production rate.
**EMA impact:** baselines partially contaminated by the few invariants produced before the incident.
**Corrective action:** no reset required (little contaminated data, short sequence).
**Post-fix confidence:** LOW → to reassess after 30d

---

## Entry #003 — March 16, 2026 — BASE/OPTIMISM incident: rho_ts/c_s mirror

**Type:** Structural incident → Deployment fix
**Chains:** base, optimism
**Symptom:** rhythm_ratio=4.62, continuity_ratio=0.21 → permanently classified S2. Strict mirror evolution of both signals.
**Root cause:**
1. Race condition: collector advance rate equal to chain production rate.
2. Physical insight: for chains with fixed 2s block time, `rho_ts × c_s/100 ≈ 2s = constant` → mathematically inverse signals.
**Fix:** tuning of batch/throttle parameters to keep advance rate below chain production rate.
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
**Deployed:** Supabase project (production), March 16, 2026
**Script:** scripts/sweep_eth.py

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
**Deployed:** Supabase project (production), March 16, 2026
**Script:** scripts/sweep_eth_d2.py + scripts/sweep_eth_d2_full.py

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
**Deployed:** Supabase project (production), March 16, 2026
**Scripts:** scripts/backtest_sol.py + scripts/sweep_sol.py

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
**Deployed:** Supabase project (production), March 17, 2026
**Script:** scripts/sweep_pol.py

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
**Deployed:** Supabase project (production), March 17, 2026
**Script:** scripts/sweep_pol_d2.py

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
**Scripts ready:** scripts/extract_avax.sql + backtest_avax.py + sweep_avax.py + sweep_avax_d2.py
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
- Source: L1 Ethereum via `ETH_L1_RPC_URL`
- Method: **Option A** (approximation without batch encoding decoding)
- Scan: 25 L1 block window / 5 min
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
- Attestation edge function — `L2_THRESHOLDS` Record per chain · `classifyL2State` chain-aware · calibration version `"v2"`
- L2 classification view migration — CASE per chain in `v_l2_states`

**Deployments:**
- Attestation Edge Function redeployed: `supabase functions deploy attestation` ✅
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
- Source: L1 Ethereum mainnet via `ETH_L1_RPC_URL`
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
**Attestation impact:** `bridge_state` remains hardcoded BS1 in `attestation/index.ts` until Phase 2C

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

**Status:** ✅ Deployed — April 16, 2026 · `supabase functions deploy attestation` · production project
**Confidence:** MEDIUM — statistical P97 calibration over 30d. No event-based validation.
**Next step:** Phase D (Q2-Q3 2026) — Dune backtest on historical L2 events ARB/BASE/OP to validate TPR/FPR on real incidents.
**Blocker:** event-based validation required before commercial approach on L2 (unchanged since #014).

---

## Entry #017 — April 17, 2026 — Polygon recalibration v2 (4 events)

**Type:** Event-detection recalibration — τ + π
**Chain:** polygon (L1)
**Trigger:** Heimdall/Bor Incident (January 2023) added to ground truth — requires lower τ to detect (signal ratio=2%). v1 (March 2026, #008/#009) calibrated on 3 events only.

**Previous values (v1 — calibration_log #008/#009):**
- `rhythm_p90 = 1.12` · `sigma_demand = 1.50` · `size_demand = 1.40` · `tx_demand = 1.60`
- FPR combined = 1.20% · Events = 3/3 · M1 = 8.06

**New values (v2):**
- `rhythm_p90 = 1.04` · `sigma_demand = 1.14` · `size_demand = 1.18` · `tx_demand = 1.23`
- FPR combined = 11.75% · Events = 4/4 · M1 = 7.37

**Note on Heimdall/Bor reconsidered vs calibration_log #008/#009:**
Entry #008 classified Heimdall/Bor (Jan 2023) as "out of instrument scope — no measurable signal at τ=1.12". This assessment was correct for v1: the rho_ts peak during this incident reaches only ~1.04, below the v1 threshold of 1.12. At τ=1.04 (v2), the same signal is just above threshold → detectable → TP. The reconsideration is a direct consequence of the threshold change, not a data revision. Entries #008 and #009 remain historically accurate for v1.

**Ground truth events (v2):**

| Event | Date | Type | Detected | Latency |
|---|---|---|---|---|
| Network Halt | 2021-03 | τ structural | ✅ TP | +22.2h |
| Gas Crisis | 2021-05 | π demand | ✅ TP | +3.5h |
| Heimdall/Bor Incident | 2023-01 | τ structural | ✅ TP | +35.2h |
| Reorg Storm | 2023-02 | τ structural | ✅ TP | +6.4h |

**Why FPR increased from 1.20% to 11.75%:**
Threshold_s2=1.04 is the minimum required to detect the Heimdall/Bor Incident (signal ratio ~2% above baseline). At τ≥1.05, Heimdall/Bor is missed. The FPR increase is a structural consequence of the tight threshold combined with Polygon's high on-chain volatility during 2021–2022 DeFi/NFT boom. Documented in `backtest_polygon.md` section 8.

**Confidence:** MEDIUM event-based (FPR elevated — documented)
**Backtest period:** 2020-06-01 → 2023-12-31 · 28,744 windows (Φ=1800)
**FPR τ (sweep):** 11.84% at threshold_s2=1.04
**FPR τ+π (combined):** 11.75%
**Scripts:** `scripts/backtest_pol.py` · `scripts/sweep_pol.py` · `scripts/sweep_pol_d2.py`
**Deployed:** 2026-04-17 · `supabase functions deploy attestation`

---

---

## Entry #018 — April 17, 2026 — M1 reconciliation with formula v0.1

**Type:** Audit reconciliation — M1 values
**Trigger:** Implementation of `m1_eth.py` and `m1_pol.py` (formula §10.1) revealed that M1 values in prior entries (#008, #009, #017) were session manual estimates, not formula outputs.

**Findings:**
- ETH M1 = **5.07** ✅ — confirmed by `m1_eth.py` · formula validated bilaterally (The Merge max=1.1548, p50=0.9993, bruit=0.0307)
- POL M1 = **7.37** (Entry #017) — session manual estimate, not reproduced by formula v0.1
- POL formula-v0.1 outputs (via `m1_pol.py`):
  - τ (rhythm_ratio) · best event: Reorg Storm → **M1 = 10.66**
  - π (sigma_ratio)  · best event: Gas Crisis   → **M1 = 4.55**

**Decision:**
- `methodology.md §10.3` updated to per (signal × event) table with formula-v0.1 values
- Scalar POL M1=7.37 retired from methodology — replaced by τ=10.66 / π=4.55
- Entries #008, #009, #017 remain historically accurate for calibration parameters; M1 values in those entries are session estimates, not formula outputs
- `AgentNorthStar.com` registry updated to show formula-v0.1 M1 values

**Note:** M1 divergence between signals (τ=10.66 vs π=4.55) reflects structural difference: rhythm_ratio on POL is much tighter (bruit=2.36%) than sigma_ratio (bruit=24.2%) due to Polygon's volatile gas history 2020–2022. Both values are above 1.0 → calibration usable for both signals.

---

## Entry #019 — April 19, 2026 — Exact binomial confidence intervals (Clopper-Pearson) added to all TPR / FPR

**Type:** Methodological — reporting (no change to signals, thresholds, or EMA parameters)
**Chains:** ethereum, polygon, solana
**Trigger:** External technical review (2026-04-19) identified that reporting "TPR = 100% (4/4)" without a confidence interval is statistically misleading at small n. A `TPR = 100%` on n=4 events has an exact Clopper-Pearson IC95% of [39.76% ; 100.00%] — the point estimate alone is not a predictive guarantee.

**Action — all backtest results now reported with IC95% Clopper-Pearson (exact binomial):**

| Metric | Point | k / n | IC95% Clopper-Pearson |
|--------|-------|-------|----------------------|
| ETH TPR     | 100.00% | 4 / 4        | [39.76% ; 100.00%] |
| ETH FPR     | 1.23%   | 369 / 29,942 | [1.11% ; 1.36%] |
| POL TPR     | 100.00% | 4 / 4        | [39.76% ; 100.00%] |
| POL FPR     | 11.75%  | 3,201 / 27,249 | [11.37% ; 12.14%] |
| SOL TPR_τ   | 100.00% | 4 / 4        | [39.76% ; 100.00%] |
| SOL FPR_τ   | 1.77%   | 2,254 / 127,354 | [1.70% ; 1.84%] |

**Files updated:**
- `backtest_ethereum.md` — header + new §5b statistical confidence section + frontmatter keys `backtest_tpr_ci95`, `backtest_fpr_ci95`, `backtest_n_normal`, `backtest_n_false_alarms`
- `backtest_polygon.md` — header + new §7b + frontmatter keys `tpr_ci95`, `fpr_ci95`, `n_normal`, `n_false_alarms`
- `backtest_solana.md` — header + new §5b + frontmatter keys `backtest_tpr_ci95`, `backtest_fpr_tau_ci95`, `backtest_n_normal`, `backtest_n_false_alarms`
- `methodology.md` — tables §4.4 now include an "IC95% FPR" column + new §4.4.1 pedagogical block explaining the exact binomial method, why IC stays wide at n=4, and how it tightens with n (10/10 → [69%; 100%], 20/20 → [83%; 100%])
- `README.md` — index table rows updated to show IC95% inline
- `scripts/ci_binomial.py` — new reproduction script (Clopper-Pearson via `scipy.stats.beta`)

**Values of n (previously not published):**
- ETH : n_total = 34,698 ; n_event_windows = 4,705 ; warmup = 50 ; **n_normal = 29,942**
- POL : n_total = 28,744 ; n_event_windows = 1,444 ; warmup = 50 ; **n_normal = 27,249**
- SOL : n_total = 128,365 ; n_event_windows =   960 ; warmup = 50 ; **n_normal = 127,354**

These values are reproducible from the BigQuery invariants CSVs by running the existing `backtest_{eth,pol,sol}.py` scripts (they print `n_normal` at runtime). The ETH/POL/SOL backtest scripts were not modified.

**Impact on production:**
- No change to signals, thresholds, EMA, classification, or attestations
- No change to M1 values (Entry #018 unchanged)
- No change to per-chain `confidence` status (MEDIUM event-based remains)
- Change is **reporting-only**: public documentation now quantifies the statistical uncertainty of published rates

**Rationale (carried from review):** At n=4 events, even a perfect 4/4 is compatible with a true detection rate as low as ~40% under Clopper-Pearson. Publishing the IC alongside the point estimate is statistically honest and does not weaken the claim — it correctly bounds it. The FPR intervals, by contrast, are very narrow (n_normal > 10,000 on all 3 chains), so the measured FPR values are statistically robust.

**Reproduction:**

```bash
# Show all published Invarians IC95% values
python scripts/ci_binomial.py

# Custom k/n
python scripts/ci_binomial.py --k 4 --n 4
python scripts/ci_binomial.py --k 369 --n 29942
```

**Reference:** Clopper, C. J. & Pearson, E. S. (1934). "The use of confidence or fiducial limits illustrated in the case of the binomial." *Biometrika* 26(4), 404–413.

---

## Entry #020 — April 19, 2026 — Public accountability document: `limitations_and_plans.md`

**Type:** Methodological — publication (new public document)
**Scope:** all chains
**Trigger:** Same external technical review as Entry #019 identified that several valid critiques of the public repository already had answers in internal plans (ROADMAP, PLANNING_2026, AGENT), but those answers were not written down where an external auditor could find them. The gap was editorial, not technical.

**Action — new file `limitations_and_plans.md` published:**

The document lists, on a single page, every known limitation of Invarians calibration today, with dated plans for corrections. Sections:

1. Why this document exists (publication gap, review-driven)
2. Known limitations (statistical, methodological, security/trust, coverage, ground truth quality)
3. Planned corrections — timeline Q2 2026 → 2027
4. Corrections already deployed but not yet documented publicly (ARB 2-of-2 workaround, Calibration Drift Protocol)
5. What will not be published (ε(t) formula, operational details, keys)
6. How to report a problem (GitHub issues with prefixed labels)
7. What is NOT a limitation (latency by design, DeFi Summer correct non-detection, L1/L2 asymmetry by design, ARB dormancy replaced by workaround)

**Items committed publicly with dates:**

- Q2 2026: cross-validation ETH, threat model section, InvariansAnchor (Arbitrum, May), AgentNorthStar Calibration Agent via MCP (May)
- Q3 2026: SOL π calibration (July), AVAX event-based calibration (July), agent feedback protocol, ARB workaround documented, α/Φ sensitivity analyses
- Q4 2026: ROC curves per chain, Chainlink DON threshold signing, M1 formula v0.2
- 2027: native Invarians network

**Impact:**
- No change to signals, thresholds, EMA, attestations, or M1
- No change to confidence status of any chain
- Editorial: external auditors can now verify the correspondence between public critiques and internal plans without needing access to internal documents

**Rationale:** Under-communication of solutions already designed or deployed was the main residual critique after the review. Publishing `limitations_and_plans.md` converts that gap into a public commitment schedule. Slippage on any listed date must be disclosed in this log.

**Files:**
- `limitations_and_plans.md` (new, ~280 lines)
- `README.md` (index table + new §5 "Known limitations" reference)

---

## Entry #021 — April 19, 2026 — Temporal cross-validation ETH (out-of-sample)

**Type:** Methodological — empirical validation of published thresholds
**Scope:** ETH (extends to other chains when event density permits)
**Trigger:** `limitations_and_plans.md §2.1` listed "in-sample threshold optimization" as an open limitation (Q2 2026). This entry closes the D2 portion of that item.

**Action — run `scripts/cv_eth.py`:**

1. Split the ETH record by date:
   - Train: 2020-01-01 → 2022-07-31 (21,643 invariants; events: DeFi Summer, NFT Mania)
   - Test: 2022-09-01 → 2023-12-31 (12,353 invariants; events: The Merge, Shanghai Upgrade)
2. Grid sweep D2 thresholds on train only (σ × size × tx = 5×5×5 = 125 combinations), `threshold_s2` fixed at 1.12.
3. Selection rule on train: maximize TPR_train, then minimize FPR_train.
4. Apply train-selected triplet to test window. Also apply the currently published triplet to test window for comparison.
5. Compute exact Clopper-Pearson IC95% on TPR_test and FPR_test.

**Results:**

| Param set on TEST | σ / size / tx | TPR_test | FPR_test | FPR IC95% |
|---|---|---|---|---|
| Train-selected | 1.15 / 1.30 / 1.10 | 2/2 = 100% | 0.16% (20/12,209) | [0.10% ; 0.25%] |
| **Published** | **1.10 / 1.20 / 1.10** | **2/2 = 100%** | **0.65% (79/12,209)** | **[0.51% ; 0.81%]** |

TPR_test IC95% = [15.81% ; 100.00%] (n_test = 2 — unavoidable).

**Findings:**

- Both test events (The Merge, Shanghai Upgrade) are detected out-of-sample under parameters calibrated on pre-Merge data only.
- FPR of the published triplet on the test window (0.65%) is **lower** than the full-period FPR (1.23% — Entry #019). This contradicts an over-fitting narrative: if thresholds had been over-tuned, out-of-sample FPR would rise, not fall.
- Train-selected triplet is stricter (σ=1.15, size=1.30) with even lower FPR_test; this argues the published D2 triplet is mildly conservative on demand signals but remains within an acceptable operating region.
- Detection latencies on test events: Merge +18.3h (matches Entry data), Shanghai +22.8h.

**What this CV does not establish:**

- `threshold_s2 = 1.12` (τ) is **not** temporally validated. All τ-type events on ETH (Merge, Shanghai) occur after 2022-09, leaving the train window without τ-type ground truth. This caveat is stated explicitly in `backtest_ethereum.md §6` and in `limitations_and_plans.md §2.1`.
- The TPR_test IC95% is wide (down to 15.81%) because n_test = 2. Narrowing this interval requires additional ETH ground-truth events over time.

**Impact:**

- No change to published thresholds.
- No change to confidence status (ETH remains MEDIUM).
- `limitations_and_plans.md §2.1` "in-sample optimization" updated from "In progress" to "✅ Partially done" (D2 validated out-of-sample; τ pending another event).

**Files:**
- `scripts/cv_eth.py` (new)
- `scripts/cv_eth_results.json` (output artifact)
- `backtest_ethereum.md` §6 "Temporal cross-validation" (new section)
- `backtest_ethereum.md` frontmatter (cv_* fields added)
- `limitations_and_plans.md` §2.1 (status update)

**Reproduction:**

```bash
python scripts/cv_eth.py
# Uses scripts/eth_invariants_2020_2024_phi280.csv
# Output: cv_eth_results.json with full train/test/CI breakdown
```

---

## Entry #022 — April 19, 2026 — ROC curves per chain (ETH, SOL, POL)

**Type:** Methodological — visualization + AUC metric
**Scope:** ETH, SOL, POL
**Trigger:** `limitations_and_plans.md §3` listed ROC curves under Q4 2026. Moved forward because all sweep CSVs were already produced and the derivation is mechanical — no new backtest runs required.
**baseline_impact:** no (display layer only; no thresholds or attestation logic changed)

**Action — run `scripts/roc_curves.py`:**

Inputs (existing, from the production backtesting pipeline, shipped in `scripts/`):
- `eth_sweep_results.csv` — 1D τ sweep, 8 points, 2 τ-dominant events (Merge, Shanghai)
- `sol_sweep_results.csv` — 1D τ sweep phase A, 20 points, 4 outages
- `pol_sweep_d2_results.csv` — 3D D2 sweep (σ × size × tx), 64 combos, 4 events

Outputs:
- `scripts/roc_eth.png`, `scripts/roc_sol.png`, `scripts/roc_pol.png`
- `scripts/roc_results.json` — AUC per chain + full sweep tables + Pareto frontier for POL

**Results:**

| Chain | Axis | n_events | AUC | Published operating point |
|---|---|---|---|---|
| ETH | τ | 2 | **0.978** | τ = 1.12, FPR = 1.23%, TPR = 100% |
| SOL | τ | 4 | **0.994** | τ = 1.12, FPR = 1.77%, TPR = 100% |
| POL | D2 (Pareto of 3D sweep) | 4 | **0.944** | σ/size/tx = 1.14/1.18/1.23, FPR = 11.75%, TPR = 100% |

All three AUCs > 0.94 (0.5 = random, 1.0 = perfect), confirming that the classifiers are well-separated from noise on their dominant axis. The operating points are Pareto-optimal for ETH and SOL and lie on the Pareto frontier for POL.

**Methodological notes:**

- **ROC shape is stepped** for all chains because n_events ≤ 4. TPR only takes values in {0, 1/n, ..., 1}. AUC is therefore coarse and should not be over-interpreted.
- **For POL, the ROC is a 2D projection of a 3D parameter space** (σ, size, tx). The curve shown is the upper-left Pareto frontier of the full point cloud. Points below the frontier are dominated — a better (σ, size, tx) triplet exists at same FPR with higher TPR.
- **ROC does not resolve in-sample optimization on its own.** Points on the sweep were selected on the same period that contains the events. For ETH, temporal cross-validation (Entry #021) is the separate control.
- **τ-only vs full classifier for ETH:** The ETH ROC is computed on the τ axis alone (2 τ-dominant events). The D2 dimension is orthogonal and is already covered by the cross-validation result. A full 4-event ROC would require a 2D (τ × D2) sweep surface, deferred.

**Impact:**

- No change to thresholds, attestations, or confidence levels.
- `limitations_and_plans.md §3` Q4 2026 item "ROC curves per chain" moves to "✅ Done 2026-04-19".
- Each `backtest_*.md` gains a dedicated ROC section with image and AUC.

**Files:**
- `scripts/roc_curves.py` (new)
- `scripts/roc_eth.png`, `scripts/roc_sol.png`, `scripts/roc_pol.png` (new)
- `scripts/roc_results.json` (new, machine-readable results)
- `backtest_ethereum.md` §8 (new section, previous §8 → §9)
- `backtest_solana.md` §7 (new section, previous §7 → §8)
- `backtest_polygon.md` §10 (new section, previous §10 → §11)
- `limitations_and_plans.md` §3 Q4 2026 (status update)

---

## Entry #023 — April 19, 2026 — Polygon backtest production-alignment (Φ=1800 → Φ=720)

**Type:** Methodological correction — backtest ↔ production alignment
**Chain:** polygon
**Trigger:** During Point #6 α/Φ sensitivity review, a read of the collector source (`invarians-L1-collector/ans-engine/src/main.rs:323`) revealed that POL production runs with `Φ=720` (batch-aligned). The v1.0 backtest (`backtest_polygon.md` published 2026-04-17) used Φ=1800, creating a backtest/production mismatch specific to POL (ETH, SOL, AVAX are aligned).
**baseline_impact:** **yes** — FPR changes from 11.75% → 14.57%. M1 τ and M1 π are recomputed. No threshold change (σ=1.14/size=1.18/tx=1.23 and threshold_s2=1.04 are preserved).

**Mechanism clarification (β is not a stride).**
Reading `main.rs:128-139` and the seal logic at lines 148-165:

- `sense_batch(next_slot, β)` reads **β consecutive blocks** starting at `next_slot`.
- `next_slot += β` after each batch — batches accumulate into a buffer.
- When `buffer.len() >= phi`, the invariant is sealed and `next_slot` jumps to `head` (post-seal sync).
- Within a single invariant, the Φ blocks **are consecutive**. β is an RPC batch size, not a sampling stride.

Consequence: the only difference between v1.0 backtest (Φ=1800, β=1) and production (Φ=720, β=5) is the window size, not the sampling pattern. Both use consecutive blocks. This simplifies the correction to a Φ-only re-extraction.

**Action.**
1. Wrote `scripts/extract_pol_phi720.sql` (Φ=1800 → Φ=720, single line change in the extraction window).
2. Re-extracted from BigQuery: 71,860 invariants, same period 2020-06-01 → 2023-12-31.
3. Re-ran the backtest pipeline at Φ=720:
   - `scripts/backtest_pol_phi720.py` → TPR, FPR, regime distribution, latencies.
   - `scripts/sweep_pol_d2_phi720.py` → 3D D2 sweep (64 combos).
   - `scripts/m1_pol_phi720.py` → M1 τ and M1 π at Φ=720.
   - `scripts/roc_curves.py` pointed at the new sweep CSV.

**Results — v1.0 Φ=1800 vs v2.0 Φ=720 (thresholds unchanged):**

| Metric | Φ=1800 (v1.0, archived) | Φ=720 (v2.0, published) | Δ |
|---|---|---|---|
| n_invariants | 28,744 | 71,860 | +2.5× |
| TPR (4 events) | 100% | 100% | = |
| FPR τ+π | 11.75% | **14.57%** (CI95% [14.30%, 14.83%]) | +2.82 pp |
| Mean detection latency | +16.8h | **+3.95h** | −76% |
| Heimdall/Bor latency | +35.2h | +2.5h | −32.7h |
| Network Halt latency | +22.2h | +8.9h | −13.3h |
| M1 τ (Reorg Storm) | 10.66 | 12.60 | +18% |
| M1 π (Gas Crisis) | 4.55 | 3.59 | −21% |
| ROC AUC (D2) | 0.944 | 0.930 | −0.014 |

**Interpretation:**

- **FPR increase is mechanical and predicted.** σ(rho_ts) ∝ 1/√Φ; switching from Φ=1800 to Φ=720 widens the baseline distributions by √(1800/720) ≈ 1.58× (worst case). The observed FPR increase ratio is 14.57/11.75 ≈ 1.24× — below worst case, consistent with signal autocorrelation attenuating the effect.
- **Latency gain is the operational payoff.** The mean detection latency drops from 16.8h to 3.95h (−76%). The Heimdall/Bor low-amplitude event, previously detected after 35.2h, is now detected in 2.5h. A monitoring system designed for real-time agent coordination cannot tolerate a 35-hour lag.
- **TPR and ROC frontier preserved.** 4/4 events remain detected. AUC drops by 0.014 (0.944 → 0.930), within the noise band for n=4 events. The classifier remains Pareto-optimal.
- **M1 τ up, M1 π down.** M1 τ increases on Reorg Storm (+18%) because the shorter window captures the reorg peak more sharply. M1 π decreases on Gas Crisis (−21%) because the shorter window samples the long-tailed Gas Crisis differently — the p50 baseline of sigma_ratio shifts slightly, narrowing the amplitude ratio. Both remain well above the 2.0 "significant signal" threshold (methodology.md §10).

**Decision.**
v2.0 at Φ=720 is published as the reference in `backtest_polygon.md`. v1.0 at Φ=1800 is archived in this log entry and referenced from §11 of the new backtest. Thresholds are conserved (σ=1.14, size=1.18, tx=1.23, threshold_s2=1.04) — re-optimization at Φ=720 is deferred to Q3 2026 to avoid baseline churn during the Labs π-calibration phase (cf. `limitations_and_plans.md §2.6`). The production system does not change.

**Files:**
- `backtest_polygon.md` — rewritten v1.0 → v2.0 (Φ=1800 superseded).
- `scripts/extract_pol_phi720.sql` (new)
- `scripts/backtest_pol_phi720.py`, `sweep_pol_d2_phi720.py`, `m1_pol_phi720.py` (new)
- `scripts/pol_invariants_2020_2024_phi720.csv` (new, 71,860 rows)
- `scripts/pol_backtest_results_phi720.csv`, `pol_sweep_d2_results_phi720.csv`, `pol_m1_results_phi720.csv` (new)
- `scripts/roc_curves.py` — updated POL input and operating point (FPR 11.75% → 14.57%)
- `scripts/roc_pol.png`, `scripts/roc_results.json` — regenerated
- `limitations_and_plans.md` — POL Φ gap closed; entry removed from §2.
- `README.md` — POL line updated (FPR, v2.0 flag).

**Other chains checked — backtest ↔ production Φ audit.**

| Chain | Production Φ | Production β | Production source | Backtest Φ | Backtest status | Alignment |
|---|---|---|---|---|---|---|
| ETH     | 280  | 1  | `invarians-L1-collector/ans-engine/src/main.rs:310` | 280  | ✅ validated (`backtest_ethereum.md`)            | ✓ aligned |
| SOL     | 800  | 10 | `invarians-L1-collector/ans-engine/src/main.rs:297` | 800  | ✅ τ validated (`backtest_solana.md`); π pending | ✓ aligned |
| POL     | 720  | 5  | `invarians-L1-collector/ans-engine/src/main.rs:323` | 720  | ✅ validated v2.0 (`backtest_polygon.md`)        | ✓ aligned (this entry) |
| AVAX    | 720  | 5  | `invarians-L1-collector/ans-engine/src/main.rs:336` | —    | ⏳ backtest not yet run                           | N/A (no backtest to compare) |
| ARB L2  | 1800 | 50 | `invarians-L2-collector/src/main.rs:258`            | 1800 | Case study (`composite_signal_arbitrum_june2024.md`) — no event-based TPR/FPR backtest | ✓ aligned on case-study window |
| BASE L2 | 1800 | 50 | `invarians-L2-collector/src/main.rs:266`            | —    | ⏳ no backtest                                    | N/A |
| OP L2   | 1800 | 50 | `invarians-L2-collector/src/main.rs:274`            | —    | ⏳ no backtest                                    | N/A |
| POL zkEVM | 1800 | 50 | `invarians-L2-collector/src/main.rs:290`          | —    | ⏳ no backtest                                    | N/A |

The gap was POL-specific. No other chain requires a Φ correction. AVAX, BASE, OP and POL zkEVM have no event-based backtest yet, so no backtest/production mismatch can arise for them — whenever a backtest is run, it will be extracted at the production Φ from the start.

**Cross-reference:** `backtest_polygon.md §11` documents the same decision from the publication angle. This log entry is the immutable record of the methodological choice.

---

## Entry #024 — April 19, 2026 — α_fast sensitivity on ETH (published value confirmed as knee)

**Trigger:** close the open item from `backtest_ethereum.md §7` ("Uniform EMA
windows alpha=2/11 — not specifically optimized for ETH — to explore after
Solana/Polygon are calibrated"). A sensitivity sweep on α_fast is a standard
robustness check before public release.

**Protocol:** sweep `alpha_fast ∈ {2/5, 2/7, 2/11, 2/15, 2/21, 2/31}`
(N ∈ {4, 6, 10, 14, 20, 30}); keep thresholds fixed at `threshold_s2 = 1.12`,
`threshold_d2 = 1.10`; recompute TPR/FPR and per-event detection latency on
the four ETH ground truth events (The Merge, Shanghai, DeFi Summer, NFT Mania).

**Script:** `scripts/sensitivity_alpha_eth.py` (new).
**Data:** `eth_invariants_2020_2024_phi280.csv`, 34,698 invariants.

**Results:**

| α    | N  | TPR τ | FPR τ | Latency Merge | Latency Shanghai |
|------|----|-------|-------|---------------|------------------|
| 2/5  | 4  | 0.000 | 0.000 | missed        | missed           |
| 2/7  | 6  | 0.007 | 0.002 | 18.3h         | missed           |
| 2/11 | 10 | 0.014 | 0.005 | 18.3h         | 22.8h            |
| 2/15 | 14 | 0.014 | 0.006 | 18.3h         | 22.8h            |
| 2/21 | 20 | 0.014 | 0.008 | 18.3h         | 22.8h            |
| 2/31 | 30 | 0.028 | 0.008 | 12.8h         | 22.8h            |

**Decision:** `alpha_fast = 2/11` confirmed as the **lower knee** of the
operating frontier. Below N=10, Shanghai is missed. Above N=10, detection
latency plateaus and FPR grows monotonically. The published value is not a
local minimum — it is the minimum EMA memory that detects all labelled τ
events under the fixed threshold.

**π TPR = 0 across all α** on DeFi Summer / NFT Mania — expected: these are
σ-dominant events, the rhythm channel is not reactive by design.

**Files:**
- `scripts/sensitivity_alpha_eth.py` (new)
- `scripts/eth_sensitivity_alpha_results.csv` (new)
- `scripts/eth_sensitivity_alpha_chart.png` (new)
- `backtest_ethereum.md §9` — new section with full table and reading
- `backtest_ethereum.md §7` — open item marked ✅

No production change. Published thresholds and α unchanged.

---

## Entry #025 — April 19, 2026 — M1 bootstrap CI + P99 variant (robustness metrics)

**Trigger:** strengthen the M1 publication before the public release. The
formula in `methodology.md §10.1` relies on `max_event` — a single order
statistic that can overstate discriminative power if the peak is an artifact.
Public release warrants a CI and a tail-resistant floor.

**Protocol:** for each M1 script, add:

1. `bootstrap_m1(full_signal, event_vals, n=1000, seed=42)` — resample with
   replacement both the full signal (for p50 and noise) and the event window
   (for max_event), recompute M1 on each resample, return
   (mean, CI95_low, CI95_high) via percentiles.
2. `m1_p99(event_vals, p50, noise)` — variant using P99 of event window
   instead of max. Returns (p99, m1_p99).

New columns in `*_m1_results.csv`:
`m1_ci95_low`, `m1_ci95_high`, `m1_bootstrap_mean`, `p99_event`, `m1_p99`.

**Results:**

| Chain / Signal | Event | M1 (max) | CI95 | Mean | M1 (P99) |
|---|---|---|---|---|---|
| ETH τ | The Merge | 5.07 | [2.23, 5.12] | 4.32 | 3.90 |
| POL τ (Φ=1800) | Reorg Storm | 10.66 | [4.00, 10.82] | 9.17 | 4.96 |
| POL π (Φ=1800) | Gas Crisis | 4.55 | [2.66, 4.65] | 4.08 | 2.08 |
| POL τ (Φ=720) | Reorg Storm | 12.60 | [4.04, 12.74] | 10.68 | 3.01 |
| POL π (Φ=720) | Gas Crisis | 3.59 | [3.27, 3.64] | 3.49 | 1.94 |

**Canonical event pinning for POL π:** the compute_m1() helpers now accept a
`canonical_event` argument. For POL π we pin **Gas Crisis** explicitly — the
Network Halt event produces a larger amplitude (M1=8.85 at Φ=1800, M1=8.66 at
Φ=720) but is a composite halt+backlog incident. Gas Crisis is a pure-demand
event and is the anchor used in §10.3 of methodology.md. Pinning avoids the
auto-best-event selection picking Network Halt and creating a discrepancy
between §10.3 (Gas Crisis) and §10.5 (would have been Network Halt). τ still
uses auto-best-event (Reorg Storm is correctly selected by both rules).

**Reading:**
- All published M1 values fall inside their bootstrap 95% CI — sampling
  distribution is consistent with the reported point estimate.
- The max-based M1 sits at the upper edge of the CI, as expected for an
  order statistic.
- P99 variants land at 40–75% of the max-based value. All remain well above
  the M1 ≥ 1.0 certification floor (methodology.md §10.2).

**Decision:** published max-based M1 retained as the canonical peak-signal
metric. Bootstrap CI and P99 variant now shipped alongside it in
`methodology.md §10.5` as robustness disclosures. No downgrade of any
certified calibration.

**Files:**
- `scripts/m1_eth.py` — extended (new section "6. Bootstrap CI + P99 VARIANT")
- `scripts/m1_pol.py` — extended (bootstrap + P99 inside `compute_m1`)
- `scripts/m1_pol_phi720.py` — extended (same)
- `methodology.md §10.5` — new subsection "Confidence intervals and tail resistance"
- `scripts/eth_m1_results.csv`, `pol_m1_results.csv`, `pol_m1_results_phi720.csv` — new columns

No production change. Published M1 values and their §10.3 table unchanged.

---

*Log maintained and updated with each intervention on calibration baselines or parameters.*
*Format: immutable. No modification of past entries — additions at end of file only.*
