# Invarians — Journal de Calibration

**Format :** entrées chronologiques, immuables.
Chaque reset EMA, incident, ou changement de paramètre est documenté ici avec sa justification.

---

## Entrée #001 — 14 Mars 2026 — Démarrage production L2

**Type :** Initialisation
**Chaînes :** arbitrum, base, optimism
**Action :** Premiers invariants L2 produits. Baselines EMA initialisées à partir du premier invariant.
**Paramètres initiaux :**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30j)
- Seuil S2 : rhythm_ratio > 1.15
- Seuil D2 : sigma_ratio > 1.20
**Statut baselines :** non calibrées — valeurs initiales arbitraires
**Confiance :** LOW

---

## Entrée #002 — 15 Mars 2026 — Incident Arbitrum : race condition

**Type :** Incident → Fix déploiement
**Chaîne :** arbitrum
**Symptôme :** buffer figé à 2/14400, aucun invariant produit après seq=10.
**Root cause :** throttle 30s avec beta=120 → advance rate 4 blocs/s > taux chaîne 3.8 blocs/s.
**Fix :** throttle 30s → 38s. Advance rate 3.16 blocs/s < 3.8 blocs/s.
**Impact EMA :** baselines partiellement contaminées par les quelques invariants produits avant l'incident.
**Action corrective :** aucun reset nécessaire (peu de données contaminées, séquence courte).
**Confiance post-fix :** LOW → à réévaluer après 30j

---

## Entrée #003 — 16 Mars 2026 — Incident BASE/OPTIMISM : miroir rho_ts/c_s

**Type :** Incident structurel → Fix déploiement
**Chaînes :** base, optimism
**Symptôme :** rhythm_ratio=4.62, continuity_ratio=0.21 → classifiés S2 en permanence. Evolution en miroir strict des deux signaux.
**Root cause :**
1. Race condition : throttle 100s avec beta=50 → advance rate 0.5 blocs/s = taux exact de la chaîne.
2. Insight physique : pour chaînes à block time fixe 2s, `rho_ts × c_s/100 ≈ 2s = constante` → signaux mathématiquement inverses.
**Fix :** throttle 100s → 110s. Advance rate 0.4545 blocs/s < 0.5 blocs/s.
**Impact EMA :** 2 semaines de baselines contaminées (c_s≈58%, rho_ts≈5s au lieu de c_s≈100%, rho_ts≈2s).
**Action corrective requise :** DELETE FROM ans_l2_rollup_signals WHERE chain IN ('base','optimism') après premier invariant propre.
**Critère validation :** c_s > 90% ET rho_ts < 2.5s sur la ligne la plus récente.
**Statut :** ⏳ En attente validation premier invariant propre.
**Note design :** c_s est un signal redondant pour Base et Optimism. À terme, n'utiliser que rho_ts ou rho_s pour ces chaînes.

---

## Entrée #004 — 16 Mars 2026 — Reset EMA BASE/OPTIMISM

**Type :** Reset EMA
**Chaînes :** base, optimism
**Trigger :** Premier invariant post-fix — critère validé :
- base : seq=20, c_s=100, rho_ts=1.9989s ✅
- optimism : seq=21, c_s=100, rho_ts=1.9989s ✅
**Action :** `DELETE FROM ans_l2_rollup_signals WHERE chain IN ('base','optimism')`
**Effet :** Baselines réinitialisées sur données propres. Convergence EMA rapide en ~5 invariants (~5h).
**Résultat attendu :** Divergence ANOMALIE/ELEVATED → NOMINAL sous ~5h.
**Statut :** ✅ Exécuté — 16 Mars 2026

---

---

## Entrée #005 — 16 Mars 2026 — Calibration ETH τ (threshold_s2)

**Type :** Calibration paramètre
**Chaîne :** ethereum (L1)
**Méthode :** Backtest event-detection sur BigQuery `bigquery-public-data.crypto_ethereum.blocks`, fenêtre 2020-01-01 → 2024-01-01, 34 697 invariants, Φ=280 blocs (~1h).
**Ancienne valeur :** `rhythm_p90 = 1.0073` (percentile P90 empirique — arbitraire)
**Nouvelle valeur :** `rhythm_p90 = 1.12` (event-detection validé)
**Justification :**
- FPR = 2.50% à threshold_s2=1.12 (vs 10.56% à 1.05)
- Détecte The Merge (15 sept 2022, latence +18.3h) ✅ et Shanghai Upgrade (12 avril 2023) ✅
- Non-détection DeFi Summer / NFT Mania : **correct** — stress τ absent, infrastructure nominale
- Plancher FPR à 2.12% au-delà de 1.18 : causé par D2 noise, pas par τ
**Signal :** rho_ts / EMA(rho_ts), alpha=2/11 (~10h)
**TPR :** 100% sur événements structurels connus (n=2)
**FPR τ seul :** 2.50%
**Confiance :** MEDIUM
**Déployé :** Supabase project `sdpilypwumxsyyipceew`, 16 Mars 2026
**Script :** BIGDATA/sweep_eth.py

---

## Entrée #006 — 16 Mars 2026 — Calibration ETH π (D2 thresholds)

**Type :** Calibration paramètre
**Chaîne :** ethereum (L1)
**Méthode :** Sweep sigma seul (sweep_eth_d2.py) puis sweep D2 complet size × tx (sweep_eth_d2_full.py). Logique production : D2 si 2 dims sur 3 (sigma, size, tx) au-dessus de leur seuil.
**Anciennes valeurs :** `sigma_demand=1.0154`, `size_demand=1.2002`, `tx_demand=1.1430` (percentiles P95 empiriques)
**Nouvelles valeurs :**
- `sigma_demand = 1.10` (sweep sigma seul, FPR π = 0.99%)
- `size_demand = 1.20` (sweep D2 full, FPR combiné τ+π = 1.23%)
- `tx_demand = 1.10` (sweep D2 full, gagne DeFi Summer S1D2 + NFT Mania S1D2)
**Justification :**
- FPR combiné (τ+π) = 1.23% — objectif < 1.5% atteint
- TPR 4/4 événements : The Merge ✅, Shanghai ✅, DeFi Summer ✅ (S1D2), NFT Mania ✅ (S1D2)
- DeFi Summer / NFT Mania détectables via size+tx multi-signal même si sigma stable (EIP-1559 stabilise rho_s) : **S1D2 = infrastructure saine, demande élevée** — comportement correct
- c_s exclu (100% constant sur ETH, aucune variance exploitable)
**Insight :** EIP-1559 stabilise sigma_ratio → sigma seul insuffisant pour détecter surcharges économiques. La combinaison size+tx capture la demande réelle.
**Logique D2 :** 2 of 3 dims ≥ seuil respectif
**TPR :** 100% (4/4 événements ground truth)
**FPR combiné :** 1.23%
**Confiance :** MEDIUM
**Déployé :** Supabase project `sdpilypwumxsyyipceew`, 16 Mars 2026
**Script :** BIGDATA/sweep_eth_d2.py + BIGDATA/sweep_eth_d2_full.py

---

---

## Entrée #007 — 16 Mars 2026 — Calibration Solana τ (rhythm_p90 + continuity_p10)

**Type :** Calibration paramètre
**Chaîne :** solana (L1)
**Méthode :** Backtest event-detection sur BigQuery `bigquery-public-data.crypto_solana_mainnet_us.Blocks`, fenêtre 2021-01-01 → 2024-01-01, 128 365 fenêtres, Φ=800 slots (~5.3 min).
**Schéma BigQuery disponible :** slot, block_hash, block_timestamp, height — pas de transaction_count.

**rhythm_p90 :**
- Ancienne valeur : `1.0340` (P90 empirique — 90j production)
- Nouvelle valeur : `1.12` (event-detection validé)
- Sweep 1.01→1.20 : 1.12 = dernier seuil détectant les 4 outages. Au-delà : Outage Mai 2022 perdu à 1.15.
- TPR τ : 100% (4/4 outages structurels)
- FPR τ : 1.77% — légèrement > 1.5% cible, inhérent à la volatilité Solana
- Latences : Outage Sept 2021 +6.7h, Jan 2022 +1.4h, Mai 2022 +15.9h, Oct 2022 +12.5h

**continuity_p10 :**
- Ancienne valeur : `0.9530` (P10 production — catastrophiquement trop haut)
- Nouvelle valeur : `null` (désactivé)
- Justification : c_s suit une distribution très large sur Solana (p10=0.775, p50=0.911, p90=0.972). Le skip rate est inhérent au protocole — même en conditions normales, c_s descend régulièrement à 77%. La valeur 0.9530 dépassait le p50 naturel → 75% FPR. Signal non discriminant comme trigger d'alarme.
- Note : rhythm_ratio=1.12 couvre déjà les cas d'outage complet (c_s très bas → rho_ts spike → rhythm_ratio >> 1.12).

**π (demande) :** ⚠️ DETTE TECHNIQUE — non calibré.
- BigQuery `crypto_solana_mainnet_us.Blocks` ne contient pas `transaction_count`.
- sigma/size/tx restent aux valeurs P90 initiales (confidence: LOW).
- Source prévue : données internes `ans_invariants_v3`, capteur `size_avg` fixé le 14 Mars 2026.
- **Cible : juillet 2026** (après 90 jours de production propre, ~mi-juin 2026 → traitement juillet).
- Blocker : à traiter avant toute approche commerciale sur Solana.

**Confiance τ :** MEDIUM
**Déployé :** Supabase project `sdpilypwumxsyyipceew`, 16 Mars 2026
**Scripts :** BIGDATA/backtest_sol.py + BIGDATA/sweep_sol.py

---

---

## Entrée #008 — 17 Mars 2026 — Calibration Polygon τ (rhythm_p90)

**Type :** Calibration paramètre
**Chaîne :** polygon (L1)
**Méthode :** Backtest event-detection sur BigQuery `bigquery-public-data.crypto_polygon.blocks`,
  fenêtre 2020-10-01 → 2023-12-31, 25 906 invariants, Φ=1800 blocs (~1h).
  Données early Polygon (juin-sept 2020, gas/tx=0) exclues — démarrage propre à partir de 2020-10-01.
**Ancienne valeur :** `rhythm_p90 = 1.04034` (P90 empirique — arbitraire)
**Nouvelle valeur :** `rhythm_p90 = 1.12` (event-detection validé)
**Justification :**
- FPR τ pur = 0.78% à threshold_s2=1.12
- Détecte Reorg Storm Fév 2023 (rho_ts peak=1.2509, latence +20.1h) ✅
- Network Halt Mars 2021 non capturé via τ (rho_ts max ~1.08 — signal faible), mais capturé via π ✅
- Heimdall/Bor Jan 2023 : pas de signal τ ni π mesurable (incident consensus/finality, hors scope instrument)
- c_s p10=1.000 → continuity_p10 = null confirmé
**Signal :** rho_ts / EMA(rho_ts), alpha=2/11 (~10h)
**Événement canonique τ :** Reorg Storm Fév 2023 — 157 blocs reorg, rho_ts disruption claire
**TPR τ :** 1/1 événements τ détectables
**FPR τ :** 0.78%
**Confiance :** MEDIUM
**Déployé :** Supabase project `sdpilypwumxsyyipceew`, 17 Mars 2026
**Script :** BIGDATA/sweep_pol.py

---

## Entrée #009 — 17 Mars 2026 — Calibration Polygon π (D2 thresholds)

**Type :** Calibration paramètre
**Chaîne :** polygon (L1)
**Méthode :** Sweep D2 complet sigma × size × tx (grille 7×7×7 + candidats équilibrés ciblés).
  Logique production : D2 si 2 dims sur 3 (sigma, size, tx) au-dessus de leur seuil.
**Anciennes valeurs :** `sigma_demand=1.13594`, `size_demand=1.17667`, `tx_demand=1.23474` (P95 empiriques)
**Nouvelles valeurs :**
- `sigma_demand = 1.50` (p99 σ=1.394 → ratio +7.6%)
- `size_demand  = 1.40` (p99 sz=1.318 → ratio +6.2%)
- `tx_demand    = 1.60` (p99 tx=1.457 → ratio +9.8%)
**Justification :**
- FPR combiné (τ+π) = 1.20% — objectif < 1.5% atteint
- TPR 3/3 événements :
  - Network Halt Mars 2021 ✅ (S1D2 via π, σ=1.764 post-halt backlog, latence +17.0h)
  - Gas Crisis Mai 2021 ✅ (S1D2, σ=1.896/sz=1.945/tx=1.889, latence +3.5h depuis onset)
  - Reorg Storm Fév 2023 ✅ (S2D1 via τ déjà, latence +20.1h)
- Seuils calibrés proportionnellement au p99 de chaque dimension (équilibrés)
- Heimdall/Bor Jan 2023 : retiré du ground truth — incident consensus/finality sans signal on-chain mesurable
**Insight :** Gas Crisis Polygon (mai 2021) = surcharge massive multi-dim (σ×2, size×2, tx×2).
  Network Halt = demande post-reprise (gas backlog accumulé). Deux signatures distinctes, toutes deux capturées.
**Logique D2 :** 2 of 3 dims ≥ seuil respectif
**TPR :** 100% (3/3 événements)
**FPR combiné :** 1.20%
**Confiance :** MEDIUM
**Déployé :** Supabase project `sdpilypwumxsyyipceew`, 17 Mars 2026
**Script :** BIGDATA/sweep_pol_d2.py

---

---

## Entrée #010 — 17 Mars 2026 — Dette technique Avalanche : absence dataset BigQuery

**Type :** Dette technique — Blocage données
**Chaîne :** avalanche (L1)
**Action :** Tentative de calibration τ+π par backtest BigQuery — bloquée.
**Diagnostic :**
- `bigquery-public-data.crypto_avalanche` : Access Denied / inexistant
- `bigquery-public-data.goog_blockchain_avalanche_c_chain_us` : Access Denied / inexistant
- Aucun dataset BigQuery public disponible pour Avalanche C-Chain à ce jour.
**Statut actuel :** Seuils P90 empiriques en production (non calibrés par event-detection)
- `rhythm_p90 = 1.0282` (P90 — LOW)
- `sigma_demand = 1.2322`, `size_demand = 1.2143`, `tx_demand = 1.2399` (P90 — LOW)
- `m1_validated = false` (rho_s médian ~7% — chaîne sous-saturée)
**Action corrective :** Backtest sur données production `ans_invariants_v3`
- Capteur actif depuis 14 Mars 2026, Φ=720 blocs (~24 inv/jour)
- 90 jours requis pour EMA stabilisée + événements détectables
- **Cible : juillet 2026** (après mi-juin 2026 → traitement juillet)
**Scripts prêts :** BIGDATA/extract_avax.sql + backtest_avax.py + sweep_avax.py + sweep_avax_d2.py
**Blocker :** À traiter avant toute approche commerciale sur Avalanche.
**Confiance :** LOW

---

## Entrée #011 — 17 Mars 2026 — Déploiement complexity_ratio L2 (Phase A)

**Type :** Nouveau signal — déploiement production
**Chaînes :** arbitrum, base, optimism
**Signal :** `complexity_ratio = (size_avg / tx_count_avg) / EMA(size_avg / tx_count_avg)`
**Physique :** bytes par transaction — mesure la complexité moyenne des données par tx, indépendante du volume.
**Motivation :** τ (rhythm_ratio) inutilisable sur L2 par design (sequencer régulier). σ Arbitrum mort (gas model incompatible). complexity_ratio = premier signal structurel L2 dérivable sans L1 monitoring.

**Baselines initiales (17 Mars 2026, première mesure) :**
- arbitrum : complexity_baseline = 589.7 bytes/tx
- base : complexity_baseline = 564.5 bytes/tx
- optimism : complexity_baseline = 302.9 bytes/tx

**Paramètres EMA :**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30j)
- Clamp ratio : [0.01, 20.0]

**Domaine signature :** `v2-l2` (nouveau domaine — incompatible avec `v1-l2` ancien)
**Reset DB :** `DELETE FROM ans_l2_chain_signals` exécuté avant déploiement
**Statut baselines :** non calibrées — valeurs initiales, 1 seul invariant
**Confiance :** LOW — calibration event-detection à faire via Dune (Phase D, Q2-Q3 2026)

**Action corrective requise :** aucune — signal opérationnel, baselines convergeront en ~10 invariants (~10h)
**Blocker calibration :** données Dune historiques ARB/BASE/OP pour identifier événements de référence

---

## Entrée #012 — 17 Mars 2026 — Déploiement gas_complexity_ratio L2 (Phase B)

**Type :** Nouveau signal — déploiement production
**Chaînes :** arbitrum, base, optimism, zksync, polygon-zkevm
**Signal :** `gas_complexity_ratio = (gas_used_avg / tx_count_avg) / EMA(gas_used_avg / tx_count_avg)`
**Physique :** gas par transaction — mesure la complexité computationnelle moyenne par tx. Contrairement à `complexity_ratio` (bytes/tx = données), `gas_complexity_ratio` capture la charge de calcul réelle imposée au sequencer.

**Architecture Phase B :**
- `ans-core` gelé (chaîne cryptographique L1 préservée)
- `gas_used_avg` calculé dans `invarians-l2-collector` : `mean(load)` sur Φ blocs du buffer, stocké comme colonne nullable dans `ans_invariants_v3`
- `load` = `gas_used` brut tel que fourni par le capteur RPC via `L0Signal.load`
- NULL safety : si `gas_used_avg IS NULL` ou `tx_count_avg = 0`, ratio = 1.0 (neutre), baseline préservée

**Migration SQL :**
```sql
ALTER TABLE ans_invariants_v3
    ADD COLUMN IF NOT EXISTS gas_used_avg DOUBLE PRECISION;
ALTER TABLE ans_l2_chain_signals
    ADD COLUMN IF NOT EXISTS gas_complexity_ratio          DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_baseline       DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_baseline_slow  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS gas_complexity_ratio_slow     DOUBLE PRECISION;
```

**Domaine signature :** `v3-l2` (rompt avec `v2-l2` Phase A — reset DB requis)
**Reset DB :** `DELETE FROM ans_l2_chain_signals` exécuté avant redémarrage services

**Paramètres EMA :**
- EMA_ALPHA = 2/11 ≈ 0.1818 (~10h)
- EMA_ALPHA_SLOW = 2/721 ≈ 0.00277 (~30j)
- Clamp ratio : [0.01, 20.0]

**Baselines initiales :** à observer sur premier cycle post-déploiement (17 Mars 2026 soir)
**Statut baselines :** non calibrées — valeurs initiales, cold start EMA
**Confiance :** LOW — calibration event-detection à faire via Dune (Phase D, Q2-Q3 2026)

**Note Arbitrum :** `gas_used_avg` attendu très élevé (modèle Nitro, gas limit ≈ 2^50). `rho_s` ≈ 0 confirme incompatibilité du ratio gasUsed/gasLimit. `gas_complexity_ratio` mesure la complexité absolue (gas/tx), pas relative au limit — signal physiquement pertinent pour Arbitrum contrairement à sigma_ratio.

---

---

## Entrée #013 — 17 Mars 2026 — Déploiement invarians-l2-adapter (Phase C)

**Type :** Nouveau service — déploiement production
**Chaînes :** base, optimism, arbitrum
**Signaux :** `publish_latency_seconds`, `calldata_bytes`, `blob_count`, `blob_usage`, `calldata_per_tx`
**Physique :** couche σ (Adaptation) — réaction du sequencer à la demande. Signaux L1 croisés avec données L2.

**Architecture :**
- Service Rust indépendant : `invarians-l2-adapter` (nouveau repo)
- Source : L1 Ethereum via `ETH_L1_RPC_URL` (Alchemy mainnet)
- Méthode : **Option A** (approximation sans décodage batch encoding)
- Scan : fenêtre 25 blocs L1 / 5 min, throttle 200ms/bloc
- Budget CU estimé : ~3.5M CU/mois (115 000 CU/jour)
- Table cible : `ans_l2_adapter_signals` + `ans_l2_adapter_state`

**Adresses surveillées :**
| Chaîne | Contrat | Adresse |
|--------|---------|---------|
| Base | BatchInbox | `0xff00...8453` |
| Optimism | BatchInbox | `0xff00...0010` |
| Arbitrum | SequencerInbox | `0x1c47...82B6` |

**Premières valeurs observées (17 Mars 2026, 21h35 UTC, blocs L1 #24679924–#24679929) :**
- `blob_usage` Base = 0.833 (5/6 blobs), Optimism = 0.833 (5/6 blobs)
- `calldata_bytes` = 655 360b (5 × 131 072b par blob)
- `publish_latency` ≈ 4 830–4 878s (~80min) — artefact approximation Option A
- Base + Optimism soumettent dans le même bloc L1 (infrastructure OP Stack partagée)
- Arbitrum : aucun batch dans la fenêtre initiale (fréquence on-chain réduite par AnyTrust)

**Note publish_latency :** la valeur ~80min reflète l'écart entre `t_L1_block` et `last_timestamp` de l'invariant L2 le plus récent (fenêtre ~1h). C'est une mesure relative, adaptée à l'EMA. La valeur absolue n'est pas interprétable directement — seules les variations vs baseline sont significatives.

**Note blob_usage = 0.833 :** signal élevé au premier relevé. Peut indiquer une forte utilisation du marché blob ce soir, ou être la baseline normale pour Base/OP. Convergence EMA nécessaire (~10 cycles = ~50 min de L1 scan) avant interprétation.

**Paramètres EMA :** à définir lors de la calibration Dune (Phase D). Pas d'EMA implémentée en Phase C — les signaux sont stockés bruts. L'EMA sera ajoutée dans un service `invarians-l2-chain` enrichi ou dans un nouveau `invarians-l2-adapter-chain`.

**Statut baselines :** non calibrées — premières données, cold start
**Confiance :** LOW — calibration event-detection Dune pending (Phase D, Q2-Q3 2026)

---

---

## Entrée #014 — 22 Mars 2026 — Calibration L2 seuils v2 (ARB · BASE · OP)

**Type :** Calibration paramètre — première calibration statistique L2
**Chaînes :** arbitrum, base, optimism
**Méthode :** Calibration statistique P90-P95 sur 7 jours de production (15-22 mars 2026).
  Pas de backtest événementiel à ce stade — données insuffisantes (n≈105-126/chaîne).
  Validation événementielle prévue Phase D (Q2-Q3 2026 sur données Dune).

**Données source :**
- `ans_l2_rollup_signals` : n=126/chaîne (τ — rhythm_ratio)
- `ans_l2_chain_signals`  : n=91-105/chaîne (π — sigma_ratio)

**Diagnostic par chaîne :**

| Chaîne | τ (rhythm_ratio) | π (sigma_ratio) | Signal discriminant |
|--------|-----------------|-----------------|---------------------|
| Arbitrum | MORT — range 0.9278-1.0135, p95=1.0018 | MORT — constant 1.0000 | Aucun. Toujours S1D1. |
| Base | MORT — constant 1.0000 | ACTIF — p90=1.0866, p95=1.1444, max=1.3068 | π uniquement |
| Optimism | MORT — constant 1.0000 | ACTIF — p90=1.0500, p95=1.0749, max=1.1368 | π uniquement |

**Note τ L2 :** τ (rhythm_ratio) est mort par design sur Base et Optimism — le sequencer impose
une cadence parfaitement régulière (block time fixe 2s). Confirmé empiriquement : toutes les
valeurs observées = 1.0000 exactement. Cohérent avec le pivot architectural du 17 Mars 2026.

**Note cold-start EMA Arbitrum (16 Mars 2026, 00:03 → 07:44) :** Analyse post-calibration des
126 observations révèle 7 entrées consécutives avec τ < 0.97 (min=0.9278) uniquement pendant
cette fenêtre de 7h. Cause : EMA non convergée après démarrage (α=0.1818, N≈10 — convergence
~10 observations = ~10h). La baseline initiale était trop haute → τ < 1.0 pendant la convergence.
Ce n'est pas un événement structurel. Impact opérationnel : **zéro** — τ < 1.0 ne franchit jamais
le seuil S2 (1.15). Le cold-start produit des τ bas (système perçu plus rapide que baseline),
jamais de faux positifs S2. Après le 16 Mars 08h : τ stable dans la bande 0.998–1.014.

**Note π Arbitrum :** sigma_ratio constant = 1.0000 sur 91 observations. Confirmé : gasLimit
Arbitrum Nitro ≈ 2^50 → rho_s ≈ 0 systématiquement → signal non discriminant. Arbitrum sera
toujours S1D1 jusqu'à calibration de complexity_ratio (Phase A — ROADMAP 1-bis).

**Anciennes valeurs (v1 — provisoires depuis 15 mars 2026) :**
- `TAU_THRESHOLD = 1.15` (global)
- `PI_THRESHOLD  = 1.20` (global)

**Nouvelles valeurs (v2 — par chaîne) :**

| Chaîne | τ (était 1.15) | π (était 1.20) | Justification |
|--------|---------------|---------------|--------------|
| Arbitrum | 1.15 (dormant) | 1.20 (dormant) | Signaux morts — seuils sans effet |
| Base | 1.05 (τ mort) | **1.10** | Entre p90 (1.0866) et p95 (1.1444) — ~p92 |
| Optimism | 1.05 (τ mort) | **1.06** | Entre p90 (1.0500) et p95 (1.0749) — ~p93 |

**Validation distribution (requête 1C avec seuils v2) :**

| Chaîne | S1D1 | S1D2 | Verdict |
|--------|------|------|---------|
| Arbitrum | 100% | 0% | Attendu — signaux morts |
| Base | 92.4% | 7.6% | ✅ Dans la cible 3-8% |
| Optimism | 92.4% | 7.6% | ✅ Dans la cible 3-8% |

**Fichiers modifiés :**
- `invarians-oracle/supabase/functions/attestation/index.ts` — `L2_THRESHOLDS` Record par chaîne · `classifyL2State` chain-aware · calibration version `"v2"`
- `invarians-oracle/supabase/migration_l2_states.sql` — CASE par chaîne dans `v_l2_states`

**Déploiements :**
- Oracle Edge Function redéployée : `supabase functions deploy attestation` ✅
- Vue `v_l2_states` recréée en production (Supabase SQL Editor) ✅

**Confiance :** MEDIUM (statistique sur 7j) — pas de backtest événementiel
**Prochaine calibration L2 :** Phase D, Q2-Q3 2026 sur données Dune historiques ARB/BASE/OP
**Blocker :** calibration événementielle requise avant approche commerciale sur L2

---

---

## Entrée #015 — 22 Mars 2026 — Déploiement invarians-bridge-collector (Phase 2A)

**Type :** Nouveau service — déploiement production
**Chaînes :** arbitrum, base, optimism
**Signal :** `last_batch_age_seconds` — temps depuis le dernier batch publié sur L1
**Physique :** liveness du batch posting séquenceur → L1. Détecte les absences (flux interrompu), pas les présences.

**Architecture :**
- Service Rust indépendant : `BRIDGE/invarians-bridge-collector/`
- Source : L1 Ethereum mainnet via `ETH_L1_RPC_URL` (même clé Alchemy que invarians-l2-adapter)
- Méthode : `eth_getLogs` sur BatchDelivered events (Arbitrum) + BatchInbox txs (Base/OP)
- Polling : 10 min
- Tables créées : `ans_bridge_signals` + `bridge_collector_state`

**Premières valeurs observées (22-23 Mars 2026, 131 cycles/chaîne) :**
- arbitrum : avg=57s, max=192s
- base     : avg=23s, max=108s
- optimism : avg=132s, max=360s

**Statut :** Phase 2A ✅ active — Phase 2B en cours (observation 30j, ~22 Avril 2026)
**Prochaine étape :** Phase 2B — calibration P90 `threshold_rupture` + `threshold_P90` par chaîne
**Confiance BS1/BS2 :** non applicable — classifier non déployé (Phase 2C, post-calibration)
**Impact oracle :** `bridge_state` reste hardcodé BS1 dans `attestation/index.ts` jusqu'à Phase 2C

---

## Entrée #016 — 16 Avril 2026 — Analyse distribution 30j L2 + Recalibration seuils BASE/OP

**Type :** Analyse distribution + Recalibration paramètre
**Chaînes :** base, optimism (arbitrum non concerné — signaux dormants)
**Trigger :** Condition H2 levée — 30j post-reset EMA BASE/OP (2026-03-16 → 2026-04-16)

---

**Requête de validation exécutée (16 Avril 2026) :**

```sql
SELECT chain, COUNT(*) as n_samples,
  ROUND(100.0 * SUM(CASE WHEN sigma_ratio >= CASE WHEN chain='base' THEN 1.10
    WHEN chain='optimism' THEN 1.06 ELSE 1.20 END THEN 1 ELSE 0 END) / COUNT(*), 2) as percent_d2,
  ROUND(AVG(sigma_ratio)::numeric, 4) as avg_sigma_ratio,
  ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY sigma_ratio)::numeric, 4) as p90,
  ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY sigma_ratio)::numeric, 4) as p95
FROM ans_l2_chain_signals
WHERE computed_at >= '2026-03-22'::timestamptz
GROUP BY chain ORDER BY chain;
```

**Résultats avec seuils v2 (calibration_log #014) :**

| Chaîne | n | D2% | avg_sigma | p90 | p95 |
|--------|---|-----|-----------|-----|-----|
| arbitrum | 555 | 0.00% | 1.0000 | 1.0000 | 1.0000 |
| base | 558 | 12.37% | 1.0007 | 1.1127 | 1.1671 |
| optimism | 558 | 11.29% | 1.0010 | 1.0675 | 1.1018 |

**Diagnostic :**
- Les seuils v2 (BASE=1.10, OP=1.06) produisent D2%=12-11% — hors cible 3-8%.
- Cause : calibration #014 effectuée sur 7 jours (fenêtre calme). Distribution 30j révèle une activité réelle plus élevée.
- **Incoherence détectée avec L1 :** FPR L1 = 1.20-1.23% (ETH, POL) via logique 2-of-3 multi-signal. L2 utilise sigma seul (mono-signal) avec les mêmes valeurs numériques de seuil → FPR 10x supérieur. Les seuils ne sont pas comparables cross-layer sans ajustement.

**Requête percentile étendue (p97-p99) :**

| Chaîne | p97 | p98 | p99 |
|--------|-----|-----|-----|
| base | 1.1933 | 1.2441 | 1.3110 |
| optimism | 1.1216 | 1.1415 | 1.2273 |

**Logique de recalibration :**

L1 cible FPR ~1.2% avec logique 2-of-3 (consensus multi-signal).
L2 utilise sigma seul (mono-signal, plus sensible) — pour un FPR équivalent, le seuil doit être positionné plus haut dans la distribution.
Cible retenue : **~3% D2 (P97 sur 30j)** — cohérent avec le FPR L1 en tenant compte de l'asymétrie mono/multi-signal.

**Nouvelles valeurs proposées (v3) :**

| Chaîne | Seuil v2 | Seuil v3 | Percentile | D2% estimé | Justification |
|--------|----------|----------|------------|------------|---------------|
| BASE | 1.10 | **1.20** | ~p97 (1.1933) | ~3% | Chiffre rond, juste au-dessus de p97 |
| OP | 1.06 | **1.12** | p97 (1.1216) | ~3% | Exactement p97 |
| ARB | 1.20 | 1.20 (inchangé) | dormant | ~0% | sigma_ratio constant 1.0000 — gasLimit ARB incompatible |

**Statut :** ✅ Déployé — 16 Avril 2026 · `supabase functions deploy attestation` · project sdpilypwumxsyyipceew
**Confiance :** MEDIUM — calibration statistique P97 sur 30j. Pas de validation événementielle.
**Prochaine étape :** Phase D (Q2-Q3 2026) — backtest Dune sur événements L2 historiques ARB/BASE/OP pour valider TPR/FPR sur incidents réels.
**Blocker :** validation événementielle requise avant approche commerciale sur L2 (inchangé depuis #014).

---

*Journal maintenu à jour à chaque intervention sur les baselines ou paramètres de calibration.*
*Format : immuable. Pas de modification des entrées passées — uniquement ajout en fin de fichier.*
