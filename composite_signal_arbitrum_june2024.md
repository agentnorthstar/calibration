# Invarians — Signal Composite : Arbitrum, 20 Juin 2024 (post-Dencun)

> **Résultat** : Invarians a détecté une dégradation multi-layer Arbitrum :
> L2 sous pression de 10:00 à 17:00 UTC (S1D2 — basefee L2 jusqu'à 16.49 gwei),
> suivie d'un gap de blob posting Bridge à 16:00 UTC (BS2 — 12.8min vs 1.03min normal).
>
> Fee monitors ETH (basefee L1) : **signal générique** (~10-25 gwei) — congestion ETH générale,
> **aucun signal discriminant Arbitrum**. Impossible de distinguer "L1 occupé" de "ARB bridge rompu".

---

## Contexte post-Dencun (EIP-4844, 13 Mars 2024)

Après Dencun, les rollups L2 postent leurs batchs sous forme de **blob transactions** sur L1.
La basefee ETH L1 est structurellement décorrélée de l'activité L2 (~3-8 gwei en régime normal).

**Ce que les fee monitors voient :** basefee L1 = proxy de congestion ETH globale.
Ils ne voient pas : l'état interne du séquenceur L2, ni le flux de blob posting.

**Ce qu'Invarians voit :**
- L2 : régime structurel ARB (basefee L2, tx volume, block size)
- Bridge : flux de blob posting vers L1 (last_blob_age vs baseline EMA)
- Composite : corrélation multi-layer en temps réel

---

## Timeline de l'incident (20 Juin 2024, UTC)

| Fenêtre (UTC) | L1 ETH | L2 ARB (basefee) | Bridge (last_age) | Basefee L1 | Invarians |
|---------------|--------|------------------|-------------------|------------|-----------|
| 2024-06-20 10:00:00 | S1D1 | S1D2 (0.0108 gwei) | BS1 (0.2min) | 6.91 gwei |  |
| 2024-06-20 11:00:00 | S1D1 | S1D2 (9.7685 gwei) | BS1 (0.6min) | 16.46 gwei |  |
| 2024-06-20 12:00:00 | S1D1 | S1D2 (16.4851 gwei) | BS1 (0.4min) | 21.28 gwei |  |
| 2024-06-20 13:00:00 | S1D1 | S1D2 (5.0647 gwei) | BS1 (0.0min) | 15.44 gwei |  |
| 2024-06-20 14:00:00 | S1D1 | S1D2 (2.3759 gwei) | BS1 (0.0min) | 13.67 gwei |  |
| 2024-06-20 15:00:00 | S1D2 | S1D2 (1.0049 gwei) | BS1 (0.0min) | 11.7 gwei |  |
| 2024-06-20 16:00:00 | S1D2 | S1D2 (0.6581 gwei) | BS2 (12.8min) | 25.68 gwei | ⚠️ **ALERTE** |
| 2024-06-20 17:00:00 | S1D2 | S1D2 (0.01 gwei) | BS1 (1.8min) | 14.82 gwei |  |
| 2024-06-20 18:00:00 | S1D1 | S1D1 (0.0144 gwei) | BS1 (1.4min) | 7.79 gwei |  |
| 2024-06-20 19:00:00 | S1D1 | S1D1 (0.0102 gwei) | BS1 (1.2min) | 6.53 gwei |  |
| 2024-06-20 20:00:00 | S1D1 | S1D1 (0.0101 gwei) | BS1 (0.4min) | 5.9 gwei |  |

---

## Lecture de la timeline

**Phase 1 — Stress L2 (10:00–15:00 UTC)**
La basefee ARB L2 monte de 0.01 gwei à **16.49 gwei** (×1649 la normale).
Invarians L2 détecte le régime S1D2 — demande élevée sur le rollup.
Fee monitors L1 : également en hausse (15-21 gwei) mais signal GÉNÉRIQUE (ETH busy, pas ARB).
**Un agent ne peut pas distinguer "ETH occupé" de "Arbitrum surchargé" avec les seuls fee monitors.**

**Phase 2 — Rupture Bridge (16:00 UTC)**
Le blob posting vers L1 s'arrête : last_blob_age = **12.8min** vs EMA = **1.03min** (×12 la normale).
Invarians Bridge passe BS2. Signal composite : **L2:S1D2 + Bridge:BS2 = MULTI_LAYER**.
Fee monitors L1 : **25.68 gwei** — signal générique L1, aucune alerte Arbitrum spécifique.

**Phase 3 — Retour à la normale (17:00–18:00 UTC)**
Bridge reprend (BS1), L2 basefee retombe à 0.01 gwei, L1 se calme.
Invarians repasse S1D1/BS1 à 18:00 UTC.

---

## Ce qu'un agent cross-chain aurait vécu

**Sans Invarians (fee monitors only) :**
```
10:00 UTC — L1 basefee : 16 gwei → décision : "L1 cher, attendre"
15:00 UTC — L1 basefee : 12 gwei → décision : "L1 revient, exécuter"
16:00 UTC — transaction cross-chain envoyée vers Arbitrum
          → bridge en gap BS2, finalisation absente
          → transaction stuck pendant ~37min sans visibilité
17:24 UTC — finalisation tardive, slippage imprevisible
```

**Avec Invarians :**
```
10:00 UTC — L2 ARB : S1D2 détecté (basefee 0.01 → 9.77 gwei) → execution_window = WAIT
16:00 UTC — Bridge BS2 détecté (last_age 12.8min) → REROUTE_L2 ou AVOID
          → 0 transaction envoyée pendant la fenêtre critique
17:00 UTC — Bridge BS1 confirmé → reprise normale
```

---

## Comparaison des signaux disponibles

| Signal | Valeur pendant l'incident | Discriminant ARB ? |
|--------|--------------------------|-------------------|
| Basefee ETH L1 | 10–25 gwei | ❌ Non — signal générique ETH |
| Gas trackers (Etherscan, Blocknative) | Alerte L1 générale | ❌ Non — pas ARB-spécifique |
| Mempool ETH | Occupé | ❌ Non |
| **Invarians L2 ARB** | **S1D2 depuis 10:00 UTC** | **✅ Oui — ARB spécifiquement** |
| **Invarians Bridge** | **BS2 à 16:00 UTC (×12 normal)** | **✅ Oui — blob posting stoppé** |

---

## Statut épistémique

- **Type** : preuve rétrospective sur données publiques
- **Source L1 + Bridge** : BigQuery `bigquery-public-data.crypto_ethereum` (blocks + transactions blob)
- **Source L2** : BigQuery `bigquery-public-data.goog_blockchain_arbitrum_one_us.blocks` (agrégé/heure)
- **Reproductible** : oui — script `h5_composite_demo.py`
- **Limite** : reconstruction post-hoc ; cause exacte de l'incident non corrélée à une status page publique

*Généré le 2026-04-03 — Invarians Phase B*
