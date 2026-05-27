# Methodology v4, ETH-POL CCTP V2 Descriptive Corpus

**Status.** v4 methodology, frozen at signature. Three steps. Each step locks before the next starts.

**Version.** v4, 2026-05-25.

**Date drafted.** 2026-05-25.

**Calendar year of corpus.** 2025.

**Audience.** External reviewer, Tier A institutional or peer. The corpus is publishable standalone.

---

## 1. Principle

The corpus is a purely descriptive observation of how the Invarians substrate matrix and Delta signals behave on the ETH-POL CCTP V2 corridor over calendar year 2025, restricted to documented incident windows and a baseline reference. The corpus reports what the instrument shows. It does not test a hypothesis, does not declare PASS or FAIL on the matrix, does not compute a p-value, does not apply Benjamini-Hochberg or any multiple-testing correction, and does not claim predictive capacity. Inferential claims are out of scope by construction.

Auditability rests on three sequential frozen artefacts. Each artefact is locked by Ed25519 signature on its SHA-256 hash before the next step begins. The final corpus manifest is anchored on Bitcoin via OpenTimestamps. Any modification after lock is recorded as a dated amendment that preserves the prior hash chain.

The methodology mirrors the inherited Invarians framework where the framework applies (panel construction, EMA dual-track baselines, signed regime codes computed from production thresholds), and stops where the framework would force an inferential claim that the sample size in this corpus cannot honestly support.

---

## 2. Scope

**Corridor.** Ethereum mainnet (L1) and Polygon PoS (L1), connected by Circle Cross-Chain Transfer Protocol Version 2.

**Directions.** Both. ETH to POL and POL to ETH.

**Topology.** L1 to L1.

**Protocol.** CCTP V2 exclusively. Fast Transfer (`minFinalityThreshold` ≤ 1000) and Standard Transfer (`minFinalityThreshold` = 2000) are tracked as two distinct populations because they have physically different attestation timing distributions.

**Time window.** 2025-01-01 00:00 UTC to 2025-12-31 23:00 UTC, hourly granularity. If CCTP V2 mainnet deployment on Polygon postdates 2025-01-01, the effective window starts at the deployment date and is documented in `LIMITATIONS.md`.

**Data sources.** Public BigQuery datasets `bigquery-public-data.crypto_ethereum` and `bigquery-public-data.crypto_polygon`. No external API dependency, no Iris probe, no Heimdall RPC dependency. All observables are retrospectively reconstructible from public on-chain state.

---

## 3. Three frozen steps

### Step 1, Incident sourcing, exhaustive and pre-filter free

Procedure produces a single artefact: `INCIDENTS_2025.md`, an inventory of all 2025 incidents matching the inclusion criteria below. The inventory is exhaustive within the criteria, not curated for expected matrix sensitivity. No incident is excluded on the basis that the matrix is expected to remain silent on it.

**Inclusion criteria, strict and pre-declared.**

1. Calendar year 2025 strict, hot-window start timestamp falls between 2025-01-01 00:00 UTC and 2025-12-31 23:59 UTC.
2. Tier A primary source available. Acceptable primary sources are: Etherscan or PolygonScan direct on-chain evidence, Metrika, official post-mortem from the affected chain or protocol (Ethereum Foundation, Polygon Foundation, Circle), institutional publication from BIS, ECB, or IOSCO, peer-reviewed paper, plus Tier B confirmation from CoinDesk or The Block when the report cites a primary source explicitly.
3. Scope is substrate mechanics or cross-chain infrastructure: hard forks, sequencer or block-producer halts, consensus or finality bugs, RPC degradation affecting block ingestion, attestation latency spikes documented in primary source, depeg cascades observable on-chain.

**Exclusion criteria, strict and pre-declared.**

- Application-layer code defects (reentrancy, rounding, price feed manipulation by application contracts).
- Governance compromise (multisig key theft, admin key retention, executive arrest).
- Social engineering (UI hijack, phishing, signature interception).
- MEV at single-transaction granularity.

These exclusions match the substrate mandate of the Invarians instrumentation. The matrix is calibrated to observe substrate mechanics. Application-layer events are out of scope as predictors and as outcomes for this corpus.

**Sources to dredge for the inventory.**

- `INCIDENTS_2025_RWA_SUBSTRATE.md` (parent folder).
- `RWA_RISKS_SOURCED_2026_05_19.md` (parent folder).
- `M2_BRIEF_v0_DRAFT.md` §2 incident references (parent folder).
- Ethereum mainnet release notes 2025, plus All Core Devs meeting minutes for fork dates.
- Polygon Foundation incident reports and Heimdall, Bor public post-mortems for 2025.
- Circle CCTP V2 public incident log if available, plus public Circle status archive for the corridor period.

**Output schema.** `INCIDENTS_2025.md` table columns: `event_id`, `date_utc_start`, `date_utc_end`, `chain_scope` (ETH, POL, or CCTP V2 corridor), `incident_type`, `tier_A_source_url`, `hot_window_start_utc`, `hot_window_end_utc`, `notes`. Hot windows are fixed from primary source before any Step 3 computation. Hot windows are not adjusted post-extraction under any circumstance.

**Lock.** Ed25519 signature on the SHA-256 hash of `INCIDENTS_2025.md`. Date and signer recorded in `corpus-2025/eth-pol-CCTP-v2/MANIFEST.md`. Late additions after lock are permitted only if a new incident is documented in a Tier A primary source between lock and Step 3 completion; such additions are recorded as dated amendments and re-sign the manifest with previous hash preserved.

### Step 2, BigQuery raw extraction, no interpretation

Procedure produces three parquet artefacts plus one SQL artefact. No regime computation, no EMA, no threshold application, no derived metric is computed at this step. The output is raw on-chain state, sufficient for any independent reviewer to recompute the matrix at Step 3 byte-for-byte.

**ETH block-level extraction.** From `bigquery-public-data.crypto_ethereum.blocks`, period 2025-01-01 to 2025-12-31, columns: `number, hash, parent_hash, timestamp, gas_used, gas_limit, transaction_count, base_fee_per_gas, size`. The `hash` and `parent_hash` columns are extracted to allow downstream reorg detection by chain consistency checks.

**POL block-level extraction.** From `bigquery-public-data.crypto_polygon.blocks`, same period, columns: `number, hash, parent_hash, timestamp, gas_used, gas_limit, transaction_count, base_fee_per_gas`. Same rationale for `hash` and `parent_hash`.

**CCTP V2 events extraction.** From `bigquery-public-data.crypto_ethereum.logs` and `bigquery-public-data.crypto_polygon.logs`, filtered on `address` matching the verified TokenMessenger V2 and MessageTransmitter V2 contracts on each chain, plus the V2 event signatures (`DepositForBurn V2`, `MessageReceived V2`). Output columns after ABI decoding: `chain, contract_address, event_name, block_number, block_timestamp, transaction_hash, log_index, nonce, source_domain, destination_domain, amount, mint_recipient, burn_token, min_finality_threshold, message_hash`.

**Contract address verification.** TokenMessenger V2 and MessageTransmitter V2 addresses on Ethereum mainnet and Polygon mainnet are verified via Etherscan and PolygonScan respectively, with the verification URL recorded in `bigquery/queries.md` alongside the SQL extracts.

**Nonce uniqueness check, pre-lock.** Before signing Step 2, the CCTP V2 events parquet is checked for `nonce` uniqueness per `(source_domain, destination_domain)` pair. The check confirms that each emitted `DepositForBurn V2` event maps to at most one `MessageReceived V2` event under the same nonce and domain pair, which is the precondition for the end-to-end latency reconstruction of Step 3. Any duplicate or unmatched nonce is enumerated in `MANIFEST.md` with its root cause (replay, retry, missing receive event, contract migration) before the lock signature is applied. Step 2 does not lock until this check produces either a clean result or a documented duplicate inventory.

**Output schema.** Three parquet files plus one SQL documentation file:

- `data/eth_blocks_2025_raw.parquet`
- `data/pol_blocks_2025_raw.parquet`
- `data/cctp_v2_events_2025_raw.parquet`
- `bigquery/queries.md`, copy-paste of every SQL query executed, with dataset, run date, row count, and SHA-256 of the resulting parquet.

**Lock.** Ed25519 signature on the SHA-256 hashes of the three parquets and of `bigquery/queries.md`. Hashes recorded in `MANIFEST.md`. Re-extraction post-lock is allowed only if a documented data source correction occurs (BigQuery dataset backfill, contract address verification revision); re-extraction is recorded as dated amendment with previous hashes preserved.

### Step 3, Matrix and Delta application against the sourced inventory

Procedure produces one report artefact and one tabular artefact. Computation applies the inherited Invarians framework to the data of Step 2, restricted to the hot windows of Step 1 plus a baseline reference.

**Metrics computed, ETH side, hourly.**

- `rhythm_ratio`, observed inter-block interval over recent target.
- `continuity_ratio`, fraction of expected blocks present in the hour.
- `sigma_demand`, coefficient of variation on `gas_used` across blocks of the hour.
- `size_demand`, average transaction count ratio against EMA baseline.
- `tx_demand`, total transaction throughput ratio against EMA baseline.

**Metrics computed, POL side, hourly.** Same five metrics, same formulas. The rho_ts axis on POL is computed and reported as observed during the hot windows, without prior declaration that the axis is inoperable. The empirical behaviour of rho_ts on POL during the documented incidents is part of what the corpus reports.

**EMA baselines.** 30-day EMA per metric per chain, half-life parameter mirroring production. Computed on the full 2025 window. EMA contamination by hot-window observations is acknowledged as a structural property of the framework (see METHODOLOGY.md §4 of the parent corpus), surfaced via the `ema_value` column and a `baseline_contamination_pct` column at each event.

**Regime classification.** Twelve signed codes per chain, computed using production thresholds applied without recalibration, in line with §6 of the parent `METHODOLOGY.md`. The codes are: S1D1, S1D2+, S1D2-, S1D2±, S2+D1, S2-D1, S2+D2+, S2+D2-, S2+D2±, S2-D2+, S2-D2-, S2-D2±. ETH production thresholds: `threshold_s2 = 1.12`, `sigma_d2 = 1.10`, `size_d2 = 1.20`, `tx_d2 = 1.10`. POL production thresholds: `threshold_s2 = 1.04`, `sigma_d2 = 1.14`, `size_d2 = 1.18`, `tx_d2 = 1.23`. Source: `l1_thresholds` Postgres table, production calibration as of 2026-04-29.

**Signed shifts.** Per metric per chain, hourly: `shift = (current_value - ema_value) / ema_value`. The sign is preserved through the analysis. Any binarisation, if performed downstream, uses ternary signed bins with asymmetric thresholds per sign rather than absolute-value bins.

**Drift composite.** `drift.structural` and `drift.demand` per chain, computed per production formula.

**CCTP V2 message-level latency, raw observables only.** End-to-end transit latency reconstructed as `receive_timestamp_destination - burn_timestamp_source`, matched per `nonce` and `(source_domain, destination_domain)`. Per direction, per `min_finality_threshold` mode (Fast or Standard), aggregated hourly: `messages_observed_1h, attestation_latency_p50_s, attestation_latency_p90_s, attestation_latency_p99_s`.

No threshold-based classification (BS1, BS2, or any equivalent) is computed at this step. A BS classification would require fitting a calibration window to the latency observable itself, which would put a derived state in the same row as the observable from which it is derived. That co-presence creates a tautological dependence between the predictor and the outcome and is therefore excluded by construction. Only the raw latency percentiles are reported. Any threshold-based interpretation belongs to a downstream phase performed after the descriptive report is locked, and is not part of this corpus.

**Per-event reporting, the primary corpus output.**

For each `event_id` from `INCIDENTS_2025.md`, one tabular sheet covers the hot window plus six pre-window hours and six post-window hours, hour by hour, with columns:

- `event_id, hour_utc, in_hot_window (bool)`
- `eth_rhythm_ratio, eth_continuity_ratio, eth_sigma_demand, eth_size_demand, eth_tx_demand`
- `pol_rhythm_ratio, pol_continuity_ratio, pol_sigma_demand, pol_size_demand, pol_tx_demand`
- `eth_struct_rhythm_shift, eth_struct_continuity_shift, eth_demand_sigma_shift, eth_demand_size_shift, eth_demand_tx_shift` (signed)
- `pol_*_shift` (signed, five columns)
- `eth_drift_structural, eth_drift_demand, pol_drift_structural, pol_drift_demand`
- `eth_regime_code, pol_regime_code` (12 signed codes each)
- `cctp_v2_messages_observed_1h_eth_to_pol_fast, cctp_v2_p50_eth_to_pol_fast_s, cctp_v2_p90_eth_to_pol_fast_s, cctp_v2_p99_eth_to_pol_fast_s` and the three other (direction, mode) combinations
- `base_fee_per_gas_eth, base_fee_per_gas_pol`

**Baseline reference sheet.** One sheet covering the average values of the same columns over all 2025 hours falling outside `±6h` of any incident hot window. The baseline is descriptive, intended for visual side-by-side comparison with per-event sheets. No statistical test is computed.

**What is explicitly excluded from Step 3.**

- No lift computation. No ratio of `P(joint_cell | hot) / P(joint_cell | baseline)`.
- No p-value. No permutation test. No Benjamini-Hochberg. No FDR.
- No PASS or FAIL verdict on the matrix.
- No claim of prediction, detection capacity, or generalization.
- No grid search over axes, K, percentile thresholds, lead times, or outcomes.

**Output schema.** Two artefacts:

- `results/REPORT_ETH_POL_CCTP_V2.md`, narrative report describing what each per-event sheet shows in plain prose, plus the baseline sheet, plus a section listing the events for which the matrix remained nominal (S1D1 throughout the hot window on a given chain) and the events for which the matrix displayed divergent codes. The report contains no inferential claim.
- `results/per_event_sheets/{event_id}.parquet`, one parquet per event, plus one for the baseline.

**Lock.** Ed25519 signature on the SHA-256 of `REPORT_ETH_POL_CCTP_V2.md` and on the per-event sheet hashes. Full manifest hash signed Ed25519 three times by separated keys (per the Standard of Reference v1) and anchored on Bitcoin via OpenTimestamps. From this point, the corpus is published. Amendments are dated and preserve the prior hash chain.

---

## 4. What this corpus does and does not claim

**It does claim.** That the matrix, applied to the documented incidents and baseline, produces the regime codes, signed shifts, drift composites, and raw CCTP V2 latency percentiles reported in the per-event sheets. The reporting is exhaustive within the scope, signed, and reproducible byte-for-byte from the data and queries committed to the corpus folder.

**It does not claim.** That the matrix detects incidents in general. That the matrix predicts incidents. That the matrix generalises beyond the 2025 ETH-POL CCTP V2 corridor. That a regime code firing during a hot window establishes a causal link. That a regime code remaining nominal during a hot window establishes the absence of substrate stress. That this corpus supports or refutes hypotheses formulated in any other Invarians publication.

The corpus is a snapshot of instrument behaviour on a defined corridor over a defined year. It is published so that any reviewer can examine what the instrument shows. Conclusions beyond that require either a larger sample, a different instrumentation, or a different methodology, and belong to follow-up work.

---

## 5. Epistemic limits documented from the start

The corpus carries the following limits, declared before execution and not subject to revision after observation.

- **Sample size.** The Step 1 inventory determines N. N is expected to be small (single-digit to low double-digit). The corpus does not attempt to compensate for small N by inflating the number of statistical tests or by applying any multiple-comparison framework. The reporting is descriptive precisely because N does not support an inferential framework that would be honest.
- **Polygon substrate rho_ts.** The parent `methodology.md` notes that POL `rho_ts` has 0.011s amplitude over 90 days in nominal operation. This is a property of nominal operation, not a verdict on incident response. The corpus reports the empirical behaviour of rho_ts on POL during the hot windows of the Polygon incidents in the Step 1 inventory. A flat rho_ts during a POL incident is reported as such. A non-flat rho_ts during a POL incident is also reported as such. The corpus does not pre-declare which outcome will occur.
- **EMA contamination.** The 30-day EMA includes hot-window observations in its baseline. This is a structural property of the framework. The corpus surfaces it via `ema_value` and `baseline_contamination_pct` per event, per parent `METHODOLOGY.md` §4.
- **CCTP V2 mode population.** Fast and Standard transfers are tracked separately. If either mode has fewer than 100 observed messages per direction over the full 2025 window, the per-event sheets for that mode are still produced but flagged `messages_thin = true`.
- **Reorg absorption.** Both BigQuery datasets serve the canonical chain after reorg resolution. Reorgs that unwound CCTP V2 transactions are not directly visible as alternate branches in the parquet outputs. The `hash` and `parent_hash` columns extracted at Step 2 allow chain-continuity checks but cannot recover branches that BigQuery has already pruned. This is documented in `LIMITATIONS.md`.

---

## 6. Publication

The corpus is published standalone at `corpus-2025/eth-pol-CCTP-v2/` on the `agentnorthstar/calibration` repository, in the same layout as the existing `corpus-2025/eth-arb-CCTP/` and `corpus-2025/eth-op-CCTP/` corpora. The `calibration_log.md` entry records the corpus release and references the manifest hash. The `methodology.md` §14 status table is extended with a row for POL V2.

---

## 7. Auditability protocol summary

| Step | Artefact | Lock |
|---|---|---|
| 1 | `INCIDENTS_2025.md` | Ed25519 signature on SHA-256, recorded in `MANIFEST.md` before Step 2 begins |
| 2 | three raw parquets plus `bigquery/queries.md` | Ed25519 signature on the four SHA-256 hashes, recorded in `MANIFEST.md` before Step 3 begins |
| 3 | `REPORT_ETH_POL_CCTP_V2.md` plus per-event parquets plus baseline parquet | triple Ed25519 signature on the corpus manifest hash, OpenTimestamps Bitcoin anchor, corpus published |

Reviewers verify the corpus end-to-end by recomputing Step 3 from the Step 2 parquets and confirming the resulting hashes match. Reviewers verify Step 2 by re-running the SQL of `bigquery/queries.md` against the public datasets and confirming the resulting parquets match. Reviewers verify Step 1 by inspecting the Tier A source URLs and confirming the hot windows match the primary documentation.

End of methodology v4.
