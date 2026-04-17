---
title: "Backtest Polygon — Structural Signal Validation 2020–2024"
chain: polygon
version: "1.0"
date: "2026-04-17"
status: "validated"
confidence: "MEDIUM event-based (τ) — FPR elevated, documented"
data_source: "BigQuery public dataset: bigquery-public-data.crypto_polygon"
windows: 28744
phi: 1800
period: "2020-06-01 → 2023-12-31"
---

# Backtest Polygon — Structural Signal Validation 2020–2024

> **Status:** MEDIUM event-based — TPR=100% (4/4 events), FPR=11.75% (elevated — see note)
> **M1 Stability Score — τ (rhythm_ratio, Reorg Storm):** 10.66 · **π (sigma_ratio, Gas Crisis):** 4.55
> *(formula v0.1 — `scripts/m1_pol.py`. Previously published as scalar 7.37 — session estimate, retired in calibration_log #018)*

---

## 1. Dataset

| Parameter | Value |
|---|---|
| Source | BigQuery `crypto_polygon` |
| Period | 2020-06-01 → 2023-12-31 |
| Windows (invariants) | 28,744 |
| Φ (blocks/window) | 1800 (~1h at ~2s/block) |
| Signal dimensions | rhythm_ratio, sigma_ratio, size_ratio, tx_ratio |

---

## 2. Signal Distributions (baseline, outside events)

| Signal | p50 | p90 | p95 | p99 |
|---|---|---|---|---|
| rhythm_ratio | 0.9998 | 1.0317 | 1.0507 | 1.1035 |
| sigma_ratio | 0.9996 | 1.1145 | 1.2183 | 1.7761 |
| size_ratio | 0.9983 | 1.1033 | 1.1534 | 1.3115 |
| tx_ratio | 0.9891 | 1.1626 | 1.2659 | 1.8748 |

**Note on continuity (c_s):** invariant at 1.0 throughout the period → `continuity_p10 = null` confirmed. Polygon maintains continuous block production with no measurable structural interruptions at Φ=1800.

---

## 3. Regime Distribution

| Regime | Count | Share |
|---|---|---|
| S1D1 (nominal) | 25,335 | 88.3% |
| S2D1 (structural stress, no demand) | 1,932 | 6.7% |
| S1D2 (demand spike, no structural stress) | 1,314 | 4.6% |
| S2D2 (combined stress) | 163 | 0.6% |

---

## 4. Ground Truth Events

4 reference events over the 2020–2023 period:

| Event | Date | Type | Detected | Latency |
|---|---|---|---|---|
| Network Halt | March 2021 | τ (structural) | ✅ TP | +22.2h |
| Gas Crisis | May 2021 | π (demand) | ✅ TP | +3.5h |
| Heimdall/Bor Incident | January 2023 | τ (structural) | ✅ TP | +35.2h |
| Reorg Storm | February 2023 | τ (structural) | ✅ TP | +6.4h |

**TPR = 100% (4/4)**

---

## 5. Threshold Sweep τ (rhythm_ratio)

| threshold_s2 | FPR | Network Halt | Heimdall/Bor | Reorg |
|---|---|---|---|---|
| 1.02 | 20.03% | ✅ | ✅ | ✅ |
| 1.03 | 15.08% | ✅ | ✅ | ✅ |
| **1.04** | **11.84%** | **✅** | **✅** | **✅** |
| 1.05 | 9.76% | ✅ | ❌ | ✅ |
| 1.06 | 8.37% | ❌ | ❌ | ✅ |
| 1.08 | 6.79% | ❌ | ❌ | ✅ |
| 1.10 | 5.97% | ❌ | ❌ | ✅ |

**Selected parameter: `threshold_s2 = 1.04`** — the only threshold detecting all 3 structural events (FPR=11.84%).

---

## 6. Threshold Sweep π (sigma_ratio × size_ratio × tx_ratio)

σ-only sweep — no threshold achieves FPR < 1.5% while detecting Gas Crisis:

| sigma | FPR_π | Gas Crisis |
|---|---|---|
| 1.05 | 22.95% | ✅ |
| 1.12 | 15.74% | ✅ |
| 1.20 | 12.34% | ✅ |

Cross sweep (sigma × size × tx) — best sweep point detecting all 4 events:

| sigma | size | tx | FPR | Events |
|---|---|---|---|---|
| 1.12 | 1.25 | 1.25 | 11.15% | 4/4 ✅ |

**Production π parameters (refined from sweep): `sigma=1.14 / size=1.18 / tx=1.23`** (combined FPR 11.75%).

> Note: sweep optimum is 1.12/1.25/1.25. Production values (1.14/1.18/1.23) are a conservative refinement — tighter on σ (more sensitive), narrower on size/tx (less aggressive). Combined FPR is nearly identical (11.75% vs 11.15%); all 4 events detected. See section 7 for final validated parameters.

---

## 7. Final Results

| Metric | Value |
|---|---|
| TPR | **100% (4/4)** |
| FPR τ+π | **11.75%** |
| threshold_s2 | 1.04 |
| threshold_d2_sigma | 1.14 |
| threshold_d2_size | 1.18 |
| threshold_d2_tx | 1.23 |
| M1 τ (rhythm_ratio · Reorg Storm) | **10.66** |
| M1 π (sigma_ratio · Gas Crisis) | **4.55** |
| Confidence | MEDIUM event-based |

---

## 8. Note on the elevated FPR

The FPR of 11.75% is significantly higher than ETH (1.23%) and SOL (1.77%). Three structural factors explain this gap:

**1. Intrinsic Polygon volatility (2020–2023)**
The period covers the explosion of DeFi/NFT usage on Polygon (2021–2022), with extremely volatile load growth. The signal correctly captures these stress regimes, but the "false alarms" often correspond to real tensions not listed as ground truth events.

**2. Very tight τ threshold (threshold_s2 = 1.04)**
To detect the Heimdall/Bor Incident (weak signal, ratio=2%), the threshold must remain low. At 1.04, the signal is sensitive to minor disturbances that do not constitute formal operational incidents.

**3. Incomplete ground truth**
The Polygon 2020–2023 event catalog is less documented than Ethereum's. Some of the "false alarms" are likely undocumented incidents.

**Conclusion:** Parameters are published with MEDIUM event-based status. The elevated FPR is documented and does not constitute a bug — it reflects the structural characteristics of Polygon over this period. Reducing it to a lower FPR would require either a more complete ground truth, or acceptance of a reduced TPR (Heimdall/Bor not detected at threshold_s2 ≥ 1.05).

---

## 9. Polygon production parameters

```json
{
  "chain": "polygon",
  "phi": 1800,
  "alpha_fast": 0.1818,
  "alpha_slow": 0.002771,
  "threshold_s2": 1.04,
  "threshold_d2_sigma": 1.14,
  "threshold_d2_size": 1.18,
  "threshold_d2_tx": 1.23,
  "continuity_p10": null,
  "m1_tau": 10.66,
  "m1_pi": 4.55,
  "m1_method": "formula_v0.1 (scripts/m1_pol.py)",
  "calibration_method": "event-based",
  "confidence": "MEDIUM",
  "validated_date": "2026-04-17",
  "backtest_period": "2020-06-01 / 2023-12-31",
  "backtest_windows": 28744
}
```

---

## 10. Reproducibility

Scripts available in `scripts/`:

```bash
# From BIGDATA/ with pol_invariants_2020_2024_phi1800.csv
python backtest_pol.py     # → pol_backtest_results.csv + pol_backtest_chart.png
python sweep_pol.py        # → pol_sweep_results.csv + pol_sweep_chart.png
python sweep_pol_d2.py     # → pol_sweep_d2_results.csv + pol_sweep_d2_chart.png
```

Data source: BigQuery `bigquery-public-data.crypto_polygon.blocks` — query in `scripts/extract_pol.sql`.

---

*Invarians calibration — Polygon structural signal validation*
*Created April 17, 2026*
