---
title: "Invarians — Pre-Engagement, Substrate-Shift Precursors against BS_STRUCTURAL_v1.1 BS2 outcome — extended feature space (v2)"
version: "2.0-draft"
status: draft
audience: [ai-agents, developers, researchers, auditors]
---

# Pre-engagement protocol v2 — substrate-shift precursors against `BS_STRUCTURAL_v1.1 BS2`, extended feature space

> **Protocol identifier.** `BS_STRUCTURAL_PRECURSORS_v2`.
>
> **Successor to.** `BS_STRUCTURAL_PRECURSORS_v1` (commit `3239fef` on the public corpus repository). v1 produced an empty survivor set on the 2025 ETH-POL CCTP V2 corpus over a single predictor family (shift-magnitude delta of the ten substrate-shift axes). The present protocol extends the predictor space to cover the four representations of the substrate matrix that are present in the locked Step 3 baseline parquet, without modifying the outcome definition, the calibration window, the SLA gating, or the statistical machinery. The empty survivor set of v1 is preserved as the published result for the v1 feature family; v2 evaluates the residual predictor space.
>
> **Lock condition.** Three Ed25519 signatures in namespace `invarians_calibration_bs_structural_precursors_v2`, OpenTimestamps Bitcoin anchor on each, before any execution of `compute_bs_structural_precursors_v2.py` against the locked Step 3 corpus parquets.

## 1. Purpose

The locked Step 3 baseline parquet exposes the substrate matrix in four signed representations per chain per axis:

- the raw hourly ratio against the 30-day EMA (`<axis>`),
- the EMA baseline itself (`<axis>_ema`),
- the signed shift `(ratio − ema) / ema_safe` (`<axis>_shift`),
- the drift composite `mean(shifts within axis-type)` (`drift_structural`, `drift_demand`).

Protocol v1 evaluated one derived representation only: the shift-magnitude delta `SMD(t) = |shift(t)| − |shift(t-1)|`. This representation collapses polarity (positive and negative stress treated identically by the absolute value) and shifts to the first difference (the rate of change of the absolute deviation, not the deviation itself). The empty survivor set under v1 does not exhaust the matrix; it documents a single projection.

Protocol v2 evaluates the three additional representations that are mechanically distinct from SMD-of-shift:

1. **Signed shift level** (`<axis>_shift` directly), with polarity-separated tail thresholds on the positive and negative distributions.
2. **Drift composite level** (`drift_structural`, `drift_demand` per chain), with polarity-separated tail thresholds.
3. **Cross-chain and multi-axis groupings** as in v1 (carried over for structural comparability).

The outcome, the corpus window, the SLA gating, the FDR alpha, the lift threshold, and the placebo permutation count are inherited verbatim from v1.

The hypothesis is:

```
H₀ (null)
  No substrate-shift representation among
  { SMD-of-shift, signed-shift-level, drift-composite-level }
  on the locked Step 3 baseline of the 2025 ETH-POL CCTP V2 corpus
  anticipates BRIDGE_STATE_STRUCTURAL_v1.1 BS2 outcome on the corridor
  at a future hour t + lead beyond its baseline rate.

H₁ (alternative)
  At least one configuration of the extended predictor space fires with
  measurable lift on P(BS2 at t+lead | configuration fires at t).
```

## 2. Outcome definition

Identical to v1 §2 verbatim:

```
BS_STRUCTURAL_v1.1 BS2(t, source, dest, mode) ≡ 1
  iff n_eligible_t ≥ 5
   AND (success_rate_t < 0.995 OR mode_fallback_rate_t > 0.05)
```

with `SLA_fast = 120 s`, `SLA_standard = 7200 s`, 1-hour aggregation window. Standard-mode triplets remain structurally NULL on the 1-hour window and are excluded from the outcome set:

```
outcome_1 = bs2_eth_to_pol_fast
outcome_2 = bs2_pol_to_eth_fast
```

The classifier semantics of v1 §2.2 (`min_finality_threshold_requested == 0 → 'other'`) are inherited.

## 3. Input data

Identical to v1 §3 verbatim:

- `data/cctp_v2_events_2025_raw.parquet` (paired via on-chain nonce on `(0, 7)` and `(7, 0)`);
- `results/per_event_sheets/baseline.parquet` and twelve per-event sheets (substrate-shift, EMA, drift columns);
- `MANIFEST.md` for root provenance.

No external data, no Iris API call, no production-database read.

## 4. Extended predictor space

### 4.1 Substrate-shift representations evaluated

Three representations are used in v2. Each is computed on each of the ten substrate axes and on the four drift composites listed in §4.2.

**Representation A — shift-magnitude delta (SMD).** Identical to v1 §4:

```
smd_axis(t) = |shift_axis(t)| − |shift_axis(t-1)|
alert_smd(t, axis, pctl, K) = (smd_axis(t) > smd_axis_pctl) sustained over K hours
```

`smd_axis_pctl` is the empirical quantile of the non-January `smd_axis` distribution at level `pctl`.

**Representation B — signed shift level, polarity-separated.** New in v2. The signed shift series `shift_axis(t)` carries a sign by construction. Stress in the upward direction (ratio above its 30-day EMA, `shift > 0`) and stress in the downward direction (`shift < 0`) are mechanically distinct events; the upward tail and the downward tail of the distribution are fit independently:

```
pos_axis_pctl = quantile(shift_axis where shift_axis > 0,  pctl)        on non-January
neg_axis_pctl = quantile(shift_axis where shift_axis < 0, 1 − pctl)     on non-January

alert_shift_pos(t, axis, pctl, K)
  = (shift_axis(t) > pos_axis_pctl) sustained over K hours
alert_shift_neg(t, axis, pctl, K)
  = (shift_axis(t) < neg_axis_pctl) sustained over K hours
```

A configuration in Representation B is identified by `(axis, polarity ∈ {pos, neg}, pctl, K, lead, outcome)`.

**Representation C — drift composite level, polarity-separated.** New in v2. The four drift composites `eth_drift_structural`, `eth_drift_demand`, `pol_drift_structural`, `pol_drift_demand` are tested on the same polarity-separated tail design:

```
alert_drift_pos(t, composite, pctl, K)
  = (drift_composite(t) > pos_composite_pctl) sustained over K hours
alert_drift_neg(t, composite, pctl, K)
  = (drift_composite(t) < neg_composite_pctl) sustained over K hours
```

`drift_structural(t) = (rhythm_ratio_shift(t) + continuity_ratio_shift(t)) / 2` per `compute_step3.py` §3, lines 148. `drift_demand(t) = (sigma_demand_shift(t) + size_demand_shift(t) + tx_demand_shift(t)) / 3` per `compute_step3.py` §3, lines 149-152.

### 4.2 Predictor inventory

```
10 substrate axes
   eth: rhythm_ratio_shift, continuity_ratio_shift,
        sigma_demand_shift, size_demand_shift, tx_demand_shift
   pol: rhythm_ratio_shift, continuity_ratio_shift,
        sigma_demand_shift, size_demand_shift, tx_demand_shift

4 drift composites
   eth: drift_structural, drift_demand
   pol: drift_structural, drift_demand
```

The fourteen series are loaded directly from `baseline.parquet` and the per-event sheets.

## 5. Configuration grid

Six families are evaluated in v2:

| Family | Description | Count |
|---|---|---|
| F0a | SMD of shift (Representation A) — 10 axes × 3 pctl × 2 K × 4 lead × 2 outcomes | 480 |
| F0b | Signed shift level (Representation B) — 10 axes × 2 polarities × 3 pctl × 2 K × 4 lead × 2 outcomes | 960 |
| F0c | Drift composite level (Representation C) — 4 composites × 2 polarities × 3 pctl × 2 K × 4 lead × 2 outcomes | 384 |
| F1 | Multi-axis grouped, voting over Representation A on the eight group definitions of v1, summing to 14 (group, threshold) pairs × 2 K × 4 lead × 2 outcomes at fixed pctl 0.90 | 224 |
| F4 | Cross-chain pair, Representation A on the two cross-chain groups of v1, 5 axes per group × 2 K × 4 lead × 1 outcome (fixed by cross-chain pair) | 80 |
| **Total** | — | **2 128** |

The F1 group definitions and the F4 cross-chain pair conventions are inherited from `compute_bs_structural_precursors_v1.py` and from the v1 spec §5 verbatim. The script `compute_bs_structural_precursors_v2.py` lists the group definitions as a constant dictionary, signed alongside the script via its SHA-256 in the output JSON.

The numerical total `2128` is the canonical count of v2; the actual enumeration in the script is the source of truth for the grid contents and is reported in the signed output JSON.

## 6. Calibration window

Identical to v1 §6 verbatim:

```
window_start = 2025-06-09 18:45 UTC
window_end   = 2025-12-31 23:59 UTC
```

Approximately 4 968 hours. Per-axis and per-composite tail thresholds (positive and negative for B and C) are fit on the non-January 2025 window:

```
pctl_fit_window_start = 2025-02-01 00:00 UTC
pctl_fit_window_end   = 2025-12-31 23:59 UTC
```

## 7. Statistical machinery

Identical to v1 §7 verbatim:

- True/false positive/negative computed against `BS2(t + lead)`.
- Lift = precision / base rate.
- Placebo p-value over 500 random label permutations.
- Benjamini-Hochberg FDR at α = 0.05 within each family (F0a, F0b, F0c, F1, F4) and combined across all 2 128 configurations.
- Survival criterion: `combined p < 0.05` AND `lift ≥ 1.5×`.

## 8. Sample-size guards

Identical to v1 §8 verbatim:

- `LOW_POWER` if positive outcomes < 30 over the window;
- `INSUFFICIENT_POWER` if < 10, excluded from the FDR family.

The v1 run reported `INSUFFICIENT_POWER` for every configuration because only six hours had a sample sufficient (`n_eligible ≥ 5`) to evaluate the outcome. This power constraint applies identically to v2 unless the underlying outcome density on the corpus changes, which it does not. The v2 protocol acknowledges in advance that the most probable outcome of the run is again an empty survivor set with the same power profile; v2 exists to exhaust the predictor space, not to relax the power criterion.

## 9. Output artefact

`scripts/compute_bs_structural_precursors_v2.py` produces:

```
results/BS_STRUCTURAL_PRECURSORS_ETH_POL_CCTP_V2_v2.json
```

The schema mirrors v1 §9, with two additions:

- `predictor_representations` lists `["A_smd_of_shift", "B_signed_shift_level", "C_drift_composite_level"]`;
- the per-survivor record carries a `representation` field in `{"A", "B", "C"}` for Family F0 entries, distinguishing them from F1 (always Representation A) and F4 (always Representation A).

The JSON is hashed, Ed25519-signed in three independent namespaces (`invarians_calibration_bs_structural_precursors_v2_output`), and OpenTimestamps-anchored on Bitcoin.

## 10. Stated limits

1. **Standard-mode outcome remains unevaluated.** The 1-hour window combined with `SLA_standard = 7200 s` produces a structurally zero eligible sample for Standard. v2 does not change the aggregation window. A `v3` may revisit Standard with a wider window.
2. **Same outcome rarity as v1.** The empirical positive rate of `BS_STRUCTURAL_v1.1 BS2` on the corpus is unchanged from v1. The post-`INSUFFICIENT_POWER` FDR family may be empty across all 2 128 configurations; this is anticipated. The result is published regardless.
3. **Three representations, not four.** Representation D — the raw ratio (`<axis>`) directly — is not in v2. The raw ratio differs from the signed shift only by a sign-preserving rescaling and contains no additional information beyond `<axis>_shift` plus `<axis>_ema`. Adding it as a separate family would inflate the FDR correction without information gain and is therefore excluded.
4. **Per-corridor scope.** The corpus covers only ETH-POL CCTP V2. Successor protocols target the other CCTP V2 corridors per their own locked corpora.
5. **Reorg-tracking invariant deferred.** As in v1, the fifth invariant (`messages_burned == messages_minted`) is out of scope; the outcome definition is BS_STRUCTURAL_v1.1 verbatim.

## 11. Verification protocol for external readers

```
ssh-keygen -Y verify -f <allowed_signers> -I invarians_bs_structural_precursors_v2_signer_<i> \
  -n invarians_calibration_bs_structural_precursors_v2 \
  -s signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md.sig.<i> \
  < PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md

ots verify signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md.sig.<i>.ots
```

Reproduction: re-running `compute_bs_structural_precursors_v2.py` against the locked Step 3 parquets must produce a JSON output whose `survivors[]`, `outcome_positive_rate_per_hour`, and `n_configurations_*` fields match the signed output byte-for-byte.

## 12. Signing

The present document is locked, SHA-256 hashed, and signed with three independent Ed25519 keys under namespace `invarians_calibration_bs_structural_precursors_v2`, then OpenTimestamps-anchored on Bitcoin. Signatures are stored at `signatures/PRE_ENGAGEMENT_BS_STRUCTURAL_PRECURSORS_v2.md.sig.{1,2,3}` with `.ots` proofs.

The Ed25519 signatures and the Bitcoin block anchor are the authoritative cryptographic record that the predictor space extension of §4, the configuration grid of §5, and all other choices are fixed prior to execution of `compute_bs_structural_precursors_v2.py` against the corpus.

---

*v2.0-draft — extended-feature-space evaluation of substrate-shift precursors against `BS_STRUCTURAL_v1.1 BS2` on the 2025 ETH-POL CCTP V2 corpus. Successor to v1, which evaluated SMD-of-shift only. Other CCTP V2 corridors require their own locked corpora and protocols.*
*Lock condition: three Ed25519 signatures + OpenTimestamps Bitcoin stamp, before any execution of `compute_bs_structural_precursors_v2.py`.*
