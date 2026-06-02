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

**Note on blob_usage = 0.833:** high signal on first reading. May indicate heavy blob market usage at the time of measurement, or be the normal baseline for Base/OP. EMA convergence needed (~10 cycles = ~50 min of L1 scan) before interpretation.

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
- ETH M1 = **5.07** ✅ — confirmed by `m1_eth.py` · formula validated symmetrically (The Merge max=1.1548, p50=0.9993, bruit=0.0307)
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
- **Latency gain is the operational payoff.** The mean detection latency drops from 16.8h to 3.95h (−76%). The Heimdall/Bor low-amplitude event, previously detected after 35.2h, is now detected in 2.5h. A monitoring system designed for low-latency agent coordination cannot tolerate a 35-hour lag.
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

## Entry #026 — April 19, 2026 — L2 Phase D protocol revised (archive node replay, supersedes Dune plan)

**Chains:** arbitrum, base, optimism
**Affected documents:** `methodology.md §9.3, §9.3b, §9.4, §9.6`
**Historical entries superseded (forward-looking Dune references only):** earlier L2 entries that cited "Dune event-detection calibration (Phase D, Q2-Q3 2026)" — their record of past decisions remains intact; only the forward-looking sentences are superseded by this entry.

**Context**

Throughout the early L2 build (March 2026), forward-looking statements in the L2 log entries planned event-detection calibration via Dune historical data (Q2-Q3 2026). A review session on 2026-04-19 concluded this plan was methodologically imprecise for two reasons:

1. **Dune does not curate an incident registry.** It indexes on-chain data and enables measurement queries, but the list of "L2 sequencer incidents" still requires editorial curation from operator status pages, postmortems, and community trackers. Crossing narrative ground truth with on-chain measurement introduces editorial bias that is inconsistent with the deterministic reproducibility standard applied to L1 calibrations.
2. **An equivalent purely on-chain signal is already in production.** The `ans_l2_adapter_signals` table (populated since 2026-03-17 by the `invarians-l2-adapter` service) contains per-batch L1 timestamps for the ARB SequencerInbox, BASE BatchInbox, and OP BatchInbox. The derived `batch_gap_seconds` signal (SQL window function, no code change required) produces a clean sequencer cadence distribution per chain with no invariant-cadence sampling bias that affects `publish_latency_seconds`.

**Validation of the event-based signal (2026-04-19, n = 93,094 gap observations, 2026-03-17 → 2026-04-19)**

| chain | p50 | p90 | p99 | p99.9 | max | p99.9/p50 |
|-------|-----|-----|-----|-------|-----|-----------|
| arbitrum | 120 s | 192 s | 252 s | 288 s | 732 s | 2.40× |
| base | 48 s | 60 s | 84 s | 132 s | 312 s | 2.75× |
| optimism | 324 s | 432 s | 504 s | 564 s | 744 s | 1.74× |

The `max_gap` on each chain corresponds to the protocol-level batch timeout (~12 min on ARB/OP, ~5 min on BASE). No L2 sequencer stress event occurred in the 2026-03-17 → 2026-04-19 window. The clean ratios confirm the signal is valid; the absence of a tail event in the window confirms a historical extension is needed for event-based validation.

**Decision**

Phase D is re-scoped as follows:

- **Source of ground truth**: `ans_l2_adapter_signals` (existing prod pipeline, no external indexer).
- **Event definition**: `batch_gap_seconds > N × protocol_ceiling` per chain (provisional candidate N=3, to be validated).
- **Historical extension**: retroactive scan of the same three L1 inbox contracts on an Ethereum archive node (Q3 2026), producing an extended `ans_l2_adapter_signals` back-fill covering documented L2 incidents (e.g. OP 2024-02-15, BASE 2024-09-05, ARB 2023-2024 events).
- **Sweep + TPR/FPR**: identical methodology to L1 calibrations (Clopper-Pearson IC95% on detection rate; wide-n FPR estimate on the calm distribution).
- **Publication gate**: thresholds enter `ans_registry` as MEDIUM event-based only after TPR/FPR validation on the archive-replayed incident set.

**Rationale — why archive node, not Dune**

- Reproducibility: any auditor with RPC access to an Ethereum archive node can replay the exact same scan. Dune queries depend on an indexer pipeline outside our control.
- Minimalism: the existing L2 adapter pipeline is the only piece of infrastructure involved. No new ETL.
- Consistency: the L2 ground truth signal becomes homogeneous with the L1 calibration chain — both are derived from L1 block-level data, not external platforms.

**Scope of change**

- `methodology.md` — §9.3 gains `batch_gap_seconds` as a derived signal; new §9.3b documents the archive-replay protocol, current distribution, provisional thresholds, and archive-replay roadmap. All five occurrences of "Dune" in §9.2, §9.4, §9.6, and §12 are replaced with explicit references to the archive node replay protocol.
- `calibration_log.md` — this entry. No rewrite of past entries (their forward-looking Dune references are now superseded, not falsified).
- No production change. The L2 adapter continues collecting, unchanged.

**Next step**

Q3 2026 — archive node replay execution + TPR/FPR sweep + publication of a dedicated L2 backtest document analogous to the existing L1 backtests.

---

## Entry #027 (2026-04-22): Native bridge thresholds P97/30d calibration (Arbitrum, Base, Optimism)

**Type:** Statistical calibration (first time native bridges enter `calibrated:true`)
**Bridges:** `arbitrum-ethereum/native`, `base-ethereum/native`, `optimism-ethereum/native`
**Trigger:** 30 days of clean `last_batch_age_seconds` collection in `ans_bridge_signals` since the bridge collector deployment of 2026-03-22 (cf. `#015`). The P97/30d statistical window is reached on 2026-04-22.

---

**Method**

The native bridge signal `last_batch_age_seconds` measures the time since the last L2 batch was confirmed on Ethereum L1 (SequencerInbox for Arbitrum, BatchInbox for Base and Optimism). For each bridge, the calibrated threshold `threshold_bs1_s` is set at the 97th percentile of the 30-day distribution of that signal. Above the threshold the bridge is reported as `BS2` (degraded posting cadence). At or below it `BS1` (nominal).

The same statistical method (P97 over a continuous 30-day window) is applied to all three native bridges. Differences between final thresholds reflect real per-bridge dynamics, not method differences.

**Guard rails (transactional, baked into `calibrate_native_p97_30d.sql`)**

- `p97_s IS NULL` for any chain → ROLLBACK
- `n_samples < 1000` for any chain → ROLLBACK
- `days_span < 25` for any chain → ROLLBACK

If any single chain fails any single rail, none of the three is committed. The three thresholds always share the same observation window.

**Calibrated thresholds**

| Bridge | `threshold_bs1_s` | n samples | days span |
|--------|-------------------|-----------|-----------|
| `arbitrum-ethereum/native` | **180.00 s** | 4,126 | 30.00 |
| `base-ethereum/native`     | **60.00 s**  | 4,126 | 30.00 |
| `optimism-ethereum/native` | **396.00 s** | 4,125 | 29.99 |

**State transition**

Before this entry, all three native bridges were exposed in the panel API as `calibrated:false / status:"UNCALIBRATED" / state:null`. After commit, each bridge serves `state ∈ {"BS1", "BS2"}` based on `last_batch_age_seconds vs threshold_bs1_s`. The Edge Function reads `bridge_thresholds` on every request, no redeploy was required.

**Status:** ✅ Deployed 2026-04-22 09:29:21 UTC, single transactional UPDATE on `bridge_thresholds`.
**Confidence:** MEDIUM statistical (P97/30d, no event-based validation yet).
**Next step:** Same method applied to CCIP lanes and CCTP routes once each accumulates 30 days of clean signals (earliest 2026-05-20).
**Limitation:** No event-based ground truth for native bridges yet. Detection of historical incidents (e.g., L2 sequencer outages with delayed batch posting) is a follow-up, paralleling the L2 archive-replay protocol introduced in `methodology.md §9.3b`.

---

## Entry #028 (2026-04-27): L2 panel entries restored, GRANT SELECT on `ans_l2_adapter_signals` for PostgREST

**Type:** Production fix (operational, no calibration parameter change)
**Surface:** `/v1/attestation/panel`, `panel.l2[]` array
**Trigger:** Sanity check of the live panel during a session resumption after 5 quiet days. The 3 L2 entries (Arbitrum, Base, Optimism) were observed returning `regime: null` and `status: "UNAVAILABLE"` since 2026-04-20 12:25 UTC, the moment the panel-based Edge Function went live (P0 J1).

---

**Symptom**

For 7 consecutive days, every call to `/v1/attestation/panel` returned the 3 L2 entries with `regime: null` and `status: "UNAVAILABLE"`, propagating a permanent `oracle_status: "DEGRADED"`. L1 Ethereum, native bridges and CCIP/CCTP lanes were unaffected. No error appeared in Edge Function logs.

**Root cause**

The Edge Function reads L2 state via the SQL view `v_l2_states`, which is created with `security_invoker=true`. Its CTE `latest_sigma` reads the underlying table `ans_l2_adapter_signals`. Under PostgREST the request runs as `service_role`. `service_role` bypasses RLS but still requires explicit table-level `GRANT SELECT`. That GRANT was never applied to `ans_l2_adapter_signals`, so the view resolved through `service_role` returned no row. `maybeSingle()` produced `error || !data` and the Edge Function fell back to its `UNAVAILABLE` skeleton without surfacing the failure.

This is a recurrence of the same GRANT pitfall first hit and patched on 2026-04-22 for the CCIP and CCTP signal tables. The original patch was not extrapolated to pre-existing L2 tables, leaving a latent bug that surfaced 5 days later.

**Fix**

```sql
GRANT SELECT ON public.ans_l2_adapter_signals TO service_role;
NOTIFY pgrst, 'reload schema';
```

No Edge Function redeploy required. PostgREST cache reload picked up the new privilege within seconds.

**Verification**

After fix, a fresh call to `/v1/attestation/panel`:

- The 3 L2 entries serve `regime: "S1D1"` with `structural` and `execution_profile` populated.
- `oracle_status` is no longer permanently `DEGRADED`. Residual `DEGRADED` reflects real infra state at fix time (1 native bridge legitimately in BS2, 1 L2 entry transiently STALE), not a silent failure.

**Status:** ✅ Deployed 2026-04-27.
**Impact estimate:** Any client filtering on `panel.l2[].status == "OK"` was in `defer()` permanently from 2026-04-20 12:25 UTC to the 2026-04-27 fix time. To be communicated to early integrators if any incident report surfaces.
**Follow-up:** Internal audit pass over every PostgREST-exposed view in the project, to detect any remaining occurrence of the same GRANT pattern.

---

## Entry #029 (2026-04-29): Calibration centralization — L1/L2 thresholds extracted to Postgres tables, view rename states→regimes, Polygon drift resolved

**Type:** Architecture refactor + drift correction (silent)
**Scope:** L1 + L2 calibration thresholds, classification views, Edge Function `attestation/index.ts`, vocabulary alignment
**Trigger:** Deep audit of the calibration pipeline triggered by post-mortem of the rsETH bridge incident (2026-04-18). Three independent asymmetries surfaced during a code-vs-Postgres review.

---

**Symptom**

1. **Polygon drift TS vs view.** TS `THRESHOLDS.polygon` carried event-based v2.0 values (`rhythm_p90=1.04, sigma=1.14, size=1.18, tx=1.23`, validated 2026-04-19, Entry #023). Postgres view `v_l1_states` carried obsolete pre-calibration values (`1.12 / 1.50 / 1.40 / 1.60`). Both live in production paths. POL not yet exposed via `PANEL_L1_CHAINS`, so external API impact zero, but any consumer reading the SQL view directly (internal dashboard, ad-hoc query) saw classifications inconsistent with the published backtest.

2. **Duplicated L1 classification logic.** `classifyL1State()` in `attestation/index.ts` reproduced the regime CASE WHEN of `v_l1_states`. Two implementations of the same logic in two languages — exposed to future drift on the same pattern.

3. **Vocabulary inconsistency.** Views named `v_l1_states` (column `state`) and `v_l2_states` (column `l2_state`) used "state" for what the docs, articles, and regime grid call "regime" (S1D1, S1D2, S2D1, S2D2). "State" is the correct word for binary bridge classifications (BS1, BS2) only. Naming was a historical carryover.

**Root cause**

Calibration values lived in three places in parallel: TS Edge Function constants, Postgres view CTE inline values, plus dead-code TS `L2_THRESHOLDS` constant. No enforced single source of truth. Each calibration update had to be propagated by hand. The POL update of 2026-04-19 (Entry #023) propagated to TS but not to the Postgres view CTE, and went undetected for 10 days because POL is not in the public panel scope (`PANEL_L1_CHAINS = ['ethereum']`).

**Fix**

A. New tables `l1_thresholds` and `l2_thresholds` in Postgres with RLS enabled (public read, service_role write). Schema mirrors `bridge_thresholds`: chain (PK), threshold columns, `calibration_method`, `calibrated_at`, `calibrated`, `notes`, `source_event_ids`. Modifiable by SQL migration only.

B. Seeded with backtest-validated values:
- `ethereum`: 1.12 / 1.10 / 1.20 / 1.10, event_based MEDIUM (backtest_ethereum.md v0.1)
- `polygon`: 1.04 / 1.14 / 1.18 / 1.23, event_based MEDIUM (backtest_polygon.md v2.0)
- `solana`: 1.12 / 1.1279 / 1.0375 / 1.1279, mixed (τ MEDIUM + π pending July 2026)
- `avalanche`: 1.0282 / 1.2322 / 1.2143 / 1.2399, statistical heuristic LOW (no published backtest yet)
- `arbitrum`: τ=1.15, σ=1.20, statistical_arbitrary, calibrated 2026-04-22 (Phase 2C)
- `base`: τ=1.05, σ=1.10, statistical_arbitrary, calibrated 2026-04-22
- `optimism`: τ=1.05, σ=1.06, statistical_arbitrary, calibrated 2026-04-22

C. New views `v_l1_regimes` and `v_l2_regimes` reading thresholds from the new tables. Identical CASE WHEN classification logic. Column renamed `state` / `l2_state` → `regime`. Returns `regime = NULL` if `calibrated = false`, mapped by Edge Function to `status: "UNCALIBRATED"`.

D. Edge Function `attestation/index.ts` modified:
- Removed: `THRESHOLDS` constant (~25 lines), `L2_THRESHOLDS` constant (4 lines), `classifyL1State()` function (18 lines), `ChainThresholds` interface (14 lines).
- Kept: `computeF3()` (used for `divergence_index`).
- Modified: `fetchL1Entry()` reads `v_l1_regimes` directly (1 SELECT instead of 2 + classification SQL instead of TS); `fetchL2Entry()` reads `v_l2_regimes`; both surface `status: "UNCALIBRATED"` when `data.calibrated === false`.
- Net: ~80 lines deleted, ~30 lines simplified. External JSON response shape unchanged. SDK 0.2.1 still aligned, no version bump required.

E. Old views `v_l1_states` and `v_l2_states` left in place during deploy and validation, then dropped after the new Edge Function was confirmed stable in production.

**Verification**

- Pre-DROP: `SELECT regime FROM v_l1_regimes` vs `SELECT state FROM v_l1_states` compared on identical timestamp. ETH/SOL/AVAX = OK match. POL = MISMATCH expected (S1D1 → S1D2 with corrected thresholds).
- Pre-DROP: L2 view comparison. ARB/BASE/OP = OK match (same thresholds both sides).
- Edge Function deployed with `--no-verify-jwt`. Live curl returned `oracle_status: "OK"`, ETH `regime: "S1D1"`, all 3 L2 `regime: "S1D1"`, all 3 native bridges `state: "BS1"`, signed_execution_context populated.
- Old views dropped 2026-04-29 after stable Edge Function validation.

**Per-chain parameter diff vs pre-migration `v_l1_states`**

| Chain | Param | Old view | New table | Δ |
|---|---|---|---|---|
| ethereum | rhythm_p90 | 1.12 | 1.12 | none |
| ethereum | sigma_demand | 1.10 | 1.10 | none |
| ethereum | size_demand | 1.20 | 1.20 | none |
| ethereum | tx_demand | 1.10 | 1.10 | none |
| **polygon** | rhythm_p90 | **1.12** | **1.04** | **tightened** |
| **polygon** | sigma_demand | **1.50** | **1.14** | **tightened** |
| **polygon** | size_demand | **1.40** | **1.18** | **tightened** |
| **polygon** | tx_demand | **1.60** | **1.23** | **tightened** |
| solana | all | unchanged | unchanged | none |
| avalanche | all | unchanged | unchanged | none |
| L2 (ARB/BASE/OP) | all | unchanged | unchanged | none |

**baseline_impact:** **yes for POL only**. Polygon regime distribution will shift toward more S1D2 / S2D1 / S2D2 windows than before because the thresholds are now event-based-tightened (matching the published backtest TPR=100%, FPR=14.57%). This is a label correction, not a real regime change on the chain. POL is not yet served by the public panel API (`PANEL_L1_CHAINS = ['ethereum']` until P2), so external impact remains zero. Internal Labs / dashboard consumers reading the views directly should segment their POL time series at 2026-04-29 12:00 UTC.

ETH / SOL / AVAX: no baseline impact (parameters unchanged).
L2 (ARB / BASE / OP): no baseline impact (parameters unchanged).
Bridges: out of scope (already in their own `bridge_thresholds` table since Entry #027).

**Architecture invariant going forward**

Any future calibration update follows a single path:
```
SQL migration on l1_thresholds / l2_thresholds
  → v_l1_regimes / v_l2_regimes (read the table on next query)
  → attestation Edge Function (reads the view on next call)
  → panel API (signed payload)
```
Single source of truth. No TS constant, no inline CTE values. Drift between code and database eliminated by construction.

**Status:** ✅ Deployed 2026-04-29. Migration SQL persisted as `oracle-repo/supabase/migration_l1_l2_thresholds_centralization.sql`. Edge Function commit on `oracle-repo/main`. Old views `v_l1_states` and `v_l2_states` dropped after stable validation.

**Follow-up**

- AVAX `calibrated=true` with `confidence: LOW` and no published backtest. Either run the calibration backtest (planned July 2026) or flip `calibrated=false` to enforce `UNCALIBRATED` status until validated. AVAX not in `PANEL_L1_CHAINS`, so external visibility nil — flag deferred.
- One-sided thresholds (`> seuil` only) ignore negative divergences. The rsETH 2026-04-18 cascade showed `tx_ratio=0.7961` (−20.4% below nominal) on ETH which the current logic does not classify as deviation. Composition skew metric (`abs(size_ratio - tx_ratio)`) under consideration for V1.1 panel API enrichment. Not addressed in this entry.
- POL exposure via panel API in P2 (CCIP/CCTP rollout). At that point the new event-based thresholds will be served publicly. No additional calibration work required, just `PANEL_L1_CHAINS` extension.
- L2 calibration remains `statistical_arbitrary`. Event-based backtests for L2 deferred to Q3 2026 (would require ground-truth L2 sequencer incidents).

---

## Entry #030 (2026-04-29 PM): Signed regime codes — schema deployed (extended classification inactive)

**Type:** Architecture extension, schema-only (no calibration value applied)
**Scope:** Calibration tables `l1_thresholds` + `l2_thresholds`, classification views `v_l1_regimes` + `v_l2_regimes`, Edge Function `Regime` type, SDK Python type
**Trigger:** Strategic discussion during the rsETH 2026-04-18 post-mortem on whether divergences should be classified with signed thresholds (positive AND negative) instead of one-sided as today. The cascade signature on Ethereum (size_ratio above nominal × tx_ratio below nominal at 14h UTC) revealed that one-sided thresholds miss asymmetric agentic concentration patterns. Two paths considered: (A) wait for calibration before any deployment, (B) deploy the schema immediately with conditional logic so future calibration is a single UPDATE. Path B chosen to remove the schema as a future blocker.

---

**Symptom**

The four-state regime grid (S1D1, S1D2, S2D1, S2D2) classifies only on the upper side of each ratio (`> threshold`). Operationally, several real-world signatures fall below the nominal:

- Cascading liquidations during exploits (rsETH 2026-04-18 14h UTC: size_ratio = 1.08 above, tx_ratio = 0.74 below; current logic emits S1D1 because size has not crossed 1.20)
- Sequencer halts on L2 (tx_ratio drops abruptly while rhythm slows)
- Censorship of specific transaction types (tx_ratio drops while size_ratio rises on residual DeFi-heavy mix)
- Stablecoin depegs absorbing volume into private bundles (size up, tx down)

None of these patterns trigger a regime change in the current model.

**Architectural decision**

Add the schema for the signed codes immediately, but gate emission behind a per-chain `low_thresholds_calibrated` boolean flag, default false. The view emits the legacy 4-state codes as long as the flag is false on a chain (or any low threshold is NULL). The view emits extended 12-state codes once the flag is true and all low thresholds are populated.

This decouples the schema decision from the calibration work:
- Schema lands in the same release window (zero behavioral change, zero risk)
- Calibration follows over Q3 2026, per chain, after event-based backtests on documented incidents
- Activation is a single UPDATE per chain, no migration, no Edge Function redeploy

**Changes deployed (2026-04-29 PM)**

A. Postgres schema extension on `l1_thresholds`:
- New columns: `sigma_demand_low`, `size_demand_low`, `tx_demand_low`, `rhythm_p10`, `low_thresholds_calibrated boolean DEFAULT false`
- New CHECK constraint `chk_l1_low_bounds` ensuring each low value (when non-NULL) is strictly below its corresponding high value

B. Postgres schema extension on `l2_thresholds`:
- New columns: `rhythm_threshold_low`, `sigma_threshold_low`, `low_thresholds_calibrated boolean DEFAULT false`
- New CHECK constraint `chk_l2_low_bounds`

C. View `v_l1_regimes` extended with conditional CASE WHEN. Outer branch on `low_thresholds_calibrated` and NULL-safety of all low values. Legacy four-state branch identical to v1.1.0. Extended classification branch concatenates struct_part || demand_part:
  - struct_part: `S2+` if rhythm > rhythm_p90, `S2-` if rhythm < rhythm_p10, else `S1`
  - demand_part: `D2±` if any-above and any-below, `D2+` if any-above only, `D2-` if any-below only, else `D1`

D. View `v_l2_regimes` extended similarly. L2 single-dim demand (sigma_ratio only) cannot produce D2±, so extended classification L2 emits 9 codes (no `S1D2±`, `S2+D2±`, `S2-D2±`).

E. Edge Function `attestation/index.ts`: `Regime` type extended to 15 string literals, `L2Regime` type extended to 12. No version bump (additive type).

F. SDK Python `invarians`: `Regime` Literal extended with the 15 values. Bumped to **0.3.1** and published on PyPI.

G. Roadmap updated: Q3 2026 entry now lists signed regime code activation alongside Solana / Avalanche calibration completion.

**Extended classification activation pre-requisites (calibration work, not part of this entry)**

Per chain, calibration of the four low bounds (or three for L2) must be derived from event-based backtests on documented incidents. Reference incidents identified for the calibration exercise:

| Incident | Date | Expected signature |
|---|---|---|
| MakerDAO Black Thursday | 2020-03-12 | ETH S1D2± (cascading liquidations) |
| USDC depeg | 2023-03-11 | ETH S1D2± (HFT arbitrage concentrated) |
| Curve July reentrancy | 2023-07-30 | ETH S1D2± (multi-pool drain) |
| ARB sequencer halt | 2024-12-15 | ARB S2+D2- (halt + drained mempool) |
| OP rare mode | 2024-09 | OP S2+D2- |
| Solana outages ×4 | 2021-09 to 2022-10 | SOL S2+D2- or S2-D1 |
| rsETH cascade | 2026-04-18 | ETH S1D2- or S1D2± |

Effort estimate: ~3-4 weeks of BigQuery extraction + TPR/FPR validation per chain. Targeted activation Q3 2026, chain by chain as backtests validate.

**Stability commitment compliance**

Per `limitations_and_plans.md §2.6`, calibration changes during the Labs baseline phase (started 2026-03-30) require explicit `baseline_impact: yes|no` flag. This entry: **baseline_impact: no** because no chain has `low_thresholds_calibrated=true` at activation. The schema landing is invisible to Labs aggregations. Future per-chain activations will each be logged with `baseline_impact: yes` for that chain only.

**Status:** ✅ Schema deployed 2026-04-29. All 7 chains (4 L1 + 3 L2) have `low_thresholds_calibrated=false`. Panel API emits legacy 4-state codes unchanged. Migration SQL persisted in the oracle repo under `supabase/` (extended-classification schema migration, 2026-04-29).

**Backward compatibility note**

When extended classification activates per chain, that chain emits new signed codes (e.g. `S1D2+` instead of `S1D2`). Clients hardcoding 4-state regex match should be updated:
- Python SDK 0.3.1+ types include the 15 values via `Literal`
- Generic clients should match prefix `S{1,2}{+,-,}D{1,2}{+,-,±,}` rather than the 4 literals

Activation announcement will be made in advance per the v1.x API versioning policy (30-day notice for breaking changes; this is technically additive but client-side string matching may break).

**Follow-up**

- Extended classification calibration backtests (Q3 2026)
- Per-chain activation announcements with 30-day notice
- Site documentation update (glossary, products, patterns, foundations) coordinated with first chain activation
- Edge Function version bump to 1.2.0 if/when activation logic ever needs runtime tuning

---

## Entry #031 (2026-04-29 PM): Signed regime codes — extended classification activated on ETH, POL, BASE, OP (statistical, provisional)

**Type:** Calibration activation (statistical, no event-based validation)
**Scope:** L1 ethereum, L1 polygon, L2 base, L2 optimism. SOL, AVAX, ARB explicitly excluded with documented reasons.
**Trigger:** Same release window as Entry #030 (schema deployment). Decision to activate immediately rather than wait Q3 2026 event-based, accepting statistical lower bounds as provisional with explicit FPR target documented.

---

**What was activated**

A. **L1 ethereum** — preset B (P2 cutoff, FPR ~2% target, FPR-symmetric with HIGH side at 1.23%)
   ```
   rhythm_p10       = 0.913
   sigma_demand_low = 0.9552
   size_demand_low  = 0.8006
   tx_demand_low    = 0.8145
   ```
   Source: `BIGDATA/eth_invariants_2020_2024_phi280.csv` (BigQuery), N=34,648 windows post-warmup

B. **L1 polygon** — preset A (P5 cutoff, FPR ~5% target — P2 unusable, sigma/tx P2 = 0 from historical Polygon downtimes)
   ```
   rhythm_p10       = 0.9407
   sigma_demand_low = 0.5055
   size_demand_low  = 0.8492
   tx_demand_low    = 0.5284
   ```
   Source: `BIGDATA/pol_invariants_2020_2024_phi720.csv` (BigQuery), N=71,206 windows post-warmup

C. **L2 base** — P2 cutoff statistical
   ```
   rhythm_threshold_low = 0.998
   sigma_threshold_low  = 0.8267
   ```
   Source: in-DB `ans_l2_rollup_signals` + `ans_l2_chain_signals` over rolling 30 days, N=652 windows

D. **L2 optimism** — P2 cutoff statistical
   ```
   rhythm_threshold_low = 0.998
   sigma_threshold_low  = 0.8575
   ```
   Source: same as BASE, N=652 windows

**What was explicitly NOT activated**

- **L1 solana**: full pi calibration scheduled July 2026 (sensor data pending). Activating now with partial signed thresholds would collide with that work.
- **L1 avalanche**: no BigQuery extract available, no calibration scheduled before July 2026.
- **L2 arbitrum**: sigma_ratio is structurally degenerate on Arbitrum Nitro (gasLimit ≈ ∞ → variance = 0 over 653 windows, min=max=1.0). Setting sigma_threshold_low ≈ 1.0 produces a threshold that can never trigger. Multi-dim demand workaround (size+tx based, AGENT internal Rule 10) deferred to Q3 2026 chain_profile_arbitrum.md.

**Live verification (2026-04-29 17:00 UTC)**

Panel API spot-check returned signed codes for the first time in production:
```json
{
  "version": "1.1.0",
  "panel": {
    "l1": [{ "chain": "ethereum",  "regime": "S1D1" }],
    "l2": [
      { "chain": "arbitrum", "regime": "S1D1"  },
      { "chain": "base",     "regime": "S1D2+" },
      { "chain": "optimism", "regime": "S1D2+" }
    ]
  }
}
```

BASE and OP emitted `S1D2+` (demand elevated, direction explicit) — the very first extended classification codes through the production stack: Postgres view → Edge Function → signed panel JSON. ETH and ARB stayed in legacy 4-state codes (ETH because conditions are nominal at 17:00 UTC, ARB because extended classification not activated).

**FPR caveat (explicit)**

These calibration values are **statistical, NOT event-based**. By construction:
- ETH lower bounds at P2 → ~2% FPR per signal (FPR-symmetric with HIGH side at 1.23%)
- POL lower bounds at P5 → ~5% FPR per signal (HIGH side accepts 14.57%, asymmetry tolerated due to Polygon variance)
- BASE/OP lower bounds at P2 → ~2% FPR per signal

These FPRs assume the historical distribution is stationary. If the chain enters a sustained drift regime (cf. AVAX rhythm_shift = -0.063), the percentile-based bounds become miscalibrated relative to the new distribution. Event-based recalibration in Q3 2026 will validate or refine.

**Backward compat**

Old clients reading `regime` as one of `{S1D1, S1D2, S2D1, S2D2}` will now occasionally see `S1D2+`, `S1D2-`, `S1D2±`, `S2+D1`, `S2-D1`, `S2+D2+`, `S2+D2-`, `S2+D2±`, `S2-D2+`, `S2-D2-`, `S2-D2±` for ETH/POL, and `S1D2+`, `S1D2-`, `S2+D1`, `S2-D1`, `S2+D2+`, `S2+D2-`, `S2-D2+`, `S2-D2-` for BASE/OP. The legacy 4-state values are preserved for SOL, AVAX, ARB.

Python SDK 0.3.1+ types include all 15 values via `Literal`. SDK clients on 0.3.1 are forward-compatible. Generic clients hardcoding a regex match on the 4 legacy values must be updated.

**baseline_impact** (per stability commitment §2.6)

- **ETH**: yes (label correction). The chain emits more granular codes; Labs aggregations will see new code categories appear from 2026-04-29 17:00 UTC. Segment time series at this cut-over.
- **POL**: yes (same).
- **BASE**: yes (BASE was emitting S1D2 already, now emits S1D2+ — semantically equivalent to S1D2 when only above triggers, but the suffix is new). Strictly speaking the underlying condition is the same as before, only the label has gained the `+` suffix.
- **OP**: yes (same as BASE).
- **SOL/AVAX/ARB**: no (unchanged).

**Status:** ✅ Deployed 2026-04-29. Migration SQL applied (extended-classification schema migration, 2026-04-29). Calibration UPDATEs applied via direct SQL (no separate migration file). Edge Function v1.1.0 unchanged (Regime type already extended in Entry #030).

**Follow-up**

- Q3 2026: event-based recalibration of L1 signed lower thresholds on documented incidents (rsETH 2026-04-18, MakerDAO Black Thursday 2020-03-12, USDC depeg 2023-03-11, Curve July 2023-07-30, ARB sequencer halt 2024-12-15, OP rare mode 2024-09, Solana outages ×4 2021-2022).
- Q3 2026: SOL/AVAX extended classification activation alongside their pi calibration completion.
- Q3 2026: ARB sigma workaround documented in `chain_profile_arbitrum.md` (multi-dim demand on size+tx).
- Stability period for the current statistical bounds: until Q3 2026 event-based pass. Any baseline-shift artifact in Labs aggregations will be flagged at this cut-over date.

---

## Entry #032 (2026-04-29): Extended classification v2 — peer-reviewed audit corrections (rename, ETH P1, BASE/OP rhythm NULL, ARB multi-dim activation)

**Type:** Calibration refinement + schema cleanup (no public behavior break)
**Scope:** L1 ethereum, L2 arbitrum, L2 base, L2 optimism. Fixes 5 sub-optimal points identified in a critical peer-reviewed audit of the Entry #031 deployment, applied within the same release window.
**Trigger:** Independent audit of the freshly-deployed extended classification state by a senior dev expert. Six issues identified, three flagged as critical, three as minor. User decision: fix all immediately rather than carry as debt.

---

**Symptom (audit findings)**

1. **Naming debt L1.** Column `l1_thresholds.rhythm_p10` named after a percentile (P10) but stored P2 for ETH and P5 for POL. The name lied about the content. Inconsistent with the L2 column `rhythm_threshold_low` which followed proper naming.

2. **ETH FPR asymmetry.** ETH HIGH side event-based combined FPR = 1.23%. ETH LOW side at P2 combined FPR ≈ 5.9% (1 - (1-0.02)³). Asymmetry ratio ≈ 5×. The system would emit S1D2- five times more often than S1D2+ for purely statistical (not operational) reasons. Defensible only as provisional, but unbalanced.

3. **BASE/OP rhythm_threshold_low at 0.998.** The L2 rollup rhythm distribution is intrinsically tight ("τ dormant" per chain profile, max ~1.03). P2 = 0.998 means the threshold triggers when rhythm_ratio drops by less than 0.2% below 1 — sub-percent fluctuations, not operational signal.

4. **ARB classification operationally degenerate.** Legacy four-state: rhythm > 1.15 essentially never happens (max observed ~1.03), sigma > 1.20 never happens (sigma_ratio frozen at 1.0 on Arbitrum Nitro). Extended classification v1 was skipped on ARB due to sigma degeneracy. Net result: ARB always emitted S1D1 regardless of conditions. Extended classification provides no signal on Arbitrum.

5. **Schema inconsistency L1 vs L2.** L1 used `rhythm_p10`, `sigma_demand_low`, `size_demand_low`, `tx_demand_low` (mixed naming). L2 used `rhythm_threshold_low`, `sigma_threshold_low` (consistent). To harmonize, L1 should adopt L2 convention OR L2 should adopt L1 convention. L2 was newer and cleaner — chose to align L1 to L2.

6. **POL FPR symmetry by accident.** POL HIGH FPR 14.57%, LOW at P5 ≈ 14.3% combined. Symmetric by coincidence due to POL's wide historical variance. Not intentional design; if POL variance reduces in the next 30 days, asymmetry will return.

**Fix**

A. **Rename L1 column** `rhythm_p10` → `rhythm_threshold_low`. CHECK constraint reference auto-updates. View `v_l1_regimes` updated to use the new name.

B. **Extend L2 schema multi-dim** with new columns `size_threshold`, `size_threshold_low`, `tx_threshold`, `tx_threshold_low`. CHECK constraint extended to enforce `_low < _high` on all four pairs (NULL allowed). View `v_l2_regimes` rewritten with multi-dim demand (sigma + size + tx) NULL-safe per axis. Legacy four-state stays single-dim sigma legacy (backward compat).

C. **Rewrite views NULL-safe.** `v_l1_regimes` and `v_l2_regimes` now treat each axis low independently: `rhythm_threshold_low IS NULL` means S2- skipped on rhythm but extended classification stays active via demand axes. Same for each demand axis. Extended classification activation gated only by `low_thresholds_calibrated = true`, not by all-lows-non-NULL.

D. **Recalibrate ETH from P2 → P1.** New values: rhythm_threshold_low=0.8991, sigma_demand_low=0.9171, size_demand_low=0.766, tx_demand_low=0.7682. FPR per axis ~1%, combined ~3%, closer to HIGH side 1.23% (asymmetry 2.4× instead of 5×).

E. **Set BASE/OP `rhythm_threshold_low = NULL`.** Rhythm L2 distribution too tight to be operationally informative. S2- on rhythm now skipped on these chains. Extended classification stays active on demand axes (sigma + size + tx).

F. **Activate ARB extended classification multi-dim.** Sigma stays degenerate (sigma_threshold_low=NULL, sigma_threshold=1.20 unchanged but never triggers). Size and tx now active with P95 high / P2 low statistical bounds:
   - size_threshold = 1.5211, size_threshold_low = 0.6551 (P95/P2 over 30d, n=653 windows)
   - tx_threshold = 1.6494, tx_threshold_low = 0.5819

G. **Same multi-dim treatment on BASE and OP.** Sigma + size + tx active, all signed (above and below). Rhythm S2- disabled (NULL).

**Per-chain parameter diff vs Entry #031**

| Chain | Param | Entry #031 | Entry #032 | Δ |
|---|---|---|---|---|
| ETH | rhythm_threshold_low | 0.913 (P2) | 0.8991 (P1) | tighter |
| ETH | sigma_demand_low | 0.9552 (P2) | 0.9171 (P1) | tighter |
| ETH | size_demand_low | 0.8006 (P2) | 0.766 (P1) | tighter |
| ETH | tx_demand_low | 0.8145 (P2) | 0.7682 (P1) | tighter |
| POL | (all) | unchanged | unchanged | none |
| ARB | low_thresholds_calibrated | false (skipped) | true (multi-dim) | activated |
| ARB | size/tx thresholds | NULL | size 1.5211/0.6551, tx 1.6494/0.5819 | added |
| BASE | rhythm_threshold_low | 0.998 (P2) | NULL | disabled |
| BASE | size/tx thresholds | NULL | size 1.2665/0.7246, tx 1.3307/0.7305 | added |
| OP | rhythm_threshold_low | 0.998 (P2) | NULL | disabled |
| OP | size/tx thresholds | NULL | size 1.306/0.7035, tx 1.1912/0.8119 | added |

**Live verification (post-migration)**

Panel API spot-check after migration:
- L1 ETH: regime currently nominal (S1D1)
- L2 ARB: size_ratio=1.4416 (below P95=1.5211), tx=1.5017 (below P95=1.6494) → S1D1 (correct, ARB now CAN emit S1D2+ when outliers occur)
- L2 BASE: sigma=1.0217 (below 1.10), size=1.1368 (below 1.2665), tx=1.1824 (below 1.3307) → S1D1
- L2 OP: sigma=1.0139 (below 1.06), size=1.2637 (below 1.306), tx=1.0866 (below 1.1912) → S1D1

All chains in nominal state at the moment, but multi-dim demand signed classification is now alive and will emit signed codes when conditions cross.

**baseline_impact**

- ETH: yes (P1 vs P2 → tighter thresholds, fewer D2- emissions, rebalanced FPR)
- POL: no (unchanged)
- ARB: yes (was always S1D1, now CAN emit S1D2+/-/± via size and tx)
- BASE/OP: minor (no more S2- emissions on rhythm, but D2±/D2- emissions via size/tx now possible)

Labs aggregations should segment time series at this cut-over (2026-04-29 late PM) for affected chains.

**Status:** ✅ Deployed 2026-04-29. Migration SQL applied via Supabase SQL Editor (extended-classification v2 audit corrections migration, 2026-04-29). Edge Function unchanged (Regime type already extended in Entry #030). SDK unchanged (Regime Literal already extended in 0.3.1).

**Follow-up**

- Q3 2026 event-based validation will refine all the statistical lows and may rebalance ETH towards even tighter cutoffs (P0.5 if event-based ground truth allows).
- ARB workaround (size+tx multi-dim) now live, replaces the planned `chain_profile_arbitrum.md` write-up. The workaround is no longer "deferred Q3" but "deployed and operational since 2026-04-29".
- POL accidental FPR symmetry will be re-examined Q3 2026 if Polygon variance changes. May need recalibration to maintain symmetry.

---

## Entry #033 (2026-04-30): API v2.0 launch, three primitives architecture (Attestation + Regime + Drift Signal)

**Type:** Major version release (breaking) + observable extension (additive on the public side)
**Surface:** Panel API endpoints, payload schema, SDK
**Trigger:** Post-mortem of the rsETH cascade (2026-04-18) and audit of the gap between regime classification and fitness-for-action. Regime alone (snapshot of substrate state) does not answer "is it safe to act in the next 30 minutes". A continuous drift signal is needed alongside the discrete regime code.

---

**Architecture change**

The panel API exposes three independent primitives in a single signed payload:

1. **Attestation** (Primitive 1, HMAC-SHA256). Existing since v1.0.0. Every payload carries `signed_execution_context = { payload_hash, signature, key_id, anchor }`. Independently verifiable via `POST /attestation/v2/verify`. The signature makes the certified execution state provable, not just observable.

2. **Regime** (Primitive 2, SxDx classification). Per-chain 12-code grid (S1, S2+, S2- on the structural axis combined with D1, D2+, D2-, D2± on the demand axis). The legacy 4-state codes (S1D1, S1D2, S2D1, S2D2) remain valid as aliases on chains without lower bounds yet calibrated.

3. **Drift Signal** (Primitive 3, NEW). For every classifying observable the panel exposes (in diagnostic mode) a `MetricBlock` with `ratio` (short EMA), `ratio_long` (long-term ~30-day baseline), `shift = ratio - ratio_long` (current deviation magnitude, signed), `shift_delta = shift_now - shift_prev` (raw direction of value movement between cycles), and `shift_magnitude_delta = |shift_now| - |shift_prev|` (whether the deviation is growing or shrinking). A composite `drift` object aggregates per axis (`structural` vs `demand`, plus their delta and magnitude_delta).

**Payload structure**

The payload is now grouped by axis (`structural` vs `demand`) per chain, with each metric a self-contained MetricBlock. Tiered exposure via `?include=core|diagnostic|full`:
- `core` (default): regime decision grade, `{ ratio }` per metric plus `epoch`/`seconds` for beacon/sequencer
- `diagnostic`: adds `ratio_long`, `shift`, `shift_delta`, `shift_magnitude_delta`
- `full`: adds raw EMAs (`baseline_short`, `baseline_long`)

**New classifying observables**

- **Ethereum** structural axis extended with `beacon_participation` (Beacon Chain validator participation rate). Drops below the calibrated lower bound trigger S2- (validator outage signature). Calibration scheduled in Entry #035.
- **L2 chains** (ARB, BASE, OP) structural axis extended with `sequencer_publish_latency` (third structural classifying observable). Spikes above the calibrated upper bound trigger S2+ (sequencer halt signature). Calibrated in Entry #034.

**Endpoints**

- `GET /attestation/v2/panel` (returns full panel; query parameters: `chains`, `bridges`, `include`)
- `POST /attestation/v2/verify` (verifies HMAC over a panel payload)
- v1.1.0 endpoints (`/attestation/panel`, `/attestation/verify`) remain live with a 60-day deprecation window, sunset 2026-06-30 (return `410 Gone` after).

**Migration v1.1.0 to v2.0**

| v1.1.0 (flat)                                  | v2.0 (axis-grouped)                       |
|------------------------------------------------|-------------------------------------------|
| `panel.l1[].rhythm_ratio`                      | `panel.l1[].structural.rhythm.ratio`      |
| `panel.l1[].sigma_ratio`                       | `panel.l1[].demand.sigma.ratio`           |
| `panel.l1[].structural_slow.rhythm_ratio_slow` | `panel.l1[].structural.rhythm.ratio_long` |
| `panel.l1[].shifts.rhythm_shift`               | `panel.l1[].structural.rhythm.shift`      |
| (no demand shifts exposed)                     | `panel.l1[].demand.{sigma,size,tx}.shift` |
| (no trend signal)                              | `shift_delta` + `shift_magnitude_delta` per metric |
| (no L2 sequencer obs in regime)                | `panel.l2[].structural.sequencer_publish_latency` |
| (no Ethereum beacon in regime)                 | `panel.l1[].structural.beacon_participation` (ETH only) |
| (no `drift` composite)                         | `panel.l1[].drift.{structural,demand}` + delta + magnitude_delta |

**SDK**

`invarians >= 0.5.0` published on PyPI with `get_panel_v2()`, `verify_panel_v2()`, `MetricBlock` dataclass, and trend helpers (`is_drifting_away`, `is_reverting`). Backwards-incompatible with 0.3.x (major bump).

**Implementation deliverables**

- Postgres: migration `migration_v2_views_and_thresholds.sql` (extends `l1_thresholds` + `l2_thresholds` schemas, creates `v2_l1_regimes` + `v2_l2_regimes` views with LAG window function for `shift_prev`).
- Edge Function: routes `/attestation/v2/panel` and `/attestation/v2/verify` deployed (~1300 lines, V2 types and helpers added).
- SDK: `invarians 0.5.0` on PyPI.

**Status:** ✅ Deployed 2026-04-30. Beacon and sequencer observables ship as `UNCALIBRATED` initially (visible to consumers but not feeding the regime CASE expression). Calibrated in Entries #034 (L2) and #035 (ETH beacon).

**Follow-up**

- Entry #034: L2 `sequencer_publish_latency` calibration on `batch_gap_seconds` (2026-05-01).
- Entry #035: Ethereum `beacon_participation` calibration via beaconcha.in 30d backfill (2026-05-01).
- Slow EMA pipelines for `batch_gap_seconds` and `validator_participation_rate`: ~30 days post-launch. Until then `shift_available: false` per V2_SPEC §6.1 footnote.
- Empirical validation of the shift signal: backtest historical regime transitions against corresponding shift values, quantify TPR/FPR per chain, refine drift_index reading thresholds. Publishable as `research/SHIFT_PREDICTIVE_VALIDATION.md`.

---

## Entry #034 (2026-05-01): L2 sequencer_publish_latency calibrated on `batch_gap_seconds`, ARB / BASE / OP

**Type:** Statistical calibration (envelope-based, no halt event in window) + architectural pivot from `publish_latency_seconds` to `batch_gap_seconds`
**Surface:** `v2_l2_regimes` view, `l2_thresholds` calibration table, `panel.l2[].structural.sequencer_publish_latency.seconds` field
**Trigger:** API v2.0 launch (Entry #033) shipped with `sequencer_publish_latency_calibrated = false` placeholder. Post-launch calibration of the S2+ trigger required to activate the observable in the regime CASE.

---

**Architectural pivot, calibrate on `batch_gap_seconds` not `publish_latency_seconds`**

The original `publish_latency_seconds` column in `ans_l2_adapter_signals` is sampling-biased. Per Entry #014 it computes `t_L1_block - last_L2_invariant_timestamp` and is dominated by the L2 invariant capture cadence (~1h), not by actual sequencer health. Entry #971 already documented the replacement path: `batch_gap_seconds = LAG(l1_block_timestamp) OVER (PARTITION BY chain ORDER BY l1_block_number)` is purely on-chain time between consecutive L1 batch inscriptions, with no invariant-cadence sampling bias.

Path A retained over Path B (ship publish_latency calibration with documented debt and migrate later) for one reason: shipping a threshold on a value the internal documentation explicitly states is "not directly interpretable in absolute" would create a publicly visible architectural inconsistency. The 20 minutes of additional SQL work to migrate the view is worth the elimination of self-documented technical debt.

**View modification**

`v2_l2_regimes` rewritten with new `adapter_ranked` CTE that computes `batch_gap_seconds` via LAG. The exposed field name is preserved (`sequencer_publish_latency.seconds`) per V2_SPEC §8.3 contract, but the underlying value is now the clean batch gap. No SDK or Edge Function code change required (field name and type unchanged).

**Distribution analysis (30 days, 2026-04-01 to 2026-05-01)**

| chain    | n_obs  | median | P95   | P99   | P99.9 | max   | nominal cadence |
|----------|--------|--------|-------|-------|-------|-------|-----------------|
| arbitrum | 19,601 | 132 s  | 216 s | 252 s | 300 s | 384 s | ~2.2 min/batch  |
| base     | 50,904 |  48 s  |  72 s |  84 s |  96 s | 264 s | ~1 batch/min    |
| optimism |  7,302 | 348 s  | 528 s | 600 s | 660 s | 732 s | ~6 min/batch    |

The 2026-04-10 spike previously visible on `publish_latency_seconds` (10000+ s on ARB, 8000+ s on BASE/OP) has disappeared. `batch_gap_seconds` shows nominal cadence on that day. **This confirms that the prior spike was a telemetry artifact, not a sequencer event.** Calibrating on `publish_latency_seconds` would have anchored the threshold on noise.

**Calibrated thresholds**

| chain    | `sequencer_publish_latency_threshold_high` | minutes | x P99 | x max_30d | x nominal cadence |
|----------|--------------------------------------------|---------|-------|-----------|-------------------|
| arbitrum | **600 s**                                  | 10 min  | x 2.4 | x 1.6     | ~ x 5             |
| base     | **480 s**                                  |  8 min  | x 5.7 | x 1.8     | ~ x 8             |
| optimism | **1800 s**                                 | 30 min  | x 3.0 | x 2.5     | ~ x 5             |

Method: per-chain envelope, semantics "halt = 5x typical cadence". FPR_30d = 0% on all three chains. Documented historical halts (ARB 2024-12-21 ~78 min, OP 2025-09-14 ~3h+, BASE 2024-11 ~30 min) all clear their respective threshold by x4 to x6.

**Finding indexed for Drift Signal validation**

The top 20 OP `batch_gap_seconds` values reveal a **soft slowdown cluster on 2026-04-27 19:59 to 2026-04-29 03:31**: 18 observations >= 648 s concentrated within a 48h window, plus an isolated pair on 2026-04-10 00:38 and 00:49 (732 and 672 s). Cadence shifted from typical ~6 min to ~11 min (x2) over the 48h cluster. Not a halt (max 732 s stays below the 1800 s threshold), but a sustained structural degradation. Per design, this event is **not classified as S2+** (the regime grid is calibrated for halt-only on this axis). It is the canonical case for the Drift Signal primitive: once the slow EMA on `batch_gap_seconds` stabilizes (~30 days post-launch, `sequencer_publish_latency_shift_available` flips to `true`), `shift_magnitude_delta` should expose this slowdown as a sustained positive drift on OP. Reserved as ground-truth case for `research/SHIFT_PREDICTIVE_VALIDATION.md` and as the empirical example for the article "Soft sequencer slowdown detection: when Drift Signal beats regime classification".

**Live verification (post-deploy)**

Smoke test on `GET /attestation/v2/panel?chains=arbitrum,base,optimism&include=core` returns:
- `arbitrum`: regime `S1D1`, `sequencer_publish_latency.seconds = 96` (well below 600)
- `base`: regime `S1D2+` (D2+ from demand axis, S1 confirmed structural), `seconds = 48` (well below 480)
- `optimism`: regime `S1D1`, `seconds = 396` (well below 1800)

Cosmetic: `sequencer_publish_latency.ratio = null` per V2_SPEC §6.1 footnote (slow EMA on `batch_gap_seconds` not yet built; `seconds` raw is the regime trigger).

**Status:** ✅ Deployed 2026-05-01 evening. Migration `oracle-repo/supabase/migration_v2_l2_batch_gap_calibration.sql` applied via Supabase SQL Editor. Edge Function unchanged.
**Confidence:** MEDIUM statistical (envelope on 30d, no halt event in window, FPR=0% by construction). Recalibration recommended at T+90j or at the first halt event observed.
**Limitation:** Single statistical window, no event-anchored calibration. The first real halt observed post-launch becomes the anchor case (event review will refine the threshold downward if the recovery window suggests it).

---

## Entry #035 (2026-05-01): Ethereum beacon_participation S2- threshold calibrated

**Type:** Statistical calibration (envelope on 30-day distribution + reference to public historical halts), enables S2- detection on Ethereum structural axis
**Surface:** `v2_l1_regimes` view, `l1_thresholds.validator_participation_threshold_low` column, `panel.l1[].structural.beacon_participation` field
**Trigger:** API v2.0 launch (Entry #033) shipped with `validator_participation_calibrated = false` placeholder. Post-launch calibration of the S2- trigger on Ethereum required to activate the observable in the regime CASE.

---

**Method**

Pulled 30 days of Ethereum Beacon Chain `globalparticipationrate` from public beaconcha.in API, sampled every 20 epochs (~2h cadence) for 338 datapoints over the window 2026-04-01 to 2026-05-01 (epochs 438123 to 444873). Distribution analysis to set the S2- low threshold for the structural axis on Ethereum.

The beacon_participation observable is bounded [0, 1.0] with mode very near 1. Its asymmetry means low-side is the only direction that triggers S2 (a participation rate above 1.0 is impossible by construction). The S2- threshold is the unique trigger for this observable on the Ethereum structural axis.

**Distribution (338 samples, 30 days)**

| stat | value |
|---|---|
| min | 0.96814 |
| P0.1 | 0.96814 |
| P1 | 0.98450 |
| P5 | 0.99523 |
| median | 0.99842 |
| P95 | 0.99892 |
| P99 | 0.99898 |
| max | 0.99901 |
| mean | 0.99774 |
| stdev | 0.00297 |

The distribution is very tight (stdev = 0.003) but with clear outliers in the lower tail, two of which observed during the fetch:

- epoch 441503: rate 0.98852 (~3 sigma below mean, isolated)
- epoch 444103: rate 0.96814 (~10 sigma below mean, the absolute min on the window)

**Reference to public historical halts**

The threshold needs to capture documented validator participation drops without firing on nominal variance:

| Event | Participation observed | Magnitude |
|---|---|---|
| Geth bug 2024-12 | ~0.94 | -6 pp |
| Lido outage early 2024 | ~0.96 | -4 pp |
| Prysm bug 2023 | ~0.92 | -8 pp |
| Coinbase staking incident | ~0.95 | -5 pp |

**Calibrated threshold**

| Chain | `validator_participation_threshold_low` | Captures halts | FPR_30d | Captures observed dip |
|---|---|---|---|---|
| ethereum | **0.97** | All public halts (margin x4 to x10) | ~0.3% (1 obs out of 338) | Yes (the 0.96814 epoch 444103) |

Method: balance between halt-only (P0.1 ~ 0.963) and aggressive (P1 ~ 0.979). A 0.97 threshold captures all public historical halts with comfortable margin, captures the 0.96814 observed dip during the fetch (potential precursor), and keeps FPR low (~0.3% on 30d, ~2 hours/month would emit S2- in nominal conditions).

This threshold corresponds to a sustained 3 percent validator participation drop, which is operationally meaningful: an agent reading ETH in S2- with this threshold knows that L1 finality timing is compromised because >3 percent of validators are simultaneously offline.

**Asymmetry note**

beacon_participation enters the regime CASE on Ethereum only via its low threshold. There is no high-side trigger by design (rate above 1.0 is impossible). This is the first observable in the v2.0 architecture with a unidirectional trigger.

**Finding indexed for Drift Signal validation**

The 0.96814 observation at epoch 444103 (during the fetch window) is a measurable transient drop, magnitude approximately 1pp below nominal. It does not reach the historical halt range (~0.94) but is clearly off baseline. Reserved as a candidate ground-truth case for Drift Signal Primitive 3 validation post-launch (alongside rsETH cascade D2± from 2026-04-18 and OP soft slowdown from 2026-04-27 to 2026-04-30). Once the slow EMA on validator_participation stabilizes (requires either a per-epoch logging table creation or external backfill from beaconcha.in / beaconscan, ETA ~30 days post-launch), the `beacon_participation_shift` field activates and `shift_magnitude_delta` should expose this dip as a transient negative drift on Ethereum.

**Live verification (post-deploy)**

Smoke test on `GET /attestation/v2/panel?chains=ethereum&include=diagnostic` returns:

```json
{
  "chain": "ethereum",
  "regime": "S1D1",
  "structural": {
    "beacon_participation": {
      "ratio": 1.0,
      "epoch": 25001869,
      "shift_available": false
    }
  }
}
```

The `shift_available: false` is expected during the pre-shift period, per V2_SPEC §6.1 footnote. The ratio (1.0) is well above the threshold (0.97), structural axis stays S1.

**Status:** ✅ Deployed 2026-05-01 evening. Single transactional UPDATE on `l1_thresholds` for chain='ethereum'. Edge Function unchanged. Smoke test PASS.
**Confidence:** MEDIUM statistical (envelope on 30d, no halt event in window) + reference to public historical halts (Geth bug 2024, Lido outage, Prysm bug 2023). All public halts clear the threshold by margin x4 to x10. Recalibration recommended at T+90 days or at the first halt event observed.
**Limitation:** Single statistical window, no event-anchored calibration. The 0.96814 dip observed during the fetch is reserved for Drift Signal post-launch validation. Sample-every-20-epoch cadence (~2h) means a single-epoch dip could pass between samples; not blocking for calibration (envelope holds), and detection in production reads `ans_sensor_health` updated each epoch (no blind spot in live regime).

**Follow-up**

- Slow EMA pipeline for `validator_participation` (per-epoch logging table or external backfill from beaconcha.in/beaconscan), required for `beacon_participation_shift_available: true`. ETA ~30 days post-launch.
- Empirical Drift Signal validation against the 3 indexed cases (rsETH D2±, OP soft slowdown, ETH beacon dip 444103), publishable as `research/SHIFT_PREDICTIVE_VALIDATION.md`.
- Recalibration of the 0.97 threshold at T+90 days using a longer baseline window.
- Public communication of v2.0 launch (LinkedIn/blog) once API v2.0 is fully calibrated (today: L1 ETH/POL, L2 ARB/BASE/OP all live with 12 signed codes; Solana/Avalanche on schedule for July 2026).

---

## Entry #036 (2026-05-04): CCTP route classification calibrated on `circle_api_latency_ms`, preliminary P97/14d

**Type:** Statistical calibration (envelope-based, preliminary 14-day window pending production-grade 30-day re-calibration)
**Surface:** `bridge_thresholds` table (10 CCTP routes), `panel.bridges[].state` field for `bridge_type='cctp'` entries
**Trigger:** Activation of bridge classification beyond native L2-to-L1, leveraging 14 days of CCTP raw signals collected since 2026-04-20 by `invarians-cctp-collector` running on the VPS.

---

**Method**

CCTP routes expose two latency observables in `ans_cctp_route_signals`: `attestation_latency_p90_s` (Circle attestation API latency for actually-transferred messages) and `circle_api_latency_ms` (continuous health-check latency on the Circle attestation API endpoint). The first is a measure of effective end-to-end message latency, the second is an availability and responsiveness probe of the underlying Circle infrastructure.

Distribution analysis on 14 days of collection (~2000 samples per route):

| observable | non_null coverage | semantics |
|---|---|---|
| `attestation_latency_p90_s` | 0% over 14d window | filled only when actual messages transit, periods of low CCTP activity leave this NULL |
| `circle_api_latency_ms` | 99.97% (19982 / 19988) | filled continuously by the collector via Circle API health probe |

The second observable is calibratable. The first is not, until throughput grows.

The chosen method calibrates the BS1/BS2 boundary on `circle_api_latency_ms`. Semantics: when Circle attestation infrastructure responds slowly under stress, downstream message attestation latency is mechanically affected. Stress on the API health check is an upstream proxy for stress on the actual settlement path.

Per-route P97 over the 14-day window:

| route | P50 (ms) | P97 (ms) | P99 (ms) | max (ms) | n samples |
|---|---|---|---|---|---|
| arbitrum-base/cctp | 151 | 265.8 | 476 | 4639 | 1999 |
| arbitrum-ethereum/cctp | 151 | 303.5 | 479 | 1385 | 1998 |
| avalanche-ethereum/cctp | 151 | 211 | 450 | 4677 | 1999 |
| base-arbitrum/cctp | 151 | 265.1 | 476 | 4744 | 1998 |
| base-ethereum/cctp | 151 | 234 | 477 | 6790 | 1997 |
| ethereum-arbitrum/cctp | 184 | 475 | 528 | 2703 | 1998 |
| ethereum-avalanche/cctp | 152 | 430.4 | 478 | 3170 | 1998 |
| ethereum-base/cctp | 152 | 447 | 485 | 2816 | 1997 |
| ethereum-optimism/cctp | 152 | 453.1 | 487 | 4264 | 1999 |
| optimism-ethereum/cctp | 151 | 207 | 450 | 9248 | 1999 |

Distributions are well-behaved with stable medians (~150ms), tight P97 (~200-475ms), and outlier tails reaching ~4-9 seconds (likely Circle API transient outages or geographic latency spikes).

**Calibrated thresholds (preliminary)**

| route | `threshold_bs1_s` (= `threshold_bs2_s`) |
|---|---|
| arbitrum-base/cctp | 0.265779 (266 ms) |
| arbitrum-ethereum/cctp | 0.303519 (304 ms) |
| avalanche-ethereum/cctp | 0.211 (211 ms) |
| base-arbitrum/cctp | 0.265059 (265 ms) |
| base-ethereum/cctp | 0.234 (234 ms) |
| ethereum-arbitrum/cctp | 0.475 (475 ms) |
| ethereum-avalanche/cctp | 0.43036 (430 ms) |
| ethereum-base/cctp | 0.447 (447 ms) |
| ethereum-optimism/cctp | 0.45306 (453 ms) |
| optimism-ethereum/cctp | 0.207 (207 ms) |

Stored in seconds per existing schema convention (`threshold_bs1_s` units). `threshold_bs1_s = threshold_bs2_s = P97` per the same convention used in native bridge calibration (Entry #027).

**Calibration method tag**

`calibration_method = 'preliminary_p97_14d_circle_api_latency'` distinguishes this run from production-grade 30-day calibrations to be applied around 2026-05-20. Confidence flag set to LOW pending the re-calibration cycle.

**Re-calibration schedule**

Two follow-up calibrations planned on the same SQL pattern:

| Date | Window | `calibration_method` | Confidence |
|---|---|---|---|
| ~2026-05-15 | 25 days | `production_p97_25d_circle_api_latency` | MEDIUM |
| ~2026-05-20 | 30 days | `production_p97_30d_circle_api_latency` | HIGH |

Each re-calibration overwrites the previous thresholds and updates the method tag plus confidence. The 14d preliminary is deliberately conservative and exists to enable BS1/BS2 classification immediately while production-grade calibration matures.

**Live verification (post-deploy)**

`SELECT bridge_id, threshold_bs1_s, calibration_method, calibrated FROM bridge_thresholds WHERE bridge_type='cctp'` returns 10 rows with `calibrated = true` and method `preliminary_p97_14d_circle_api_latency`. Edge Function `attestation/v2/panel` to be updated separately to consume these thresholds and emit BS1/BS2 classification on CCTP routes (target 2026-05-05).

**Status:** ✅ Calibration thresholds written 2026-05-04 evening via transactional UPDATE on `bridge_thresholds`. Edge Function consumer update pending.
**Confidence:** LOW (preliminary 14-day window). Will progress to MEDIUM at 25d and HIGH at 30d per the re-calibration schedule above.
**Limitation:** Calibration uses `circle_api_latency_ms` (health probe) as a proxy for end-to-end message latency. The direct observable `attestation_latency_p90_s` requires sustained message throughput which is currently below the threshold for statistical baseline. Once message volume on CCTP routes increases (Q3 2026 RWA mainstream adoption target), a direct calibration on `attestation_latency_p90_s` may supersede or complement the current proxy approach.

**Follow-up**

- Edge Function `attestation/v2/panel` update: consume new CCTP thresholds, emit `state: BS1|BS2` per route.
- Detector `stress-events` reformulation: integrate CCTP BS state as part of event severity classification.
- 25-day re-calibration cycle: target 2026-05-15.
- 30-day re-calibration cycle: target 2026-05-20.
- Post-throughput-emergence calibration on direct `attestation_latency_p90_s` observable: ETA Q3 2026 with RWA mainstream CCTP adoption (USDC institutional inter-chain settlements).

---

## Entry #037 (2026-05-04): CCIP lane calibration deferred, empirical observation of below-baseline throughput

**Type:** Statistical observation, calibration explicitly deferred
**Surface:** `bridge_thresholds` table (10 CCIP lanes, all remain `calibrated = false`), `panel.bridges[].state` field for `bridge_type='ccip'` entries (no classification emitted, raw observables exposed)
**Trigger:** Attempted P97/14d calibration on the only continuously-filled observable available (`last_sequence_advance_s`).

---

**Method and observation**

CCIP lanes expose several observables in `ans_ccip_lane_signals`. Two were considered for calibration:

| observable | non_null coverage | semantics |
|---|---|---|
| `total_latency_p90_s`, `commit_latency_p90_s`, `execute_latency_p90_s` | 0% over 14d window | filled only when actual messages transit, periods of low CCIP activity leave these NULL |
| `last_sequence_advance_s` | 100% (20029 / 20029) | continuous time delta since last DON commit nonce increment, filled by collector independently of message transit |

The first set requires sustained message throughput. The second is the time-since-last-DON-activity, which is filled continuously regardless of message volume.

Distribution of `last_sequence_advance_s` by lane on the 14-day window:

| lane | P50 (s) | P97 (s) | P99 (s) | max (s) | n samples |
|---|---|---|---|---|---|
| arbitrum-ethereum/ccip | 3903 | 9999 | 9999 | 9999 | 2003 |
| avalanche-ethereum/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| base-ethereum/ccip | 3185 | 9999 | 9999 | 9999 | 2003 |
| ethereum-arbitrum/ccip | 9999 | 9999 | 9999 | 9999 | 2002 |
| ethereum-avalanche/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| ethereum-base/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| ethereum-optimism/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| ethereum-polygon/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| optimism-ethereum/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |
| polygon-ethereum/ccip | 9999 | 9999 | 9999 | 9999 | 2003 |

The value 9999 is the cap applied by the collector on the time-since-last-DON-activity field. Eight of ten lanes have P50 at this cap, meaning the DON has not advanced its commit nonce for at least the cap duration in more than half of the observation samples. Two lanes (`arbitrum-ethereum`, `base-ethereum`) show a P50 around 3000-3900 seconds (~50-65 minutes between commits), but their P97 still saturates at the cap.

**Conclusion**

The observable `last_sequence_advance_s` does not contain enough information at the upper percentile (P97) to anchor a meaningful BS1/BS2 boundary. All 10 lanes saturate at or near the collector cap. A threshold derived from this distribution would be either equal to the cap (semantically meaningless, since "above the cap" is not observable) or lower than the cap (which would mean classifying nominal cap-saturation as stress, a constant false-positive emission).

This is consistent with public observations of low cross-chain message volume on Chainlink CCIP. The current throughput on the lanes monitored by Invarians is below the threshold required for production-grade statistical baseline calibration.

**Decision**

Calibration of CCIP lanes is explicitly deferred. The 10 lanes remain in `bridge_thresholds` as placeholders with `calibrated = false`, `threshold_bs1_s = NULL`. The Edge Function `attestation/v2/panel` will continue to expose CCIP lanes in the panel as raw observability entries (with `state: null`, `calibrated: false`, and the current observable values exposed for consumers who want raw access), but no BS1/BS2 classification is emitted.

**Reserved for future activation**

CCIP classification will activate when sustained throughput emerges on the lanes. Sustained CCIP message volume is expected to grow as institutional RWA cross-chain settlement workflows adopt variable-latency bridges. Estimated timeline: Q3 2026, contingent on observed throughput growth on the lanes.

The Invarians infrastructure (collectors, schema, calibration scripts) is ready to activate classification immediately when throughput reaches the statistical threshold. No additional engineering required, only a re-execution of the calibration pattern (P97 on `total_latency_p90_s` over a window of sufficient activity).

**Status:** ❌ Calibration not committed. CCIP lanes remain in `calibrated = false` state. Decision logged here for transparency and future re-evaluation.
**Confidence:** N/A (calibration deferred, no thresholds emitted).
**Limitation:** Empirical observation that current CCIP throughput on the monitored lanes is below the statistical threshold for baseline calibration. This observation is itself a publishable insight into the current state of cross-chain message volume on Chainlink CCIP.

**Follow-up**

- Quarterly re-evaluation of CCIP throughput: monitor `last_sequence_advance_s` distribution evolution. Re-attempt calibration when distribution shows meaningful P97 below the cap (i.e., DON commit activity becomes regular enough to dominate the observation window).
- Consider direct calibration on `total_latency_p90_s` once message volume per lane exceeds approximately 100 messages per day per direction (rough heuristic for non-NULL coverage > 50% over a 30-day window).
- Article publishable from this observation: "CCIP throughput observability, empirical observations from a calibration attempt", documenting the methodology, the cap saturation result, and the implication for institutional adopters monitoring Chainlink CCIP for RWA settlement.

---

## Entry #038 (2026-05-04): Native bridge L2-to-L1 scope abandoned, value lever shifted to variable-latency bridges

**Type:** Strategic scope decision, follow-up to Entries #027 (native bridge calibration committed 2026-04-22) and #036-#037 (CCTP and CCIP scope expansion).
**Surface:** `invarians-bridge-collector` service on VPS (stopped), public narrative on `invarians-site/`, `agentnorthstar/calibration` repo positioning.
**Trigger:** Recognition that the institutional-grade value of Invarians on optimistic-rollup native bridges (Arbitrum, Base, Optimism canonical L2-to-L1 withdrawals) is structurally limited by the protocol-immutable 7-day challenge period.

---

**Reasoning**

Optimistic rollup native bridges (Arbitrum One, Base, Optimism, Linea, Scroll) impose a 7-day challenge period on L2-to-L1 withdrawals by design. This duration is fixed by the protocol-level fraud-proof window and is not affected by network conditions, by Invarians, or by any external observability layer. Capital initiated for L2-to-L1 withdrawal via the canonical bridge is exposed for 7 days regardless of the structural state of L1, L2, or the bridge itself at the moment of initiation.

The only lever Invarians can provide on these bridges is the choice of moment of initiation (so that the 7-day exposure window starts in a verified nominal state rather than in a structural cascade). This is a marginal lever compared to bridges where latency is itself a function of network state.

In contrast, variable-latency bridges (CCIP, CCTP, fast LP-based bridges such as Across or Hop) operate with baseline latencies of 5 to 30 minutes that can stretch by a factor of 4 to 8 during structural network stress. On these bridges, Invarians provides a primary lever: by deferring during stressed windows, the agent reduces actual transit duration, not just initiation timing. The value is mechanically larger and quantitatively measurable.

Institutional RWA settlement workflows that adopt high-frequency cross-chain settlement operate on variable-latency bridges (CCIP for tokenized fund transfers, CCTP for stablecoin rebalancing, fast LP-based bridges for institutional DeFi flows). Institutional flows that operate on native 7-day bridges (maturity-based credit pools, term loan vaults, real estate fund T+30 redemptions) do so by design and have already accepted the 7-day exposure window as part of their settlement architecture.

The Invarians value proposition aligns with the variable-latency segment.

**Action taken**

`invarians-bridge-collector` service stopped and disabled on the VPS at approximately 2026-05-04 21:00 UTC. The collector will not restart at boot. Alchemy compute unit consumption attributable to native bridge monitoring ceases immediately.

```
sudo systemctl stop invarians-bridge-collector
sudo systemctl disable invarians-bridge-collector
```

CCIP and CCTP collectors continue to run unaffected (they are separate services).

**Data preservation**

The historical data already collected on `ans_bridge_signals` (native bridge batch posting cadence on Arbitrum-Ethereum, Base-Ethereum, Optimism-Ethereum since approximately 2026-03-17) is preserved in the database. The `bridge_thresholds` rows for native bridges (committed in Entry #027 with `calibration_method = 'event_based_p97_30d'`, P97 thresholds of 180s, 60s, 384s for ARB, BASE, OP respectively) remain in the table with `calibrated = true` and represent a historical baseline observability of native bridge batch posting cadence at the time of commitment.

No data is deleted. No re-write of historical entries. No retraction of the calibration methodology committed in Entry #027.

**Public narrative repositioning**

The Invarians public narrative (on `invarians-site/`, `agentnorthstar.com/calibration`, and associated documentation) shifts to position CCIP, CCTP, and fast bridges as the primary scope of the value lever. Native canonical bridges are repositioned as historical observability baseline (with documented calibration as a methodological reference) rather than as the central product surface.

This shift is consistent with the empirical observation that Invarians' marginal lever on protocol-immutable 7-day bridges is structurally limited, while its lever on variable-latency bridges is mechanically aligned with stress observability.

**Status:** ✅ Collector stopped 2026-05-04 21:00 UTC. Historical data and Entry #027 calibration retained for reference. Narrative repositioning to be executed across `invarians-site/` pages over the following days.
**Confidence:** High (decision based on protocol-mechanical reasoning, not on statistical uncertainty).
**Limitation:** None on the operational side (collector stopped, no ongoing CU consumption). The narrative repositioning across public-facing pages is the remaining execution task.

**Follow-up**

- Edge Function `attestation/v2/panel` update: remove native bridge entries from the live panel (or expose them with `calibrated: true, deprecated: true` annotation, decision pending). Target 2026-05-05.
- Detector `stress-events` reformulation: remove native bridge state as input dimension for event severity classification. Target 2026-05-05.
- Public narrative refonte: pages `index.html`, `products.html`, `roadmap.html`, `cre.html`, `faq.html`, `developers.html` and others on `invarians-site/`. Target 2026-05-09.
- Update `methodology.md` (this repo) with the variable-latency vs fixed-latency bridge distinction and the rationale for scope focus.
- Update `limitations_and_plans.md` (this repo) to reflect the abandoned native bridge scope and the variable-latency bridge focus.

---

## Entry #039 (2026-05-11): CCTP per-message Circle ECDSA attestation capture deployed

**Type:** Capability upgrade, follow-up to Entry #036 (CCTP preliminary P97/14d calibration on `circle_api_latency_ms`, 2026-05-04).
**Surface:** `invarians-cctp-collector` service on VPS, `ans_cctp_message_attestations` Postgres table, Edge Function `attestation` (Supabase), Cloudflare Worker `api.invarians.com`, SDK Python `invarians 0.8.0` on PyPI.
**Trigger:** Capability gap on CCTP signals. The aggregate flow (Entry #036) calibrated on `circle_api_latency_ms` (Circle attestation API health proxy) was acknowledged as a proxy. Direct per-message attestation latency and the Circle ECDSA signature itself were not captured, leaving the CCTP signal one verifiability layer short of full crypto-grounding.

---

**Reasoning**

CCTP messages are attested by Circle's Iris service: each message that completes attestation receives a 65-byte ECDSA secp256k1 signature emitted by Circle's attester. The signature is independently verifiable against Circle's published attester public key, which is a verification path distinct from the Invarians HMAC envelope. Capturing this signature per message anchors CCTP route signals in a cryptographic chain of trust native to the protocol, rather than in a proxy health metric.

The collector cycle (10 min) is shorter than source-chain finality on Ethereum-anchored chains (~13-19 min). A naive flow would lose any message whose Iris attestation becomes available after the cycle in which the source `DepositForBurn` was observed. A pending queue resolves this: each new burn is INSERTed into `ans_cctp_message_attestations` with `attestation_signature = NULL` and re-polled against Iris at every subsequent cycle until the signature is captured or 2 hours elapse.

**Action taken**

- New table `ans_cctp_message_attestations` (BYTEA `message_hash`, BYTEA `attestation_signature` nullable, BIGINT `attestation_latency_ms` nullable, TIMESTAMPTZ `first_observed_at` / `attestation_observed_at`). RLS active, service_role-only.
- New RPC `cctp_get_attestation_by_hash(text) → jsonb` with SECURITY DEFINER, accepting hex string, decoding to BYTEA server-side.
- Rust collector rewritten with pending-queue model: detect new `DepositForBurn`, compute `messageHash = keccak256(MessageSent.message)`, INSERT pending, then poll Iris for all pending of the route in parallel (concurrency-limited).
- Edge Function `attestation` extended with `GET /v2/cctp/attestation/{message_hash}`. Bridge entries now expose `capability_level: per_message_attested`, `crypto.anchor: circle_ecdsa`, `crypto.verifiable_via`, and structured `metrics` derived from per-message latencies (`attestation_latency_p90_s`, `attestation_latency_p99_s`, `attestation_success_rate_1h`).
- Cloudflare Worker `api.invarians.com` allowlist regex added for the new dynamic path.
- SDK Python `invarians 0.8.0` ships with `client.get_cctp_attestation(message_hash)`, `BridgeMetrics`, `BridgeCrypto`, `CapabilityLevel`, and `BridgeEntry.is_crypto_anchored` property. Backward-compatible with 0.7.x.

**Status:** ✅ Deployed end-to-end 2026-05-11. Confidence MEDIUM (per-message, EVM only). Solana CCTP routes (ETH ↔ SOL × 2) remain `Planned 2026-Q3` until the Solana RPC pipeline is integrated.
**Confidence:** MEDIUM, ten EVM CCTP routes captured per message with cryptographic signature.
**Limitation:** Polling cadence introduces an upper-bound bias on `attestation_latency_ms` of up to one cycle period (10 min). Documented in `limitations_and_plans.md §2.4`. Not a calibration defect, transparent to auditors.

---

## Entry #040 (2026-05-12): CCIP per-message capture deployed via messageId matching

**Type:** Capability upgrade, follow-up to Entry #037 (CCIP preliminary calibration deferred 2026-05-04) and Entry #039 (symmetric CCTP per-message capture 2026-05-11).
**Surface:** `invarians-ccip-collector` service on VPS, `ans_ccip_messages` Postgres table, Edge Function `attestation` (Supabase), Cloudflare Worker `api.invarians.com`, SDK Python `invarians 0.9.0` on PyPI.
**Trigger:** Asymmetry between CCTP (now `per_message_attested` since Entry #039) and CCIP (still `aggregate`) was acknowledged as a known limitation. Additionally, a latent defect was confirmed: the pre-existing aggregate flow attempted to read `sequence_gap` from `topics[1]` of the `CCIPSendRequested` event, but this event has no indexed parameter; the field was `NULL` on every row for the prior three weeks.

---

**Reasoning**

CCIP exposes a natural per-message key in both directions of a lane: each `CCIPSendRequested` event emitted by the source OnRamp carries a bytes32 `messageId` at inner slot 12 of its ABI v1.2 tuple, and each `ExecutionStateChanged` event emitted by the destination OffRamp re-exposes the same `messageId` as an indexed `topics[2]`. Matching source against destination by `messageId` yields real per-message send-to-execute latency per lane per direction, replacing the aggregate proxy.

The same pending-queue pattern proven on CCTP applies: collector cycle (10 min) is shorter than typical CCIP end-to-end latency (a few minutes to tens of minutes depending on lane and source-chain finality). Each new `CCIPSendRequested` is INSERTed as a pending row in `ans_ccip_messages` with `dest_tx_hash = NULL`. At every subsequent cycle, destination OffRamp logs are scanned for `ExecutionStateChanged` events matching pending messageIds. Matched rows are UPDATEd with destination tx hash, block number, block timestamp, and execution state. Expiry is 2 h.

The `sequence_gap = NULL` defect is resolved as a natural side-effect: `sequence_gap` is now derived from `MAX(sequence_number) - MAX(sequence_number) FILTER (executed)` over `ans_ccip_messages`, computed in the collector at every cycle.

**Action taken**

- New table `ans_ccip_messages` (BYTEA `message_id` UNIQUE, source send metadata: sender, receiver, sequence_number, nonce, gas_limit, fee_token, fee_token_amount, source_tx_hash, source_block_*; destination metadata nullable until execute matched: dest_tx_hash, dest_block_*, execution_state). RLS active, service_role-only.
- New RPC `ccip_get_message_by_id(text) → jsonb` with SECURITY DEFINER, accepting hex string, decoding to BYTEA server-side.
- Rust collector rewritten with ABI v1.2 decoder (slot offsets cross-checked against a reference production transaction). Pending-queue flow on `ans_ccip_messages` mirrors the CCTP pattern.
- Edge Function `attestation` extended with `GET /v2/ccip/message/{message_id}`. CCIP bridge entries now expose `capability_level: per_message_attested`, `crypto.anchor: null`, and structured `metrics` derived from per-message data (`execute_latency_p90_s`, `sequence_gap`, `messages_confirmed_1h`).
- Cloudflare Worker `api.invarians.com` allowlist regex added for the new dynamic path.
- SDK Python `invarians 0.9.0` ships with `client.get_ccip_message(message_id)`. Backward-compatible with 0.8.x.

**Verification**

First live captures observed on 2026-05-12: one ETH → AVAX pending row (sequence 5300, source tx `0xd0630f...935b`) and one AVAX → ETH pending row on the regular destination scan. Endpoint `/v2/ccip/message/{messageId}` returns the full per-message row including ABI-decoded fields (source/dest chain selectors, sender, receiver, sequence_number, nonce, gas_limit, fee_token, fee_token_amount), confirming end-to-end correctness with production data.

**Status:** ✅ Deployed end-to-end 2026-05-12. CCIP `capability_level` reaches parity with CCTP. The `sequence_gap = NULL` defect (3-week duration) is naturally resolved.
**Confidence:** MEDIUM, ten EVM CCIP lanes captured per message. Solana CCIP (ETH ↔ SOL × 2) remains pending the Solana RPC pipeline integration.
**Limitation:** `crypto.anchor` for CCIP entries stays `null`. CCIP's native cryptographic anchor is the DON threshold-signed `CommitReport` (F+1 multi-sig over the batch Merkle root, with per-message Merkle inclusion proof), structurally different from CCTP's single-attester ECDSA. Capture of `CommitReport` events on the destination CommitStore is the next step (target: late May / early June 2026), which will upgrade CCIP `capability_level` from `per_message_attested` to `per_message_crypto_anchored`.

---

## Entry #041 (2026-05-20): Delta v3 per-chain precursors deployed, chain-type-exclusivity established empirically

**Type:** Primitive redesign, follow-up to Entry #033 (v2.0 panel launch with composite drift block, 2026-04-30).
**Surface:** Postgres table `delta_precursors_calibration` + view `v_delta_precursors_panel` (Supabase), Edge Function `attestation/index.ts` (per-entry `precursors[]` array), SDK Python `invarians 0.10.0` on PyPI, public research note on `invarians.com`.
**Trigger:** Empirical re-evaluation of the v2.0 composite Delta block (`drift.structural`, `drift.demand` and their `_magnitude_delta` companions) against documented bridge stress on 2025 corpora. The canonical aggregation did not produce a validated agent-orientation signal under strict multiple-testing-corrected validation.

---

**Empirical campaign**

A 648-configuration grid was run twice independently, once on the ETH-ARB-CCTP 2025 corpus and once on the ETH-OP-CCTP 2025 corpus. Each grid spans four strategy families: single-axis with three percentiles × two K values × four lead horizons (288 configurations), multi-axis grouped union/voting predictors (64), alternative narrower outcomes (192), ML logistic regression on 24 features (8 configurations after H1/H2 split), and cross-chain direction-aware predictors (96). Each configuration is evaluated with 500 placebo permutations, then Benjamini-Hochberg FDR correction is applied within each family and across the 648 combined. Survival criterion: combined FDR p-adjusted < 0.05 AND lift >= 1.5x.

**Three tests**

1. **ARB grid → 6 survivors.** On the ETH-ARB-CCTP corpus, six configurations survive both filters, with lifts 1.53 to 2.36x. Four target the narrower outcomes `latency_high_only` or `bs2_only`, one is a cross-chain prediction (`bridge_arb_to_eth`). The strongest is `arb_struct_seq_publish_latency_shift` (K=2, pctl=0.90, lead 3h, lift 2.36x).

2. **OP grid → 1 survivor.** On the ETH-OP-CCTP corpus, run independently with the same 648-configuration architecture, exactly one configuration survives: `eth_struct_continuity_shift` (K=2, pctl=0.95, lead 6h, outcome `bridge_stress_full`, lift 3.72x, combined FDR p-adjusted 0.000).

3. **Cross-corpus tests, both directions.**
   - The six ARB survivors were applied to the OP panel by axis substitution (arb_* renamed op_*), outcome substitution (latency / BS2 on the ETH-OP-CCTP corridor), with no parameter re-tuning. None of the six holds: all four targeting `latency_high_only` produce lift 0.00 (positive base rate on OP too low at 9 hours per year), the eth_demand_tx survivor produces lift 1.11 (p=0.35), the cross-chain survivor produces lift 1.42 (p=0.36). All FAIL the lift >= 1.5x AND p < 0.05 criterion.
   - The OP survivor (`eth_struct_continuity_shift`) was applied to the ARB panel without re-tuning. Result: lift 0.83 (below unconditional baseline), placebo p-value 0.74. FAIL.

**Reading**

The three tests converge to a single empirical conclusion. Each chain produces its own validated Delta precursor configurations on its own corpus, and these configurations do not transfer when applied to a chain with a different execution typology. ARB (Nitro rollup, sub-second blocks, SequencerInbox event-based batches, high CCTP throughput) and OP (OP Stack rollup, 2-second blocks, BatchInbox EOA-based batches, moderate CCTP throughput) operate on distinct substrate dynamics. A predictor calibrated on one captures the dynamics of that substrate, not a regularity that crosses substrates. Delta calibration is chain-type-exclusive.

This is consistent with the substrate physics. A signal that transferred universally across these typologies would have warranted close scrutiny rather than this one.

**Action taken**

- New Postgres table `delta_precursors_calibration` with primary key `(chain, axis, k_consecutive_hours, lead_hours, outcome_category)`. Seven rows seeded: six on `arbitrum` (all `cross_chain_status: FAIL_on_optimism`), one on `optimism` (`cross_chain_status: FAIL_on_arbitrum`). RLS active, service_role-only.
- New view `v_delta_precursors_panel` exposes the calibration rows to the Edge Function.
- Edge Function `attestation/v2/panel` extended: each L1/L2 entry now carries a `precursors[]` array populated by joining `v_delta_precursors_panel` on `chain`. Each precursor element exposes `axis`, `fires`, `current_smd`, `smd_threshold_value`, `k_consecutive_hours`, `pctl_threshold`, `lead_hours`, `outcome_category`, `bridge_corridor`, `baseline_lift`, `baseline_p_adj`, `baseline_precision`, `baseline_alert_rate`, `cross_chain_status`, `cross_chain_lift`, `cross_chain_placebo_p`, `calibrated_at`. The v2 `drift.*` composite block remains exposed during the transition release window for backward compatibility.
- SDK Python `invarians 0.10.0` ships with `DeltaPrecursor`, `parse_delta_precursors`, `firing_precursors`. V2L1Entry and V2L2Entry extended with `precursors: List[DeltaPrecursor]`. Backward-compatible with 0.9.x (drift block still accessible via `entry.drift.demand` etc.).
- HMAC integrity preserved (precursors attached to entries are part of the signed payload).

**Status:** ✅ Deployed end-to-end 2026-05-20. Seven precursors live in production (six arbitrum, one optimism). Each carries its cross-chain status from the published article. The v2 drift block is kept in parallel for the transition release window.
**Confidence:** MEDIUM per-chain. The 648-configuration grid + combined BH FDR + cross-corpus test is the strongest validation discipline applied to a calibrated signal in this project. The MEDIUM rating reflects N = 2 corpora (ARB, OP); HIGH would require a third chain corpus producing an independent set of survivors and a cross-test grid completing the typology coverage.
**Limitation:** `smd_threshold_value` is currently null on six of seven rows (placeholder pending re-derivation from the production substrate pipeline rolling P90 over 30 days on `shift_magnitude_delta` per axis). The OP precursor carries its seeded threshold from the grid output (0.006711). Until thresholds are seeded for all rows, `fires` returns null on those rows, and the precursors expose only their calibration metadata (lift, lead, outcome, cross-chain status), not an actionable boolean. The metadata is itself useful for auditors and for agent design (it documents which axis, lead, and outcome are validated per chain). Re-derivation of the empirical P90 thresholds from production data is the next operational step.

**Documentation**

- Public research note: [invarians.com/blog/delta-recalibration-eth-arb-cctp-2025.html](https://invarians.com/blog/delta-recalibration-eth-arb-cctp-2025.html) (Delta calibration is chain-type-exclusive: ETH-ARB-CCTP and ETH-OP-CCTP, 2025)
- Public methodology: section "Delta v3 per-chain precursor registry" in `methodology.md` (this repo)
- Public limits: section "Per-chain precursor calibration and the universality question for Primitive 2" in `limitations_and_plans.md` (this repo)
- Consumer guide: [invarians.com/developers.html#consume-precursors](https://invarians.com/developers.html#consume-precursors) (three reference policies for agents reading precursors)

**Follow-up**

- Re-derive `smd_threshold_value` for the six arbitrum precursors on the production rolling P90 over 30 days; UPDATE table in place. Target: 2026 Q3.
- A formal statistical test of the universality of Primitive 2 (Regime + Bridge State) across chain typologies on a corpus of 50+ documented infrastructure-grade events with placebo permutation framework. Target: 2026 Q3 to Q4 follow-up study. Out of scope for the present entry.

---

## Entry #042 (2026-05-22): Public corpus-2025/ folder released, ETH-ARB-CCTP and ETH-OP-CCTP artefacts published

**Type:** Documentation release, follow-up to Entry #041 (V3 Delta per-chain precursors deployed, 2026-05-20).
**Surface:** `corpus-2025/` folder on this repository (`agentnorthstar/calibration`).
**Trigger:** The V3 Delta deployment in Entry #041 referenced an empirical campaign run on two 2025 corpora. The campaign artefacts (hourly panels, extraction queries, pipeline scripts, result outputs) were not yet published. The reproducibility claim in `methodology.md` §14.8 was therefore not externally verifiable. The present entry closes that gap.

---

**What is published**

The new folder `corpus-2025/` ships, organized by corridor:

- `corpus-2025/README.md`: top-level overview of why the two corridors were selected and the chain-type-exclusivity test design.
- `corpus-2025/eth-arb-CCTP/`: full corridor artefact set for ETH L1 to Arbitrum L2 via CCTP V1.
  - `README.md`, `METHODOLOGY.md`, `EVENTS_2025.md`, `API_CONTRACT.md`, `LIMITATIONS.md`.
  - `data/`: hourly panel for 2025 (parquet + csv + data dictionary), reconstructed bridge state.
  - `bigquery/`: extraction queries (5 SQL files + `queries.md`).
  - `scripts/`: six Python scripts (panel export, baseline and per-event plots, Delta full exploration, FDR grid search, reconfig A/B/C tests).
  - `results/`: JSON outputs and Markdown reports for the three Delta tests.
  - `plots/`: annual baseline plus five per-event figures.
- `corpus-2025/eth-op-CCTP/`: corridor artefact set for ETH L1 to Optimism L2 via CCTP V1.
  - `README.md`, `METHODOLOGY.md`, `LIMITATIONS.md`.
  - `data/`: OP hourly panel for 2025, reconstructed bridge state.
  - `bigquery/pull_op_cctp.md`: extraction query documentation.
  - `scripts/`: five Python scripts (BigQuery pull, panel construction, Delta full exploration, OOS validation in both directions).
  - `results/`: Delta full-grid outputs, ARB-to-OP transfer test, OP-to-ARB transfer test.
- `corpus-2025/shared/`: cross-corridor synthesis (event inventories for both chains, qualitative matrix universality study).

**Reading boundary**

The shipped artefacts cover three legitimate audit needs:

1. **Methodology audit**: read the per-corridor `METHODOLOGY.md`, the BigQuery query texts in `bigquery/`, and the script source code in `scripts/`. These document exactly what the panels and the validation tests compute.
2. **Result verification**: read the result JSON and Markdown files in `results/` and verify the published lifts, FDR-adjusted p-values, and cross-corridor outcomes against the shipped panel parquets. This does not require re-running the pipeline.
3. **End-to-end re-execution**: the Python scripts depend on an internal helper package (`lib/`) that is not shipped. The shipped panels and queries are sufficient for any external party to rebuild a comparable pipeline from public BigQuery data without that helper.

**Action taken**

- Created `corpus-2025/` folder with 53 files (3 corridor MD sets, 4 binary data files, 11 Python scripts, 5 SQL files, 11 JSON outputs, 8 Markdown reports, 6 PNG plots, 5 internal MDs).
- Patched `methodology.md` §14.8 to point at the corpus and clarify the helper-package boundary. Methodology footer bumped from v0.7 to v0.8.
- No change to the v2.0 API behavior, no change to the calibration parameters of any chain. This entry is documentation-only.

**Status:** ✅ Released 2026-05-22 on `agentnorthstar/calibration`. Reproducibility claim from Entry #041 §14.8 is now externally verifiable on the result level; pipeline-level re-execution remains scoped to consumers willing to derive comparable helpers.
**Confidence:** N/A (documentation release, no calibration change).
**Limitation:** The internal `lib/` helper package is not shipped. Consumers who want a turn-key re-execution of the pipeline must derive equivalent helper functions from the methodology. The shipped result artefacts (parquets + JSON + reports) allow verification without that.
**Follow-up:** None tied to this entry. Future corridor studies (e.g., ETH-POL via variable-latency bridge, mentioned in §14.7) will extend `corpus-2025/` with their own subfolder when calibrated.

---

## Entry #043: Bridge state methodology rewritten from statistical to structural — `BRIDGE_STATE_STRUCTURAL_v1` locked

**Type:** Methodology change, supersedes the prior P97-on-latency approach for CCTP V2 and CCIP V1.5 / V1.6 surfaces (Entry #036 for CCTP V1, the ETH-POL CCTP V2 protocol identifier `BS_CALIBRATION_v1` for V2). Prepares a coordinated migration of `bridge_thresholds` rows and the Edge Function classification rule.
**Surface:** `bridge_state_methodology.md` (root of this repository), prospective changes to `bridge_thresholds` schema usage, Edge Function `attestation/index.ts`, SDK Python.
**Trigger:** Internal audit identified that the prior approach — computing a P97 quantile on `attestation_latency_p90_s` over a corpus window and labeling the binary classification a *bridge state* — is conceptually a *Bridge Latency State*, not a *Bridge Reliability State*. The externally testable outcomes attached to Element 2 (BS1/BS2 stability) are *attestation failure rate, fast-mode fallback rate, stuck-funds events* — not latency in any quantile. The protocol identifier of the prior CCTP V2 calibration, `BS_CALIBRATION_v1` (Ed25519-signed, OpenTimestamps-anchored, with four mode-suffixed thresholds seeded on ETH-POL CCTP V2: 1132.79 s, 12201.56 s, 1115.15 s, 78523.85 s), is preserved as a candidate *latency precursor* under a successor protocol `LATENCY_PRECURSOR_v1`, to be validated by independent empirical lift against the structural BS2 outcome defined below.

---

**Reasoning**

A bridge state classification labelled BS1 or BS2 must answer the proposition the consuming agent actually decides on. For RWA cross-chain settlement workflows, that proposition is *the transfer will settle within its contractual envelope*. A P97 quantile on latency answers a different proposition: *the latency on this aggregation window lies in the upper tail of the 2025 distribution of latencies*. The two are not equivalent.

The cross-chain protocols Invarians observes — CCTP V2 (Circle ECDSA attestation) and CCIP V1.5 / V1.6 (Chainlink DON consensus) — both expose a set of contractual invariants that, when violated, constitute a real failure of the transfer to honor its envelope. These invariants are observable on the existing aggregation rows (`ans_cctp_v2_route_signals`, `ans_ccip_messages`). They are binary or near-binary by protocol design, not statistical distributions.

For CCTP V2 the four invariants are:

| # | Invariant | Observable | Pre-engaged tolerance |
|---|---|---|---|
| I1 | Attestation delivered | `attestation_success_rate` | `>= 0.995` |
| I2 | Requested mode honored | `mode_fallback_rate` | `<= 0.05` |
| I3 | Instrument valid | `confounded_by_iris_downtime` | `== false` |
| I4 | Sample sufficient | `n_observations` | `>= 5` |

For CCIP V1.5 / V1.6 the four invariants are symmetric: `execution_success_rate_1h >= 0.995`, `rmn_cursed == false`, instrument validity, minimum sample size.

The tolerances are pre-engaged mechanically. `0.995` is the institutional infrastructure SLA tier-1 floor (four nines target, three-and-a-half nines tolerance for the 1-hour window). `0.05` on `mode_fallback_rate` is the operational margin admitting one Fast-to-Standard escalation per twenty requests, consistent with Circle CCTP V2 documentation framing the fallback as a *rare high-load event*. `n_observations >= 5` is the minimum sample below which a single failure ratio (0.20) is noise rather than signal. The tolerances are committed in the methodology document prior to observing any of the observables on the production database or on the 2025 corpus; any adjustment requires rotation to a successor protocol with its own pre-engagement signature.

The state computed by AND-conjunction of the holding invariants is mode-agnostic at the level of the `BridgeEntry.id` exposed in the API: a single corridor `ethereum-polygon/cctp` resolves to `BS1`, `BS2`, or `UNAVAILABLE` based on whether the latest aggregation row for that corridor satisfies all invariants. The four mode-suffixed rows previously seeded under `BS_CALIBRATION_v1` are retired from `bridge_thresholds`.

**Action taken**

- Methodology `BRIDGE_STATE_STRUCTURAL_v1` produced at `bridge_state_methodology.md`, root of this repository, version 1.0. Locked with three independent Ed25519 signatures in namespace `invarians_calibration_bridge_state_structural_v1` (`signatures/bridge_state_methodology.md.sig.{1,2,3}`, public keys at `signatures/public_keys/ed25519_bs_structural_v1_{1,2,3}.pub`) and OpenTimestamps-anchored on Bitcoin (`signatures/bridge_state_methodology.md.sig.{1,2,3}.ots`).
- The methodology covers CCTP V2 (§3) and CCIP V1.5 / V1.6 (§4) uniformly, with explicit deferral of a fifth burn-to-mint reorg-tracking invariant to `v1.1`.
- The four P97 latency thresholds previously seeded under `BS_CALIBRATION_v1` are reclassified as candidate inputs to `LATENCY_PRECURSOR_v1`, retained in their signed corpus output `corpus-2025/eth-pol-CCTP-v2/results/BS_CALIBRATION_ETH_POL_CCTP_V2.json` (Ed25519 + OpenTimestamps anchored, see prior commit `00006eb` on `corpus-2025/eth-pol-CCTP-v2/`) as pre-validation artefact, not as production-deployed signal.

**Action pending (deployment phase, post-lock)**

- Migration SQL: DELETE the four mode-suffixed rows (`ethereum-polygon/cctp/fast`, `ethereum-polygon/cctp/standard`, `polygon-ethereum/cctp/fast`, `polygon-ethereum/cctp/standard`), restore the two mode-agnostic rows (`ethereum-polygon/cctp`, `polygon-ethereum/cctp`) with `calibrated = true`, `calibration_method = 'BRIDGE_STATE_STRUCTURAL_v1'`, `threshold_bs1_s = NULL`.
- Refactor Edge Function `attestation/index.ts` to evaluate the four CCTP V2 invariants on the latest `ans_cctp_v2_route_signals` row per corridor, classifying `BridgeEntry.state` directly without a per-row threshold lookup. The same refactor applies the four CCIP J-series invariants and lifts CCIP lanes out of the deferred state described in `methodology.md` §13.4.
- Upgrade SDK to surface a `latency_precursor` field on `BridgeEntry` once `LATENCY_PRECURSOR_v1` is locked, distinct from the structural `state` field.

**Verification protocol for external readers**

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_bs_structural_v1_signer_<i> \
  -n invarians_calibration_bridge_state_structural_v1 \
  -s signatures/bridge_state_methodology.md.sig.<i> < bridge_state_methodology.md

ots verify signatures/bridge_state_methodology.md.sig.<i>.ots
```

The signers of `BRIDGE_STATE_STRUCTURAL_v1` are independent of the signers of the prior corpus Step 0/2/3 keys. The three public keys are recorded under `signatures/public_keys/ed25519_bs_structural_v1_{1,2,3}.pub`.

**Status:** Methodology locked and published. Production migration deferred until the migration SQL and Edge Function refactor are produced and applied.
**Confidence:** HIGH on the methodology design (mechanically justified by protocol contract, not by data distribution). The empirical false-positive / true-positive rate of the rule will be measured against `LATENCY_PRECURSOR_v1` validation and against documented incidents (Polygon Heimdall consensus bugs, USDe cascade) once the rule is deployed on production data.
**Limitation:** The fifth invariant — `messages_burned == messages_minted` over a cumulative window — is deferred to `BRIDGE_STATE_STRUCTURAL_v1.1` pending the production SQL view that joins source `DepositForBurn` to destination `MessageReceived` by `nonce` over the settlement-bounded window. The current four invariants do not yet capture *stuck funds* as a distinct trigger; they capture upstream attestation and mode-honoring violations that would precede a stuck event.

---

## Entry #044: Methodology amendment v1.0 to v1.1 — SLA gating on denominators of I1 and I2

**Type:** Methodology amendment, follow-up to Entry #043 (BRIDGE_STATE_STRUCTURAL_v1 locked) and to first-production observation of the structural rule against the live `ans_cctp_v2_route_signals` rows.
**Surface:** `bridge_state_methodology.md` v1.0 to v1.1, prospective patch to `bridge/cctp-v2-collector/src/aggregator.rs`, no immediate SDK change.
**Trigger:** First live evaluation of the structural rule against the production database revealed a denominator bias in the observables that back invariants I1 (`attestation_success_rate`) and I2 (`mode_fallback_rate`). The aggregator computes both ratios over the full 1-hour window of `ans_cctp_v2_message_attestations`, including messages whose nominal attestation envelope has not yet elapsed at observation time. A Fast message burnt eight seconds ago is `attested = false` not because the protocol failed but because the message is in flight; counting it in the denominator drives the ratio toward zero on low-volume routes and produces false-positive BS2 verdicts. The bias was confirmed against the live panel: ten of ten CCTP V2 corridors with healthy Iris (`circle_api_status = OK`, `confounded_by_iris_downtime = false`) reported `attestation_success_rate` between 0.60 and 0.89 on routes with two to nine recent messages — values inconsistent with the absence of any documented degradation in the corresponding window.

---

**Reasoning**

I1 and I2 are invariants on the protocol's *contract*, not on instantaneous snapshots. The protocol's contract is *messages of mode `m` shall be attested within their nominal envelope*. A message younger than the nominal envelope is neither attested nor in default; it is in-flight. Including it in the denominator of either ratio treats normal in-flight messages as failures.

The fix is to gate both denominators by a per-mode SLA, fixing the SLA values mechanically before observing the production data:

| Mode | `SLA_mode` | Justification |
|---|---|---|
| Fast | 120 s | Nominal envelope 8-30 s per Circle CCTP V2 docs. Margin x4 over upper bound. |
| Standard | 7200 s (2 h) | Nominal envelope 13-19 min (Ethereum-side originator) to 30-60 min (Polygon-side originator). Margin x2 over worst-case nominal upper bound. |

Only messages with `source_block_timestamp < NOW() - SLA_mode` are eligible for the I1 and I2 computations. Messages younger than `SLA_mode` are excluded from the denominator.

The revised formulas are:

```
attestation_success_rate = COUNT(attested AND source_block_ts < NOW() - SLA_mode)
                         / COUNT(source_block_ts < NOW() - SLA_mode)

mode_fallback_rate       = COUNT(mode_requested = 'fast'
                                 AND source_block_ts < NOW() - SLA_fast
                                 AND mode_executed = 'standard')
                         / COUNT(mode_requested = 'fast'
                                 AND source_block_ts < NOW() - SLA_fast
                                 AND mode_executed IS NOT NULL)
```

The denominators may be zero for low-volume corridors within a 1-hour aggregation window, in which case the row returns NULL on the affected observable and the structural rule resolves the direction's verdict on the other mode (or to UNAVAILABLE if neither mode has an eligible sample).

I4 (`n_observations >= 5`) is interpreted on the post-gating `n_eligible` count, not on the raw window count. The 1-hour aggregation window itself is unchanged; only the denominators of I1 and I2 are gated.

**Action taken**

- `bridge_state_methodology.md` amended to v1.1 with the addition of §3.5 (SLA gating). Hash recomputed; the v1.0 hash `65357b46a0f0c9ed51ec61f87833f168e88c7904211b7729506b30be2fef21e2` is superseded by the v1.1 hash `0733932048d3fc539f5a938a505fd02f2589b1ea839f26273ec36a57ea33737d`. The v1.0 signatures and OpenTimestamps proofs remain valid for the v1.0 state of the document; they are preserved in `signatures/bridge_state_methodology.md.sig.{1,2,3}` and the associated `.ots` files.
- v1.1 locked with three independent Ed25519 signatures in namespace `invarians_calibration_bridge_state_structural_v1_1` using the same three keys as v1.0 (`ed25519_bs_structural_v1_{1,2,3}.pub`). Signatures stored at `signatures/bridge_state_methodology.md.v1_1.sig.{1,2,3}` and OpenTimestamps-anchored on Bitcoin (`signatures/bridge_state_methodology.md.v1_1.sig.{1,2,3}.ots`).

**Action pending (deployment phase)**

- Patch `bridge/cctp-v2-collector/src/aggregator.rs` to apply the SLA gating in the SQL CTE. The constants `SLA_FAST_SECS = 120` and `SLA_STANDARD_SECS = 7200` are hardcoded in the Rust module to match v1.1.
- Recompile the Rust collector and redeploy the `invarians-cctp-v2-collector` systemd service on the VPS.
- The next aggregation cycle (10 min interval) begins writing corrected `attestation_success_rate` and `mode_fallback_rate` values into `ans_cctp_v2_route_signals`. The Edge Function code does not change; only the upstream values change.

**Verification protocol for external readers**

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_bs_structural_v1_1_signer_<i> \
  -n invarians_calibration_bridge_state_structural_v1_1 \
  -s signatures/bridge_state_methodology.md.v1_1.sig.<i> < bridge_state_methodology.md

ots verify signatures/bridge_state_methodology.md.v1_1.sig.<i>.ots
```

The three public keys (same as v1.0) are recorded under `signatures/public_keys/ed25519_bs_structural_v1_{1,2,3}.pub`. The namespace `invarians_calibration_bridge_state_structural_v1_1` distinguishes v1.1 signatures from v1.0 signatures cryptographically.

**Status:** Methodology v1.1 locked and published. Collector patch deferred to a separate commit once the Rust changes are written and tested.
**Confidence:** HIGH. The SLA values 120 s (Fast) and 7200 s (Standard) are mechanically justified by the Circle CCTP V2 documented nominal envelopes plus an explicit operational margin (x4 and x2 respectively). Both values are pre-engaged before any aggregator change is observed against the production database.
**Limitation:** SLA gating reduces the post-gating sample size on low-volume corridors. Routes with fewer than five messages older than `SLA_mode` within a 1-hour window will report `UNAVAILABLE` on the mode-specific evaluation. This is the intended behavior: a route with insufficient eligible sample is not classifiable, not classifiable as BS1 by default.

---

## Entry #045: Mode-classification bug — `min_finality_threshold = 0` was treated as Fast

**Type:** Implementation bug fix on the source-side mode classifier. No change to `BRIDGE_STATE_STRUCTURAL_v1.1` methodology — the spec is correct; the Rust function that translates the raw protocol parameter into the categorical `mode_requested` field was over-broad.
**Surface:** `bridge/cctp-v2-collector/src/routes.rs::classify_mode_requested`. Affects every row inserted into `ans_cctp_v2_message_attestations` from now on, and indirectly every aggregation row in `ans_cctp_v2_route_signals`.
**Trigger:** First live evaluation of `BRIDGE_STATE_STRUCTURAL_v1.1` against the production database reported three corridors in `BS2` with `mode_fallback_rate` between 12.5 % and 79.8 % (ethereum-polygon, base-ethereum, ethereum-base, plus 100 % artefacts on polygon-ethereum and avalanche-ethereum). The pattern was uniform: every reported fallback had `min_finality_threshold_requested = 0` and `min_finality_threshold_executed = 2000`, with average latency in the Standard nominal envelope (~17 min). Cross-tabulation `(req, exec)` showed: messages with `req = 1` or `req = 1000` were always executed at `1000` (Fast nominal); messages with `req = 0` were always executed at `2000` (Standard nominal). No mixed pattern, no genuine Fast→Standard escalation observed across any of the four BASE-corridor or POL-corridor BS2-reporting routes.

---

**Reasoning**

CCTP V2 exposes a per-message `minFinalityThreshold` parameter on the source-chain `depositForBurn` call. Circle documentation frames the field as follows: a low value (1..=1000) signals a Fast Transfer request, a high value (2000) signals a Standard Transfer request, and the absence of an explicit preference manifests on-chain as `minFinalityThreshold = 0`. Circle's attestation pipeline treats `0` as "any finality"; in practice it delivers Standard (hard finality) for those messages, since that is the safer default and does not require the additional Fast-transfer infrastructure path.

The classifier `classify_mode_requested(u32)` was written with a single inequality:

```rust
if min_finality_threshold <= 1000 { "fast" }
else if min_finality_threshold == 2000 { "standard" }
else { "other" }
```

This treats `0` as `"fast"` because `0 ≤ 1000`. The classifier is mechanically correct on the inequality but semantically over-broad: a message with `minFinalityThreshold = 0` did not request Fast. The caller expressed no preference, and Circle's default behavior is Standard. Counting these messages in the Fast cohort and subsequently observing their Standard execution as "fallback" is a measurement artefact, not a protocol event.

Production observation on the BASE corridor confirmed the pattern unambiguously: 79 of 89 Fast-classified messages on `ethereum→base` and `base→ethereum` over the prior two hours had `req = 0` and `exec = 2000`, with no exception. The 10 messages with `req ∈ {1, 1000}` were all executed at `exec = 1000`. There is no genuine Fast→Standard escalation on the corridor; the protocol is honoring the request type it was given. The `BS2` verdicts produced under `BRIDGE_STATE_STRUCTURAL_v1.1` I2 (`mode_fallback_rate ≤ 0.05`) on these corridors are therefore false positives caused by the upstream classification.

The methodology of `BRIDGE_STATE_STRUCTURAL_v1.1` is not at fault. Its specification of I2 implicitly assumes that `mode_requested = 'fast'` denotes an explicit Fast request. The implementation that produces that label must enforce the same implicit semantic.

**Action taken**

- `classify_mode_requested` is updated to a `match` expression with an explicit handling of the `0` case:

  ```rust
  match min_finality_threshold {
      0           => "other",       // no preference; not a Fast request
      1..=1000    => "fast",        // explicit Fast request
      2000        => "standard",    // explicit Standard request
      _           => "other",       // atypical, excluded from corridor scope
  }
  ```

- The same function is reused on `finality_threshold_executed` (from Iris) to derive `mode_executed`. Iris returns only `1000`, `2000`, or `NULL` in practice; the new `0 → "other"` branch is therefore observed exclusively on the source-side requested threshold and does not change `mode_executed` for any historical or future row.

- The collector is rebuilt and redeployed. From the next cycle on, messages with `min_finality_threshold_requested = 0` are inserted with `mode_requested = 'other'`. They no longer contribute to the Fast denominator nor to the Standard denominator of any subsequent aggregation row. The Edge Function filters on `mode_requested IN ('fast', 'standard')` and ignores `'other'`, so the `BridgeEntry` evaluation under `BRIDGE_STATE_STRUCTURAL_v1.1` no longer sees those messages.

**Historical data**

Past rows in `ans_cctp_v2_message_attestations` with `mode_requested = 'fast'` and `min_finality_threshold_requested = 0` remain unchanged for reproducibility of the production observation that triggered this entry. They are tagged for analysts via the raw field; consumers running ad-hoc cohort analyses should filter accordingly. Past rows in `ans_cctp_v2_route_signals` aggregated over the affected window are kept as-is; the next cycle of the aggregator produces corrected rows and the false-positive BS2 verdicts disappear within one observation interval.

**Verification**

Three Supabase Studio queries documented the bug end-to-end on 2026-06-01:

1. Distribution of `min_finality_threshold_executed` over the last 6 hours, all corridors: 1000 → fast (284 rows), 2000 → standard (400 rows), NULL (20 rows). Iris returns only canonical values; no malformed input.
2. BASE-corridor Fast-requested distribution over the last 2 hours grouped by `(mode_executed, req_thr, exec_thr)`: 79 rows at `(req=0, exec=2000)` versus 22 rows at `(req∈{1,1000}, exec=1000)`. No mixed pattern.
3. Sample of ten Fast→Standard "escalated" rows on the BASE corridor: every single row carried `req_thr = 0`, latency in the 800-1200 s range (Standard nominal), no genuine fallback.

After redeployment, the same three queries on a one-hour-fresh window must show `mode_requested = 'other'` for `req = 0` rows and `mode_fallback_rate` at zero on the BASE corridor (no remaining "fallback" once the artefact is removed).

**Status:** Patch applied to source, redeployed on the production collector VPS. The next aggregation cycle (interval 600 s) writes corrected rows. The Edge Function code is unchanged; only the upstream classification changes.
**Confidence:** HIGH. The cross-tabulation `(req, exec)` is unambiguous: the bug is mechanical, the fix is mechanical, no statistical inference is required.
**Limitation:** Aggregation rows already written with the buggy classifier remain in `ans_cctp_v2_route_signals`. They are not retroactively recomputed. Any consumer running a post-mortem on the BS2 verdicts of 2026-06-01 should be aware of the discontinuity at the redeployment timestamp.

---

## Entry #046: Retroactive reclassification of historical Fast/req=0 rows

**Type:** One-off data remediation on the message-level table, follow-up to Entry #045. No code or methodology change.
**Surface:** `ans_cctp_v2_message_attestations` rows historically inserted with `mode_requested = 'fast'` and `min_finality_threshold_requested = 0`.
**Trigger:** Immediately after the collector redeployment of Entry #045, the first two production aggregation cycles still reported `BS2` on the BASE corridors with `mode_fallback_rate` between 0.54 and 0.81. The cycles were inspecting a 1-hour rolling window of `ans_cctp_v2_message_attestations` rows that were still tagged `mode_requested = 'fast'` for the `req = 0` cohort, because the fix only applies to new inserts. Waiting one full hour for the buggy rows to roll out of the window would have left the BS verdicts inconsistent with the corrected classifier semantics during the entire window.

---

**Reasoning**

The classifier fix of Entry #045 is forward-only by design: the Rust code controls the value written at insert time, not the value of rows already in the table. The 1-hour rolling aggregation window of `aggregator.rs` reads every row whose `first_observed_at` falls in the last hour, regardless of when it was inserted. Until the buggy rows naturally exit the window, the aggregation continues to count them in the Fast cohort and to record their Standard execution as fallback. The remediation is to align the historical row tagging with the corrected semantics in one explicit, idempotent, documented statement.

The remediation does not alter any cryptographic-grade observable: the source-side `min_finality_threshold_requested` field, the destination-side `min_finality_threshold_executed` field, the source / destination tx hashes, the attestation signature, the timestamps — all of these are preserved. Only the derived categorical `mode_requested` is updated to match the value the corrected classifier produces for the same source observable. Any external auditor recomputing the categorical from the preserved raw observable would arrive at the same value.

**Action taken**

- Pre-check on the production database:

  ```sql
  SELECT COUNT(*) AS n_rows_to_reclassify
  FROM ans_cctp_v2_message_attestations
  WHERE mode_requested = 'fast'
    AND min_finality_threshold_requested = 0;
  ```

  Result: 806 rows. The cohort covers the entire production lifetime of the V2 collector since 2026-05-27 (six days), consistent with the observed Fast-traffic rate.

- Remediation statement applied to Supabase:

  ```sql
  UPDATE ans_cctp_v2_message_attestations
  SET mode_requested = 'other'
  WHERE mode_requested = 'fast'
    AND min_finality_threshold_requested = 0;
  ```

  806 rows updated. Distribution of `mode_requested` over the last two hours after the update:

  | mode_requested | n |
  |---|---|
  | fast | 124 |
  | other | 87 |
  | standard | 70 |

- The CCTP V2 collector service was restarted (`systemctl restart invarians-cctp-v2.service`), forcing an immediate aggregation cycle that recomputed `ans_cctp_v2_route_signals` rows from the corrected message-level table.

**Verification**

The first aggregation cycle after the restart produced 19 route_signals rows in 4.87 seconds. Live `/v2/panel` evaluation immediately after:

| corridor | state | status | fast_n | fast_fb |
|---|---|---|---|---|
| ethereum-polygon/cctp | BS1 | OK | 8 | 0.000 |
| arbitrum-ethereum/cctp | BS1 | OK | 32 | 0.000 |
| base-ethereum/cctp | BS1 | OK | 7 | 0.000 |
| ethereum-arbitrum/cctp | BS1 | OK | 11 | 0.000 |
| ethereum-base/cctp | BS1 | OK | 9 | 0.000 |
| polygon-ethereum/cctp | null | UNAVAILABLE | 3 | (n_eligible < 5) |
| avalanche-ethereum/cctp | null | UNAVAILABLE | 1 | (n_eligible < 5) |
| ethereum-avalanche/cctp | null | UNAVAILABLE | 2 | (n_eligible < 5) |
| ethereum-optimism/cctp | null | UNAVAILABLE | 1 | (n_eligible < 5) |
| optimism-ethereum/cctp | null | UNAVAILABLE | 1 | (n_eligible < 5) |

All previously reported BS2 verdicts on the BASE corridors and on ethereum-polygon are resolved to BS1. The corridors that fall in `UNAVAILABLE` do so under I4 (`n_eligible >= 5`) as specified in `bridge_state_methodology.md` v1.1 §3.5; they are not BS2 by default.

**Status:** Data remediation applied and verified. The Fast cohort denominator now contains only explicitly Fast-requested messages.
**Confidence:** HIGH. The cohort definition before and after the UPDATE is `min_finality_threshold_requested = 0`; the only column modified is the derived categorical `mode_requested`; the SQL statement is idempotent (running it again is a no-op). Raw fields are preserved for full auditability.
**Limitation:** `ans_cctp_v2_route_signals` rows aggregated under the buggy classifier between 2026-05-27 and 2026-06-01 are kept as-is. Any consumer running a post-mortem on the BS verdicts of that period must be aware that the underlying Fast cohort definition changed at the timestamp of this remediation.

---

## Entry #047: Substrate-shift precursors — distinction between latency outcome and `BS_STRUCTURAL_v1.1 BS2` outcome

**Type:** Methodological clarification, no code change, no migration. Records the disposition of two existing families of substrate-shift precursors against the new bridge-state definition, and announces a forthcoming pre-engagement protocol for the structural outcome.
**Surface:** documentation only. Affects `bridge_state_methodology.md` v1.1 §6 interpretation, the seven Delta-v3 precursors seeded by `migration_delta_precursors_v3.sql` in production, the nineteen substrate-shift candidates published in the matrix-and-drift article on the ETH-POL CCTP V2 corpus, and a new protocol to be locked.
**Trigger:** The transition of the bridge-state definition from `BS_CALIBRATION_v1` (statistical P97 on attestation latency, Entry #043 supersession) to `BRIDGE_STATE_STRUCTURAL_v1.1` (mechanical invariants with SLA gating on the denominator, Entry #043 and #044) changes the outcome variable that substrate-shift precursors are calibrated against. Two distinct cohorts of precursors are documented in this repository: the seven Delta-v3 precursors on Arbitrum (6) and Optimism (1), and the nineteen substrate-shift candidates on ETH-POL CCTP V2. Both cohorts were calibrated against latency-derived outcomes. Their continued exposure in the production API and on the public site requires an explicit disposition.

---

**Reasoning**

A substrate-shift precursor is a configuration that maps a substrate-matrix observable on Ethereum or on the destination chain to a binary alert at hour `t`, paired with an outcome label at hour `t + lead`. The outcome label is what the precursor is calibrated to anticipate. Three outcomes are present in the repository:

```
outcome (A)  latency_high_only        the corridor's hourly p90 attestation latency
                                       exceeds a corpus-derived percentile threshold

outcome (B)  bs2_only                  the legacy BS_CALIBRATION_v1 (statistical P97) BS2
                                       on the corridor's hourly p90 attestation latency

outcome (C)  bridge_*_to_*             a directional latency-derived outcome on the corridor
                                       (e.g. fast_pol_to_eth_stressed = p90 > 300 s)

outcome (D)  BS_STRUCTURAL_v1.1 BS2    the new mechanical outcome (success_rate < 0.995 OR
                                       mode_fallback_rate > 0.05, SLA-gated)
```

The seven Delta-v3 precursors carry `outcome_category` in {`latency_high_only`, `bs2_only`, `bridge_arb_to_eth`, `bridge_stress_full`}. All four are variants of outcomes (A), (B), (C) — none target outcome (D). The nineteen ETH-POL substrate-shift candidates target a derivative of (C): `fast_<direction>_stressed` and `standard_<direction>_stressed` defined as `p90_latency > 300 s` and `p90_latency > 3600 s` respectively. None target outcome (D) either.

Outcome (D) is the operationally-relevant outcome under `BRIDGE_STATE_STRUCTURAL_v1.1`. A precursor that anticipates outcome (A) anticipates a latency anomaly; a precursor that anticipates outcome (D) anticipates a protocol-contract violation. The two are correlated but not equivalent: a fast message that attests slowly within its envelope produces an outcome-(A) positive but an outcome-(D) negative; a fast message that escalates to Standard produces an outcome-(D) positive even at nominal latency.

**Disposition retained — option A (immediate, no statistical re-run)**

The seven Delta-v3 precursors and the nineteen ETH-POL substrate-shift candidates are **requalified as candidate inputs to a separate, narrower precursor surface** denoted `LATENCY_PRECURSOR_v1`. This surface is defined as:

```
LATENCY_PRECURSOR_v1.firing(t, corridor, direction, mode)
  ≡ corridor's hourly p90 attestation latency at t exceeds the corpus-2025 P97
    of the triplet's non-null hourly p90 distribution
    (the four thresholds locked in BS_CALIBRATION_ETH_POL_CCTP_V2.json under
     the BS_CALIBRATION_v1 protocol, signed Ed25519 ×3 and OpenTimestamps Bitcoin-anchored)
```

The seven and nineteen precursors remain statistically valid against their original outcome — the requalification is a renaming of their operational role, not a change of their pre-engaged statistics. Their `lift`, `baseline_p_adj`, `baseline_precision` fields stay identical. The labels `outcome_category` and `bridge_corridor` are interpreted as the latency-derived outcome family henceforth referred to as `LATENCY_PRECURSOR_v1`.

The production API exposure of these precursors (the `precursors[]` array on `L2Entry`) continues unchanged until a separate decision is taken. Consumers reading them must understand they predict latency anomalies on the corridor, not `BRIDGE_STATE_STRUCTURAL_v1.1 BS2` events.

**Forthcoming — option B (statistical re-run against outcome D)**

A separate protocol, `BS_STRUCTURAL_PRECURSORS_v1`, is drafted at `PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md` (root of this repository). It defines the statistical re-evaluation of substrate-shift configurations against outcome (D) on the locked 2025 ETH-POL CCTP V2 corpus, using:

- the same ten substrate-shift axes (5 ETH + 5 POL);
- a configuration grid of 768 entries (480 F0 single-axis, 128 F1 multi-axis grouped, 160 F4 cross-chain) restricted to the two Fast-mode outcomes (Standard-mode outcome is structurally NULL on a 1-hour window per `bridge_state_methodology.md` v1.1 §3.5);
- Benjamini-Hochberg FDR at α = 0.05, lift ≥ 1.5×, 500 placebo permutations;
- explicit power flags `LOW_POWER` (<30 positive outcomes) and `INSUFFICIENT_POWER` (<10, excluded from FDR family).

The protocol explicitly acknowledges that the empirical positive rate of outcome (D) on the 2025 corpus is unknown at lock time, and accepts the empty survivor set as a possible legitimate outcome. The script `scripts/compute_bs_structural_precursors_v1.py` implements the protocol and is signable independently.

When (and only when) the protocol is signed Ed25519 + OpenTimestamps anchored and the script is executed against the locked corpus, the resulting survivor set (zero or more substrate-shift configurations) will be exposed in the production API as `bs_structural_precursors[]` distinct from the existing `precursors[]`. Until then, no new precursor field is added.

**Forthcoming — extension to other CCTP V2 corridors**

`BS_STRUCTURAL_PRECURSORS_v1` is scoped to ETH-POL CCTP V2. The extension to ETH-ARB, ETH-BASE, ETH-OP CCTP V2 (rollup destinations) and to ETH-AVAX, ETH-SOL CCTP V2 (L1-to-L1 destinations) requires a per-corridor 2025 corpus that does not yet exist in the repository. Each successor corpus will trigger a successor pre-engagement (`BS_STRUCTURAL_PRECURSORS_v1_eth_arb`, etc.). This entry does not commit to a timeline for those corpora.

**Action taken**

- Disposition (option A) recorded in this entry. No production database change. No SDK change. No methodology amendment.
- `PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md` produced at the root of this repository, locked with three Ed25519 signatures in namespace `invarians_calibration_bs_structural_precursors_v1` (signatures and OpenTimestamps Bitcoin proofs at `signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md.sig.{1,2,3}`).
- `scripts/compute_bs_structural_precursors_v1.py` produced under `corpus-2025/eth-pol-CCTP-v2/scripts/` (in the corpus repository), not yet executed. Its SHA-256 will be embedded in the signed output JSON when the protocol is locked and executed.

**Status:** Methodological clarification recorded. Production state unchanged. Protocol B drafted, awaiting lock and execution.
**Confidence:** N/A (this entry contains no statistical claim of its own).
**Limitation:** The cohabitation of `LATENCY_PRECURSOR_v1` (existing) and `BS_STRUCTURAL_PRECURSORS_v1` (forthcoming) creates two precursor surfaces in the API design space. Consumers must distinguish: latency precursors predict latency anomalies; structural precursors predict protocol-contract violations. The two are co-existing, not substitutes. A future decision may restrict the public API to one surface, but that decision is not part of this entry.

---

## Entry #048: BS_STRUCTURAL_PRECURSORS_v1 — execution against the 2025 ETH-POL CCTP V2 corpus, empty survivor set

**Type:** Empirical result of `BS_STRUCTURAL_PRECURSORS_v1`. Follow-up to Entry #047 (protocol drafted) and to the locked pre-engagement at `PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md`. No code change, no methodology change.
**Surface:** `corpus-2025/eth-pol-CCTP-v2/results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json` (signed). The script `corpus-2025/eth-pol-CCTP-v2/scripts/compute_bs_structural_precursors_v1.py` is executed against the locked corpus parquets.
**Trigger:** Lock of the pre-engagement document with three Ed25519 signatures under namespace `invarians_calibration_bs_structural_precursors_v1` and OpenTimestamps Bitcoin anchor (cf. commit on `PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v1.md` and its `signatures/` artefacts at the root of this repository).

---

**Execution outputs**

The protocol is implemented byte-for-byte by `compute_bs_structural_precursors_v1.py`. The script:

1. Loads the locked Step 3 raw events parquet (`cctp_v2_events_2025_raw.parquet`, sha-256 recorded in the output JSON), pairs `MessageSent` against `MessageReceived` via on-chain `nonce` restricted to source/destination domains in `{(0, 7), (7, 0)}`, classifies `mode_requested` and `mode_executed` with the v1.1 classifier (see `calibration_log.md` #045).
2. Reconstructs the binary outcome `BS_STRUCTURAL_v1.1 BS2` per hour per Fast triplet (eth_to_pol, pol_to_eth) over the corridor-active window `2025-06-09 18:45 UTC → 2025-12-31 23:59 UTC`, with SLA gating (`SLA_fast = 120 s`).
3. Loads the locked substrate-shift baseline (`baseline.parquet`, sha-256 recorded), computes hourly shift-magnitude delta per axis, applies per-axis percentile thresholds fit over the non-January 2025 window.
4. Evaluates the configuration grid against the two Fast-mode outcomes; computes lift, placebo p-value over 500 label permutations.
5. Applies Benjamini-Hochberg FDR within family and combined; filters at `combined p < 0.05` and `lift ≥ 1.5×`.
6. Writes the signable JSON output.

The execution counters are:

| Field | Value |
|---|---|
| Paired ETH-POL messages | 6 583 |
| `mode_requested = 'fast'` (post v1.1 classifier) | 3 098 |
| `bs2_eth_to_pol_fast` evaluable hours (n_eligible ≥ 5) | 4 |
| `bs2_pol_to_eth_fast` evaluable hours (n_eligible ≥ 5) | 2 |
| Configuration grid total | 784 |
| Configurations at raw `placebo_p < 0.05` | 0 |
| Configurations surviving BH within-family FDR `α = 0.05` | 0 |
| Configurations surviving combined FDR AND lift ≥ 1.5× | 0 |
| Survivor set | `[]` (empty) |

The output JSON `BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json` is locked: three Ed25519 signatures under namespace `invarians_calibration_bs_structural_precursors_v1_output` (`signatures/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2.json.sig.{1,2,3}`), each OpenTimestamps-anchored on Bitcoin.

**Reading**

The empty survivor set is a legitimate outcome explicitly anticipated in the pre-engagement §10.2. Two independent constraints produce it:

1. **The outcome is rare.** Over 4 968 hours of corridor-active window, only six hours present a Fast-mode sample sufficient (n_eligible ≥ 5) to evaluate `BS_STRUCTURAL_v1.1 BS2`. The 1-hour aggregation window combined with the corpus-2025 Fast-traffic profile leaves most hours under the sample-sufficiency threshold. The pre-engagement §8 power flags `INSUFFICIENT_POWER` apply to every configuration in the grid, which excludes them from the FDR family.

2. **Where evaluable, the outcome is BS2 in 100 % of the cases.** All four hours of `bs2_eth_to_pol_fast` and both hours of `bs2_pol_to_eth_fast` are positive. This pattern is consistent with the sample-sufficiency gate selecting precisely the high-traffic hours, which coincide with windows of stress on the corridor, but the sample size precludes any lift estimation against substrate-shift predictors.

The structural interpretation, conditional on this run, is:

```
On the 2025 ETH-POL CCTP V2 corpus and under BRIDGE_STATE_STRUCTURAL_v1.1 with
the corpus-2025 Fast-traffic profile, substrate-shift configurations on ETH or POL
do not show statistically validated predictive lift against the protocol-contract
BS2 outcome.
```

This result does **not** disprove a relationship; it documents the absence of detectable lift under the pre-engaged statistical protocol on this particular corpus, with this particular outcome definition, with this particular 1-hour window, with this Fast-traffic volume. A higher-volume corridor, a longer aggregation window, or a different outcome definition may yield non-empty survivors. Each such variant requires its own locked pre-engagement.

**Discrepancy on the configuration grid total — recorded for transparency**

The pre-engagement document §5 lists `Total: 768 configurations`, computed as `F0 (480) + F1 (128) + F4 (160)`. The script enumerates 784 configurations:

- `F0` = 10 axes × 3 pctl × 2 K × 4 lead × 2 outcomes = 480 (matches the spec).
- `F1` = 14 (group, threshold) combinations × 2 K × 4 lead × 2 outcomes = 224. The textual description of the grid lists eight group definitions each carrying one or more voting thresholds, summing to fourteen (group, threshold) pairs. The arithmetic in the spec collapses this to `8 × …` and produces 128 instead of 224.
- `F4` = 2 cross-chain groups × 5 axes × 2 K × 4 lead × 1 outcome (fixed by cross-chain pair) = 80. The spec text says `× 2 outcomes` whereas the F4 construction by design pins the outcome to the partner chain (ETH-axes predict the pol_to_eth outcome; POL-axes predict the eth_to_pol outcome). The factor 2 outcomes is therefore incorrect; the correct count is 80, not 160.

The grid **definition** by family (axes, pctl, K, lead, outcomes, voting thresholds) is correctly described in the pre-engagement. Only the per-family arithmetic and the total are mis-summed. The script implements the grid definition literally and reports 784 in the signed JSON output.

The discrepancy is recorded here and not amended back into the pre-engagement document: the v1.0 SHA-256 anchored on Bitcoin remains the cryptographic record of what was committed to before the run. An amended `BS_STRUCTURAL_PRECURSORS_v1.0.1` may be published to correct the arithmetic prose; it would not affect the survivor set, which is empty independently of the count.

**Implications**

1. The hypothesis that the substrate matrix on Ethereum or Polygon anticipates protocol-contract violations on the ETH-POL CCTP V2 corridor — within the per-engaged statistical machinery on this corpus — is not supported.
2. The earlier finding of nineteen substrate-shift candidates against the latency-derived outcome (cf. `corpus-2025/eth-pol-CCTP-v2/` matrix-and-drift publication) is operationally on a different signal: the substrate may anticipate latency anomalies; it does not — on this corpus — anticipate the binary protocol-contract violation defined by `BRIDGE_STATE_STRUCTURAL_v1.1`.
3. Other CCTP V2 corridors (ETH-ARB, ETH-BASE, ETH-OP rollup; ETH-AVAX, ETH-SOL L1-to-L1) have not been evaluated; each requires its own locked corpus and its own pre-engaged protocol.

**Status:** Locked and published. The signed empty survivor set is the final result for the 2025 ETH-POL CCTP V2 corpus under `BS_STRUCTURAL_PRECURSORS_v1`.
**Confidence:** N/A on individual predictions (survivor set empty); HIGH on the methodological discipline of the run (every choice locked Ed25519 + OpenTimestamps Bitcoin-anchored before execution).
**Limitation:** Statistical power is intrinsically limited by the sparsity of evaluable hours (6 of 4 968). A protocol variant on a wider aggregation window, or on a longer-corpus successor (e.g. 2026 once accumulated), or on a more permissive sample-sufficiency floor would change the power profile and may yield different survivors. None of these variants is part of the present protocol.

---

## Entry #049: BS_STRUCTURAL_PRECURSORS_v2 — execution against the 2025 ETH-POL CCTP V2 corpus, empty survivor set on extended feature space

**Type:** Empirical result of `BS_STRUCTURAL_PRECURSORS_v2`. Successor to Entry #048 (`BS_STRUCTURAL_PRECURSORS_v1`). No code change beyond the locked v2 script, no methodology change.
**Surface:** `corpus-2025/eth-pol-CCTP-v2/results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json` (signed). The script `corpus-2025/eth-pol-CCTP-v2/scripts/compute_bs_structural_precursors_v2.py` is executed against the locked corpus parquets.
**Trigger:** Lock of the v2 pre-engagement with three Ed25519 signatures under namespace `invarians_calibration_bs_structural_precursors_v2` and OpenTimestamps Bitcoin anchor (cf. commit on `PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md` at the root of this repository). The v1 empty survivor set was scoped to a single predictor representation (SMD-of-shift). v2 extends the predictor space to cover the three mechanically distinct representations available in the locked Step 3 baseline parquet.

---

**Execution outputs**

The protocol is implemented by `compute_bs_structural_precursors_v2.py` (SHA-256 recorded in the output JSON) on the same locked Step 3 corpus as v1. The script reuses verbatim the outcome reconstruction of v1 (paired source-destination CCTP V2 messages via on-chain nonce, classifier v1.1, SLA gating). The configuration grid is extended as follows:

| Family | Representation | Count |
|---|---|---|
| F0a | A — SMD of shift (verbatim v1) | 480 |
| F0b | B — Signed shift level, polarity-separated tails | 960 |
| F0c | C — Drift composite level, polarity-separated tails | 384 |
| F1 | A — Multi-axis grouped, voting (verbatim v1) | 224 |
| F4 | A — Cross-chain (verbatim v1) | 80 |
| **Total** | | **2 128** |

| Field | Value |
|---|---|
| Paired ETH-POL messages | 6 583 |
| `mode_requested = 'fast'` (post v1.1 classifier) | 3 098 |
| `bs2_eth_to_pol_fast` evaluable hours (n_eligible ≥ 5) | 4 |
| `bs2_pol_to_eth_fast` evaluable hours (n_eligible ≥ 5) | 2 |
| Configuration grid total | 2 128 |
| Configurations at raw `placebo_p < 0.05` | 0 |
| Configurations surviving BH within-family FDR `α = 0.05` | 0 |
| Configurations surviving combined FDR AND lift ≥ 1.5× | 0 |
| Survivor set | `[]` (empty) |

Every configuration is flagged `INSUFFICIENT_POWER` because `n_positive_outcomes < 10` on both Fast triplets. The FDR family is therefore empty across all 2 128 configurations.

The output JSON `BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json` is locked with three Ed25519 signatures under namespace `invarians_calibration_bs_structural_precursors_v2_output` (`signatures/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json.sig.{1,2,3}`), each OpenTimestamps-anchored on Bitcoin.

**Reading — joint interpretation of v1 and v2**

v1 and v2 share the same outcome density on the corpus: six evaluable hours over 4 968. v2 extends the predictor space by a factor of 2.7× (784 → 2 128 configurations) covering the three mechanically distinct representations of the substrate matrix that the locked Step 3 baseline produces:

```
A — SMD of shift             |shift(t)| - |shift(t-1)|   (rate of change of absolute deviation)
B — Signed shift level       shift(t)                    (deviation itself, with polarity)
C — Drift composite level    drift_<axis-type>(t)        (axis-aggregated deviation)
```

The empty survivor set survives the extension. The mechanism is the power constraint, not the predictor coverage: regardless of the representation chosen, the post-`INSUFFICIENT_POWER` FDR family is empty because fewer than ten Fast-mode hours in the corridor-active window have a sample sufficient (n_eligible ≥ 5) to evaluate the outcome.

The joint interpretation is therefore:

```
On the 2025 ETH-POL CCTP V2 corpus, under BRIDGE_STATE_STRUCTURAL_v1.1
with a 1-hour aggregation window and the corpus-2025 Fast-traffic profile,
the substrate matrix (in any of the three representations available
from the locked Step 3 baseline) cannot be evaluated as a predictor of
the protocol-contract BS2 outcome because the outcome itself is too sparse
within the window for the statistical machinery to operate.
```

This is a "no data" result, not a "no signal" result. The pre-engagement protocol explicitly anticipates this case (cf. v2 §10.2 and v1 §10.2): the empty survivor set is the legitimate output when statistical power is insufficient. v1 and v2 jointly close the substrate-shift evaluation on the 2025 ETH-POL CCTP V2 corpus under the present outcome definition and window.

**Implications**

1. The substrate-matrix → `BRIDGE_STATE_STRUCTURAL_v1.1 BS2` mapping is empirically undetermined on this corpus. No directional claim is supported by the data.
2. The earlier latency-outcome candidates (nineteen substrate-shift configurations published in the corpus matrix-and-drift article) remain valid against their original latency-derived outcome but are silent on the structural outcome.
3. To obtain a statistically operative evaluation, three independent avenues exist:
   - **Wider aggregation window.** A protocol variant evaluating the outcome on a 3-hour or 6-hour window would raise the per-window `n_eligible` count and make Standard-mode triplets evaluable in parallel with Fast. The variant requires its own locked pre-engagement (`BS_STRUCTURAL_PRECURSORS_v3` for window 3h, `_v4` for 6h, etc.); it changes the operational semantics of the outcome and therefore is a distinct protocol from v1.1 in production.
   - **Longer-corpus successor.** Cumulative live data from the production `ans_cctp_v2_route_signals` table since 2026-05-27 (V2 collector deployment) provides a continuously growing observation window. A successor protocol evaluating substrate-shift precursors against the production-database outcome — once the cumulative volume reaches a few hundred BS2-positive hours — would have the statistical power that the 2025 corpus alone cannot provide.
   - **Higher-volume corridor.** The ETH-ARB, ETH-BASE, ETH-OP CCTP V2 corridors have substantially higher Fast-mode traffic than ETH-POL. Each requires its own locked corpus (extraction, decode, signing) and its own pre-engaged protocol. The first such corpus to be built will likely yield the first non-power-limited evaluation of substrate → BS_STRUCTURAL.

**Discrepancy on the configuration grid total — verified**

v2 reports `n_configurations_total = 2 128`, matching the spec §5 sum of `480 + 960 + 384 + 224 + 80 = 2 128`. No discrepancy between spec and code in v2, in contrast to v1 (cf. Entry #048).

**Status:** Locked and published. The signed empty survivor set is the final result of the v2 evaluation on the 2025 ETH-POL CCTP V2 corpus. Combined with v1, the substrate-matrix → BS_STRUCTURAL evaluation is closed on this corpus.
**Confidence:** N/A on individual predictions (no survivor); HIGH on the methodological discipline of the run.
**Limitation:** The corpus-2025 outcome density on a 1-hour window does not support statistical evaluation. Any forward-looking decision on substrate-shift precursors against `BS_STRUCTURAL_v1.1` requires a different corpus, a different window, or a different outcome density profile, each formalized in a fresh pre-engagement.

---

## Entry #050: `BRIDGE_STATE_STRUCTURAL_v1.2` — event-based invariant I5 for Standard-mode stuck detection

**Type:** Methodology amendment, v1.1 to v1.2. Adds one event-based invariant (`I5`) to the existing window-aggregated I1-I4. No change to the SLA gating of v1.1, no change to the outcome semantics, no change to CCIP J1-J4. The amendment closes the gap that left Standard-mode unevaluated by `BRIDGE_STATE_STRUCTURAL_v1.1`.
**Surface:** `bridge_state_methodology.md` v1.1 → v1.2. Future implementation slot in the forthcoming `bridge/classifier` Rust service (cf. `bridge/ARCHITECTURE_DEBT.md` in the backend repository). The Edge Function code is not modified in this entry; activation in production follows the implementation phase.
**Trigger:** v1.1 defined I1-I4 on a 1-hour rolling window with `SLA_standard = 7200 s`. The combination `(window = 1 h) ∧ (SLA_standard = 7200 s)` produces a structurally zero eligible sample for Standard-mode evaluation on every hour (the intersection of `[t-1h, t]` and `[..., t-2h]` is empty). Under v1.1, Standard-mode classification is therefore systematically `UNAVAILABLE`, and the direction-level state rests on the Fast-mode evaluation alone. This outcome conflicts with the corpus-anchored positioning of Standard as the canonical RWA settlement mode, documented in `products.html` and reflected in the SDK contract (`metrics` exposes the Standard mode, `observed_fast_mode` the Fast mode as subordinated). An external review summarized the conflict as: *a bridge state methodology that qualifies Fast and leaves Standard without verdict does not serve the audience the corridor is designed for.*

---

**Reasoning**

Three observations drive the resolution.

1. Latency in the Standard-mode envelope is not, by itself, an anomaly. The pairing convention of `compute_step3.py` line 236 in the locked 2025 ETH-POL CCTP V2 corpus (Step 3, signed Ed25519 + OpenTimestamps Bitcoin-anchored) sets a 48-hour upper bound on the plausible Standard latency for the Polygon-originated side. The P97 of the empirical hourly p90 distribution on the corridor-active 2025 window reaches 21 h 48 min on the `pol_to_eth` Standard triplet. A 21-hour latency is a high but legitimate point of the physical queue (Heimdall checkpoint cycle plus Ethereum finality plus Iris attestation), not a contract breach.

2. A window-based aggregation of Standard observables cannot distinguish *slow-but-normal* from *stuck* without introducing a latency threshold below the physical envelope. Any such threshold replicates the failure mode rejected in `BS_CALIBRATION_v1` (latency-as-state, calibration_log #043). The window approach is therefore exhausted for Standard under the BS_STRUCTURAL philosophy.

3. The unambiguous failure mode that an RWA agent acts on is *the message has not been attested within Circle's mechanical envelope*, regardless of where in the envelope it sits. This is a per-message binary fact, evaluable without windowing. The amendment encodes it directly as an event-based invariant.

**I5 definition (verbatim from v1.2 §3.6):**

```
I5 — Stuck Standard detection
  n_stuck_standard(t) ≡ COUNT(messages m where
                                m.mode_requested = 'standard'
                                AND m.attestation_signature IS NULL
                                AND m.source_block_timestamp < t − 48 h)

  I5 holds                  ⇔ n_stuck_standard(t) == 0
  I5 violated → BS2 trigger ⇔ n_stuck_standard(t)  > 0
```

The 48-hour cap is fixed mechanically by composition of the physical envelope (Heimdall checkpoint cycle worst case ~ 4 h, pathological Ethereum non-finalization ~ 24 h, Iris delivery upper bound ~ 1 h, margin × ~ 1.5). It is identical to the 48-hour latency upper bound already signed in the corpus pairing convention (`compute_step3.py` line 236, ETH-POL CCTP V2 Step 3). The cap is not adjustable on the basis of observed latency distributions; rotation to `v1.2.1` requires a documented protocol-level change from Circle (a published formal maximum settlement time on CCTP V2).

**Combine rule revised in §2:**

```
For each direction (source, dest) at evaluation instant t:

  if (confounded_by_iris_downtime == true)                  ⇒ UNAVAILABLE
  if (n_eligible_fast < 5)                                  ⇒ Fast verdict := UNAVAILABLE
                                                           else evaluate I1+I2 on Fast → BS1 or BS2

  evaluate I5 (event-based, independent of window)

  BS2(t)         ≡ (Fast verdict = BS2) OR (n_stuck_standard > 0)
  BS1(t)         ≡ (Fast verdict = BS1) AND (n_stuck_standard == 0)
  UNAVAILABLE(t) ≡ instrument confounded
                   OR (Fast verdict = UNAVAILABLE AND n_stuck_standard == 0)
```

The audience priority is encoded: a stuck Standard message cannot be silenced by a healthy Fast window. The two channels are operationally distinct and asymmetric: Fast is window-aggregated, Standard is event-based; both feed the same direction-level state.

**Discrimination properties of the 48-hour cap (deliberately designed):**

| Observed latency on a Standard message | I5 verdict |
|---|---|
| 17 min (Ethereum-originated nominal) | BS1 |
| 1 h 54 (Polygon-originated nominal, corpus 2025 median) | BS1 |
| 21 h 48 (Polygon-originated P97, corpus 2025) | BS1 |
| 47 h 59 (extreme physical stress, still inside cap) | BS1 |
| 48 h 01+ | BS2 |

The cap does not alarm on long latency per se. It fires only when a message has not been attested within an envelope that no composition of the protocol's physical steps can justify.

**Detection lag — accepted property:**

Because the cap is set at the outer envelope of the physical distribution, a genuinely stuck Standard message is confirmed `BS2` only at `source_block_timestamp + 48 h`. This delay is irreducible: discriminating *legitimately slow* from *stuck* earlier than this requires a threshold below the physical envelope. The pre-settlement signal an RWA agent consumes therefore comes from two channels of different temporal character — Fast window-aggregated invariants I1-I4 for rapid signaling, and Standard event-based invariant I5 as the late but definitive confirmation of an individual stuck message.

**Action taken**

- `bridge_state_methodology.md` amended to v1.2 at the root of this repository. The amendment adds §3.6 (I5 definition and justification), revises §2 (combine rule), updates the table of invariants in §3, requalifies the prior reorg-tracking note as a future I6 (burn-to-mint reconciliation, deferred), and adds a v1.2 entry to the footer change log. The v1.1 SHA-256 of the document was `0733932048d3fc539f5a938a505fd02f2589b1ea839f26273ec36a57ea33737d`; the v1.2 SHA-256 is recorded in the verification block below.
- v1.2 locked with three independent Ed25519 signatures in namespace `invarians_calibration_bridge_state_structural_v1_2` using the same three keys as v1.0 and v1.1 (`ed25519_bs_structural_v1_{1,2,3}.pub`). Signatures stored at `signatures/bridge_state_methodology.md.v1_2.sig.{1,2,3}`, OpenTimestamps-anchored on Bitcoin via `.ots` companion files.
- The v1.0 and v1.1 signatures and OpenTimestamps proofs remain valid for the v1.0 and v1.1 states of the document respectively, preserved verbatim in the repository (signatures named without the `v1_2` infix). The cryptographic record of each amendment is independent.

**Verification protocol for external readers**

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_bs_structural_v1_2_signer_<i> \
  -n invarians_calibration_bridge_state_structural_v1_2 \
  -s signatures/bridge_state_methodology.md.v1_2.sig.<i> < bridge_state_methodology.md

ots verify signatures/bridge_state_methodology.md.v1_2.sig.<i>.ots
```

The three public keys (same as v1.0 and v1.1) are recorded under `signatures/public_keys/ed25519_bs_structural_v1_{1,2,3}.pub`. The namespace `invarians_calibration_bridge_state_structural_v1_2` distinguishes v1.2 signatures from v1.0 and v1.1 cryptographically.

**Status:** Methodology v1.2 locked and published. Production implementation of I5 is deferred to the forthcoming `bridge/classifier` Rust service documented in `bridge/ARCHITECTURE_DEBT.md` (backend repository). Until that service is deployed, the production Edge Function continues to evaluate I1-I4 only; Standard-mode classification remains `UNAVAILABLE` in the API payload. The methodology is the public commitment; the implementation phase follows.

**Confidence:** HIGH on the methodology design (mechanically justified by protocol contract and by an external review that converged on the same conclusion independently). The empirical false-positive rate of I5 is bounded by construction: the cap is set above the physical envelope, so a legitimate transfer cannot trigger it absent a structural breach by Circle.

**Limitation:** A genuinely stuck Standard message is confirmed `BS2` only 48 hours after the burn, by design. Faster confirmation would require introducing a latency threshold below the physical envelope, which the methodology rejects on principle. The 48-hour delay is the price of avoiding statistical thresholds on a multi-modal physical distribution.

---

*Log maintained and updated with each intervention on calibration baselines or parameters.*
*Format: immutable. No modification of past entries, additions at end of file only.*
