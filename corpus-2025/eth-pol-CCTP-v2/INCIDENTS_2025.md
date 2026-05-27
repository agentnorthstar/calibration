# Incidents 2025, ETH-POL CCTP V2 Corpus

**Status.** Draft, pre-signature. Awaiting Ed25519 signature as Step 1 lock per the contract.

**Date drafted.** 2026-05-25.

**Contract reference.** This inventory is produced under `METHODOLOGY.md` §3 Step 1, locked 2026-05-25, SHA-256 `1b0ef577733d1bb05b372547e26f0c633b6a1e4873fa2d67e1c640c2f51c67e7`, triple Ed25519 signed and OpenTimestamps Bitcoin stamped.

**Scope.** Calendar year 2025, Ethereum mainnet (L1) and Polygon PoS (L1) substrate plus the CCTP V2 corridor between them. Out-of-scope chains (Arbitrum, Base, Optimism, Solana, testnets) are not included in the inventory.

---

## 1. Inclusion and exclusion criteria, restated from contract

**Included if all three conditions hold:**

1. Hot-window start timestamp falls between 2025-01-01 00:00 UTC and 2025-12-31 23:59 UTC.
2. Tier A primary source is available: Etherscan or PolygonScan direct on-chain evidence, Metrika, official post-mortem from the affected chain or protocol (Ethereum Foundation, Polygon Foundation, Polygon Labs community forum, Circle), institutional publication from BIS, ECB, or IOSCO, peer-reviewed paper, or Tier B confirmation (CoinDesk, The Block, Decrypt, Cointelegraph) only when the report cites a primary source explicitly.
3. The incident or infrastructure event affects substrate mechanics or the cross-chain corridor: hard forks, sequencer or block-producer halts, consensus or finality bugs, RPC degradation affecting block ingestion, attestation latency spikes, depeg cascades observable on-chain, validator participation events, protocol mainnet deployments.

**Excluded by rule:**

- Application-layer code defects (reentrancy, rounding, price feed manipulation by application contracts).
- Governance compromise (multisig key theft, admin retention, executive arrest).
- Social engineering (UI hijack, phishing, signature interception).
- MEV at single-transaction granularity.

**Discipline.** No event is excluded on the basis that the matrix is expected to remain silent on it. The detectability of any included event is a finding of Step 3, not a pre-filter at Step 1. Consistent with the prior corpora `eth-arb-CCTP` and `eth-op-CCTP`, the matrix may surface additional substrate events not in this inventory; the inventory enumerates only the externally sourced primary-documented events.

---

## 2. Inventory

| event_id | date_utc_start | date_utc_end | chain_scope | incident_type | tier_A_source_url | hot_window_start_utc | hot_window_end_utc | notes |
|---|---|---|---|---|---|---|---|---|
| `CCTP_V2_MAINNET_LAUNCH_2025_03_11` | 2025-03-11 | 2025-03-11 | CCTP_V2_corridor | protocol_mainnet_launch | https://www.circle.com/pressroom/circle-launches-next-evolution-of-cctp-to-enable-fast-cross-chain-settlement-for-crypto-capital-markets | 2025-03-11T00:00:00Z | 2025-03-11T23:59:59Z | CCTP V2 launched on Ethereum and Avalanche mainnet. Approximately 8-second USDC transfers under Fast mode versus multi-minute V1. Foundational milestone marking the start of CCTP V2 corridor observability on Ethereum. Polygon-side activation later (see `CCTP_V2_POLYGON_DEPLOYMENT_2025_06`). |
| `ETH_PECTRA_MAINNET_2025_05_07` | 2025-05-07 | 2025-05-07 | ETH | hard_fork_activation | https://blog.ethereum.org/en/2025/04/29/checkpoint-2 | 2025-05-07T10:05:11Z | 2025-05-07T18:00:00Z | Pectra mainnet activation at epoch 364032. EIP-7702 smart-account migration, EIP-7251 validator consolidation, max stake raised to 2048 ETH, blob count adjustments. Stabilisation period approximately 8 hours post-activation. |
| `CCTP_V2_POLYGON_DEPLOYMENT_2025_06` | 2025-06-01 | 2025-06-30 | CCTP_V2_corridor | protocol_mainnet_deployment | https://www.bitget.com/news/detail/12560604838008 | 2025-06-01T00:00:00Z | 2025-06-30T23:59:59Z | Polygon PoS officially connected to the CCTP V2 corridor mid-2025. Enables ETH↔POL V2 observability. Date imprecise (month-only); exact deployment timestamp to confirm in Phase 0 via Etherscan and PolygonScan contract creation timestamps and Circle official announcement. |
| `POL_HEIMDALL_CONSENSUS_2025_07_30` | 2025-07-30 | 2025-07-30 | POL | consensus_bug_finality_lag | https://www.coindesk.com/markets/2025/09/10/polygon-pos-sees-transaction-finality-lag-patch-in-progress | 2025-07-30T09:30:00Z | 2025-07-30T11:01:00Z | Polygon PoS Heimdall consensus bug triggered by an unexpected validator exit. Approximately 1 hour 31 minutes Heimdall halt; Bor block production continued. Reported in retrospective post-mortem at September 10 incident announcement. |
| `ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09` | 2025-09-09 | 2025-09-26 | ETH | mass_validator_exit | https://www.coindesk.com/tech/2025/09/10/kiln-exits-ethereum-validators-in-orderly-move-following-swissborg-exploit | 2025-09-09T00:00:00Z | 2025-09-26T23:59:59Z | Kiln, an institutional staking operator, exited all validators as a precautionary measure following the SwissBorg exploit and an NPM supply-chain incident affecting key management. Triggered a record validator exit queue: approximately 2.65 million ETH waiting, queue stretched to 44 to 46 days at peak. Substrate-observable via exit queue dynamics, churn rate, and beacon participation rate during the window. |
| `ETH_SSV_MASS_SLASHING_2025_09_10` | 2025-09-10 | 2025-09-10 | ETH | validator_mass_slashing_dvt | https://www.theblock.co/post/370299/ssv-labs-ceo-protocol-not-compromised-following-validator-slashing-incidents | 2025-09-10T00:00:00Z | 2025-09-10T23:59:59Z | 39 validators slashed via SSV Network (distributed validator technology). Root cause: operator-side maintenance on Ankr's systems combined with third-party key management errors. Not a protocol bug. Correlated slashing triggers inactivity leak amplification. Co-occurs same calendar day with `POL_HEIMDALL_MILESTONE_2025_09_10` and falls inside `ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09` window. Hot window hour-precision to refine in Phase 0. |
| `POL_HEIMDALL_MILESTONE_2025_09_10` | 2025-09-10 | 2025-09-10 | POL | consensus_milestone_bug_finality_lag | https://www.coindesk.com/markets/2025/09/10/polygon-pos-sees-transaction-finality-lag-patch-in-progress | 2025-09-10T04:30:00Z | 2025-09-10T16:30:00Z | Polygon PoS consensus milestone bug. Bor block production continued but Heimdall finality determination froze. Finality delays ranged from 15 minutes to 1 hour over a 12-hour window. Emergency hard fork resolution approximately 5 hours into the incident. Metrika post-mortem available at https://www.metrika.co/blog/post-mortem-polygon. |
| `POL_HEIMDALL_V2_HARD_FORK_2025_09_16` | 2025-09-16 | 2025-09-16 | POL | hard_fork_consensus_upgrade | https://forum.polygon.technology/t/heimdall-v2-v0-3-0-release-for-mainnet/21270 | 2025-09-16T14:00:00Z | 2025-09-16T14:30:00Z | Heimdall v2 v0.3.0 hard fork at block 28913694. Follow-up to the Heimdall V2 migration on CometBFT. 5-second finality target active post-fork. Status of execution: successful per Polygon community forum announcement. |
| `USDE_DEPEG_CASCADE_2025_10_10` | 2025-10-10 | 2025-10-11 | ETH+POL+CCTP_V2_corridor | depeg_cascade_settlement_stress | https://www.coindesk.com/markets/2025/10/11/ethena-s-usde-briefly-loses-peg-during-usd19b-crypto-liquidation-cascade | 2025-10-10T20:30:00Z | 2025-10-11T06:00:00Z | USDe (Ethena) depeg cascade on Binance. Off-chain trigger: US-China tariff announcement at approximately 21:00 UTC. Binance external price-feed read halted at 22:15 UTC. Cascading liquidations 23:00 UTC to 02:00 UTC. Local USDe price reached 0.62 to 0.65 USD against 1.00 USD reference. Approximately 19 billion USD total liquidations. Binance SAFU fund injection at 02:00 UTC. Peg restored by 06:00 UTC. Cross-chain corridor stress documented in independent post-mortem at https://insights4vc.substack.com/p/inside-the-19b-flash-crash. |
| `ETH_FUSAKA_MAINNET_2025_12_03` | 2025-12-03 | 2025-12-04 | ETH | hard_fork_activation_peerdas | https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement | 2025-12-03T21:49:11Z | 2025-12-04T05:00:00Z | Fusaka mainnet activation at epoch 411,392. PeerDAS (Peer Data Availability Sampling) introduced. Throughput multiplier of approximately 8x for L2 data availability. Blob fee floor mechanism activated. Validator participation rate dipped briefly to approximately 91% near activation and recovered to approximately 99% within hours. |
| `ETH_BPO1_MAINNET_2025_12_09` | 2025-12-09 | 2025-12-09 | ETH | hard_fork_blob_parameters | https://www.metrika.co/blog/eth-fusaka-bpo1-activation | 2025-12-09T14:21:11Z | 2025-12-09T22:00:00Z | BPO1 (Blob Parameter Only) fork at epoch 412,672. Blob target raised from 6 to 10, maximum from 9 to 15. Brief participation dip to approximately 91% near activation epoch, recovered to approximately 99%. Finality interval unchanged at 2 epochs. |
| `POL_BOR_RPC_2025_12` | 2025-12-12 | 2025-12-18 | POL | rpc_degradation_no_consensus_impact | https://forum.polygon.technology/t/polygon-pos-incident-post-incident-summary/21487 | 2025-12-12T00:00:00Z | 2025-12-18T23:59:59Z | Two-phase event. December 12: earlier slowdown with transactions reported as "missing" and 10% higher gas recommended as workaround. December 17 to 18: Bor nodes stalled by a faulty validator proposal forking Bor nodes; RPC latency elevated; chain block production continued. Patch deployed progressively. Polymarket among affected platforms. |

**Total events in inventory:** 12.

**Distribution by chain_scope:**
- ETH only: 5 (Pectra, Kiln mass exit, SSV mass slashing, Fusaka, BPO1).
- POL only: 4 (Heimdall July 30, Heimdall milestone September 10, Heimdall V2 hard fork September 16, Bor RPC December).
- CCTP V2 corridor only: 2 (V2 mainnet launch March 11, Polygon deployment June).
- Cross-chain (ETH and POL with CCTP V2 corridor effect): 1 (USDe depeg cascade October 10 to 11).

**Date precision:**
- Hour-precise UTC: 10 events.
- Month-only or week-range, requiring Phase 0 refinement: 2 events (`CCTP_V2_POLYGON_DEPLOYMENT_2025_06`, `POL_BOR_RPC_2025_12`).
- Day-precise but hour to refine: 1 event (`ETH_SSV_MASS_SLASHING_2025_09_10`).

---

## 3. Application-layer, governance, and social engineering events excluded by rule

The following events were documented in public sources during 2025 but excluded per the rule criteria of §1. They are listed for audit trail transparency.

| event_id_excluded | date_utc | category_excluded_under | source |
|---|---|---|---|
| Phemex hot-wallet drain | 2025-01-23 | social_engineering / operational_key_management | https://phemex.com/announcements/phemex-hot-wallet-security-incident-update-and-timeline |
| AdsPower supply chain | 2025-01-21 | application_layer_supply_chain | https://www.halborn.com/reports/top-100-defi-hacks-2025 |
| Bybit Safe UI hijack | 2025-02-21 | social_engineering | https://www.ic3.gov/psa/2025/psa250226 |
| Infini admin retention | 2025-02-24 | governance_compromise | https://www.theblock.co/post/342911/stablecoin-neobank-infini-exploited-for-49-million-security-analysts |
| Hyperbridge protocol code bug | 2025-03-15 | application_layer_code_defect | https://www.mexc.com/news/1032019 |
| Bitget VOXEL MM quote manipulation | 2025-04-20 | mev_application_layer | https://www.theblock.co/post/380992/biggest-crypto-hacks-2025 |
| Synthetix sUSD depeg | 2025-04-18 | application_layer_governance (SIP-420) | https://cointelegraph.com/explained/what-happened-to-susd-how-a-crypto-collateralized-stablecoin-depegged |
| Cetus overflow check (SUI) | 2025-05-22 | application_layer_code_defect | https://www.dlnews.com/articles/defi/how-hacker-used-fake-tokens-to-syphon-220m-sui-dex-cetus/ |
| Nobitex exchange hack | 2025-06-18 | operational_key_compromise | https://www.theblock.co/post/380992/biggest-crypto-hacks-2025 |
| GMX V1 reentrancy | 2025-07-09 | application_layer_code_defect | https://www.halborn.com/blog/post/explained-the-gmx-hack-july-2025 |
| Nemo Protocol exploit | 2025-09-08 | application_layer_code_defect | https://decrypt.co/338412/defi-platform-nemo-protocol-exploited-for-2-4-million-in-hack |
| Abracadabra flash loan | 2025-10-01 | application_layer_price_feed_accounting | https://www.theblock.co/post/380992/biggest-crypto-hacks-2025 |
| Balancer V2 rounding | 2025-11-03 | application_layer_code_defect | https://blog.trailofbits.com/2025/11/07/balancer-hack-analysis-and-guidance-for-the-defi-ecosystem/ |
| Upbit KRW exchange breach | 2025-11 | operational_key_compromise | https://www.theblock.co/post/380992/biggest-crypto-hacks-2025 |

---

## 4. Out-of-corridor events documented for transparency but not in inventory

The following 2025 events affect substrate mechanics on chains other than ETH or POL (Arbitrum, Base, Optimism mainnet, or any testnet). They are documented here strictly for transparency: they are not part of the ETH-POL CCTP V2 inventory and are not tested at Step 3.

| event_id_oos | chain | type | source |
|---|---|---|---|
| ARB_SEPOLIA_OUTAGE_2025_03_06 | ARB testnet | sequencer_halt_testnet | https://status.arbitrum.io/cm7xmg3ga002sz8snml0zso5o |
| ETH_PECTRA_HOLESKY_NON_FINALIZATION | ETH testnet | consensus_non_finalization_testnet | https://www.coindesk.com/tech/2025/02/24/ethereum-s-pectra-upgrade-goes-live-on-holesky-testnet-but-fails-to-finalize |
| ARB_SEQUENCER_CONNECTIVITY_2025_06_12 | ARB mainnet | rpc_degradation_sequencer_feed | https://status.arbitrum.io/history/1 |
| BASE_SEQUENCER_HANDOFF_2025_08_05 | BASE mainnet | sequencer_halt_block_production | https://www.coindesk.com/tech/2025/08/06/base-says-sequencer-failure-caused-block-production-halt-of-33-minutes |
| OP_MAINNET_RPC_ENDPOINT_2025_08_19 | OP mainnet | rpc_degradation_with_sequencer_footprint | https://status.optimism.io/history |

The ARB and OP mainnet events are part of the companion corpora `corpus-2025/eth-arb-CCTP/` and `corpus-2025/eth-op-CCTP/` respectively. They are out of scope for this ETH-POL CCTP V2 corpus by chain definition.

---

## 5. Events reviewed but not included pending Phase 0 reconfirmation

The following events surfaced during international scraping but could not be confirmed against a Tier A primary source at the time of this draft. They are not in the inventory of §2. If a Tier A primary source is identified during Phase 0, they are added by dated amendment with prior hash chain preserved.

| event_id_pending | date_utc | type | secondary_source | refinement_method |
|---|---|---|---|---|
| ETH_PRYSM_PARTICIPATION_DROP_2025_12 | 2025-12 (date imprecise) | consensus_client_participation_drop | https://www.halborn.com/blog/post/2025-blockchain-security-forecast-top-threats-for-the-year-ahead | Cross-reference with Ethereum Foundation post-mortem, All Core Devs consensus meeting minutes, or beacon participation logs in Phase 0 |

---

## 6. Sources consulted

Sources dredged on 2026-05-25 in the following order.

**Internal corpus folder sources:**

1. `INCIDENTS_2025_RWA_SUBSTRATE.md` (parent folder, internal inventory compiled 2026-05-19).
2. `RWA_RISKS_SOURCED_2026_05_19.md` (parent folder, academic and institutional sourcing).
3. `M2_BRIEF_v0_DRAFT.md` §2 (parent folder, incident inventory references).
4. `SOURCING_2026_05_15.md` (parent folder, methodology sourcing).
5. `m2_inventory_2025/INFRA_CRITICAL_ETH_ARB_2025.md` and `m2_inventory_2025/INFRA_CRITICAL_ETH_OP_2025.md` (parent subfolder, prior corpus filtering rationale).
6. `m2_inventory_2025/PATTERN_ANALYSIS_2026_05_19.md` (parent subfolder, hot-window definitions used in eth-arb and eth-op corpora).

**External Tier A primary sources:**

- Ethereum Foundation announcements (Pectra, Fusaka).
- Circle pressroom (CCTP V2 launch).
- Metrika post-mortems (Polygon September 10, BPO1).
- Polygon Foundation community forum (Heimdall v2 release, post-incident summaries).
- CoinDesk (Polygon September 10, USDe depeg, Kiln exit).
- The Block (SSV slashing incident).
- Independent cascade analysis (insights4vc.substack.com).

**International scraping (non-anglo-saxon, May 2026 access):**

- ChainCatcher EN, Wu Blockchain, Foresight News (sino-asiatique).
- CoinPost JP (japonophone).
- Cryptoast, Journal du Coin (francophone).
- BTC Echo (germanophone).

No additional incidents beyond those captured in §2 were sourced to Tier A primary documentation from the non-anglo-saxon sources reviewed.

---

## 7. Notes and uncertainties documented before Step 2

**Imprecise dates to refine at Phase 0.**

Three events have precision below hour-level at draft time. Phase 0 on-chain archive replay will refine their hot windows before Step 2 BigQuery extraction begins:

- `CCTP_V2_POLYGON_DEPLOYMENT_2025_06`: refinement via Etherscan and PolygonScan contract creation timestamps for TokenMessenger V2 and MessageTransmitter V2, plus Circle official announcement timestamp.
- `ETH_SSV_MASS_SLASHING_2025_09_10`: refinement via beacon chain slashing event timestamps for the 39 affected validators.
- `POL_BOR_RPC_2025_12`: refinement via Polygon Bor RPC node logs and Polygon community forum post-incident summary timestamps.

**Polygon substrate observable status.**

The production methodology reports the Polygon `rho_ts` axis as having 0.011 second amplitude over 90 days in nominal operation. This corpus does not pre-declare `rho_ts` inoperable during incident windows. The empirical behaviour of `rho_ts` on Polygon during the four POL events (Heimdall July 30, Heimdall milestone September 10, Heimdall V2 hard fork September 16, Bor RPC December) is part of what Step 3 reports.

**CCTP V2 corridor activation timeline.**

The corridor ETH↔POL via CCTP V2 becomes observable only after both endpoints are deployed: Ethereum on 2025-03-11 (V2 mainnet launch) and Polygon mid-2025 (June, exact date pending Phase 0). Events in this inventory prior to the Polygon deployment can exhibit ETH substrate signal but cannot exhibit CCTP V2 corridor signal because the V2 contracts did not yet exist on Polygon. This is documented in `LIMITATIONS.md` of the published corpus.

**Multi-chain event attribution.**

The USDe depeg cascade (`USDE_DEPEG_CASCADE_2025_10_10`) is annotated `ETH+POL+CCTP_V2_corridor` because it propagated across both substrates and exhibited cross-chain settlement stress. It is counted once in the inventory.

**September 10 2025 temporal cluster.**

Three events of this inventory have hot windows on 2025-09-10: `POL_HEIMDALL_MILESTONE_2025_09_10`, `ETH_SSV_MASS_SLASHING_2025_09_10`, and `ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09` (whose hot window extends across that day). The co-occurrence is reported here without interpretation; whether it reflects a common root cause, a chained dependency, or an independent coincidence is a finding of Step 3, not a pre-judgement.

**Sourced vs detected event sets.**

The inventory enumerates events documented externally by Tier A primary sources. Consistent with the prior corpora `eth-arb-CCTP` and `eth-op-CCTP`, the matrix may surface additional substrate events not in this inventory (events that pass the matrix detector but were not externally sourced as standalone incidents). Such broader detection is a property of the matrix, not a deficiency of the sourced inventory. Each externally sourced event in §2 will be examined at Step 3 against the matrix output for that hot window.

---

## 8. Lock procedure

Once this inventory is finalised, the following steps complete Step 1:

1. SHA-256 hash of this file computed and recorded in `MANIFEST.md` §Step 1.
2. Ed25519 signature with key 1 from the contract Step 0 set, produced under namespace `invarians_corpus_eth_pol_cctp_v2_step1`.
3. Signature recorded in `signatures/INCIDENTS_2025.md.sig.1` and verified against `signatures/public_keys/ed25519_1.pub`.
4. `MANIFEST.md` §Step 1 fields updated.

Once Step 1 is locked, Step 2 (BigQuery raw extraction) may begin.

---

End of INCIDENTS_2025.md draft v2 (consolidated, 2026-05-25).
