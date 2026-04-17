# Invarians — Protocol Watch

**Format :** évolutions de protocoles externes vérifiées sur sources primaires, classées par impact sur la calibration Invarians.
**Règle :** toute entrée doit être sourcée sur ethereum.org, le GitHub EIP tracker, ou la documentation officielle du projet. Aucune source tierce.

---

## EIP-4844 — Proto-Danksharding

**Statut :** Final — déployé mainnet mars 2024
**Source :** github.com/ethereum/EIPs/blob/master/EIPS/eip-4844.md

**Description technique :**
Introduit un nouveau type de transaction ("blob-carrying transaction") avec un marché de gas distinct (blob gas) pour le posting de données L2 → L1. Les blobs sont temporaires (environ 18 jours) et moins chers que le calldata.

**Impact sur Invarians :**

La pression économique π sur L1 était historiquement corrélée à l'activité L2 via le calldata posting. Depuis EIP-4844, les L2 postent leurs données en blobs à un coût structurellement inférieur et sur un marché distinct. Conséquence : π sur L1 est partiellement découplé de l'activité L2.

Les baselines π calculées sur des données antérieures à mars 2024 intègrent un niveau de pression L1 structurellement plus élevé qu'il ne l'est désormais. Tout backtest utilisant des données pre-4844 pour calibrer les seuils S1D2/S2D2 doit en tenir compte.

**Action requise :**
- Vérifier que les baselines π ETH sont calculées sur des données post-mars 2024 uniquement
- Documenter explicitement la date de rupture dans les backtests ETH
- Signaler dans tout pitch ou publication que les comparaisons pre/post-4844 ne sont pas directement équivalentes

**Priorité :** Haute — impacte directement la fiabilité des baselines π ETH

---

## EIP-7702 — Account Abstraction pour EOA (Pectra)

**Statut :** Final — déployé mainnet mai 2025
**Source :** github.com/ethereum/EIPs/blob/master/EIPS/eip-7702.md

**Description technique :**
Permet à un EOA de déléguer temporairement son exécution à un smart contract via une transaction de type SET_CODE. Utilisé notamment pour les session keys dans les pipelines agentiques.

**Impact sur Invarians :**

Augmentation structurelle du volume de transactions agentiques sur L1 et L2. Les agents AI peuvent désormais exécuter des stratégies multi-étapes de manière non-custodiale. La pression π sur les chaînes supportant EIP-7702 sera progressivement modifiée par ce nouveau type de trafic.

C'est un accélérateur de la thèse Invarians : plus d'agents actifs = signal d'exécution context plus fréquemment sollicité.

**Action requise :**
- Surveiller l'évolution des baselines π ETH post-mai 2025
- Identifier si les UserOps (EIP-4337) et les SET_CODE (EIP-7702) introduisent des patterns de congestion distincts dans les métriques σ
- Aucune recalibration immédiate requise — surveiller sur 90 jours

**Priorité :** Moyenne — opportunité, pas contrainte

---

## EIP-7781 — Réduction du slot time (en cours de spécification)

**Statut :** Draft
**Source :** github.com/ethereum/EIPs/issues — à confirmer sur EIP tracker officiel avant toute citation publique

**Description technique :**
Propose de réduire le slot Ethereum de 12 secondes à 8 secondes.

**Impact sur Invarians :**

La fenêtre structurelle Invarians est exprimée en nombre de blocs (~280 blocs pour ETH ≈ 1h). Si le slot passe à 8s, 280 blocs représentent ~37 minutes au lieu de ~56 minutes. La fenêtre temporelle se comprime.

Options à évaluer au moment du déploiement :
- Ajuster le nombre de blocs pour maintenir une fenêtre ~1h (280 → 450 blocs)
- Ou accepter la fenêtre plus courte et recalibrer les baselines

**Action requise :**
- Surveiller le statut de cette EIP — ne rien changer tant qu'elle n'est pas en "Last Call"
- Préparer le script de recalibration fenêtre à l'avance

**Priorité :** Basse à ce stade — à réactiver quand statut = Last Call

---

## Shared Sequencers — Espresso Systems, Astria

**Statut :** Testnets actifs, intégrations L2 en cours (avril 2026)
**Sources :** docs.espressosys.com · astria.org

**Description technique :**
Un sequencer partagé gère l'ordering de transactions pour plusieurs L2 simultanément, permettant l'interopérabilité inter-L2 sans bridge.

**Impact sur Invarians :**

Si plusieurs L2 monitorés par Invarians partagent un sequencer commun (ex: Espresso), un incident sur ce sequencer produit une corrélation soudaine entre chaînes habituellement indépendantes. Risque de faux signal S2 multi-chaînes simultané.

Sans identification du sequencer sous-jacent, Invarians peut interpréter une panne d'infrastructure tierce comme une saturation native du réseau.

**Action requise :**
- Identifier le sequencer sous-jacent de chaque L2 monitoré (natif vs partagé)
- Envisager un champ `sequencer_type: native | shared` dans la matrice régimes
- Documenter les L2 sur Espresso/Astria dès qu'ils passent en mainnet

**Priorité :** Moyenne — devient haute si un L2 monitoré migre vers shared sequencer

---

## EIP-4337 — Account Abstraction via Bundlers

**Statut :** Final — déployé mainnet mars 2023
**Source :** github.com/ethereum/EIPs/blob/master/EIPS/eip-4337.md

**Description technique :**
Introduit les UserOperations traitées par des bundlers — une couche d'agrégation entre les wallets smart contract et le mempool L1.

**Impact sur Invarians :**

Les bundlers ajoutent une latence et une compétition spécifiques qui n'existaient pas avec les transactions EOA classiques. La pression π peut présenter des patterns atypiques lors des pics de volume UserOps (ex: drops NFT, liquidations DeFi via smart wallets).

**Action requise :**
- Surveiller si les baselines π ETH présentent des signatures distinctes lors des pics UserOps connus
- Pas de recalibration immédiate requise

**Priorité :** Basse — surveillance passive

---

*Dernière mise à jour : 2026-04-11*
*Règle de mise à jour : toute nouvelle entrée doit citer une source primaire vérifiée.*
