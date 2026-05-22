# Five Substrate-Critical Events, ETH-ARB-CCTP Corridor, 2025

The five events below match two criteria:

1. They have at least one Tier A peer-reviewed academic source documenting the underlying failure mode.
2. They have at least one Tier A institutional source documenting their RWA criticality.

Application-layer hacks (smart contract bugs, governance compromises, exchange breaches) are explicitly excluded per the Invarians substrate observability mandate.

Order: chronological.

## E1, Pectra Mainnet Hard Fork, 2025-05-07 10:05 UTC

### What happened

Ethereum mainnet activated the Pectra hard fork at epoch 364032, on 2025-05-07 at 10:05:11 UTC. The upgrade introduced EIP-7702 (smart account migration), EIP-7251 (validator consolidation, maximum stake raised from 32 to 2048 ETH per validator), and revised blob parameters. Activation was reported as a "quiet launch" on mainnet, though the prior Holesky testnet activation on 2025-02-24 failed to finalize for 18 to 24 days due to a misconfigured deposit contract address that produced a client split between Geth, Nethermind, Besu on one side and Erigon, Reth on the other.

### Academic backing of the failure mode

- Schwarz-Schilling, Neu, Monnot, Asgaonkar, Tas, Tse, "Three Attacks on Proof-of-Stake Ethereum", Financial Cryptography 2022, eprint.iacr.org/2021/1413, arxiv 2110.10086. Documents ex-ante and ex-post reorg attack surfaces in PoS Ethereum that hard fork parameter changes can amplify or reduce.
- "Available Attestation: Towards a Reorg-Resilient Solution for Ethereum", eprint.iacr.org/2025/097. Documents that 1-3 block reorgs remain non-negligible post-Merge.
- Grandjean, Heimbach, Wattenhofer, "Ethereum Proof-of-Stake Consensus Layer: Participation and Decentralization", Financial Cryptography 2024 Workshops, Springer LNCS 14746. Measures validator participation drops empirically.

### Institutional RWA criticality

- ECB Eurosystem, "Bridging Innovation and Stability: the Eurosystem's Exploratory Work on New Technologies for Wholesale Central Bank Money Settlement", June 2025. Identifies operational concentration in DLT operators and the need for coordinated upgrades as a residual risk for institutional tokenized settlement (https://www.ecb.europa.eu/press/pubbydate/2025/html/ecb.exploratoryworknewtechnologies202506.en.html).
- Paxos public maintenance announcement for ETH and ERC-20 transfers during the upgrade window (https://support.paxos.com/hc/en-us/articles/37221865480724-Ethereum-Pectra-Upgrade-on-May-7-2025), documenting that institutional issuers paused transfers for 2 to 4 hours around the activation.

### Plot

`plots/S03_pattern.png`

## E2, Arbitrum One Sequencer Connectivity Issue, 2025-06-12 19:05 to 21:40 UTC

### What happened

Arbitrum One sequencer experienced a connectivity issue lasting approximately 2 hours 35 minutes. Block production at the sequencer side continued, but the RPC and feed delivery to users was degraded. Documented on the Arbitrum status page (https://status.arbitrum.io/history/1).

### Academic backing of the failure mode

- Gorzny, Po-An, Derka, "Ideal Properties of Rollup Escape Hatches", DICG 2022, ACM (https://dl.acm.org/doi/pdf/10.1145/3565383.3566107). Formalizes the properties an L2 escape hatch must satisfy when the sequencer is unavailable.
- "A Practical Rollup Escape Hatch Design", arxiv 2503.23986, March 2025. Documents that force-inclusion mechanisms on Arbitrum, Optimism, and Base have varying effectiveness and may not fully mitigate sequencer censorship or outage.
- "Ethical Risk Analysis of L2 Rollups", arxiv 2512.12732. Treats L2 sequencer centralization as a governance and regulatory risk in addition to a technical risk.

### Institutional RWA criticality

The event itself is below the institutional RWA cadence threshold (typical RWA flows operate at T+0 hours to T+1 next business day; a 2h35min outage does not breach this). The event is included in the analysis as a precision case: the substrate matrix is expected to classify the corridor as nominal during this event, because the underlying block production was nominal, and the issue was at the RPC and feed layer, not the substrate. A substrate observability instrument should not raise an alarm in this case.

### Plot

`plots/L02_pattern.png`

## E3, USDe Cascade and CCTP Attestation Latency Spike, 2025-10-10 20:30 to 2025-10-11 06:00 UTC

### What happened

A market-wide liquidation cascade triggered by US-China trade announcements at 21:00 UTC on 2025-10-10, followed by Binance price feed reading interruptions at 22:15 UTC and cascading position liquidations at 23:00 UTC, pushed USDe (Ethena synthetic stablecoin) local price on Binance to between $0.62 and $0.65. Approximately $19 billion in crypto positions were liquidated. Binance deployed $283 million from its SAFU fund at 02:00 UTC on 2025-10-11. USDe peg was fully restored by 06:00 UTC. During the cascade, CCTP attestation latency on the Ethereum-to-Arbitrum route spiked to approximately 11.9 hours on p90.

### Academic backing of the failure mode

- Federal Reserve FEDS Note, "In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins", 2025-12-17 (https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html). Documents two-way feedback between TradFi banking stress and DeFi stablecoin runs as a structural channel.
- BIS Working Paper No 1164, "Public Information and Stablecoin Runs", https://www.bis.org/publ/work1164.pdf. Theoretical model of run dynamics on stablecoins.
- Belchior, Augusto et al., "SoK: Security of Cross-chain Bridges", arxiv 2312.12573. Off-chain attestor latency is documented as a vulnerability class.
- Augusto, Belchior et al., "SoK: Cross-Chain Bridging Architectural Design Flaws and Mitigations", arxiv 2403.00405. Off-chain dependency timing as architectural risk component.

### Institutional RWA criticality

- IOSCO Final Report FR/17/2025, "Tokenization of Financial Assets", November 2025 (https://www.iosco.org/library/pubdocs/pdf/IOSCOPD809.pdf). Explicitly identifies the lack of credible settlement assets and depeg of settlement-layer stablecoins as a structural risk for RWA tokenization adoption.
- BIS Project Agora (https://www.bis.org/about/bisih/topics/fmis/agora.htm). States that "uncertainty over when settlement is final" is a core risk for cross-border tokenized payments.
- BIS Project Mariana (https://www.bis.org/publ/othp75.pdf). PvP atomic settlement is necessary to eliminate principal risk; depeg of a settlement leg breaks atomicity.

### Plot

`plots/D01_pattern.png`

## E4, Fusaka Mainnet Hard Fork with PeerDAS, 2025-12-03 21:49 UTC

### What happened

Ethereum mainnet activated the Fusaka hard fork at epoch 411,392, on 2025-12-03 at 21:49:11 UTC. Fusaka introduced PeerDAS (Peer Data Availability Sampling), enabling nodes to verify rollup data availability without downloading it in full. Layer 2 throughput improved by an order of 8, and transaction costs on rollups dropped to between $0.01 and $0.10. Both Ethereum L1 and Arbitrum L2 substrate matrices showed simultaneous divergent regimes during the activation window, indicating strong cross-chain coupling.

### Academic backing of the failure mode

- Heimbach, Wattenhofer et al., "Two Sides of the Same Coin: Large-scale Measurements of Builder and Rollup after EIP-4844", arxiv 2411.03892, November 2024. Sets the empirical context for PeerDAS, which extends the blob market dynamics that EIP-4844 introduced.
- Gorzny, Po-An, Derka, "Ideal Properties of Rollup Escape Hatches", DICG 2022 (cited above). PeerDAS materially changes the data availability assumptions on which rollups rely; the framework is the formal reference.

### Institutional RWA criticality

- Fidelity Digital Assets Research, "The Fusaka Upgrade: Scaling Meets Value Accrual" (https://www.fidelitydigitalassets.com/research-and-insights/fusaka-upgrade-scaling-meets-value-accrual).
- AMINA Bank Research, "Ethereum Fusaka Upgrade: Scaling Infrastructure Through Data Efficiency".
- Amundi (Europe's largest asset manager) launched a tokenized share class of its money market fund directly on public Ethereum in November 2025, in preparation for the post-Fusaka cost economics. Reported by https://ledgerinsights.com and confirmed in Fidelity coverage. This is a direct documented case of RWA enablement by a substrate upgrade.

### Plot

`plots/S04_pattern.png`

## E5, BPO1 Mainnet Activation, 2025-12-09 14:21 UTC

### What happened

Ethereum mainnet activated the first Blob Parameter Only (BPO1) fork at epoch 412,672, on 2025-12-09 at 14:21:11 UTC. BPO1 raised the per-block blob target from 6 to 10 and the maximum from 9 to 15. A brief participation dip to approximately 91 percent was observed near the activation epoch before recovery to 99 percent. Finality continued at 2 epochs throughout.

### Academic backing of the failure mode

- Heimbach et al. EIP-4844 paper, arxiv 2411.03892. Direct relevance: BPO1 changes the blob target parameters that this empirical study characterizes.
- Reijsbergen, Sridhar, Monnot et al., "Transaction Fees on a Honeymoon: Ethereum's EIP-1559 One Month Later", arxiv 2110.04753. Sensitivity of inclusion delay and fee dynamics to parameter changes of EIP-1559-style mechanisms.

### Institutional RWA criticality

- Metrika analysis, "Ethereum's Fusaka Upgrade and BPO1 Activation" (https://www.metrika.co/blog/eth-fusaka-bpo1-activation). Documents participation dynamics and operational implications.
- Direct implication: RWA issuers using rollup-side blob data must readjust their settlement cost economics after the parameter change. Less broad than Fusaka but operationally non-trivial.

### Plot

`plots/S05_pattern.png`

## Reading guide

Each plot follows the same 7-panel layout (see `METHODOLOGY.md` section 5.4):

- Top 4 panels: categorical strips for ETH regime, ARB regime, bridge state ETH-to-ARB, bridge state ARB-to-ETH.
- Middle 2 panels: continuous signed shifts for ETH (5 axes) and ARB (8 axes), aligned with the v2.0 API contract.
- Bottom panel: CCTP attestation latency p50, p90, p99 on both routes, log scale, with the hourly combined-cell lift overlaid on the right axis (log scale).

Vertical red lines and shading mark the hot window of the event.

Note on E2 (Arbitrum sequencer): the plot is expected to show nominal classification during the hot window (lift around 2, dominated by the baseline cell). This is the correct behavior given that the event is sub-critical for substrate-level RWA flows. A false positive on this event would erode the precision of the instrument for the cases where the substrate matters.

Note on E4 (Fusaka): the plot shows the largest combined-cell lift of the five events (more than 2000x on the dominant hot cell), reflecting the cross-chain coupling of the deepest substrate upgrade of 2025.

## Excluded from this scope

The following 2025 events are documented in other Invarians research but excluded from this corridor-specific analysis:

- Polygon PoS finality lag, 2025-09-10. Critical event but Polygon is not in the ETH-ARB-CCTP corridor.
- Base sequencer handoff failure, 2025-08-05. Base is not in the corridor.
- Polygon Heimdall consensus bug, July 2025. Not in the corridor.
- Polygon Bor RPC disruption, December 2025. Not in the corridor.
- All 2025 hacks and exploits (Bybit, Balancer, GMX, Cetus, Infini, etc.). Out of scope per Invarians substrate observability mandate.

## Limitations

See `LIMITATIONS.md` for the four caveats that apply across all five events.
