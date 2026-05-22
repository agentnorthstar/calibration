# OOS validation report: ETH-OP-CCTP 2025

Corridor tested: ETH-OP-CCTP (out-of-sample relative to ETH-ARB-CCTP).

Pre-engaged survivors re-tested: **6**
Placebo permutations per survivor: 1000
PASS criterion per survivor: lift >= 1.5 AND placebo p < 0.05.

## Verdict: **FAIL**

0 of 6 survivors hold their effect on the out-of-sample corridor.

Decision rule (pre-engaged):
- PASS_strong: 4+ survivors hold
- PASS_weak: 2-3 survivors hold
- FAIL: fewer than 2 survivors hold

## Per-survivor results

| ID | Predictor axis | K | lead | outcome | ARB lift | OP lift | OP placebo p | status |
|---|---|---|---|---|---|---|---|---|
| S1 | `op_struct_seq_publish_latency_shift` | 2 | 3h | latency_high_only | 2.357 | 0.0 | 1.0 | **FAIL** |
| S2 | `op_struct_seq_publish_latency_shift` | 2 | 6h | latency_high_only | 1.913 | 0.0 | 1.0 | **FAIL** |
| S3 | `op_demand_tx_shift` | 2 | 6h | latency_high_only | 1.846 | 0.0 | 1.0 | **FAIL** |
| S4 | `op_demand_size_shift` | 2 | 6h | latency_high_only | 1.815 | 0.0 | 1.0 | **FAIL** |
| S5 | `eth_demand_tx_shift` | 2 | 6h | bs2_only | 1.558 | 1.11 | 0.35 | **FAIL** |
| S6 | `op_struct_seq_publish_latency_shift` | 2 | 12h | bridge_op_to_eth | 1.531 | 1.42 | 0.357 | **FAIL** |

## Interpretation

The Delta configurations that survived on ETH-ARB-CCTP do NOT generalize to ETH-OP-CCTP. 
This indicates the surviving predictors were corridor-specific artefacts of the ARB corpus 
rather than a generic agent-orientation signal. V3 deployment with the current 
ARB-calibrated thresholds is paused. Next step: a per-corridor calibration registry, where 
each corridor receives its own discovery process and its own validated precursors.
