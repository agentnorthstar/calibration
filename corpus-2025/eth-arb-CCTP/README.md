# Invarians ETH-ARB-CCTP Corridor Analysis, 2025

Public research artifact maintained by Invarians. Documents the substrate observability of the Ethereum L1 to Arbitrum L2 corridor and the CCTP V1 (Cross-Chain Transfer Protocol version 1) bridge between them, for calendar year 2025.

## Purpose

Demonstrate that the Invarians v2.0 API, deployed in production, captures the substrate-level events documented as critical for Real World Asset (RWA) settlement flows on this corridor, using only signals exposed by the public API contract.

No new instrument is introduced. No new calibration is applied. The analysis uses the v2.0 API output as a black box, applied retrospectively to the 2025 historical reconstruction.

## Folder contents

| File | Purpose |
|---|---|
| `METHODOLOGY.md` | Framework, key glossary terms, scope, method, reproducibility |
| `EVENTS_2025.md` | Five substrate-critical events on the corridor with peer-reviewed academic backing |
| `API_CONTRACT.md` | What the v2.0 API exposes, with mapping to the analysis columns |
| `LIMITATIONS.md` | Caveats including beacon participation gap and research vs production calibration distinction |
| `data/` | BigQuery-derived hourly panel for 2025 (parquet + csv + data dictionary) |
| `plots/` | One annual baseline figure plus one per-event pattern figure (five events) |
| `scripts/` | Reproducible Python scripts producing the panel and the plots |
| `bigquery/` | BigQuery source queries used to derive the panel |
| `results/` | Delta exploration outputs (full grid, FDR survivors, reconfiguration tests) |

## How to read

1. Start with `METHODOLOGY.md` for the framework and scope.
2. Open `EVENTS_2025.md` to see the five documented events with their academic sources.
3. Inspect `plots/annual_baseline_2025.png` for the 2025 nominal substrate context, then the five per-event figures.
4. For data scientists or auditors: `data/DATA_DICTIONARY.md` defines every column; `scripts/` provides reproducibility.
5. Limitations of the present analysis are acknowledged in `LIMITATIONS.md`.
6. Statistical validation of the Delta primitive is documented in `results/`.

## What this is not

This is not a backtest of a prediction strategy. The Invarians regime classification is not designed to predict events; it is designed to qualify the substrate state at a given hour. The analysis documents whether the v2.0 API output matches the substrate footprint of documented critical events, not whether it predicts them.

This is not an audit of application-layer code defects. Smart contract bugs, governance compromises, and social engineering events are explicitly out of scope per the Invarians substrate observability mandate.

## Reproducibility

Every figure in `plots/` is produced by a Python script in `scripts/` from data in `data/`. Reproducing requires Python 3.11+, pandas, matplotlib, and pyarrow. No private credentials, RPC endpoints, or proprietary data are needed.

## References

- Invarians production API: https://api.invarians.com
- API documentation: https://invarians.com/developers.html
- Glossary: https://invarians.com/glossary.html
