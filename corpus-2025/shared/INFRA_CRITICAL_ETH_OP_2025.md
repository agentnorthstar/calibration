# Infrastructure-Critical Events: ETH-OP Corridor, 2025

This file mirrors `INFRA_CRITICAL_ETH_ARB_2025.md` for the Optimism corridor. It lists documented infrastructure-grade events in calendar year 2025 that have a measurable substrate footprint on Ethereum L1, Optimism L2, or the ETH-OP-CCTP bridge corridor. Application-layer bugs, governance compromises, UI exploits, and price feed errors are out of scope by design (consistent with the Invarians substrate observability mandate).

## Methodology

Sources consulted: status.optimism.io (notice history 2024 to 2026), Optimism Docs outage page, Optimism blog, Ethereum Foundation announcements (Pectra, Fusaka), public analyses of the October 10 to 11, 2025 cascade, and Blockworks. Documented events are mapped to the Invarians substrate matrix at hour-level resolution via `op_panel_2025.parquet` and the ETH panel columns of `annual_panel_2025.parquet`.

## Events retained for the cross-matrix test

| ID    | Date / time (UTC)                       | Title                                                | Substrate footprint expected on ETH-OP-CCTP                              | Mirror of ARB event |
|-------|-----------------------------------------|------------------------------------------------------|---------------------------------------------------------------------------|---------------------|
| S03   | 2025-05-07 10:05                        | Pectra mainnet activation (Ethereum L1)              | ETH structural rhythm + beacon participation; blob target 6 to 9         | S03 (ARB)           |
| S03b  | 2025-05-09 16:00                        | Isthmus hard fork (OP Stack mainnet)                 | OP-specific Prague L2 features rollout; sequencer config change required | OP-only             |
| D01   | 2025-10-10 20:30 to 2025-10-11 06:00    | USDe Binance cascade, $19B liquidations              | ETH demand axis (sigma/size/tx spike), CCTP both directions reroute      | D01 (ARB)           |
| S04   | 2025-12-03 21:49                        | Fusaka mainnet activation (Ethereum L1)              | ETH structural (PeerDAS), blob target step                               | S04 (ARB)           |
| S05   | 2025-12-09 14:21                        | BPO1 mainnet activation (blob target 6 to 10, max 9 to 15) | ETH demand axis (blob market step), L2 fee curve discontinuity      | S05 (ARB)           |

## Events NOT retained, with reason

- **2025-08-19 17:43 to 18:05 (OP Mainnet Public Endpoint Outage, 22 min)**: initially characterized as RPC-layer only by the official status page. Reclassified after investigation: the OP substrate panel shows `sequencer_publish_latency` rising from 516s (17h) to 708s (18h, +37%) with positive shift +0.486. Block production cadence remained stable (1800 blocks per hour). The cluster upgrade affected the batch-submission service in addition to the public endpoint, producing a measurable substrate footprint that the matrix detected. See `eth-op-CCTP/LIMITATIONS.md` for the discussion.
- **2025 Q1 to Q3 outside the above events**: status.optimism.io reports 100.0% uptime on Transaction Sequencing, Batch Submission, and Node Sync components for the calendar year, with the single exception above. Unlike ARB which had a documented sequencer connectivity incident on 2025-06-12 (L02, 2h35), OP did not experience a comparable mainnet sequencer downtime in 2025.
- **2025-09-25 and 2025-09-26 (Flashblocks Sepolia maintenance)**: testnet only.
- **2025-11-19 (Flashblocks Sepolia outage 2h03)**: testnet only.

## Key contrast with ARB 2025

The ARB corpus contains one OP-stack-incompatible incident (L02 sequencer connectivity 2h35 on 2025-06-12) that surfaced an Arbitrum-Nitro-specific substrate footprint. No equivalent event is documented for OP mainnet in 2025. The ETH-OP-CCTP cross-matrix is therefore tested on five system-wide transitions (Pectra, Isthmus, USDe cascade, Fusaka, BPO1), four of which are shared with ARB and one of which (Isthmus) is OP-specific.

## Outputs of the cross-matrix test

For each event window of plus or minus 6 hours around the event start, the analysis computes:

- The distribution of `regime_op` codes observed during the window.
- The distribution of `regime_eth` codes during the window.
- The distribution of `bridge_state_eth_op` and `bridge_state_op_eth` codes.
- The lift of non-`S1D1` regime occurrence versus the year baseline (event vs baseline rate).
- The lift of `BS2` occurrence versus the year baseline.

The same logic was previously applied to the ARB corpus. The comparison between the two outputs answers the question of whether the Regime + Bridge State primitive (Primitive 2) captures documented events with consistent operational meaning across chain typologies. The synthesis is in `MATRIX_UNIVERSALITY_ARB_VS_OP.md`.
