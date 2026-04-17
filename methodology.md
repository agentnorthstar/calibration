---
title: "Invarians — Methodology"
version: "0.4"
status: draft
date: "2026-04-17"
audience: [ai-agents, developers, researchers]
---

# Invarians — Méthode de mesure structurelle des blockchains

> **Statut :** draft — en attente de validation par backtest avant publication finale.

---

## 1. Principe fondamental

Invarians ne mesure pas *ce qui se passe maintenant* sur une blockchain.
Il mesure *dans quel régime structurel la chaîne opère-t-elle*.

```
SIGNAL INSTANTANÉ  →  bruit MEV, arb, liquidations, mempool games
RÉGIME STRUCTUREL  →  état de l'infrastructure sous-jacente
```

La distinction est critique pour les agents IA : un signal instantané peut être
manipulé ou bruité. Un régime structurel est calculé sur des données finalisées,
intégré sur ~1 heure, et indépendant des jeux de marché à court terme.

---

## 2. Architecture du signal

### 2.1 Les deux dimensions mesurées

**τ — Structure (Block/Slot layer)** *(valide sur L1 uniquement — structurellement non discriminant sur L2, cf. section 7.1)*
Mesure le comportement physique du protocole de consensus : cadence, inertie temporelle,
continuité de production, saturation des slots.

**π — Pression + Composition (Chain layer)**
Mesure la pression économique sur la chaîne : saturation des blocs par les transactions,
évolution de la taille moyenne des blocs, volume de transactions.
Sur L2, π s'étend à la **composition** des transactions (Phase A/B) — bytes/tx et gas/tx —
qui forment une sous-couche μ (cf. section 7.4). π pur = pression volumétrique ; μ = pression compositionnelle.

### 2.2 Les deux vitesses d'EMA

Chaque signal est exprimé comme un ratio current/baseline :
```
ratio = signal_current / EMA_baseline
```

Deux baselines EMA sont maintenues en parallèle :
- **EMA rapide** : capture les déviation récentes (~10h par défaut, per-chain)
- **EMA lente** : baseline structurelle long terme (~30 jours par défaut, per-chain)

Le ratio rapide détecte les épisodes de stress. Le ratio lent mesure un drift structurel.

### 2.3 Classification des états

```
τ (structure) :
  S1 : rhythm_ratio < threshold_s2     → structure nominale
  S2 : rhythm_ratio ≥ threshold_s2     → dérive structurelle

π (demande) :
  D1 : sigma_ratio < threshold_d2      → demande nominale
  D2 : sigma_ratio ≥ threshold_d2      → surcharge de demande

États composites :
  S1D1 → infrastructure saine, charge nominale
  S1D2 → infrastructure saine, demande élevée (gaz cher)
  S2D1 → dérive structurelle SANS signature économique visible ← cas critique
  S2D2 → dérive structurelle + surcharge simultanées
```

**S2D1 est l'état le plus important.** Il représente un stress structurel sans signature
économique visible. Aucun fee monitor, aucun gas tracker ne le détecte. C'est la
différence compétitive fondamentale d'Invarians.

> ⚠️ Cette classification (SxDx) s'applique à **L1 uniquement**. Sur L2, τ est mort par design
> (section 7.1) — la classification S2Dx n'existe pas. L2 utilise un framework distinct (π, μ, σ),
> voir section 7.4.

---

## 3. Pipeline de calcul

```
BLOCKCHAIN
  → L0Signal(bloc_index, timestamp, load, capacity, size, tx_count)
  → SHA256(chain:index:timestamp:load:capacity:size:tx_count) = l0_hash

L1INVARIANT (Φ blocs intégrés)
  → rho_st  : cadence moyenne (blocs/s)
  → rho_ts  : inertie temporelle (s/bloc = duration/count)
  → c_s     : continuité (blocs valides / plage totale slots × 100)
  → rho_s   : saturation (load/capacity × 100)
  → size_avg, tx_count_avg
  → l0_batch_hash = SHA256(l0_hash_1 || l0_hash_2 || ... || l0_hash_Φ)
  → l1_hash = SHA256(tous les champs L1)

CLASSIFIER
  → EMA_rapide(rho_ts) = baseline_fast
  → EMA_lente(rho_ts)  = baseline_slow
  → rhythm_ratio = rho_ts / baseline_fast
  → continuity_ratio = c_s / baseline_continuity
  → EMA_rapide(sigma%) = baseline_sigma
  → sigma_ratio = sigma% / baseline_sigma
  → Classification : S1D1 | S1D2 | S2D1 | S2D2

ORACLE
  → Signature Ed25519(état classifié + baselines + hashes)   ← intégrité asymétrique, vérifiable sans clé partagée
  → HMAC-SHA256(payload, clé_service) + TTL 1h               ← authenticité transport entre nœud et consommateur
  → Attestation vérifiable indépendamment
```

---

## 4. Paramètres per-chaîne

> ⚠️ Les paramètres ci-dessous sont des **estimations théoriques**.
> Ils seront remplacés par des valeurs validées par backtest au fur et à mesure.
> Voir `backtest_{chain}.md` pour les valeurs définitives.

### 4.1 Fenêtres d'intégration Φ

| Chaîne | Block time | Φ | β | Throttle | Fenêtre ~1h |
|--------|-----------|---|---|----------|-------------|
| Solana | ~0.4s | 800 | 10 | 45s | ✅ |
| Ethereum | 12s | 280 | 1 | 13s | ✅ |
| Polygon | 2s | 720 | 5 | 25s | ✅ |
| Avalanche | 2s | 720 | 5 | 25s | ✅ |
| Arbitrum | ~0.25s | 14400 | 120 | 38s | ✅ |
| Base | 2s | 1800 | 50 | 110s | ✅ |
| Optimism | 2s | 1800 | 50 | 110s | ✅ |

### 4.2 Signaux valides par chaîne

> **Mise à jour 16 Mars 2026 — validé empiriquement sur données Supabase.**
> L1 (Solana, Ethereum, Polygon, Avalanche) : 90j de données, n≥338 invariants par chaîne.
> L2 (Arbitrum, Base, Optimism) : données insuffisantes (n=14–19) — démarrage production 14 Mars 2026.

| Chaîne | τ signaux valides | π signaux valides | Signaux exclus | Justification empirique |
|--------|------------------|------------------|----------------|------------------------|
| Solana | rho_ts | sigma_ratio, tx_ratio | c_s (99.85%±0.33%), size_ratio (size_avg=0 historique) | c_s quasi-constant — détecteur extrême uniquement |
| Ethereum | rho_ts (faible var.) | sigma_ratio, size_ratio, tx_ratio | c_s (100.00%±0.00%), rho_s (50.76%±0.81%) | rho_s ultra-stable EIP-1559 — sigma_ratio faiblement discriminant |
| Polygon | rho_s (dual τ+π) | sigma_ratio, size_ratio, tx_ratio | rho_ts (2.000s±0.005s), c_s (99.99%±0.06%) | rho_ts : 0.011s d'amplitude sur 90j → inopérable |
| Avalanche | rho_ts (~1s, variable) | sigma_ratio, size_ratio, tx_ratio | c_s (99.99%±0.06%) | Block time réel ~1-1.3s (pas 2s). c_s quasi-constant. |
| Arbitrum | rho_ts | ❌ sigma_ratio CASSÉ | c_s (données insuffisantes), rho_s (0.00% — mesure erreur) | rho_s = 0 : capacity = gas_limit_protocole (1.125e15) au lieu de effective (~32M) |
| Base | rho_ts (post-reset) | sigma_ratio, size_ratio, tx_ratio | c_s (contaminé + miroir rho_ts) | En attente reset EMA. Données actuelles contaminées (c_s min=14.17%) |
| Optimism | rho_ts (post-reset) | sigma_ratio, size_ratio, tx_ratio | c_s (contaminé + miroir rho_ts) | En attente reset EMA. Données actuelles contaminées (c_s min=13.97%) |

> Signaux "exclus" = non utilisés pour la classification, toujours calculés et stockés.
> c_s reste calculé : utile pour détecter les outages extrêmes (drop > 10%), non pour la dérive précoce.

#### Données empiriques rho_s (90j)

| Chaîne | n | avg_rho_s | std_rho_s | p50 | p85 | p95 | CV | Verdict |
|--------|---|-----------|-----------|-----|-----|-----|----|---------|
| Solana | 338 | 72.93% | 11.49% | 71.16% | 86.87% | 93.94% | 15.8% | ✅ Fort |
| Polygon | 354 | 62.44% | 6.10% | 64.11% | 67.75% | 70.08% | 9.8% | ✅ Bon |
| Optimism | 15 | 44.21% | 2.23% | 45.16% | 45.96% | 47.53% | 5.0% | ✅ Modéré (contaminé) |
| Ethereum | 349 | 50.76% | 0.81% | 50.74% | 51.42% | 52.14% | 1.6% | ⚠️ Faible (EIP-1559) |
| Avalanche | 354 | 12.94% | 2.83% | 11.74% | 16.42% | 18.80% | 21.9% | ✅ Bon (CV élevé) |
| Base | 14 | 13.92% | 1.12% | 13.71% | 14.99% | 15.58% | 8.0% | ⚠️ Modéré (contaminé) |
| Arbitrum | 19 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | — | ❌ Mesure cassée |

### 4.3 Données empiriques rho_ts (90j)

| Chaîne | n | avg_rho_ts | std_rho_ts | p50 | p90 | p95 | p99 | p99/p50 |
|--------|---|------------|------------|-----|-----|-----|-----|---------|
| Polygon | 354 | 1.9974s | 0.0013s | 1.9972s | 1.9972s | 1.9972s | 2.0068s | **1.005** |
| Ethereum | 349 | 12.0155s | 0.0548s | 12.000s | 12.086s | 12.129s | 12.171s | **1.014** |
| Solana | 339 | 0.3937s | 0.0044s | 0.3938s | 0.3988s | 0.4007s | 0.4081s | **1.036** |
| Arbitrum | 19 | 0.2521s | 0.0058s | 0.2500s | 0.2550s | 0.2572s | 0.2715s | **1.086** |
| Avalanche | 354 | 1.0719s | 0.0660s | 1.0403s | 1.1774s | 1.2060s | 1.2446s | **1.197** |
| Base | 14 | 4.679s | 4.135s | 2.950s | 11.622s | 14.024s | 14.098s | **4.78** |
| Optimism | 15 | 4.564s | 4.070s | 2.885s | 10.900s | 14.055s | 14.263s | **4.94** |

> Base et Optimism : données contaminées (race condition). p50 ~3s au lieu de 2s. Reset EMA pending.
> Avalanche : block time réel ~1.04s (p50), pas 2s comme documenté initialement.

### 4.4 Seuils de classification — état de calibration par chaîne

**Niveaux de confiance :**
- `MEDIUM event-based` — backtest BigQuery validé, TPR+FPR mesurés sur événements ground truth réels → **publiable**
- `MEDIUM statistique` — P97 sur ≥30j de production, sans événements ground truth → opérationnel en production, calibration event-based pending
- `LOW` — estimation empirique uniquement, pas de backtest → non publiable
- `HIGH` — TPR ≥ 0.80, FPR ≤ 0.10, n ≥ 3 événements, déployé >30j → cible Q3-Q4 2026

> ⚠️ Seuls les paramètres `MEDIUM event-based` sont publiés ici.
> Les seuils en production sur les autres chaînes sont disponibles dans l'API mais
> ne sont pas certifiés publiquement avant validation event-based complète.

#### τ — Seuils structurels (threshold_s2) — publiés

| Chaîne | threshold_s2 | Événements validés | FPR_τ | Confidence | Statut |
|--------|-------------|-------------------|-------|------------|--------|
| **Ethereum** | **1.12** | The Merge (sept 2022) · Shanghai Upgrade (avril 2023) | 0.38% | **MEDIUM event-based** | ✅ publié |
| **Polygon** | **1.04** | Network Halt · Gas Crisis · Heimdall/Bor · Reorg Storm (2021–2023) | 11.75% | **MEDIUM event-based** | ✅ publié |
| **Solana** | **1.12** | 4 major outages (Sept 2021 · Jan 2022 · May 2022 · Oct 2022) | 1.77% | **MEDIUM event-based** | ✅ publié |
| Avalanche τ | en cours | Calibration event-based juillet 2026 | — | pending | ⏳ |
| Arbitrum τ | Dormant | Sequencer régulier par design — signal non discriminant | — | Dormant | — |
| Base τ | Dormant | Sequencer régulier par design | — | Dormant | — |
| Optimism τ | Dormant | Sequencer régulier par design | — | Dormant | — |

#### π — Seuils de demande — publiés

| Chaîne | D2 logic | sigma | size | tx | FPR combiné (τ+π) | Confidence | Statut |
|--------|----------|-------|------|----|--------------------|------------|--------|
| **Ethereum** | **2 of 3** | **1.10** | **1.20** | **1.10** | **1.23%** | **MEDIUM event-based** | ✅ publié |
| **Polygon** | **2 of 3** | **1.14** | **1.18** | **1.23** | **11.75%** | **MEDIUM event-based** | ✅ publié |
| Solana π | en cours | Données exploitables mi-juin 2026 | — | — | — | pending | ⏳ |
| Avalanche π | en cours | Calibration event-based juillet 2026 | — | — | — | pending | ⏳ |
| Base π | MEDIUM statistique en prod | Calibration event-based Phase D (Q2-Q3 2026) | — | — | — | pending | ⏳ |
| Optimism π | MEDIUM statistique en prod | Calibration event-based Phase D (Q2-Q3 2026) | — | — | — | pending | ⏳ |
| Arbitrum π | signal absent par construction | gasLimit Nitro ≈ ∞ — rho_s structurellement nul | — | — | — | fix pending | ⏳ |

#### Événements ground truth ETH validés (backtest BigQuery 2020–2024)

| Événement | Type | État attendu | Détecté | Latence |
|-----------|------|-------------|---------|---------|
| DeFi Summer (juin–sept 2020) | Surge demande pré-EIP-1559 | S1D2 | ✅ | — |
| NFT Mania (mars–mai 2021) | Surge demande | S1D2 | ✅ | — |
| The Merge (15 sept 2022) | Transition PoW→PoS | S2D1 | ✅ | +18.3h |
| Shanghai Upgrade (12 avril 2023) | Activation withdrawals | S2D1 | ✅ | +22.8h |

### 4.5 Pipeline de calibration complet — OFFLINE → ONLINE

```
╔══════════════════════════════════════════════════════════════╗
║  OFFLINE  (calibration — une fois par version de threshold)  ║
╚══════════════════════════════════════════════════════════════╝

  Distribution historique des ratios EMA (4 ans BigQuery)
    + événements ground truth (Merge, outages, upgrades…)
              ↓
    MÉTHODE A — Event-based (L1 mature : ETH, POL, SOL)
      → Sweeper thresholds candidats (1.01 → 1.25)
      → Choisir le plus élevé qui détecte 100% des événements
      → P90/P95/P97 borne la zone de recherche, pas le résultat
              ↓
    MÉTHODE B — Statistique (L2 sans événements historiques : BASE, OP)
      → 30j de production propre
      → Threshold = P97 de la distribution
      → Confidence : MEDIUM statistique (vs MEDIUM event-based pour L1)
              ↓
    Threshold fixe versionné (ex: threshold_s2=1.12 pour ETH τ)
    stocké dans AgentNorthStar.com registry
              ↓
    M1 — Metric Stability Score calculé sur la distribution calibrante
    (cf. section 10)


╔══════════════════════════════════════════════════════════════╗
║  ONLINE  (production — à chaque fenêtre Φ de blocs)          ║
╚══════════════════════════════════════════════════════════════╝

  Signal brut (rho_ts, sigma, size, tx) depuis la blockchain
              ↓
    EMA rapide (α=2/11, ~10h)   ← "comportement récent"
    EMA lente  (α=2/721, ~30j)  ← "baseline structurelle long terme"
              ↓
    ratio = signal_actuel / EMA_rapide
    → adimensionnel : 1.0 = nominal, 1.15 = 15% au-dessus de la baseline
    → comparable entre ETH (12s/bloc) et SOL (0.4s/bloc)
              ↓
    ratio ≥ threshold_τ ?      → S2 (dérive structurelle)  / S1 (nominal)
    ≥2 dims sur 3 ≥ threshold_π ? → D2 (demande élevée)   / D1 (nominal)
              ↓
    État : S1D1 | S1D2 | S2D1 | S2D2
              ↓
    PoEC signé Ed25519 + HMAC-SHA256
```

**Propriété architecturale clé :** le threshold est stable et versionné (auditable),
mais le référentiel (EMA) s'adapte en continu à la chaîne. Si ETH devient
naturellement plus lent après un upgrade, l'EMA s'ajuste en ~10h et le système
ne sonne plus en permanence. Stabilité de l'alarme + adaptabilité de la baseline.

---

## 5. Chaîne cryptographique de confiance

```
L0Signal  →  SHA256  →  L1Invariant  →  SHA256  →  L2Signal  →  Ed25519  →  Oracle  →  Agent
```

Ce qu'Invarians **atteste** :
> "Le nœud X a observé Y à l'instant T via les méthodes M sur le bloc B."

Ce qu'Invarians **n'atteste PAS** :
- Que Y est universellement vrai
- Qu'un autre nœud verrait la même chose
- Que l'observation est reproductible demain

L'intégrité de l'observation est garantie. La vérité universelle ne l'est pas.

---

## 6. Limites instrumentales connues

| Chaîne | Limitation | Impact | Compensé par |
|--------|-----------|--------|-------------|
| Ethereum | c_s=100% par construction (capteur EVM, pas slot-par-slot) | c_s non informative | Beacon chain monitoring séparé |
| Ethereum | rho_s 50.76%±0.81% (EIP-1559 cible 50%) | sigma_ratio très faiblement discriminant — seuil D2 devra être très proche de 1.0 | Combinaison size_ratio + tx_ratio |
| Polygon | rho_ts 2.000s±0.005s (block time gouverné 2s fixe) | rho_ts inopérable — amplitude totale 0.011s sur 90j | rho_s = signal τ ET π principal |
| Avalanche | Block time documenté 2s, réel ~1-1.3s | Documentation incorrecte, paramètres Φ à recalibrer | Φ basé sur block time réel mesuré |
| Arbitrum | rho_s = 0.00% systématique | σ signal totalement absent — classification π impossible | Fix requis : utiliser gas_used / block_gas_limit effectif (~32M) |
| Base, OP | rho_ts et c_s mathématiquement inverses (block time 2s fixe) | c_s redondant, pas un signal indépendant | Utiliser uniquement rho_ts |
| Base, OP | Baselines EMA contaminées (race condition 16 Mars 2026) | c_s min=14.17/13.97%, rho_ts max=14s — baselines faussées | Reset EMA après premier invariant propre |
| Toutes L2 | Post-seal sync : ~60% du temps non couvert | Couverture discontinue | Design intentionnel — fenêtre fraîche |
| Toutes chaînes | c_s ≈ 100% en opération nominale (sauf outage extrême) | Faible pouvoir discriminant pour la dérive précoce | c_s conservé comme détecteur d'outage extrême (drop > 10%) |
| Polygon, Arbitrum (τ) | Un seul signal τ opérationnel | Fragilité : si le signal unique est bruité, pas de redondance pour S1/S2 | À documenter — amélioration future |

### 6.1 Propriété mathématique du ratio EMA

Le signal `rhythm_ratio = rho_ts / EMA(rho_ts)` a une propriété importante à comprendre :

```
Phase 1 — surge :   rho_ts monte, EMA lag     → ratio élevé → S2 détecté        ✅
Phase 2 — retour :  rho_ts redescend, EMA haute → ratio < 1  → retour S1         ✅
Phase 3 — shadow :  EMA encore haute (~10h)    → sensibilité réduite temporairement ⚠️
```

Après un événement S2, il existe une **fenêtre d'insensibilité temporaire** (~10h, durée de l'EMA rapide) pendant laquelle un second événement aurait besoin d'une déviation plus forte pour être détecté. Ce n'est pas un bug — c'est une propriété mécanique des ratios à dénominateur retardé. L'EMA lente (30j) ne subit pas cette compression et maintient une baseline stable sur le long terme.

**Règle de reset EMA :** un reset est légitime uniquement lors d'un changement de régime d'instrumentation (fix capteur, race condition corrigée, paramètre Φ modifié). Un reset ne peut pas être motivé par un désaccord avec la classification produite — ce serait une falsification de l'historique.

---

---

## 7. L2 Rollups — Pourquoi les signaux sont différents

### 7.1 La contrainte physique fondamentale

Sur L1, le protocole de consensus produit les blocs. Un écart de cadence → stress structurel réel.

Sur L2, un **sequencer centralisé** produit les blocs à cadence régulière par design :

```
L1 (Ethereum, Solana, Polygon…)   → consensus distribué → cadence variable → τ mesurable
L2 (Arbitrum, Base, Optimism…)    → sequencer unique    → cadence fixe     → τ mort par design
```

Conséquence directe : `rhythm_ratio ≈ 1.0` en permanence sur L2. Ce n'est pas un bug de mesure — c'est une propriété structurelle des rollups. **τ n'est pas un signal discriminant sur L2.**

### 7.2 Le cas Arbitrum — rho_s cassé

Sur Ethereum, `rho_s = gasUsed / gasLimit`. Le gasLimit effectif (~30M) est proche du gasUsed (~15-25M), ce qui donne un ratio informatif.

Sur Arbitrum Nitro, le gasLimit protocole est `2^50 ≈ 1.125×10¹⁵`. Le gasUsed est ~2-3 milliards.
```
rho_s(Arbitrum) = 2×10⁹ / 1.125×10¹⁵ ≈ 0.000001 → arrondi à 0.00%
```

**σ standard est structurellement absent sur Arbitrum.** La chaîne opère toujours à saturation quasi-nulle par construction du modèle de gas Nitro.

### 7.3 Ce qui est opérationnel sur L2

| Signal | Arbitrum | Base | Optimism | Raison |
|--------|----------|------|----------|--------|
| `rhythm_ratio` (τ) | ❌ mort | ❌ mort | ❌ mort | Sequencer régulier par design |
| `sigma_ratio` (π) | ❌ cassé | ✅ | ✅ | gasLimit Nitro ≈ ∞ sur Arbitrum |
| `size_ratio` (π) | ✅ | ✅ | ✅ | Taille des blocs mesurable sur tous |
| `tx_ratio` (π) | ✅ | ✅ | ✅ | Volume de txs mesurable sur tous |
| `complexity_ratio` (π) | ✅ | ✅ | ✅ | Dérivé de size_avg/tx_count_avg |
| `gas_complexity_ratio` (π) | ✅ | ✅ | ✅ | Dérivé de gas_used_avg/tx_count_avg |

### 7.4 Nouvelle architecture de comparaison — L1 cause / L2 réponse

**Pourquoi (SxDx)L1 vs (SxDx)L2 ne fonctionne pas :**

L'intention initiale était une symétrie :
```
L1 : S (structure) + D (demande)
L2 : S (structure) + D (demande)
```

Cette symétrie est physiquement incorrecte. Sur L2, S ≈ constant (sequencer).
La dimension τ dégénère en constante → classifier inutile → perte d'information.

**La découverte réelle :**
```
L1 = système physique → observable directement → sensing direct
L2 = couche de transformation → observable indirectement → sensing indirect
```

L2 n'est pas une "mini L1". C'est une couche de **réponse** à l'état L1.

**Nouvelle architecture :**

```
L1 → (S, D)                          Bridge → (BS*)            L2 → (π, μ, σ)
  S = structure (τ)                     état opérationnel           π = pression (tx, size, sigma)
  D = demande   (π)                     (latency, backlog)          μ = composition (complexity_ratio, gas_complexity_ratio)
                                                                    σ = adaptation (publish_latency, blob_usage)
```

**Logique causale :**
```
L1 = CAUSE → état structurel global du système
Bridge     → canal de transmission — conditionne la propagation
L2 = EFFET → réponse locale à cet état
```

Invarians ne compare plus des chaînes entre elles symétriquement.
Il lit des couches d'un même système : **Invarians = cross-layer interpreter**.

**Grille de lecture causale :**

| État L1 | Bridge | Réponse L2 typique | Interprétation |
|---------|--------|-------------------|----------------|
| S1D1 | BS1L1 | π↓ μ↓ σ↓ | Calme global — infrastructure saine |
| S1D2 | BS1L1 | π↑ μ stable σ stable | Adoption saine — L2 absorbe la demande normalement |
| S2D1 | BS1L1 | π↓ μ↑ σ↑ | Stress structurel invisible côté prix — L2 s'adapte sans demande apparente |
| S2D2 | BS1L1 | π↑ μ↑ σ↑ | Congestion systémique — stress à toutes les couches |
| * | BS2L* | σ↑ | Bridge congestionné — transmission rompue, L2 répond seul |

> Le cas S2D1 + π↓ μ↑ σ↑ est particulièrement intéressant pour les agents IA :
> il signale un stress réel d'infrastructure **avant** qu'il soit visible dans les fee markets.

**Ce que ça change pour le produit :**

Avant : dashboard + monitoring
Maintenant : **oracle de contexte d'exécution** — input pour agents, routing intelligent, décision multi-layer.

---

## 8. Extension signaux L2 — Phases A, B, C (déployées 17 Mars 2026)

### 8.1 Phase A — complexity_ratio : bytes/tx (proxy complexité données)

**Motivation :** sur L2, τ est mort et σ Arbitrum est cassé. La première dérivation utile depuis les données existantes est la complexité des données par transaction.

```
complexity = size_avg / tx_count_avg   (bytes par transaction)
complexity_ratio = complexity / EMA(complexity)
```

**Physique :** un complexity_ratio élevé indique que les transactions deviennent plus lourdes en données — signature de smart contracts complexes, de transfers NFT massifs, ou de calldata dense. Signal utile même quand rho_s est absent.

**Implémentation :** dérivé directement dans `invarians-l2-chain/src/lib.rs` depuis les champs existants `DemandSnapshot.size_avg` et `DemandSnapshot.tx_count_avg`. **Aucun changement côté collector.**

**EMA :** même alpha que les autres signaux (2/11 rapide, 2/721 lente). Cohérence temporelle avec π.

**Baselines initiales (17 Mars 2026) :**
- Arbitrum : 589.7 bytes/tx
- Base : 564.5 bytes/tx
- Optimism : 302.9 bytes/tx

---

### 8.2 Phase B — gas_complexity_ratio : gas/tx (complexité computationnelle)

**Motivation :** complexity_ratio mesure le poids des *données*. Il manque une mesure du poids *computationnel* — ce que la chaîne calcule réellement par transaction. C'est le signal σ pour Arbitrum.

```
gas_complexity = gas_used_avg / tx_count_avg   (gas par transaction)
gas_complexity_ratio = gas_complexity / EMA(gas_complexity)
```

**Physique :** un gas_complexity_ratio élevé indique que les transactions sont computationnellement plus lourdes — DeFi complexe, smart contracts intensifs. Sur Arbitrum en particulier, c'est le seul proxy de surcharge computationnelle disponible (rho_s étant structurellement nul).

**Contrainte technique :** `ans-core` est **gelé** — `L0Signal` et `InvariantL1` sont immuables (intégrité de la chaîne cryptographique L1). `gas_used_avg` est calculé dans `invarians-l2-collector` depuis le buffer : `mean(load)` sur Φ blocs, stocké comme colonne nullable dans `ans_invariants_v3`.

```
Implémentation :
invarians-l2-collector  → gas_used_avg = sum(s.load) / buffer.len()   [hors ans-core]
ans_invariants_v3       → ADD COLUMN gas_used_avg DOUBLE PRECISION
invarians-l2-chain      → gas_complexity_ratio depuis gas_used_avg/tx_count_avg
```

**NULL safety :** si `gas_used_avg IS NULL` ou `tx_count_avg = 0`, le ratio revient à 1.0 (neutre) et la baseline est préservée. Cold start attendu : 1 cycle collector (~1h) avant première valeur non-NULL.

---

### 8.3 Phase C — invarians-l2-adapter : la couche σ (Adaptation)

**Motivation :** τ est mort sur L2. π mesure la demande sur la chaîne. Il reste une dimension non mesurée : **comment le sequencer réagit à la demande** — c'est la couche σ (Adaptation).

La source de ces signaux n'est pas la L2 mais **L1 Ethereum** : le sequencer matérialise son adaptation en soumettant des batchs à L1. Ces batchs sont observables on-chain.

```
DEMANDE (L2)    →  sequencer réagit  →  BATCH SUBMISSION (L1)
     π mesure ici                              σ mesure ici
```

**Trois signaux σ produits :**

| Signal | Calcul | Physique |
|--------|--------|----------|
| `publish_latency_seconds` | `t_L1_inclusion − last_timestamp_L2` (approx) | Délai de publication du batch. Augmente sous charge extrême ou congestion L1. |
| `calldata_bytes` | `input.len()` (calldata tx) ou `blob_count × 131 072` (blob tx) | Taille totale du batch soumis. Proxy du volume de données L2 compressé. |
| `blob_usage` | `blob_count / 6` | Saturation du marché EIP-4844. Ressource partagée entre TOUS les L2 — signal systémique cross-L2. |
| `calldata_per_tx` | `calldata_bytes / tx_count_ref` (approx) | Efficacité de compression des données par transaction L2. |

**Pourquoi blob_usage est stratégique :** EIP-4844 alloue 6 blobs par bloc L1. Base et Optimism se disputent ces blobs avec tous les autres L2. Un stress blob touche simultanément tous les OP Stack. C'est un signal d'infrastructure partagée invisible dans les métriques par-chaîne.

**Méthode — Option A (approximation) :** pas de décodage du batch encoding (OP Span Batch / Arbitrum Nitro). `publish_latency` est approximé par `t_L1_block − last_timestamp` du dernier invariant L2. Valeur relative, adaptée à l'EMA. La précision absolue n'est pas requise pour détecter des régimes.

**Adresses L1 surveillées :**
| Chaîne | Contrat | Adresse |
|--------|---------|---------|
| Base | BatchInbox | `0xff00000000000000000000000000000000008453` |
| Optimism | BatchInbox | `0xff00000000000000000000000000000000000010` |
| Arbitrum | SequencerInbox | `0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6` |

**Infrastructure :** scan L1 toutes les 5 minutes, fenêtre 25 blocs (~5 min L1 = 12s/bloc). Source : Alchemy mainnet. Budget : ~3.5M CU/mois.

**Premières observations (17 Mars 2026) :**
- Base + Optimism soumettent dans le **même bloc L1** (infrastructure OP Stack partagée)
- `blob_usage = 0.833` (5/6 blobs) — marché blob sous forte utilisation
- Arbitrum : fréquence on-chain réduite (AnyTrust réduit les soumissions on-chain)

---

## 9. Synthèse complète des métriques Invarians

### 9.1 L1 — Couches τ et π

| Métrique | Calcul | Couche | Chaînes actives | Signal |
|---------|--------|--------|----------------|--------|
| `rho_ts` | durée_fenêtre / nb_blocs | τ | ETH, SOL, AVAX, ARB | Inertie temporelle — cadence en s/bloc |
| `rhythm_ratio` | rho_ts / EMA(rho_ts) | τ | ETH, SOL, AVAX, ARB | Dérive de cadence vs baseline |
| `c_s` | blocs_valides / plage_slots × 100 | τ | toutes | Continuité — détecteur outage extrême |
| `rho_s` | gasUsed / gasLimit × 100 | π | ETH, SOL, POL, AVAX | Saturation computationnelle |
| `sigma_ratio` | rho_s / EMA(rho_s) | π | ETH, SOL, POL, AVAX | Surcharge computationnelle vs baseline |
| `size_avg` | bytes moyen par bloc | π | toutes | Volume données |
| `size_ratio` | size_avg / EMA(size_avg) | π | toutes | Pression données vs baseline |
| `tx_count_avg` | transactions moyennes par bloc | π | toutes | Volume opérationnel |
| `tx_ratio` | tx_count_avg / EMA(tx_count_avg) | π | toutes | Pression opérationnelle vs baseline |

### 9.2 L2 — Couche π (Pression volumétrique)

| Métrique | Calcul | Phase | Chaînes | Signal |
|---------|--------|-------|---------|--------|
| `sigma_ratio` | rho_s / EMA(rho_s) | baseline | BASE, OP | Saturation (❌ Arbitrum : gas model incompatible) |
| `size_ratio` | size_avg / EMA(size_avg) | baseline | ARB, BASE, OP | Volume données L2 |
| `tx_ratio` | tx_count_avg / EMA(tx_count_avg) | baseline | ARB, BASE, OP | Volume transactions L2 |

> Note : `rhythm_ratio` est calculé et stocké sur L2 mais structurellement ≈ 1.0 — non discriminant.

**Pourquoi la calibration L2 diffère structurellement de L1 :**

1. **Mono-signal vs multi-signal.** Sur L1, D2 requiert 2 dims sur 3 (sigma + size + tx) — consensus multi-signal, FPR combiné ~1.2%. Sur L2, `sigma_ratio` est le seul signal fiable sur BASE/OP (size et tx non calibrés événementiellement). Un seuil mono-signal placé au même percentile que L1 produit un FPR structurellement supérieur. Les seuils L2 ne sont pas numériquement comparables aux seuils L1.

2. **Statistique vs événementiel.** Les seuils L1 sont dérivés par event-detection (BigQuery — The Merge, Solana outages, Polygon Reorg Storm). Les seuils L2 sont statistiques (percentile sur distribution de production) — aucun événement L2 calibrant disponible avant Phase D (Dune, Q2-Q3 2026).

**Statut de calibration L2 :**
- Seuils en production (opérationnels), dérivés par méthode statistique P97 sur ≥30j
- Calibration event-based (Phase D — Dune) : Q2-Q3 2026
- Seuils numériques publiés dans `ans_registry` après validation Phase D uniquement

### 9.2b L2 — Couche μ (Composition — Phases A/B)

μ est une sous-couche de π qui mesure la **structure interne** des transactions,
pas leur volume. Un tx_ratio stable avec un μ croissant signale une recomposition
de l'activité (transactions plus complexes, pas nécessairement plus nombreuses).

| Métrique | Calcul | Phase | Chaînes | Signal |
|---------|--------|-------|---------|--------|
| `complexity_ratio` | (size_avg/tx_count_avg) / EMA | **Phase A** | ARB, BASE, OP | Complexité données par tx (bytes/tx) — proxy poids calldata |
| `gas_complexity_ratio` | (gas_used_avg/tx_count_avg) / EMA | **Phase B** | ARB, BASE, OP | Complexité computationnelle par tx (gas/tx) — proxy charge DeFi |

### 9.3 L2 Adapter — Couche σ (Adaptation)

| Métrique | Calcul | Phase | Chaînes | Signal |
|---------|--------|-------|---------|--------|
| `publish_latency_seconds` | t_L1_block − last_timestamp_L2 | **Phase C** | ARB, BASE, OP | Délai de publication batch L1 |
| `calldata_bytes` | input.len() ou blob_count×131072 | **Phase C** | ARB, BASE, OP | Taille batch soumis à L1 |
| `calldata_per_tx` | calldata_bytes / tx_count_ref | **Phase C** | ARB, BASE, OP | Efficacité compression par tx (approx) |
| `blob_count` | len(blobVersionedHashes) | **Phase C** | BASE, OP | Nombre de blobs EIP-4844 utilisés |
| `blob_usage` | blob_count / 6 | **Phase C** | BASE, OP | Saturation marché blob (ressource cross-L2) |

### 9.4 Synthèse par couche et framework d'état

```
L1 → (S, D) states
  S1D1 | S1D2 | S2D1 | S2D2

L2 → (π, μ, σ) states  [framework en construction — Phase D]
  π = pression volumétrique (tx, size, sigma)
  μ = composition (complexity_ratio, gas_complexity_ratio)
  σ = adaptation via L1 (publish_latency, blob_usage)
```

Classification L2 cible (post Phase D) :

| π | μ | σ | Interprétation |
|---|---|---|----------------|
| ↓ | ↓ | ↓ | Activité faible — régime calme |
| ↑ | stable | stable | Adoption saine — volume en hausse, complexité stable |
| stable | ↑ | stable | Recomposition — transactions plus complexes sans volume |
| ↑ | ↑ | stable | Adoption complexe — DeFi intensif |
| ↑ | ↑ | ↑ | Stress réel — congestion à toutes les couches |

> Cette grille sera calibrée par backtest Dune sur événements L2 historiques (Phase D).

### 9.5 Bridge — Couche de transmission

Le bridge est la **membrane entre L1 et L2**. Il ne mesure pas l'état de L1 ou de L2 —
il mesure si le **canal de transmission entre les deux couches est opérationnel**.

**Rôle systémique :**
```
L1 (état global)
  → Bridge (transmission)
    → L2 (exécution)
```

Le bridge conditionne la propagation du stress entre couches. Un stress L1 peut rester
contenu (bridge peu actif) ou se propager massivement (flux bridge élevé). Un bridge
congestionné casse la transmission — L2 se retrouve isolé.

**Dimension opérationnelle — BS* (Phase 2, Q3 2026) :**

| Métrique | Nature | Signal |
|---------|--------|--------|
| `latency_ratio` | t_relay / expected | Délai de relay message L1↔L2 |
| `backlog_ratio` | pending / throughput | Saturation file de messages |

Classification BS* :

| État | Condition | Signification |
|------|-----------|---------------|
| **BS1L1** | Latency normal, backlog normal | Bridge sain |
| **BS1L2** | Latency normal, backlog élevé | File d'attente |
| **BS2L2** | Latency élevée + backlog | Stress bridge |
| **BS2L1** | Latency élevée, backlog nominal | Instabilité relayers |

> Pas d'hystérésis sur les bridges — polling 5-15 min (mesure directe, pas de fenêtre ~1h).
> Un bridge peut passer de sain à congestionné en 5-15 minutes.

**Dimension de flux — ω (Phase 3, prospectif) :**

Une extension future introduira **ω** (flux inter-couches) comme signal de propagation
économique — distinct de l'état opérationnel BS*.

> ⚠️ Note : β est déjà utilisé en section 4.1 comme paramètre de batch interne.
> Le flux bridge est noté ω pour éviter la collision.

| Signal ω (futur) | Nature | Interprétation |
|-----------------|--------|----------------|
| Volume bridgé (ETH→L2) | Flux économique | Migration d'activité L1→L2 |
| Dépôts / Retraits | Direction flux | Panic/risk-off si retraits massifs |
| Déséquilibre L1↔L2 | Asymétrie | Arbitrage ou fuite de liquidité |

```
ω = signal de propagation économique
BS* = état opérationnel du canal
```

> ω n'est pas encore implémenté — aucune donnée collectée. À évaluer post Phase D.

### 9.6 Disponibilité des EMA par couche

| Couche | EMA rapide | EMA lente | Baselines calibrées |
|--------|-----------|-----------|-------------------|
| L1 τ+π | ✅ (2/11, ~10h) | ✅ (2/721, ~30j) | ETH : MEDIUM. Autres : LOW ou pending |
| L2 π+μ | ✅ (2/11, ~10h) | ✅ (2/721, ~30j) | toutes LOW — calibration Dune pending |
| L2 σ (adapter) | ⏳ non encore | ⏳ non encore | À implémenter post Phase D |

> Les signaux Phase C sont actuellement stockés **bruts** (pas d'EMA). L'EMA σ sera ajoutée après calibration Dune (Phase D, Q2-Q3 2026).

---

## 10. M1 — Metric Stability Score

> **Statut :** formule en cours de formalisation — valeurs publiées sur AgentNorthStar.com, calcul documenté ici dès validation.

M1 quantifie la **fiabilité calibratoire** d'un signal sur une chaîne donnée.
Il répond à la question : *ce signal est-il suffisamment discriminant pour produire
une alarme fiable, ou est-il trop bruité / trop plat pour être utile ?*

### 10.1 Formule (validée — session calibration 17 Avril 2026)

```
M1 = amplitude_dynamique / bruit_baseline

amplitude_dynamique  = (max_event − p50) / p50
                       max_event = maximum du ratio EMA observé pendant le meilleur événement ground truth
                       p50       = médiane du ratio EMA sur le backtest complet

bruit_baseline       = std(signal) / mean(signal)
                       calculé sur les fenêtres où ratio < 1.05 (régime nominal strict)
```

**Propriété :** M1 mesure combien de fois l'amplitude du signal lors d'un événement réel
dépasse le bruit structurel du régime nominal. M1 ≥ 1.0 signifie que le signal
discrimine mieux qu'il ne bruite — calibration utilisable. M1 < 0.5 signifie que
le bruit domine l'amplitude — signal non discriminant.

**Vérification numérique ETH (session 17 Avril 2026) :**
```
Signal       : rhythm_ratio (rho_ts / EMA_fast)
max_event    : 1.1548  (The Merge, 15 sept 2022)
p50          : 0.9993
amplitude    : (1.1548 − 0.9993) / 0.9993 = 0.1556
bruit        : std/mean du signal < 1.05 = 0.0307
M1_calculé   : 0.1556 / 0.0307 = 5.07  ✅  (valeur publiée : 5.05)
```

### 10.2 Interprétation

| Score M1 | Niveau | Signification |
|----------|--------|---------------|
| ≥ 2.0 | Excellent | Signal fortement discriminant |
| ≥ 1.0 | Certified | Calibration event-based validée |
| ≥ 0.5 | Operational | Calibration statistique acceptable |
| < 0.5 | Provisional | Signal faible — utiliser avec précaution |

**Statuts spéciaux :**
- **Dormant** : signal constant par design (ex: ARB τ — sequencer régulier). M1 non calculable.
- **Observational** : données insuffisantes pour calibration (ex: Bridge BS2 pré-Phase 2C).

### 10.3 Valeurs publiées (MEDIUM event-based uniquement)

| Chaîne | Signal | M1 | Méthode | Confidence |
|--------|--------|-----|---------|------------|
| **Ethereum** | τ (rho_ts) | **5.07** | Event-based · The Merge max=1.155 | **MEDIUM event-based** |
| **Polygon** | π (rho_s) | **7.37** | Event-based · Gas Crisis max=2.10 | **MEDIUM event-based** |
| Solana | τ | — | Backtest τ validé — M1 pending formalisation complète | LOW — non publié |
| Avalanche | τ | — | Calibration event-based pending (juillet 2026) | LOW — non publié |
| Arbitrum | τ/π | — | Dormant (sequencer régulier par design) | Dormant |
| Base | π | — | Phase D pending (Q2-Q3 2026) | Observational |
| Optimism | π | — | Phase D pending (Q2-Q3 2026) | Observational |

> Formule validée le 17 Avril 2026 sur données BigQuery ETH (34 697 fenêtres).
> **Note :** les valeurs précédemment publiées sur AgentNorthStar.com (ETH=5.05, POL=8.06)
> étaient des estimations manuelles. Les valeurs recalculées avec la formule formalisée
> sont ETH=5.07 et POL=7.37. Mise à jour ANS registry pending.
> Seules les valeurs MEDIUM event-based sont publiées ici.

### 10.4 Protocole de recalcul

M1 est recalculé uniquement lors de :
- Ajout d'un événement ground truth au backtest
- Changement de threshold (nouvelle version)
- Reset EMA après incident capteur

M1 ne fluctue pas en production — c'est une propriété de la calibration, pas du runtime.

---

## 11. Prochaines évolutions

- [x] Phase A : complexity_ratio L2 (17 Mars 2026)
- [x] Phase B : gas_complexity_ratio L2 (17 Mars 2026)
- [x] Phase C : invarians-l2-adapter — publish_latency, calldata_per_tx, blob_usage (17 Mars 2026)
- [ ] Phase D : calibration Dune — seuils Phase A+C sur événements L2 historiques (Q2-Q3 2026)
- [ ] EMA σ : ajouter EMA rapide/lente sur les signaux Phase C (après Phase D) — `σ_ratio = σ / EMA(σ)`
- [ ] Classifier L2 (π, μ, σ) : implémenter les états (cf. section 9.4) après calibration Phase D
- [ ] **Phase 2 — Bridge BS*** : invarians-bridge module (ARB · OP/BASE · Across · LayerZero · CCTP) — latency_ratio, backlog_ratio, états BS1/BS2 (Q3 2026)
- [ ] **Phase 3 — ω (flux inter-couches)** : volume bridgé, dépôts/retraits, déséquilibres L1↔L2 — signal de propagation économique (post Phase D, évaluation 2027)
- [ ] Validation seuils L1 restants par backtest (Solana π, Avalanche τ+π)
- [ ] Fix rho_s Arbitrum : utiliser gas_used / block_gas_limit_effectif (~32M)

---

*Version 0.4 — Draft — 17 Mars 2026*
*v0.3 : pivot architectural L1 cause / L2 réponse, introduction couche μ (composition),*
*section 7.4 grille causale, section 9.2b μ distinct de π, section 9.4 classifier (π,μ,σ) cible*
*v0.4 : intégration bridge comme couche de transmission — cadre causal L1→Bridge→L2,*
*section 9.5 BS* opérationnel (Phase 2) + ω flux inter-couches (Phase 3, prospectif),*
*grille causale étendue avec colonne Bridge, section 10 phases 2+3 planifiées*
*Publication effective après validation backtest minimum sur 2 chaînes*
