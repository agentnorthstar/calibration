---
title: "Drift Signal Predictive Validation"
status: in-progress
date: "2026-05-02"
audience: [ai-agents, developers, researchers]
related: ["methodology.md", "calibration_log.md", "limitations_and_plans.md"]
---

# Drift Signal Predictive Validation

> **Status:** in progress.
>
> The Drift Signal primitive (API v2.0, since 2026-04-30) exposes per-metric `MetricBlock` fields (`ratio`, `ratio_long`, `shift`, `shift_delta`, `shift_magnitude_delta`) plus a per-axis composite drift. This document tracks the empirical validation of the Drift Signal as a leading indicator on observed substrate events.

---

## 1. Why this document exists

API v2.0 introduces Drift Signal as a third primitive alongside Attestation and Regime. The architectural intent is that Regime classification stays calibrated halt-only on the structural axis (1800 s on Optimism, 480 s on Base, 600 s on Arbitrum for `sequencer_publish_latency`; 0.97 low threshold for `beacon_participation` on Ethereum), and Drift Signal carries the continuous magnitude of soft slowdowns and slow drifts that do not flip the regime.

The intent is testable: if Drift Signal is useful, observed deviations on `shift` and `shift_magnitude_delta` should correlate with documented substrate events on the same chain and same window, with timing detectable before or contemporaneously with the event.

This document indexes candidate ground-truth cases, defines the validation protocol, and will be extended with empirical results as the long-term EMAs stabilize and `shift_available` flips to `true` per metric.

---

## 2. Indexed candidate cases (as of 2026-05-02)

### Case A: rsETH cascade D2±, Ethereum, 2026-04-18

**Event:** Restaking liquidation cascade observed on rsETH between 17:35 and 19:02 UTC, 2026-04-18. The structural and demand axes both moved into a composite signature consistent with agentic concentration on a single asset class. Pre-event window (24 h prior to 17:35) showed elevated drift mean on `tx_ratio` and `size_ratio` with episodic D2+ pulses. Cascade window (~2 h) showed compressed drift and 100% S1D1 regime. Post-event window (52 h) showed reduced drift and reduced D2+ pulse rate relative to a control window of similar length.

**Indexed for Drift Signal validation:**
- Pre-event window: `sigma_shift`, `tx_shift`, `size_shift` expected positive on Ethereum L1 demand axis.
- Cascade window: D2± regime emitted (composition split), expected on signed regime codes.
- Post-event window: drift trajectory reverting toward baseline.

**Limitation:** N=1 case. Statistical generalization requires multi-event observation.

### Case B: Optimism soft slowdown, 2026-04-27 to 2026-04-30

**Event:** Sustained 70 percent drift on `batch_gap_seconds` over approximately 4 days. Top-tail observations: 18 batches with `batch_gap_seconds >= 648 s` across 48 hours (mean ~660 s, x1.9 nominal). 6-hour running mean ~580 s (x1.7 nominal ~348 s). Maximum single batch gap 732 s (x2.1 nominal, well below the calibrated S2+ threshold at 1800 s). Regime stayed `S1D1` throughout. A smaller bump on 2026-04-21 to 2026-04-22 (~24 h, x1.5 nominal) is included in the same window.

**Indexed for Drift Signal validation:**
- `sequencer_publish_latency.shift` on Optimism L2 expected positive and sustained around +0.7 (i.e. +70 percent of baseline) for the duration of the cluster.
- `shift_magnitude_delta` expected to capture the rising-then-stable-then-reverting trajectory across the 4 days.
- Cross-check against Arbitrum and Base running means over the same window: correlated drift would suggest upstream blob market saturation; drift isolated to Optimism would suggest sequencer-side or chain-specific maintenance.

**Limitation:** Single chain, single cluster, no causal attribution.

### Case C: Ethereum beacon participation dip, epoch 444103

**Event:** During the calibration fetch on 2026-05-01, a single-epoch validator participation rate of 0.96814 was observed on epoch 444103, approximately 10 sigma below the mean of the calibration window (mean 0.99774, stdev 0.00297, n=338 samples). The dip is well above the historical halt range (Geth bug 2024-12 at ~0.94, Lido outage early 2024 at ~0.96) but clearly off baseline.

**Indexed for Drift Signal validation:**
- `beacon_participation_shift` on Ethereum L1 expected to register a transient negative deviation at the epoch in question.
- `shift_magnitude_delta` expected to flag the magnitude of the dip relative to its prior trajectory.

**Limitation:** Single epoch, calibration fetch only sampled every 20 epochs (~2 hours), so an isolated single-epoch dip can be missed in production sampling. Reserved as a candidate, not a confirmed in-production signal.

---

## 3. Validation protocol

For each indexed case, the following procedure applies once the relevant metric has `shift_available: true`:

1. Pull the panel API time series for the chain and metric over a window starting 7 days before the event and ending 7 days after.
2. Tag the documented event window (`event_start`, `event_end`).
3. Plot `ratio` and `shift` over the window. Mark the event window.
4. Compute the maximum `|shift|` inside the event window vs the maximum `|shift|` in the surrounding control window (same length, no event).
5. Compute the lead time: time elapsed between the first sample where `|shift| > threshold` and the event start. Negative lead times indicate the signal lagged the event.
6. Report the contingency on the chain population: `lead_time_minutes`, `peak_shift`, `regime_codes_emitted`.

A meta-protocol over multiple cases (target N >= 5 per metric) computes:
- Distribution of lead times.
- TPR (event-anchored): fraction of cases where `|shift|` exceeded threshold inside or before the event window.
- FPR (control): fraction of equal-length non-event windows where `|shift|` exceeded threshold.

Clopper-Pearson IC95% applies as in `backtest_ethereum.md`.

---

## 4. Activation status

| Metric | Chain | `shift_available` | Activation target |
|---|---|---|---|
| `rhythm.shift` | Ethereum | true | active since v2.0 launch |
| `continuity.shift` | Ethereum | true | active since v2.0 launch |
| `sigma.shift` | Ethereum, Polygon | true | active since v2.0 launch |
| `size.shift` | Ethereum, Polygon | true | active since v2.0 launch |
| `tx.shift` | Ethereum, Polygon | true | active since v2.0 launch |
| `beacon_participation.shift` | Ethereum | false | end-May 2026 (30 d post-launch) |
| `sequencer_publish_latency.shift` | Arbitrum, Base, Optimism | false | end-May 2026 (30 d post-launch) |
| `complexity.shift` | Arbitrum, Base, Optimism | true | active since v2.0 launch |
| `gas_complexity.shift` | Arbitrum, Base, Optimism | true | active since v2.0 launch |

Cases A (rsETH, demand axis on ETH) is testable now against `sigma_shift`, `size_shift`, `tx_shift` time series for 2026-04-18.
Case B (Optimism) becomes testable end-May 2026 once `sequencer_publish_latency.shift` activates.
Case C (Ethereum beacon dip) becomes testable end-May 2026 once `beacon_participation.shift` activates.

---

## 5. Public commitment

This document will be extended with empirical results as the relevant `shift_available` flags flip to `true` and the indexed cases become testable. Negative results (the Drift Signal failed to detect a documented event, or fired in the absence of an event) are part of the publication discipline; they will be reported with the same rigor as positive results, in line with `methodology.md` §10 and `backtest_ethereum.md`.

The protocol is pre-registered: thresholds, window sizes, and TPR/FPR computation are fixed before any empirical analysis is published. Any subsequent change to the protocol will be logged in `calibration_log.md` with rationale and a flag distinguishing methodological refinement from data-driven adjustment.

---

*Created 2026-05-02. Living document, updated as `shift_available` activations and cases accumulate.*
