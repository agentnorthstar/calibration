# Methodology

## 1. What Invarians does

Invarians is a continuous observability service for the substrate of public blockchains. It measures the mechanical state of block production, demand absorption, and inter-chain message attestation on Ethereum L1, Arbitrum L2, Base, Optimism, and Polygon, and publishes a cryptographically signed snapshot of that state at hourly cadence through a public API.

The mandate is narrow and explicit:

- **Cross-chain and bridge infrastructure risks**: latency, finality, attestation timing on canonical bridges (CCTP, CCIP) and on native rollup-to-L1 channels.
- **Infrastructure state proof**: each hourly snapshot is signed with Ed25519 by the producing node and exposed via a panel API. Independent verification of the signature is provided by the public attester key.

What Invarians does not do:

- It does not predict events. The classification qualifies the substrate state at the current hour given calibrated thresholds; it does not forecast the next hour.
- It does not audit smart contract code. Application-layer defects (reentrancy, rounding, governance compromise) are outside the substrate mandate.
- It does not measure end-to-end usability for user-facing applications. A substrate that is statistically nominal may still be operationally degraded for users if the issue is at the RPC or feed layer rather than block production.

## 2. Key glossary terms

The terms below are used throughout the analysis. Canonical definitions are maintained at https://invarians.com/glossary.html.

The v2.0 API exposes three primitives. Primitive 1 (Attestation) wraps the entire panel in an HMAC SHA-256 envelope for integrity verification. Primitive 2 (Regime + Bridge State) classifies each chain into one of 12 signed codes and each canonical bridge route into BS1 (nominal) or BS2 (degraded). Primitive 3 (Delta) exposes the set of delta signals: per-metric `shift` (signed deviation versus the 30-day baseline), `shift_delta`, `shift_magnitude_delta`, plus axis-level `drift` composites with their own `_magnitude_delta`. Drift and shift are not primitives; they are observables that compose Delta. Bridges carry no Delta block because they are operational pipelines, not substrates; their attestation consists of latency percentiles plus per-message cryptographic anchors when available (Circle ECDSA on CCTP V1, DON multi-signature on CCIP planned).

- **Structural regime** (Primitive 2): a 12-code categorical classification of the L1 or L2 substrate state at a given hour. Two signed axes: structural (S) and demand (D). Examples: `S1D1` nominal, `S1D2+` demand above its upper bound, `S2+D1` rhythm slowed, `S2+D2+` both axes stressed upward.
- **Bridge state** (Primitive 2): a 2-code classification of a bridge route, `BS1` (nominal) or `BS2` (degraded). Calibrated preliminarily on per-message latency baselines (P97 over rolling 14 days on attestation latency p90). CCTP V1 reached per_message_attested capability on Ethereum-to-Arbitrum routes on 2026-05-11. Calibration refinement is in progress as additional baseline data accumulates.
- **Drift composite** (sub-element of Primitive 3, Delta): per-axis aggregate trend over a 30-day baseline, exposed as `drift.structural` and `drift.demand` in the API panel.
- **Signed shift** (sub-element of Primitive 3, Delta): per-metric deviation between the short EMA ratio (current vs 10-hour baseline) and the long EMA ratio (current vs 30-day baseline). Exposed as `shift`, `shift_delta`, and `shift_magnitude_delta` per metric.
- **Execution context attestation** (Primitive 1): the JSON panel returned by `GET /v2/panel`, signed with HMAC SHA-256, containing the regime, Delta signals, and bridge state for each chain and route under observation.
- **CCTP V1**: Circle Cross-Chain Transfer Protocol version 1, burn-and-mint via Circle attester (Iris). The corridor under analysis here is CCTP V1 ETH-to-ARB and ARB-to-ETH.

The full glossary defines additional terms and the underlying physical observables (rhythm, continuity, sigma, size, tx, complexity, gas_complexity, sequencer_publish_latency, beacon_participation) measured per chain.

## 3. Objective of this analysis

Demonstrate that the v2.0 API, in its current production state, captures the substrate footprint of the events documented in 2025 as structurally critical for the Ethereum-to-Arbitrum corridor and the CCTP V1 bridge that connects them.

Criteria for an event to be in scope:

1. The event occurred during calendar year 2025.
2. The event affects substrate mechanics on ETH L1, ARB L2, or the CCTP V1 bridge between them.
3. The event has at least one Tier A academic or institutional source documenting the underlying failure mode (peer-reviewed paper, central bank publication, IOSCO/BIS report).
4. The event has at least one Tier B or A source documenting its RWA criticality (institutional roadmap, regulatory framework, or industry post-mortem with credibility).

Five events satisfy these criteria. They are listed in `EVENTS_2025.md` with their academic sources.

## 4. Scope

- **Chains**: Ethereum L1 mainnet, Arbitrum L2 (Arbitrum One mainnet).
- **Bridge**: CCTP V1 between Ethereum and Arbitrum, both directions.
- **Time window**: 2025-01-01 00:00 UTC to 2025-12-31 23:00 UTC, 8760 hours.
- **Granularity**: 1-hour UTC bucket.
- **Observable set**: strictly the metrics exposed by the v2.0 API (see `API_CONTRACT.md`). Beacon participation on Ethereum is in the API contract but absent from the 2025 historical reconstruction because the production sensor was calibrated only in 2026 (see `LIMITATIONS.md`).

Out of scope:

- Other L1 chains (Polygon, Avalanche, Solana).
- Other L2 rollups (Base, Optimism, Polygon zkEVM, zkSync).
- CCIP and native bridges.
- Application-layer events (smart contract bugs, exchange hacks, governance compromises).

## 5. Method

### 5.1 Data acquisition

The 2025 hourly panel is reconstructed from BigQuery public datasets `bigquery-public-data.crypto_ethereum` and `bigquery-public-data.crypto_arbitrum`, processed through the Invarians reference pipeline (`lib/` in the parent research repository). The same Rust pipeline that runs in production was applied retrospectively to the historical block data, producing per-hour ratios and EMA baselines aligned with the v2.0 API output. The bridge state was reconstructed from on-chain CCTP V1 events (DepositForBurn, MessageReceived) matched by domain and nonce per route. Notes on the BigQuery extracts are provided in `bigquery/queries.md`.

### 5.2 Event window definition

For each of the five events, two windows are defined:

- **Hot window**: from the event start to the event end, as reported by the primary source. Examples: a hard fork activation epoch to T+8 hours, a sequencer outage start to end timestamp.
- **Extended window**: hot window plus or minus 6 hours, for pre and post pattern visualization.

### 5.3 Baseline reference

The 2025 baseline is defined as all 2025 hours outside any extended event window. Empirically, 8187 hours qualify (out of 8281 hourly observations available). The baseline distribution over the joint categorical cell `(regime_eth, regime_arb, bridge_state_eth_arb, bridge_state_arb_eth)` is computed and used as the reference for measuring the lift of any event window cell.

### 5.4 Per-event analysis

Each event produces a 7-panel figure:

- Panel 1 to 4: categorical strips for ETH regime, ARB regime, BS eth-arb, BS arb-eth, colored by code value.
- Panel 5: ETH continuous signed shifts, 5 axes (rhythm, continuity, sigma, size, tx).
- Panel 6: ARB continuous signed shifts, 8 axes (rhythm, continuity, sequencer_publish_latency, sigma blindspot, size, tx, complexity, gas_complexity).
- Panel 7: CCTP attestation latency p50, p90, p99 for both directions, log scale, with hourly combined-cell lift overlay on the right axis.

The plots in `plots/` follow this 7-panel layout exactly. The annual baseline plot in `plots/annual_baseline_2025.png` uses the same layout for the full year with all 5 event windows masked.

### 5.5 What the plots demonstrate

For each event, the plot shows whether the v2.0 API output during the hot window deviates from the 2025 baseline along the four axes (regime, bridge state, continuous shifts, attestation latency). The hourly combined-cell lift quantifies how rare the observed regime tuple is, relative to the baseline distribution.

A high lift (above 3) indicates the substrate state during the event was statistically unusual compared to nominal 2025 conditions. A near-1 lift indicates the substrate was nominal during the event window, which is a valid outcome when the event is operationally sub-critical for the substrate (for example a brief sequencer connectivity issue that does not affect block production).

## 6. Data

- `data/annual_panel_2025.parquet`: 8281 rows by 31 columns, hourly UTC index, joined panel of ETH regime, ARB regime, both bridge states, 13 continuous signed shifts, 8 CCTP latency observables, and event annotations.
- `data/annual_panel_2025.csv`: same data, plain text format.
- `data/DATA_DICTIONARY.md`: column-by-column definitions, units, and caveats.

The total panel size is approximately 1.4 MB in parquet, 3.5 MB in CSV. The dataset is suitable for direct ML experimentation by an external data scientist.

## 7. Reproducibility

- `scripts/export_panel_2025.py`: reconstructs the panel from the source parquets.
- `scripts/plot_annual_baseline_2025.py`: produces the annual figure.
- `scripts/plot_patterns_per_incident.py`: produces the 5 per-event figures.

Running `python scripts/export_panel_2025.py` then `python scripts/plot_*.py` reproduces all artifacts in `data/` and `plots/` deterministically from the source parquets shipped in `data/`.

No private API keys are required. The original BigQuery extracts have already been processed into the parquets included in the folder.

## 8. Relation to the v2.0 API

The analysis uses strictly the observables that the v2.0 API exposes. The production API serves these same observables in JSON form via `GET /v2/panel`. The mapping from the API JSON structure to the analysis columns is documented in `API_CONTRACT.md`.

The v2.0 API is open and accessible at `https://api.invarians.com/v2/panel`. The client SDK is published as `invarians` on PyPI. The server-side reference implementation is not publicly distributed at this time; the API contract documented in `API_CONTRACT.md` is sufficient for any client to consume and independently verify signed payloads.
