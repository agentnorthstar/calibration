# Invarians ETH-OP-CCTP Corridor Analysis, 2025

Public research artifact maintained by Invarians. Documents the substrate observability of the Ethereum L1 to Optimism L2 corridor and the CCTP V1 (Cross-Chain Transfer Protocol version 1) bridge between them, for calendar year 2025.

## Purpose

Demonstrate that the Invarians v2.0 API, deployed in production, captures the substrate-level events on the ETH-OP-CCTP corridor using only signals exposed by the public API contract.

The ETH-OP corridor serves as a chain-type-exclusive out-of-sample (OOS) test of the Delta primitive configurations originally discovered on the ETH-ARB corridor. It is paired with the ARB analysis (see `../eth-arb-CCTP/`) to verify whether predictors generalize across L2 typologies.

## Calibration constraints specific to Optimism

- OP Stack rollup architecture (distinct from Arbitrum Nitro): 2-second L2 block cadence, BatchInbox EOA-based batch submission to L1.
- Moderate CCTP V1 throughput on both directions during 2025 (ETH-OP and OP-ETH).
- No comparable mainnet sequencer outage event in 2025 (Arbitrum had a 2h35 connectivity issue, OP did not).
- Single OP-specific hard fork on the OP Stack in 2025 (Isthmus, 2025-05-09 16:00 UTC), in addition to the shared Ethereum L1 forks (Pectra, Fusaka, BPO1).

## Folder contents

| File | Purpose |
|---|---|
| `METHODOLOGY.md` | Pipeline, panel construction, Delta validation protocol, OP-specific notes |
| `LIMITATIONS.md` | Caveats, including single validated precursor and OP RPC reclassification |
| `data/` | OP hourly panel for 2025 and reconstructed bridge state |
| `bigquery/pull_op_cctp.md` | BigQuery queries used to extract CCTP V1 events for Optimism |
| `scripts/` | Python pipeline scripts: pull, build, Delta exploration, OOS validation |
| `results/` | Delta full-grid exploration and OOS validation outputs |

## Outcome summary

The 648-configuration Delta exploration on the OP panel produced exactly one validated precursor surviving Benjamini-Hochberg FDR correction at alpha=0.05 with lift at or above 1.5x:

```
eth_struct_continuity_shift  |  pctl=0.95  K=2  lead=6h  |  lift=3.72x  p_adj=0.0
```

The six ARB-discovered survivors did not generalize to OP (0 of 6 pass). The single OP-corpus survivor, tested cross-corridor on the ARB panel, also did not generalize.

Together these results indicate that Delta operational configurations are chain-type-exclusive. The Regime + Bridge State primitive, by contrast, retained a consistent descriptive vocabulary across both corridors (see `../shared/MATRIX_UNIVERSALITY_ARB_VS_OP.md`).

## How to read

1. Start with `METHODOLOGY.md` for the pipeline and the Delta protocol.
2. Inspect `results/delta_full_exploration_op_report.md` for the full grid output.
3. Read `results/oos_validation_op_report.md` for the ARB-to-OP transfer test.
4. Read `results/oos_validation_op_survivor_on_arb_output.json` for the symmetric OP-to-ARB transfer.
5. `LIMITATIONS.md` documents the caveats.

## References

- Invarians production API: https://api.invarians.com
- API documentation: https://invarians.com/developers.html
- Companion analysis: `../eth-arb-CCTP/`
- Cross-corridor synthesis: `../shared/MATRIX_UNIVERSALITY_ARB_VS_OP.md`
