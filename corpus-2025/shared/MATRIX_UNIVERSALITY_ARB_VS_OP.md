# Matrix Universality Test: ARB vs OP on 2025 Documented Events

## Question

The Delta primitive (Primitive 3) is chain-type-exclusive: ARB-discovered configurations do not transfer to OP, and the OP-discovered configuration does not transfer to ARB (see the OOS validation outputs under each corridor's `results/`). The natural follow-up question is whether the Regime + Bridge State primitive (Primitive 2) carries its descriptive vocabulary consistently across the two chain typologies, or whether it is also chain-type-exclusive.

## Method

A cross-matrix script per corridor computes, for the hot window of every documented 2025 event, the share of hours in which:

- the L1 chain (Ethereum) shows a non-`S1D1` regime,
- the L2 chain (ARB or OP) shows a non-`S1D1` regime,
- the bridge direction L1-to-L2 shows `BS2`,
- the bridge direction L2-to-L1 shows `BS2`.

Year-long divergent-regime baselines for 2025:

| Component                | Share of hours non-S1D1 / BS2 |
|--------------------------|--------------------------------|
| ethereum_divergent_share | 29.5%                          |
| op_divergent_share       | 28.4%                          |
| eth-op_bs2_share         | 3.0%                           |
| op-eth_bs2_share         | 5.8%                           |

ARB-side divergent shares and BS2 shares are documented in the ARB results folder.

## Side-by-side: events shared between ARB and OP corpora

For the four hard forks plus the USDe cascade, both panels saw the same window. The matrix response is reported below.

| Event ID | Title                           | ETH divergent (ARB run) | L2 divergent on ARB | L1->L2 BS2 ARB | L2->L1 BS2 ARB | ETH divergent (OP run) | L2 divergent on OP | L1->L2 BS2 OP | L2->L1 BS2 OP |
|----------|---------------------------------|--------------------------|----------------------|-----------------|-----------------|-------------------------|----------------------|----------------|----------------|
| S03      | Pectra mainnet activation       | 75.0%                    | 0.0%                 | 0.0%            | 0.0%            | 75.0%                   | 0.0%                 | 0.0%           | 0.0%           |
| S04      | Fusaka mainnet activation       | 100.0%                   | 100.0%               | 0.0%            | 25.0%           | 100.0%                  | 100.0%               | 20.0%          | 0.0%           |
| S05      | BPO1 activation                 | 75.0%                    | 25.0%                | 0.0%            | 12.5%           | 75.0%                   | 12.5%                | 0.0%           | 0.0%           |
| D01      | USDe Binance cascade            | 20.0%                    | 50.0%                | 0.0%            | 30.0%           | 20.0%                   | 100.0%               | 0.0%           | 0.0%           |

## Reading

**Hard forks (S03, S04, S05).** The matrix captures hard fork windows consistently across both L2 typologies. On Pectra (S03) the ETH panel fires at 75% on both runs (same Ethereum panel), and both L2 panels remain at S1D1 (L1-only impact at the substrate level, the L2 sequencer cadence is not perturbed). On Fusaka (S04) the matrix fires at 100% on both ETH and on both L2 panels simultaneously, with bridge BS2 also firing on at least one direction in each corridor. On BPO1 (S05) the matrix fires on ETH at 75% on both runs and shows a smaller L2-side response (12.5% to 25%), as expected from a blob-target adjustment that affects calldata pricing rather than block-production cadence.

**USDe cascade (D01).** Same window, different L2 responses: ARB panel fires at 50% with bridge BS2 on arb-to-ETH at 30% (heavy outbound flow from ARB during the cascade); OP panel fires at 100% but bridge BS2 stays at 0% (less outbound CCTP volume from OP). The matrix vocabulary applies in the same way in both cases; the underlying chain behaviour differs.

**Chain-specific events.** ARB had L02 (sequencer connectivity 2h35) which left the matrix flat on the hot window (both ETH and ARB at S1D1). This is a known edge: the matrix is computed on observed blocks, and a sequencer downtime that suppresses block production leaves no signal in the regime vocabulary. The OP corridor did not have a comparable mainnet event in 2025. OP had Isthmus (S03b, OP Stack hard fork on 2025-05-09 16:00 UTC) which the matrix qualified at 80% ETH-side divergent and 0% OP-side: the OP Stack upgrade did not interrupt sequencer cadence at hour granularity. OP also had a 22-minute RPC endpoint outage (2025-08-19) which the matrix qualified at 100% divergent on the OP panel during the exact hour, despite the official OP status page reporting no sequencer impact, suggesting that the public-endpoint outage affected data collection feeding the regime computation on that hour.

## Verdict

The Regime + Bridge State primitive uses a consistent descriptive vocabulary across both chain typologies. On shared documented events (hard forks, macro cascades), the matrix response is qualitatively similar between the ARB and OP runs, with chain-specific differences in magnitude that map to the actual substrate dynamics rather than to vocabulary translation issues. Fusaka (S04) in particular fires at 100% on both L1 and both L2 panels, with bridge BS2 detected on both corridors. Pectra fires at 75% on ETH and stays at S1D1 on both L2 panels.

This is consistent with the universality conjecture noted in the Delta research synthesis: Primitive 2 carries its descriptive vocabulary across chain typologies, whereas Primitive 3 (Delta) is chain-type-exclusive. The result is qualitative, not statistically tested at the strict level applied to Delta. A formal universality test of Primitive 2 would require a larger event corpus and a placebo-permutation framework over the regime distribution, which is a separate study.

## Limits

- Six events on OP, eight on ARB. Small N. Qualitative comparison only.
- The matrix vocabulary is the same by construction (`S1`, `S2+`, `S2-`, `D1`, `D2+`, `D2-`, `D2`-mixed, `BS1`, `BS2`). The test verifies operational meaning, not whether the same regime code maps to the same underlying substrate physics across chains.
- The L02 ARB sequencer outage exposed a known matrix limit (blocks absent are not blocks divergent). This applies symmetrically to OP though OP did not have a comparable event in 2025 to confirm the limit on the OP corpus.
- The 2025-08-19 OP RPC event suggests an unexpected sensitivity of the matrix to RPC endpoint health on the data collection side. To be re-examined: the regime computation pipeline should be resilient to single-hour RPC outages or it should explicitly mark the hour as unavailable rather than as divergent.

## Companion files

- `../eth-arb-CCTP/results/` (ARB corridor outputs).
- `../eth-op-CCTP/results/` (OP corridor outputs).
- `INFRA_CRITICAL_ETH_ARB_2025.md` (ARB event inventory).
- `INFRA_CRITICAL_ETH_OP_2025.md` (OP event inventory).
