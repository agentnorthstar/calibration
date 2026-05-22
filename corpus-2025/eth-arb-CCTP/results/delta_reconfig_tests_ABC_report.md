# Delta Reconfiguration Tests A, B, C

Three pre-engaged reconfigurations of the canonical Delta operational definition. 
Same outcome (bridge stress in next 6h), same eligible hours, same placebo. 
No post-hoc tuning.

## Comparison summary

| Config | Lift | Placebo p | Precision | Recall | Alert rate | Events w/ precursor |
|---|---|---|---|---|---|---|
| A_normalized | **0.992x** | 0.633 | 39.7% | 26.7% | 26.88% | 4/5 |
| B_sequencer_only | **1.485x** | 0.012 | 59.5% | 0.8% | 0.54% | 1/5 |
| C_trend_12h | **0.75x** | 1.0 | 30.0% | 2.1% | 2.82% | 0/5 |
| INITIAL_canonical | **1.055x** | 0.19 | 42.2% | 5.7% | 5.37% | 1/5 |

## Per-configuration verdict

### A_normalized

**Placebo non-significant (p=0.633).** Observed lift compatible with random.

**FAIL**: signal does not meaningfully exceed null distribution.

- Precision: 39.7%
- Recall: 26.7%
- Alert rate: 26.88%
- Lift: 0.992x (vs base rate 40.0%)
- Events with precursor: 4/5
  - S03: YES
  - L02: YES
  - D01: YES
  - S04: NO
  - S05: YES

### B_sequencer_only

**Placebo significant (p=0.012).** Lift unlikely under random labels.

**FAIL**: signal does not meaningfully exceed null distribution.

- Precision: 59.5%
- Recall: 0.8%
- Alert rate: 0.54%
- Lift: 1.485x (vs base rate 40.0%)
- Events with precursor: 1/5
  - S03: NO
  - L02: NO
  - D01: YES
  - S04: NO
  - S05: NO

### C_trend_12h

**Placebo non-significant (p=1.0).** Observed lift compatible with random.

**FAIL**: signal does not meaningfully exceed null distribution.

- Precision: 30.0%
- Recall: 2.1%
- Alert rate: 2.82%
- Lift: 0.75x (vs base rate 40.0%)
- Events with precursor: 0/5
  - S03: NO
  - L02: NO
  - D01: NO
  - S04: NO
  - S05: NO

### INITIAL_canonical

**Placebo non-significant (p=0.19).** Observed lift compatible with random.

**FAIL**: signal does not meaningfully exceed null distribution.

- Precision: 42.2%
- Recall: 5.7%
- Alert rate: 5.37%
- Lift: 1.055x (vs base rate 40.0%)
- Events with precursor: 1/5
  - S03: NO
  - L02: NO
  - D01: YES
  - S04: NO
  - S05: NO

## Reading

Best lift overall: **B_sequencer_only** with lift 1.485x, placebo p=0.012.

None of the three reconfigurations produce a lift sufficient for agent orientation use. The Delta concept may require a different reformulation (other outcome, longer lead window, or cross-channel integration). Honest reading: the v2 substrate Delta primitive does not orient agent decisions on bridge stress in 2025 ETH-ARB-CCTP under any of the four tested operational definitions.
