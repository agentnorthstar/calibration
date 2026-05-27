# Report, ETH-POL CCTP V2 Corpus, Step 3

**Status.** Pre-lock draft.

**Contract reference.** `METHODOLOGY.md` §3 Step 3 and `METHODOLOGY_STEP3_CONVENTIONS.md`.

## 1. Corpus scope recap

Events in inventory: 12.
Per-event sheets produced: 12.
Baseline hours: 7272 out of 8760 corpus hours.

## 2. Per-event narrative

### CCTP_V2_MAINNET_LAUNCH_2025_03_11

Hot window: 2025-03-11 00:00:00+00:00 to 2025-03-11 23:59:59+00:00 UTC.
Extended window hours: 36. Hot window hours: 24.
Chain scope: CCTP_V2_corridor. Type: protocol_mainnet_launch.

- ETH non-S1D1 firing rate during hot window: 4/24 hours (16.7%).
  Top regime codes: S1D1=20, S1D2+=4
- POL non-S1D1 firing rate during hot window: 1/24 hours (4.2%).
  Top regime codes: S1D1=23, S1D2±=1
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=0 Standard=0, pol_to_eth Fast=0 Standard=0.

### ETH_PECTRA_MAINNET_2025_05_07

Hot window: 2025-05-07 10:05:11+00:00 to 2025-05-07 18:00:00+00:00 UTC.
Extended window hours: 20. Hot window hours: 8.
Chain scope: ETH. Type: hard_fork_activation.

- ETH non-S1D1 firing rate during hot window: 4/8 hours (50.0%).
  Top regime codes: S1D1=4, S1D2±=3, S1D2+=1
- POL non-S1D1 firing rate during hot window: 2/8 hours (25.0%).
  Top regime codes: S1D1=6, S1D2±=2
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=0 Standard=0, pol_to_eth Fast=0 Standard=0.

### CCTP_V2_POLYGON_DEPLOYMENT_2025_06

Hot window: 2025-06-01 00:00:00+00:00 to 2025-06-30 23:59:59+00:00 UTC.
Extended window hours: 732. Hot window hours: 720.
Chain scope: CCTP_V2_corridor. Type: protocol_mainnet_deployment.

- ETH non-S1D1 firing rate during hot window: 230/720 hours (31.9%).
  Top regime codes: S1D1=490, S1D2±=209, S1D2+=13
- POL non-S1D1 firing rate during hot window: 213/720 hours (29.6%).
  Top regime codes: S1D1=507, S1D2+=105, S1D2±=92
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=9 Standard=1, pol_to_eth Fast=4 Standard=8.

### POL_HEIMDALL_CONSENSUS_2025_07_30

Hot window: 2025-07-30 09:30:00+00:00 to 2025-07-30 11:01:00+00:00 UTC.
Extended window hours: 14. Hot window hours: 2.
Chain scope: POL. Type: consensus_bug_finality_lag.

- ETH non-S1D1 firing rate during hot window: 2/2 hours (100.0%).
  Top regime codes: S1D2±=2
- POL non-S1D1 firing rate during hot window: 1/2 hours (50.0%).
  Top regime codes: S1D1=1, S1D2±=1
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=0 Standard=0, pol_to_eth Fast=0 Standard=0.

### ETH_KILN_MASS_VALIDATOR_EXIT_2025_09_09

Hot window: 2025-09-09 00:00:00+00:00 to 2025-09-26 23:59:59+00:00 UTC.
Extended window hours: 444. Hot window hours: 432.
Chain scope: ETH. Type: mass_validator_exit.

- ETH non-S1D1 firing rate during hot window: 130/432 hours (30.1%).
  Top regime codes: S1D1=302, S1D2±=121, S1D2+=7
- POL non-S1D1 firing rate during hot window: 169/432 hours (39.1%).
  Top regime codes: S1D1=263, S1D2±=127, S1D2-=38
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=171 Standard=19, pol_to_eth Fast=126 Standard=120.

### ETH_SSV_MASS_SLASHING_2025_09_10

Hot window: 2025-09-10 00:00:00+00:00 to 2025-09-10 23:59:59+00:00 UTC.
Extended window hours: 36. Hot window hours: 24.
Chain scope: ETH. Type: validator_mass_slashing_dvt.

- ETH non-S1D1 firing rate during hot window: 7/24 hours (29.2%).
  Top regime codes: S1D1=17, S1D2±=7
- POL non-S1D1 firing rate during hot window: 15/24 hours (62.5%).
  Top regime codes: S1D2±=14, S1D1=9, S1D2-=1
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=3 Standard=0, pol_to_eth Fast=2 Standard=1.

### POL_HEIMDALL_MILESTONE_2025_09_10

Hot window: 2025-09-10 04:30:00+00:00 to 2025-09-10 16:30:00+00:00 UTC.
Extended window hours: 24. Hot window hours: 12.
Chain scope: POL. Type: consensus_milestone_bug_finality_lag.

- ETH non-S1D1 firing rate during hot window: 5/12 hours (41.7%).
  Top regime codes: S1D1=7, S1D2±=5
- POL non-S1D1 firing rate during hot window: 7/12 hours (58.3%).
  Top regime codes: S1D2±=6, S1D1=5, S1D2-=1
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=1 Standard=0, pol_to_eth Fast=0 Standard=1.

### POL_HEIMDALL_V2_HARD_FORK_2025_09_16

Hot window: 2025-09-16 14:00:00+00:00 to 2025-09-16 14:30:00+00:00 UTC.
Extended window hours: 13. Hot window hours: 1.
Chain scope: POL. Type: hard_fork_consensus_upgrade.

- ETH non-S1D1 firing rate during hot window: 1/1 hours (100.0%).
  Top regime codes: S1D2±=1
- POL non-S1D1 firing rate during hot window: 1/1 hours (100.0%).
  Top regime codes: S1D2±=1
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=0 Standard=0, pol_to_eth Fast=0 Standard=0.

### USDE_DEPEG_CASCADE_2025_10_10

Hot window: 2025-10-10 20:30:00+00:00 to 2025-10-11 06:00:00+00:00 UTC.
Extended window hours: 22. Hot window hours: 10.
Chain scope: ETH+POL+CCTP_V2_corridor. Type: depeg_cascade_settlement_stress.

- ETH non-S1D1 firing rate during hot window: 5/10 hours (50.0%).
  Top regime codes: S1D1=5, S1D2±=4, S1D2+=1
- POL non-S1D1 firing rate during hot window: 7/10 hours (70.0%).
  Top regime codes: S1D2±=4, S1D2+=3, S1D1=3
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=3 Standard=6, pol_to_eth Fast=4 Standard=9.

### ETH_FUSAKA_MAINNET_2025_12_03

Hot window: 2025-12-03 21:49:11+00:00 to 2025-12-04 05:00:00+00:00 UTC.
Extended window hours: 20. Hot window hours: 8.
Chain scope: ETH. Type: hard_fork_activation_peerdas.

- ETH non-S1D1 firing rate during hot window: 5/8 hours (62.5%).
  Top regime codes: S1D2+=3, S1D1=3, S1D2±=2
- POL non-S1D1 firing rate during hot window: 5/8 hours (62.5%).
  Top regime codes: S1D1=3, S1D2+=3, S1D2±=2
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=52 Standard=11, pol_to_eth Fast=3 Standard=1.

### ETH_BPO1_MAINNET_2025_12_09

Hot window: 2025-12-09 14:21:11+00:00 to 2025-12-09 22:00:00+00:00 UTC.
Extended window hours: 20. Hot window hours: 8.
Chain scope: ETH. Type: hard_fork_blob_parameters.

- ETH non-S1D1 firing rate during hot window: 3/8 hours (37.5%).
  Top regime codes: S1D1=5, S1D2+=2, S1D2±=1
- POL non-S1D1 firing rate during hot window: 5/8 hours (62.5%).
  Top regime codes: S1D2+=5, S1D1=3
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=12 Standard=7, pol_to_eth Fast=1 Standard=2.

### POL_BOR_RPC_2025_12

Hot window: 2025-12-12 00:00:00+00:00 to 2025-12-18 23:59:59+00:00 UTC.
Extended window hours: 180. Hot window hours: 168.
Chain scope: POL. Type: rpc_degradation_no_consensus_impact.

- ETH non-S1D1 firing rate during hot window: 110/168 hours (65.5%).
  Top regime codes: S1D2±=81, S1D1=58, S1D2+=25
- POL non-S1D1 firing rate during hot window: 94/168 hours (56.0%).
  Top regime codes: S1D1=74, S1D2±=53, S1D2+=34
- CCTP V2 corridor activity during hot window: eth_to_pol Fast=118 Standard=128, pol_to_eth Fast=59 Standard=37.

## 3. Baseline aggregate distribution

```
                       count      mean       std       min       25%       50%       75%       max
eth_rhythm_ratio      7272.0  1.000000  0.000000  1.000000  1.000000  1.000000  1.000000  1.000000
eth_continuity_ratio  7272.0  0.993403  0.005452  0.953333  0.990000  0.993333  0.996667  1.000000
eth_sigma_demand      7272.0  1.036883  0.156255  0.663663  0.917048  1.016643  1.141184  1.583993
eth_size_demand       7272.0  1.042533  0.148719  0.509877  0.946904  1.052091  1.136337  3.118972
eth_tx_demand         7272.0  1.041499  0.148608  0.511420  0.946140  1.049873  1.134939  3.123919
pol_rhythm_ratio      7272.0  1.001994  0.054024  1.000000  1.000000  1.000000  1.000000  3.000000
pol_continuity_ratio  7272.0  0.945575  0.042664  0.318333  0.932778  0.941111  0.941667  1.000000
pol_sigma_demand      7272.0  0.959490  0.150870  0.575812  0.857129  0.946404  1.045349  3.585734
pol_size_demand       7272.0  1.073309  0.192260  0.572991  0.944946  1.072352  1.193027  3.191164
pol_tx_demand         7272.0  1.090920  0.196569  0.502429  0.957213  1.091497  1.217863  3.201219
```

## 4. Limitations applicable to Step 3

- EMA warmup: January 2025 hours carry `ema_warmup=True`. Interpret with care.
- POL substrate observation: `rho_ts` reported empirically.
- Month-only event precision: `POL_HEIMDALL_CONSENSUS_2025_07` and `POL_BOR_RPC_2025_12` span entire months plus padding.
- POL dataset selection: per MANIFEST.md §Step 2.
- Convention transparency: formulas in METHODOLOGY_STEP3_CONVENTIONS.md.

## 5. Outputs

- 12 per-event parquet files in `results/per_event_sheets/`.
- `results/per_event_sheets/baseline.parquet` (7272 rows).

End of report.