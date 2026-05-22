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
| F0_single_axis | 288 | 23 | 12 | 1 |
| F1_multi_axis | 64 | 4 | 0 | 0 |
| F2_alt_outcomes | 192 | 8 | 6 | 0 |
| F3_ML_LR | 8 | 4 | 4 | 0 |
| F4_cross_chain | 96 | 13 | 8 | 0 |

## Combined FDR (across all configs)

- Combined FDR survives: **28** / 648
- Combined FDR + lift >= 1.5x: **1** / 648

## Top 15 by lift

| Family | Predictor | Lead | Lift | P raw | P adj combined | Precision | Alert rate |
|---|---|---|---|---|---|---|---|
| F2_alt_outcomes | `op_demand_gas_complexity_shift|K=2|pctl=0.9` | 3h | **4.257** | 0.226 | 1.0 | 1.5% | 0.87% |
| F0_single_axis | `eth_struct_continuity_shift|pctl=0.95|K=2` | 3h | **4.118** | 0.022 | 0.324 | 42.9% | 0.10% |
| F0_single_axis | `eth_struct_continuity_shift|pctl=0.95|K=2` | 6h | **3.717** | 0.0 | 0.0 | 71.4% | 0.10% |
| F4_cross_chain | `ETH_predict_eth_to_op_bridge|eth_struct_rhythm_shift|K=2|pctl=0.9` | 3h | **2.645** | 0.078 | 0.7406 | 17.4% | 0.31% |
| F0_single_axis | `eth_struct_rhythm_shift|pctl=0.95|K=2` | 3h | **2.62** | 0.096 | 0.8406 | 27.3% | 0.15% |
| F0_single_axis | `op_struct_seq_publish_latency_shift|pctl=0.95|K=2` | 6h | **2.602** | 0.166 | 0.9836 | 50.0% | 0.05% |
| F4_cross_chain | `ETH_predict_eth_to_op_bridge|eth_struct_rhythm_shift|K=2|pctl=0.9` | 6h | **2.411** | 0.014 | 0.2592 | 30.4% | 0.31% |
| F0_single_axis | `op_struct_seq_publish_latency_shift|pctl=0.95|K=2` | 3h | **2.402** | 0.334 | 1.0 | 25.0% | 0.05% |
| F0_single_axis | `eth_struct_rhythm_shift|pctl=0.95|K=2` | 6h | **2.366** | 0.06 | 0.6586 | 45.5% | 0.15% |
| F0_single_axis | `eth_demand_sigma_shift|pctl=0.95|K=2` | 12h | **2.22** | 0.1 | 0.8416 | 75.0% | 0.05% |
| F4_cross_chain | `ETH_predict_eth_to_op_bridge|eth_struct_continuity_shift|K=2|pctl=0.9` | 6h | **2.16** | 0.04 | 0.5082 | 27.3% | 0.30% |
| F2_alt_outcomes | `op_demand_gas_complexity_shift|K=2|pctl=0.9` | 6h | **2.129** | 0.4 | 1.0 | 1.5% | 0.87% |
| F2_alt_outcomes | `op_demand_gas_complexity_shift|K=2|pctl=0.9` | 12h | **2.129** | 0.252 | 1.0 | 3.0% | 0.87% |
| F0_single_axis | `eth_struct_continuity_shift|pctl=0.95|K=2` | 12h | **2.115** | 0.064 | 0.6683 | 71.4% | 0.10% |
| F4_cross_chain | `ETH_predict_eth_to_op_bridge|eth_demand_sigma_shift|K=2|pctl=0.9` | 3h | **2.098** | 0.128 | 0.9645 | 13.8% | 0.39% |

## Combined survivors

**1 configurations survive combined FDR + lift threshold.**
- F0_single_axis | `eth_struct_continuity_shift|pctl=0.95|K=2` | lead=6h | lift=3.717 | precision=71.4% | p_adj=0.0
