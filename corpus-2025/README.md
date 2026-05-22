# Invarians Calibration Corpus, 2025

Public research corpus documenting the substrate observability of two cross-chain corridors for calendar year 2025: Ethereum L1 to Arbitrum L2 via CCTP V1 (Cross-Chain Transfer Protocol version 1), and Ethereum L1 to Optimism L2 via CCTP V1.

## Why these two corridors

The corpus is restricted to the smallest valid pavage of corridors that allows a meaningful chain-type-exclusivity test of the Invarians v2.0 API Delta primitive. ETH-ARB and ETH-OP share the same L1 (Ethereum) and the same bridge protocol (CCTP V1), but differ in L2 typology (Arbitrum Nitro versus OP Stack). Any predictor that holds on both corridors is unlikely to be an artefact of one chain's specific mechanics. Any predictor that holds on one and fails the other is, by construction, chain-type-exclusive.

The corpus does NOT cover Base, Polygon, Avalanche, Solana, or other corridors. These are documented as separate studies when calibrated.

## Folder structure

```
corpus-2025/
├── README.md                          (this file)
├── eth-arb-CCTP/                      (ETH L1 to ARB L2 corridor, CCTP V1)
│   ├── README.md                      (corridor overview)
│   ├── METHODOLOGY.md                 (data sources, pipeline, validation protocol)
│   ├── EVENTS_2025.md                 (5 substrate-critical events, academic backing)
│   ├── API_CONTRACT.md                (v2.0 API column mapping)
│   ├── LIMITATIONS.md                 (caveats)
│   ├── data/                          (hourly panel, bridge state, data dictionary)
│   ├── bigquery/                      (BigQuery extraction queries and notes)
│   ├── scripts/                       (reproducible Python pipeline)
│   ├── results/                       (Delta exploration, FDR survivors, reconfig tests)
│   └── plots/                         (annual baseline + per-event figures)
├── eth-op-CCTP/                       (ETH L1 to OP L2 corridor, CCTP V1)
│   ├── README.md
│   ├── METHODOLOGY.md
│   ├── LIMITATIONS.md
│   ├── data/                          (OP hourly panel + bridge state)
│   ├── bigquery/                      (OP-specific extraction queries)
│   ├── scripts/                       (OP pipeline + Delta exploration + OOS validation)
│   └── results/                       (OP grid output, ARB-to-OP transfer test)
└── shared/                            (cross-corridor synthesis)
    ├── INFRA_CRITICAL_ETH_ARB_2025.md  (ARB event inventory and exclusion rationale)
    ├── INFRA_CRITICAL_ETH_OP_2025.md   (OP event inventory and exclusion rationale)
    └── MATRIX_UNIVERSALITY_ARB_VS_OP.md  (Primitive 2 vocabulary test across both corridors)
```

## Where to start

For each corridor, the reading order is:

1. The corridor `README.md` for the high-level overview.
2. `METHODOLOGY.md` for the protocol and pipeline.
3. The event inventory (`EVENTS_2025.md` for ARB, or `../shared/INFRA_CRITICAL_ETH_OP_2025.md` for OP).
4. The plots (for ARB) or the result JSON / report (for OP) for the empirical observations.
5. `LIMITATIONS.md` for the caveats.

For cross-corridor synthesis, see `shared/MATRIX_UNIVERSALITY_ARB_VS_OP.md`.

## Key findings, in one line each

- **ARB Delta exploration (648 configs, BH FDR alpha=0.05, lift >= 1.5x)**: 6 configurations survive.
- **OP Delta exploration (648 configs, same protocol)**: 1 configuration survives.
- **ARB-to-OP OOS transfer**: 0 of 6 ARB survivors hold on OP (chain-type-exclusive Delta).
- **OP-to-ARB cross-corridor**: the 1 OP survivor does not hold on ARB.
- **Primitive 2 (Regime + Bridge State)**: qualitatively consistent vocabulary across both corridors on shared documented events (Pectra, Fusaka, BPO1, USDe cascade).

These findings are documented in detail in `eth-arb-CCTP/results/`, `eth-op-CCTP/results/`, and `shared/MATRIX_UNIVERSALITY_ARB_VS_OP.md`.

## What this corpus is not

- It is not a backtest of a prediction strategy. The regime classification qualifies the substrate state at a given hour; it does not forecast the next hour.
- It is not an audit of application-layer code defects. Smart contract bugs, governance compromises, exchange hacks, and social engineering events are explicitly out of scope per the Invarians substrate observability mandate.
- It is not a complete coverage of 2025 cross-chain activity. The corpus is the smallest pavage that supports the chain-type-exclusivity test. Other corridors are studied separately.

## Reproducibility

Each corridor folder ships its own scripts and data. All results in `results/` can be regenerated from `data/` and `scripts/` using standard scientific Python (pandas, numpy, scikit-learn, matplotlib, pyarrow). No private credentials or proprietary feeds are required. BigQuery extracts are documented in `bigquery/` for consumers who want to rebuild from raw chain data.

## References

- Invarians production API: https://api.invarians.com
- API documentation: https://invarians.com/developers.html
- Glossary: https://invarians.com/glossary.html
- Foundations: https://invarians.com/foundations.html
- This corpus relates to the V3 Delta deployment documented in the public calibration log, Entry #041, and to `methodology.md` Section 14 of the calibration repository.
