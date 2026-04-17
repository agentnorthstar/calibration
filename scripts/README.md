# Scripts de calibration — Invarians

Ces scripts permettent de **reproduire indépendamment** les backtests Invarians
depuis les données publiques BigQuery.

---

## Prérequis

```bash
pip install pandas numpy matplotlib
```

Accès BigQuery requis pour l'extraction initiale (compte GCP, dataset public gratuit).

---

## Ethereum — Reproduire le backtest

### Étape 1 — Extraire les données depuis BigQuery

Les données ETH sont extraites depuis `bigquery-public-data.crypto_ethereum.blocks`.
Script d'extraction disponible dans le repo (requête SQL non publiée ici — données déjà fournies).

**Données déjà disponibles :** `eth_invariants_2020_2024_phi280.csv` (34 697 fenêtres, 2020–2024)

### Étape 2 — Backtest + Sweep

```bash
# Backtest principal (classification SxDx sur 4 ans)
python backtest_eth.py

# Sweep threshold_s2 (τ)
python sweep_eth.py

# Sweep threshold_d2 sigma seul (π)
python sweep_eth_d2.py

# Sweep D2 full 3-dimensions (σ × size × tx)
python sweep_eth_d2_full.py
```

**Résultats attendus :**
- `eth_backtest_results.csv` — TPR/FPR par événement
- `eth_sweep_results.csv` — FPR vs threshold_s2 (1.01 → 1.25)
- `eth_sweep_d2_full_results.csv` — grille FPR vs (size_demand, tx_demand, sigma_demand)
- `eth_backtest_chart.png`, `eth_sweep_chart.png` — visualisations

**Résultat validé :** threshold_s2=1.12, D2 (sigma=1.10, size=1.20, tx=1.10), FPR=1.23%, TPR=100% (4/4)

---

## Polygon — Reproduire le backtest

### Extraction BigQuery

```sql
-- extract_pol.sql — bigquery-public-data.crypto_polygon.blocks
-- Fenêtre Φ=1800 blocs (~1h à 2s/bloc)
```

**Données disponibles :** `pol_invariants_2020_2024_phi1800.csv` (2020–2024)

```bash
python backtest_pol.py
python sweep_pol.py
```

**Événements ground truth POL :** Network Halt Mars 2021 · Gas Crisis Mai 2021 · Heimdall/Bor Jan 2023 · Reorg Storm Fév 2023

---

## Solana — Reproduire le backtest τ

### Extraction BigQuery

```sql
-- extract_sol.sql — bigquery-public-data.crypto_solana_mainnet_us.blocks
-- Fenêtre Φ=800 slots (~5.3 min à 0.4s/slot)
-- Note : transaction_count absent de BigQuery Solana — τ uniquement
```

**Données disponibles :** `sol_invariants_2021_2024_phi800.csv` (2021–2024)

```bash
python backtest_sol.py
python sweep_sol.py
```

**Événements ground truth SOL τ :** 4 outages majeurs (Sept 2021 · Jan 2022 · Mai 2022 · Oct 2022)
**Résultat validé :** threshold_s2=1.12, FPR_τ=1.77%, TPR=100% (4/4)

---

## Architecture commune des scripts

Tous les scripts suivent le même protocole :

```
1. Charger les invariants (CSV BigQuery)
2. Calculer EMA fast (α=2/11, ~10h) + EMA slow (α=2/721, ~30j)
3. Calculer ratios : rhythm_ratio, sigma_ratio, size_ratio, tx_ratio
4. Classifier chaque fenêtre : S1D1 | S1D2 | S2D1 | S2D2
5. Confronter aux événements ground truth (TPR / latence)
6. Sweeper les thresholds candidats (FPR vs détection)
7. Exporter résultats CSV + graphiques
```

---

*Scripts créés Mars 2026 — Invarians calibration v0.4*
*Données sources : Google BigQuery public datasets (gratuit avec compte GCP)*
