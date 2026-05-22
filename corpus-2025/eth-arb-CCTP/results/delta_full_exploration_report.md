# Delta Full Exploration: 4 families + combined FDR

Total configurations tested: **648**

Strategy families:
- F0 single-axis grid: 288 configs
- F1 multi-axis grouped: 64 configs
- F2 alternative outcomes: 192 configs
- F3 ML logistic regression: 8 configs
- F4 cross-chain: 96 configs

Multiple-testing correction: Benjamini-Hochberg FDR alpha=0.05.
Survival criterion: combined FDR p_adj < 0.05 AND lift >= 1.5x.

## Per-family summary

| Family | Configs | Raw p<0.05 | FDR survives (within family) | FDR + lift >=1.5x |
|---|---|---|---|---|
| F0_single_axis | 288 | 56 | 24 | 0 |
| F1_multi_axis | 64 | 10 | 0 | 0 |
| F2_alt_outcomes | 192 | 49 | 25 | 5 |
| F3_ML_LR | 8 | 2 | 2 | 0 |
| F4_cross_chain | 96 | 17 | 9 | 1 |

## Combined FDR (across all configs)

- Combined FDR survives: **61** / 648
- Combined FDR + lift >= 1.5x: **6** / 648

## Top 15 by lift

| Family | Predictor | Lead | Lift | P raw | P adj combined | Precision | Alert rate |
|---|---|---|---|---|---|---|---|
| F4_cross_chain | `ETH_predict_eth_to_arb_bridge|eth_demand_sigma_shift|K=2|pctl=0.9` | 3h | **2.399** | 0.01 | 0.0913 | 28.6% | 0.39% |
| F2_alt_outcomes | `arb_struct_seq_publish_latency_shift|K=2|pctl=0.9` | 3h | **2.357** | 0.004 | 0.0425 | 29.3% | 0.57% |
| F2_alt_outcomes | `eth_demand_sigma_shift|K=2|pctl=0.9` | 3h | **2.126** | 0.014 | 0.1148 | 38.5% | 0.37% |
| F2_alt_outcomes | `arb_struct_seq_publish_latency_shift|K=2|pctl=0.9` | 6h | **1.913** | 0.002 | 0.0231 | 43.9% | 0.57% |
| F2_alt_outcomes | `arb_demand_tx_shift|K=2|pctl=0.9` | 3h | **1.911** | 0.018 | 0.1372 | 23.7% | 0.81% |
| F2_alt_outcomes | `arb_demand_size_shift|K=2|pctl=0.9` | 3h | **1.879** | 0.018 | 0.1372 | 23.3% | 0.83% |
| F2_alt_outcomes | `arb_demand_tx_shift|K=2|pctl=0.9` | 6h | **1.846** | 0.0 | 0.0 | 42.4% | 0.81% |
| F2_alt_outcomes | `arb_demand_size_shift|K=2|pctl=0.9` | 6h | **1.815** | 0.0 | 0.0 | 41.7% | 0.83% |
| F4_cross_chain | `ETH_predict_eth_to_arb_bridge|eth_demand_sigma_shift|K=2|pctl=0.9` | 6h | **1.788** | 0.028 | 0.1728 | 39.3% | 0.39% |
| F2_alt_outcomes | `eth_struct_rhythm_shift|K=2|pctl=0.9` | 3h | **1.678** | 0.19 | 0.513 | 20.8% | 0.33% |
| F2_alt_outcomes | `eth_demand_tx_shift|K=2|pctl=0.9` | 3h | **1.658** | 0.008 | 0.0774 | 30.0% | 1.00% |
| F0_single_axis | `eth_demand_sigma_shift|pctl=0.95|K=2` | 12h | **1.644** | 0.128 | 0.4106 | 100.0% | 0.06% |
| F0_single_axis | `eth_demand_sigma_shift|pctl=0.9|K=2` | 3h | **1.625** | 0.048 | 0.2321 | 38.5% | 0.38% |
| F0_single_axis | `eth_demand_tx_shift|pctl=0.95|K=2` | 3h | **1.609** | 0.134 | 0.4195 | 38.1% | 0.31% |
| F4_cross_chain | `ETH_predict_eth_to_arb_bridge|eth_demand_sigma_shift|K=2|pctl=0.9` | 12h | **1.605** | 0.012 | 0.1037 | 60.7% | 0.39% |

## Combined survivors

**6 configurations survive combined FDR + lift threshold.**
- F2_alt_outcomes | `eth_demand_tx_shift|K=2|pctl=0.9` | lead=6h | lift=1.558 | precision=48.6% | p_adj=0.0231
- F2_alt_outcomes | `arb_struct_seq_publish_latency_shift|K=2|pctl=0.9` | lead=3h | lift=2.357 | precision=29.3% | p_adj=0.0425
- F2_alt_outcomes | `arb_struct_seq_publish_latency_shift|K=2|pctl=0.9` | lead=6h | lift=1.913 | precision=43.9% | p_adj=0.0231
- F2_alt_outcomes | `arb_demand_size_shift|K=2|pctl=0.9` | lead=6h | lift=1.815 | precision=41.7% | p_adj=0.0
- F2_alt_outcomes | `arb_demand_tx_shift|K=2|pctl=0.9` | lead=6h | lift=1.846 | precision=42.4% | p_adj=0.0
- F4_cross_chain | `ARB_predict_arb_to_eth_bridge|arb_struct_seq_publish_latency_shift|K=2|pctl=0.9` | lead=12h | lift=1.531 | precision=61.5% | p_adj=0.0425
