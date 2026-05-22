# Delta Grid Search with FDR Correction

Exploration of 288 pre-engaged configurations along 4 dimensions: 
axis (single-axis predictor among 12 substrate shifts), lead window (3/6/12/24h), 
K consecutive hours (1/2), smd threshold percentile (0.85/0.90/0.95).

**Multiple testing correction**: Benjamini-Hochberg FDR at alpha=0.05.
**Survival criterion**: FDR-corrected p < 0.05 AND lift >= 1.5x.

## Summary

- Configs evaluated: **288**
- Raw p < 0.05 (uncorrected): 56 / 288 = 19.4%
- BH FDR survives (alpha=0.05): **24** / 288 = 8.3%
- FDR + lift >= 1.5x survives: **0** / 288

## Top 10 by lift

| Axis | Lead | K | Pctl | Lift | P raw | P adj BH | Precision | Alert rate | FDR survives |
|---|---|---|---|---|---|---|---|---|---|
| `eth_demand_sigma_shift` | 12h | 2 | 0.95 | **1.644** | 0.128 | 0.4051 | 100.0% | 0.06% | NO |
| `eth_demand_sigma_shift` | 3h | 2 | 0.9 | **1.625** | 0.048 | 0.2469 | 38.5% | 0.38% | NO |
| `eth_demand_tx_shift` | 3h | 2 | 0.95 | **1.609** | 0.134 | 0.415 | 38.1% | 0.31% | NO |
| `arb_struct_seq_publish_latency_shift` | 6h | 2 | 0.95 | **1.605** | 0.042 | 0.2372 | 64.3% | 0.20% | NO |
| `arb_struct_seq_publish_latency_shift` | 3h | 2 | 0.9 | **1.598** | 0.034 | 0.204 | 37.8% | 0.54% | NO |
| `eth_demand_tx_shift` | 6h | 2 | 0.95 | **1.546** | 0.028 | 0.192 | 61.9% | 0.31% | NO |
| `eth_struct_rhythm_shift` | 3h | 2 | 0.85 | **1.509** | 0.024 | 0.1868 | 35.7% | 0.82% | NO |
| `arb_struct_seq_publish_latency_shift` | 3h | 2 | 0.85 | **1.487** | 0.016 | 0.1486 | 35.2% | 1.04% | NO |
| `arb_struct_seq_publish_latency_shift` | 6h | 2 | 0.9 | **1.485** | 0.01 | 0.1108 | 59.5% | 0.54% | NO |
| `arb_struct_seq_publish_latency_shift` | 12h | 2 | 0.9 | **1.466** | 0.0 | 0.0 | 89.2% | 0.54% | YES |

## Survivors (FDR + lift >= 1.5x)

**NONE.** No configuration passed both FDR correction and lift threshold.

Honest verdict: under this 288-configuration grid search with BH FDR alpha=0.05 
and lift >= 1.5x threshold, the Delta primitive in any single-axis configuration 
(varied along axis, lead window, K, and threshold percentile) does NOT produce a 
statistically robust orientation signal for bridge stress in 6h-24h windows on the 
ETH-ARB-CCTP 2025 corpus.
