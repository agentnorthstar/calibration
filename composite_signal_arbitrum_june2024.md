# Invarians — Composite Signal: Arbitrum, June 20, 2024 (post-Dencun)

> **Notation note (April 2026):** This case study was written before the architectural pivot of March 2026. L2 states are labeled here using the L1 SxDx notation (S1D1, S1D2, etc.) for readability. Since methodology v0.3, L2 uses a distinct framework (π, μ, σ) — L2 S2Dx no longer exists by design (τ is dormant on L2). The data and conclusions of this case study remain valid; only the state labels differ from current methodology notation.

> **Result**: Invarians detected a multi-layer Arbitrum degradation:
> L2 under pressure from 10:00 to 17:00 UTC (S1D2 — L2 basefee up to 16.49 gwei),
> followed by a Bridge blob posting gap at 16:00 UTC (BS2 — 12.8min vs 1.03min normal).
>
> ETH fee monitors (L1 basefee): **generic signal** (~10-25 gwei) — general ETH congestion,
> **no discriminating Arbitrum signal**. Impossible to distinguish "L1 busy" from "ARB bridge broken".

---

## Post-Dencun context (EIP-4844, March 13, 2024)

After Dencun, L2 rollups post their batches as **blob transactions** on L1.
The ETH L1 basefee is structurally decorrelated from L2 activity (~3-8 gwei in normal regime).

**What fee monitors see:** L1 basefee = proxy for global ETH congestion.
They do not see: the internal state of the L2 sequencer, nor the blob posting flow.

**What Invarians sees:**
- L2: ARB structural regime (L2 basefee, tx volume, block size)
- Bridge: blob posting flow to L1 (last_blob_age vs EMA baseline)
- Composite: real-time multi-layer correlation

---

## Incident timeline (June 20, 2024, UTC)

| Window (UTC) | L1 ETH | L2 ARB (basefee) | Bridge (last_age) | L1 basefee | Invarians |
|---------------|--------|------------------|-------------------|------------|-----------|
| 2024-06-20 10:00:00 | S1D1 | S1D2 (0.0108 gwei) | BS1 (0.2min) | 6.91 gwei |  |
| 2024-06-20 11:00:00 | S1D1 | S1D2 (9.7685 gwei) | BS1 (0.6min) | 16.46 gwei |  |
| 2024-06-20 12:00:00 | S1D1 | S1D2 (16.4851 gwei) | BS1 (0.4min) | 21.28 gwei |  |
| 2024-06-20 13:00:00 | S1D1 | S1D2 (5.0647 gwei) | BS1 (0.0min) | 15.44 gwei |  |
| 2024-06-20 14:00:00 | S1D1 | S1D2 (2.3759 gwei) | BS1 (0.0min) | 13.67 gwei |  |
| 2024-06-20 15:00:00 | S1D2 | S1D2 (1.0049 gwei) | BS1 (0.0min) | 11.7 gwei |  |
| 2024-06-20 16:00:00 | S1D2 | S1D2 (0.6581 gwei) | BS2 (12.8min) | 25.68 gwei | ⚠️ **ALERT** |
| 2024-06-20 17:00:00 | S1D2 | S1D2 (0.01 gwei) | BS1 (1.8min) | 14.82 gwei |  |
| 2024-06-20 18:00:00 | S1D1 | S1D1 (0.0144 gwei) | BS1 (1.4min) | 7.79 gwei |  |
| 2024-06-20 19:00:00 | S1D1 | S1D1 (0.0102 gwei) | BS1 (1.2min) | 6.53 gwei |  |
| 2024-06-20 20:00:00 | S1D1 | S1D1 (0.0101 gwei) | BS1 (0.4min) | 5.9 gwei |  |

---

## Reading the timeline

**Phase 1 — L2 Stress (10:00–15:00 UTC)**
ARB L2 basefee rises from 0.01 gwei to **16.49 gwei** (×1649 normal).
Invarians L2 detects the S1D2 regime — elevated demand on the rollup.
L1 fee monitors: also rising (15-21 gwei) but GENERIC signal (ETH busy, not ARB).
**An agent cannot distinguish "ETH busy" from "Arbitrum overloaded" using fee monitors alone.**

**Phase 2 — Bridge rupture (16:00 UTC)**
Blob posting to L1 stops: last_blob_age = **12.8min** vs EMA = **1.03min** (×12 normal).
Invarians Bridge switches to BS2. Composite signal: **L2:S1D2 + Bridge:BS2 = MULTI_LAYER**.
L1 fee monitors: **25.68 gwei** — generic L1 signal, no specific Arbitrum alert.

**Phase 3 — Return to normal (17:00–18:00 UTC)**
Bridge resumes (BS1), L2 basefee drops back to 0.01 gwei, L1 calms down.
Invarians returns to S1D1/BS1 at 18:00 UTC.

---

## What a cross-chain agent would have experienced

**Without Invarians (fee monitors only):**
```
10:00 UTC — L1 basefee: 16 gwei → decision: "L1 expensive, wait"
15:00 UTC — L1 basefee: 12 gwei → decision: "L1 returning, execute"
16:00 UTC — cross-chain transaction sent to Arbitrum
          → bridge in BS2 gap, finalization absent
          → transaction stuck for ~37min with no visibility
17:24 UTC — delayed finalization, unpredictable slippage
```

**With Invarians:**
```
10:00 UTC — L2 ARB: S1D2 detected (basefee 0.01 → 9.77 gwei) → execution_window = WAIT
16:00 UTC — Bridge BS2 detected (last_age 12.8min) → REROUTE_L2 or AVOID
          → 0 transactions sent during the critical window
17:00 UTC — Bridge BS1 confirmed → normal resumption
```

---

## Comparison of available signals

| Signal | Value during incident | Discriminating for ARB? |
|--------|--------------------------|-------------------|
| ETH L1 basefee | 10–25 gwei | ❌ No — generic ETH signal |
| Gas trackers (Etherscan, Blocknative) | General L1 alert | ❌ No — not ARB-specific |
| ETH mempool | Busy | ❌ No |
| **Invarians L2 ARB** | **S1D2 from 10:00 UTC** | **✅ Yes — ARB specifically** |
| **Invarians Bridge** | **BS2 at 16:00 UTC (×12 normal)** | **✅ Yes — blob posting stopped** |

---

## Epistemic status

- **Type**: retrospective proof on public data
- **L1 + Bridge source**: BigQuery `bigquery-public-data.crypto_ethereum` (blocks + blob transactions)
- **L2 source**: BigQuery `bigquery-public-data.goog_blockchain_arbitrum_one_us.blocks` (aggregated/hour)
- **Reproducible**: yes — script `h5_composite_demo.py`
- **Limitation**: post-hoc reconstruction; exact cause of the incident not correlated to a public status page

*Generated 2026-04-03 — Invarians Phase B*
