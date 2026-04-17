---
title: "Invarians — Publications de calibration"
version: "0.1"
date: "2026-04-17"
audience: [ai-agents, developers, researchers]
---

# Invarians — Publications de calibration

> **AgentNorthStar.com** — registre public de calibration Invarians
> Ces documents constituent la spécification technique vérifiable du système de mesure.

---

## Lire dans cet ordre

### 1. Comprendre la méthode — `methodology.md`

Point d'entrée pour tout lecteur. Couvre :
- Principe fondamental : régime structurel vs signal instantané
- Architecture du signal (τ structure, π demande)
- Pipeline complet OFFLINE/ONLINE (section 4.5)
- Paramètres per-chaîne + état de calibration
- M1 Metric Stability Score (section 10)
- L2 Rollups : pourquoi les signaux diffèrent
- Métriques complètes par couche (L1, L2 π/μ/σ, Bridge)

**Audience :** développeurs intégrant l'API, agents IA consommant les attestations, chercheurs auditant la méthode.

### 2. Résultats de validation — `backtest_ethereum.md`

Backtest BigQuery 2020–2024 sur 34 697 fenêtres Ethereum.
- Sweeps threshold_s2 et threshold_d2
- Événements ground truth : The Merge, Shanghai Upgrade, DeFi Summer, NFT Mania
- TPR=100% (4/4), FPR τ+π=1.23%
- Paramètres ETH finaux validés (confidence: MEDIUM)

### 3. Journal d'incidents — `calibration_log.md`

Historique immuable de toutes les décisions de calibration (resets EMA, corrections bugs, choix méthodologiques). Référence d'audit.

### 4. Suivi protocoles — `protocol_watch.md`

Impact des upgrades blockchain (EIP-4844, EIP-7702, EIP-7781, Shared Sequencers) sur la calibration Invarians. Mis à jour à chaque évolution protocolaire significative.

---

## Index

| Fichier | Statut | Date | Description |
|---------|--------|------|-------------|
| `methodology.md` | 🟡 draft | 2026-04-17 | Méthode complète — pipeline, signaux, calibration, M1 |
| `backtest_ethereum.md` | ✅ validated | 2026-03-16 | Backtest ETH 2020–2024 — TPR=100%, FPR τ+π=1.23% (4/4 événements) |
| `backtest_solana.md` | ✅ validated | 2026-03-16 | Backtest SOL τ 2021–2024 — TPR=100%, FPR_τ=1.77% (4/4 outages) · π pending |
| `calibration_log.md` | 🟡 active | 2026-04-16 | Journal incidents + décisions — 16 entrées |
| `protocol_watch.md` | 🟡 active | 2026-04-11 | Suivi EIPs et upgrades — 5 entrées |
| `composite_signal_arbitrum_june2024.md` | ✅ validated | 2026-04-03 | Case study ARB 20 juin 2024 — L2:S1D2 + Bridge:BS2 invisible aux fee monitors |
| `scripts/` | ✅ reproductible | 2026-03-16 | Scripts Python + SQL BigQuery — ETH, POL, SOL + h5_composite_demo.py (reproductibles indépendamment) |
| `backtest_polygon.md` | ✅ validated | 2026-04-17 | Backtest POL 2020–2024 — TPR=100% (4/4), FPR=11.75% (élevé, documenté), M1=7.37 |
| `chain_profile_ethereum.md` | ⏳ pending | — | Profil ETH complet (pending M1 formalisé) |
| `chain_profile_solana.md` | ⏳ pending | — | Profil SOL (pending calibration π juillet 2026) |
| `chain_profile_polygon.md` | ⏳ pending | — | Profil POL (pending exécution backtest) |

**Statuts :**
- ✅ validated — publié, données validées par backtest
- 🟡 active/draft — en cours, partiellement publié
- ⏳ pending — contenu disponible, publication en attente

---

## Ce qui n'est PAS ici

- Code source → GitHub [invarians-oracle]
- API documentation → docs.invarianslabs.com
- Valeurs M1 en temps réel → AgentNorthStar.com

---

*Invarians mesure dans quel régime structurel une blockchain opère.*
*Ces publications permettent d'auditer la méthode indépendamment.*

*Créé le 17 Avril 2026*
