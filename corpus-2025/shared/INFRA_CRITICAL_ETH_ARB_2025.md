# Infrastructure-Critical Events: ETH-ARB Corridor, 2025

Filtered per the Invarians substrate observability scope. Includes only events that affect substrate or bridge infrastructure layer. Excludes application-layer code bugs, governance compromises, social engineering.

The list is the candidate dataset for the pre / during / post pattern analysis (lift + shift + attestation).

## Included events (substrate / infrastructure / settlement-asset)

| ID  | timestamp_utc            | type                                       | chain          | severity                          | source |
|-----|--------------------------|--------------------------------------------|----------------|-----------------------------------|--------|
| S03 | 2025-05-07 10:05         | Hard fork mainnet                          | ETH            | structural                        | [EF Checkpoint 2](https://blog.ethereum.org/en/2025/04/29/checkpoint-2) |
| L02 | 2025-06-12 19:05 - 21:40 | L2 sequencer connectivity issue            | ARB            | operational sub-RWA-critical      | [Arbitrum status](https://status.arbitrum.io/history/1) |
| D01 | 2025-10-10 20:30 to 2025-10-11 06:00 | Settlement-asset cascade (USDe + CCTP latency) | ETH + ARB (via CCTP) | settlement-asset critical | [CoinDesk USDe](https://www.coindesk.com/markets/2025/10/11/ethena-s-usde-briefly-loses-peg-during-usd19b-crypto-liquidation-cascade) |
| S04 | 2025-12-03 21:49         | Hard fork mainnet (Fusaka, PeerDAS)        | ETH            | structural                        | [EF Fusaka](https://blog.ethereum.org/2025/11/06/fusaka-mainnet-announcement) |
| S05 | 2025-12-09 14:21         | Hard fork BPO1 (blob target adjustment)    | ETH            | structural minor                  | [Metrika BPO1](https://www.metrika.co/blog/eth-fusaka-bpo1-activation) |

## Excluded events (application-layer code or governance, out of substrate scope)

| ID  | Why excluded |
|-----|--------------|
| B01 Phemex      | Hot wallet compromise, application-layer |
| B02 AdsPower    | Supply-chain attack on browser software |
| B03 Bybit       | Gnosis Safe UI hijack, social engineering |
| B04 Infini      | Admin rights retention, governance failure |
| B05 Hyperbridge | Bridge code bug |
| B06 Bitget VOXEL| Market-maker quote manipulation |
| B07 Cetus       | Overflow check bug (SUI, also outside corpus) |
| B08 Nobitex     | Politically-motivated exchange hack |
| B09 GMX V1      | Reentrancy code bug (substrate on ARB but cause is contract) |
| B10 Nemo        | Yield protocol bug (SUI primary) |
| B11 Abracadabra | Flash-loan code exploit |
| B12 Balancer V2 | Rounding bug in stable pool math |
| B13 Upbit       | KRW exchange hack |
| D02 Nov DeFi depegs | Code-exploit-triggered depegs |
| L01 ARB Sepolia | Testnet, outside mainnet corpus |
| L03 Base sequencer | Outside ETH-ARB corpus |
| S01 Pectra Holesky | Testnet, no Holesky data in parquets |
| S02 Pectra Sepolia | Testnet |

## Rationale for the five included events

- **S03 Pectra**: substrate-level upgrade affecting all of Ethereum. Validators, builders, and RPC providers must coordinate. Documented as RWA-relevant per ECB DLT trial findings on operational concentration.
- **L02 Arbitrum sequencer connectivity**: although NOT documented as RWA-critical (sub-RWA-cadence at 2h35), the event is included as an infrastructure-substrate test case. Expected behavior: matrix classes nominal because substrate side is fine, the issue is at the RPC and feed layer. The intent is to demonstrate that a substrate observability instrument does not raise a false alarm on a non-substrate issue.
- **D01 USDe cascade**: settlement-asset depeg with massive on-chain consequences. Critical for any RWA flow using USDe-adjacent collateral. Substrate consequences include CCTP attestation_p90 spike to approximately 11.9 hours, ARB demand surge, and `sequencer_publish_latency_arb` shift z approximately 3.28.
- **S04 Fusaka**: deepest substrate change of 2025 (PeerDAS). All chains exposed.
- **S05 BPO1**: blob parameter adjustment, minor but structural. Tests matrix sensitivity to subtle substrate changes.

## Why the application-layer filter is consistent with the substrate mandate

The matrix measures substrate (block production rhythm, demand, finality, bridge attestation). It does not measure smart contract correctness, multisig integrity, or off-chain attestor liveness. Including application-layer hacks in a substrate test would test the wrong instrument. The filter is honest scoping, not cherry-picking.

The L02 inclusion (although the event is not RWA-critical) is intentional: it lets the analysis demonstrate that the matrix correctly classifies a sub-RWA-cadence sequencer halt as nominal, because operationally it IS nominal for the RWA use case. This is precision aligned with criticality.

## Known observable gap: ETH beacon_participation 2025

`beacon_participation` is exposed by the v2.0 API on Ethereum L1 as a structural observable (third axis alongside `rhythm` and `continuity`). It is NOT covered in this analysis for the 2025 corpus.

The Invarians production sensor for beacon participation was calibrated and deployed around 2026-05-01 (threshold low = 0.97). For 2025 historical reconstruction, the only available external sources are (a) beaconcha.in public API (rate-limited free tier), (b) Dune SQL (paid subscription), and (c) paid third-party providers (Goldsky, Allium). All three carry a cost or operational risk that the marginal value of beacon_participation on the events tested here does not justify (Pectra and Fusaka typically show participation near 99% even at activation; the dip is not the primary substrate signal at activation hours).

Future analyses on events post-2026-05-01 can integrate this third axis.
