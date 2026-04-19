# Calibration scripts — Invarians

These scripts allow **independent reproduction** of Invarians backtests
from public BigQuery data.

> **Scope:** these scripts reproduce TPR/FPR, threshold sweeps, temporal cross-validation,
> ROC/AUC, and M1 Stability Scores for ETH, POL and SOL.
> Every numeric result quoted in `backtest_*.md` can be regenerated from these scripts.

---

## Prerequisites

```bash
pip install pandas numpy matplotlib scipy
```

BigQuery access (free Google Cloud account, public datasets) is required
for the initial extraction step of every chain.

---

## Data layout

All scripts assume **CSV inputs live next to the script**:

```
scripts/
├── backtest_eth.py
├── eth_invariants_2020_2024_phi280.csv       ← you produce this from BigQuery
├── backtest_pol_phi720.py
├── pol_invariants_2020_2024_phi720.csv       ← you produce this from BigQuery
├── backtest_sol.py
├── sol_invariants_2021_2024_phi800.csv       ← you produce this from BigQuery
└── ...
```

The scripts use `DATA_DIR = Path(__file__).parent`. Place the extracted CSVs
directly in the `scripts/` directory before running them.

---

## Step 1 — BigQuery extraction (every chain)

The `extract_*.sql` files contain the canonical extraction queries.
Run each query in the BigQuery console against its public dataset and
export the result as CSV into `scripts/`:

| Chain | Dataset | Query | Output CSV |
|-------|---------|-------|------------|
| ETH   | `bigquery-public-data.crypto_ethereum.blocks`            | *(extraction at Φ=280, 13s/block)*                 | `eth_invariants_2020_2024_phi280.csv`  |
| POL   | `bigquery-public-data.crypto_polygon.blocks`             | `extract_pol_phi720.sql` (production-aligned Φ=720) | `pol_invariants_2020_2024_phi720.csv`  |
| POL   | (legacy)                                                 | `extract_pol.sql` (legacy Φ=1800, v1.0 backtest)    | `pol_invariants_2020_2024_phi1800.csv` |
| SOL   | `bigquery-public-data.crypto_solana_mainnet_us.blocks`   | `extract_sol.sql` (Φ=800, ~5.3 min at 0.4s/slot)    | `sol_invariants_2021_2024_phi800.csv`  |

> **Note on SOL:** the BigQuery `crypto_solana_mainnet_us.blocks` table does not
> expose `transaction_count`, which is why SOL π is not calibrated here.
> SOL π calibration is pending accumulation of data on the production Supabase store
> (target: July 2026 — see `limitations_and_plans.md`).

---

## Step 2 — Reproduce Ethereum

```bash
python backtest_eth.py          # SxDx classification 2020–2024
python sweep_eth.py             # threshold_s2 sweep (τ)
python sweep_eth_d2.py          # threshold_d2 sigma-only sweep (π)
python sweep_eth_d2_full.py     # full D2 3D sweep (σ × size × tx)
python m1_eth.py                # M1 Stability Score
python cv_eth.py                # temporal cross-validation (train 2020→2022-08, test 2022-09→2024)
```

**Expected validated results:**
- `threshold_s2 = 1.12`, D2 (σ=1.10, size=1.20, tx=1.10)
- TPR = 100% (4/4), FPR = 1.23% [CI95% 1.11% ; 1.36%]
- CV: TPR_test = 100% (2/2), FPR_test = 0.65%
- M1 = 5.07 (formula §10.1)

---

## Step 3 — Reproduce Polygon (production-aligned Φ=720)

```bash
python backtest_pol_phi720.py        # SxDx classification at production Φ=720
python sweep_pol_d2_phi720.py        # 3D D2 sweep at Φ=720
python m1_pol_phi720.py              # M1 τ and π at Φ=720
```

**Expected validated results (v2.0 — 2026-04-19, production-aligned):**
- `threshold_s2 = 1.04`, D2 (σ=1.14, size=1.18, tx=1.23)
- TPR = 100% (4/4), FPR = 14.57% [CI95% 14.30% ; 14.83%]
- M1 τ (Reorg Storm) = 12.60  ·  M1 π (Gas Crisis) = 3.59
- Mean detection latency = 3.95 h

Legacy Φ=1800 scripts (`backtest_pol.py`, `sweep_pol.py`, `m1_pol.py`) are kept
for audit trail — see `calibration_log.md #023` for the v1.0 → v2.0 decision.

---

## Step 4 — Reproduce Solana (τ only, π pending)

```bash
python backtest_sol.py
python sweep_sol.py
```

**Expected validated results:**
- `threshold_s2 = 1.12`
- TPR_τ = 100% (4/4), FPR_τ = 1.77% [CI95% 1.70% ; 1.84%]
- π calibration: pending (July 2026)

Ground-truth events: the four major outages (Sept 2021, Jan 2022, May 2022, Oct 2022).

---

## Step 5 — Cross-chain ROC curves

```bash
python roc_curves.py
```

Reads per-chain sweep CSVs and produces:
- `roc_eth.png`, `roc_sol.png`, `roc_pol.png`
- `roc_results.json` — AUC per chain + operating point

---

## Step 6 — Binomial confidence intervals

```bash
python ci_binomial.py
```

Clopper–Pearson exact CI95% for all published TPR/FPR rates.

---

## Common pipeline

All `backtest_*.py` scripts follow the same protocol:

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

## Auxiliary — Composite signal demo (Arbitrum, June 2024)

```bash
python h5_composite_demo.py
```

Demonstrates the L1 × L2 × Bridge composite signal on the Arbitrum June 20, 2024
blob-posting gap (~37 min, post-Dencun). Requires three CSV extracts
(see file header comments).

---

*Scripts created March–April 2026 — Invarians calibration v0.4*
*Data sources: Google BigQuery public datasets (free with a GCP account).*
