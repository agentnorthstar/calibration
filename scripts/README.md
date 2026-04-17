# Calibration scripts — Invarians

These scripts allow **independent reproduction** of Invarians backtests
from public BigQuery data.

> **Scope:** These scripts reproduce TPR/FPR results, threshold sweeps, and M1 Stability Scores.
> Running `sweep_eth.py` reproduces FPR=1.23% and TPR=100% (4/4) for ETH.
> Running `m1_eth.py` reproduces M1=5.07 for ETH (formula §10.1 — validated ✅).
> Running `m1_pol.py` computes M1 for POL using formula §10.1 (τ and π signals separately).

---

## Prerequisites

```bash
pip install pandas numpy matplotlib
```

BigQuery access required for initial extraction (GCP account, free public dataset).

---

## Ethereum — Reproduce the backtest

### Step 1 — Extract data from BigQuery

ETH data is extracted from `bigquery-public-data.crypto_ethereum.blocks`.
Extraction script available in the repo (SQL query not published here — data already provided).

**Data already available:** `eth_invariants_2020_2024_phi280.csv` (34,697 windows, 2020–2024)

### Step 2 — Backtest + Sweep

```bash
# Main backtest (SxDx classification over 4 years)
python backtest_eth.py

# threshold_s2 sweep (τ)
python sweep_eth.py

# threshold_d2 sigma-only sweep (π)
python sweep_eth_d2.py

# Full D2 sweep 3-dimensions (σ × size × tx)
python sweep_eth_d2_full.py
```

**Expected results:**
- `eth_backtest_results.csv` — TPR/FPR per event
- `eth_sweep_results.csv` — FPR vs threshold_s2 (1.01 → 1.25)
- `eth_sweep_d2_full_results.csv` — FPR grid vs (size_demand, tx_demand, sigma_demand)
- `eth_backtest_chart.png`, `eth_sweep_chart.png` — visualizations

**Validated result:** threshold_s2=1.12, D2 (sigma=1.10, size=1.20, tx=1.10), FPR=1.23%, TPR=100% (4/4)

---

## Polygon — Reproduce the backtest

### BigQuery extraction

```sql
-- extract_pol.sql — bigquery-public-data.crypto_polygon.blocks
-- Window Φ=1800 blocks (~1h at 2s/block)
```

**Data available:** `pol_invariants_2020_2024_phi1800.csv` (2020–2024)

```bash
python backtest_pol.py
python sweep_pol.py
```

**Ground truth events POL:** Network Halt March 2021 · Gas Crisis May 2021 · Heimdall/Bor Jan 2023 · Reorg Storm Feb 2023

---

## Solana — Reproduce the τ backtest

### BigQuery extraction

```sql
-- extract_sol.sql — bigquery-public-data.crypto_solana_mainnet_us.blocks
-- Window Φ=800 slots (~5.3 min at 0.4s/slot)
-- Note: transaction_count absent from BigQuery Solana — τ only
```

**Data available:** `sol_invariants_2021_2024_phi800.csv` (2021–2024)

```bash
python backtest_sol.py
python sweep_sol.py
```

**Ground truth events SOL τ:** 4 major outages (Sept 2021 · Jan 2022 · May 2022 · Oct 2022)
**Validated result:** threshold_s2=1.12, FPR_τ=1.77%, TPR=100% (4/4)

---

## Common script architecture

All scripts follow the same protocol:

```
1. Load invariants (BigQuery CSV)
2. Compute fast EMA (α=2/11, ~10h) + slow EMA (α=2/721, ~30d)
3. Compute ratios: rhythm_ratio, sigma_ratio, size_ratio, tx_ratio
4. Classify each window: S1D1 | S1D2 | S2D1 | S2D2
5. Compare against ground truth events (TPR / latency)
6. Sweep candidate thresholds (FPR vs detection)
7. Export results CSV + charts
```

---

## M1 Stability Score

```bash
python m1_eth.py    # → M1=5.07 for Ethereum τ (rhythm_ratio, The Merge)
python m1_pol.py    # → M1 for Polygon τ (rhythm_ratio) and π (sigma_ratio)
```

**Expected ETH result:** M1=5.07 ✅ — exact match with methodology §10.3
**Expected POL result:** τ M1=10.66 (Reorg Storm) · π M1=4.55 (Gas Crisis) ✅ — matches methodology §10.3 and ANS registry (updated 2026-04-17, calibration_log #018)

---

*Scripts created March–April 2026 — Invarians calibration v0.4*
*Data sources: Google BigQuery public datasets (free with GCP account)*
