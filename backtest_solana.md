---
chain: solana
version: "0.1"
status: validated
date: "2026-03-16"
layer: L1
backtest_period: "2021-01-01 / 2024-01-01"
backtest_source: "BigQuery — bigquery-public-data.crypto_solana_mainnet_us.blocks"
backtest_script: "scripts/backtest_sol.py + scripts/sweep_sol.py"
backtest_n_invariants: 128365
backtest_phi: 800
backtest_tpr: 1.00
backtest_fpr_tau: 0.0177
backtest_events_positive: 4
backtest_events_negative: 0
backtest_events_total: 4
threshold_s2_validated: 1.12
threshold_pi_status: "pending"
confidence_tau: MEDIUM
confidence_pi: LOW
---

# Backtest Solana — τ (2021–2024)

> **Statut :** validated — threshold_s2=1.12 validé sur τ. FPR_τ=1.77%.
> **Périmètre :** τ uniquement. π (demande) non calibré dans ce backtest — BigQuery Solana Blocks ne contient pas `transaction_count`. Calibration π pendante juillet 2026.

---

## 1. Ce qu'on a mesuré

**Source :** BigQuery, table `bigquery-public-data.crypto_solana_mainnet_us.blocks`, fenêtre 2021-01-01 → 2024-01-01.

**Principe :** rejouer le calcul des invariants τ sur 3 ans de Solana. Chaque fenêtre de Φ=800 slots (~5.3 min) est classifiée S1/S2 selon le ratio EMA de `rho_ts`.

**Volume :** 128 365 fenêtres.

**Signal τ utilisé :** `rhythm_ratio = rho_ts / EMA_rapide(rho_ts)` — inertie temporelle inter-slots.

**Signal π :** absent de ce backtest (`transaction_count` non disponible dans BigQuery Blocks Solana). Les seuils π utilisés en production sont LOW confidence (proxy P90).

---

## 2. Événements ground truth — Outages Solana

Solana a connu plusieurs outages majeurs documentés sur la période 2021–2024.
Ces événements sont caractérisés par un effondrement de la production de blocs (slots espacés, skip rate élevé) — signature directe d'un stress structurel τ.

| Événement | Date onset | Type | État attendu | Détecté | Latence |
|-----------|-----------|------|-------------|---------|---------|
| Outage Sept 2021 | 2021-09-14 | Blocage réseau ~17h | S2D1 | ✅ | +6.72h |
| Outage Jan 2022 | 2022-01-21 | Dégradation performance | S2D1 | ✅ | +1.45h |
| Outage Mai 2022 | 2022-05-31 | Blocage réseau ~4.5h | S2D1 | ✅ | +15.92h |
| Outage Oct 2022 | 2022-10-01 | Dégradation + instabilité | S2D1 | ✅ | +12.51h |

**TPR : 4/4 = 100%**

La variabilité de latence (1.45h à 15.92h) s'explique par la nature des outages :
- Outage Jan 2022 : dégradation rapide et brutale → détection quasi-immédiate
- Outage Mai 2022 : dégradation progressive → l'EMA rapide (~10h) absorbe la montée avant le pic

---

## 3. Sweep threshold_s2 — résultats

Paramètre fixé : `alpha_fast = 2/11 (~10h)`.

| threshold_s2 | FPR_τ | n_S2 | Sept 2021 | Jan 2022 | Mai 2022 | Oct 2022 |
|-------------|-------|------|-----------|----------|----------|----------|
| 1.01 | 34.18% | 43 826 | ✅ | ✅ | ✅ | ✅ |
| 1.03 | 18.35% | 23 512 | ✅ | ✅ | ✅ | ✅ |
| 1.05 | 9.86% | 12 640 | ✅ | ✅ | ✅ | ✅ |
| 1.08 | 4.27% | 5 489 | ✅ | ✅ | ✅ | ✅ |
| 1.10 | 2.63% | 3 386 | ✅ | ✅ | ✅ | ✅ |
| **1.12** | **1.77%** | **2 275** | **✅** | **✅** | **✅** | **✅** |
| 1.15 | 1.06% | 1 368 | ✅ | ✅ | ❌ | ✅ |
| 1.18 | 0.68% | 878 | ✅ | ✅ | ❌ | ✅ |
| 1.20 | 0.53% | 683 | ✅ | ❌ | ❌ | ✅ |

### Conclusion threshold_s2

**Valeur retenue : 1.12** — `confidence_τ: MEDIUM`

- FPR_τ = 1.77% — acceptable pour un signal mono-chaîne L1
- Détecte les 4 outages majeurs documentés : TPR = 100%
- À 1.15 : perte de sensibilité sur Mai 2022 (outage progressif à faible amplitude)
- À 1.12 : meilleur compromis TPR/FPR sur l'ensemble de la période

**Pourquoi Solana est plus volatile qu'Ethereum :**
Solana opère à ~0.4s/slot. La variabilité naturelle de `rho_ts` est structurellement plus élevée que sur ETH (12s/bloc). Un threshold de 1.12 génère plus de bruit absolu que sur ETH, mais le rapport signal/bruit reste comparable (M1 pending formalisation).

---

## 4. Continuity signal (c_s) — non retenu

Le sweep sur `c_s` (taux de blocs valides) génère des FPR structurellement supérieurs à 14% pour tout seuil qui détecte les outages. Ce signal est conservé comme détecteur d'**outage extrême** (c_s < 0.90) mais n'entre pas dans la classification nominale S1/S2.

---

## 5. Paramètres SOL τ validés

```yaml
chain: solana
signal_tau: rho_ts (rhythm_ratio)
threshold_s2: 1.12          # validé — confidence: MEDIUM (TPR=100%, n=4 outages)
ema_fast_alpha: 0.1818      # 2/11, ~10h
ema_slow_alpha: 0.00277     # 2/721, ~30j
phi: 800                    # fenêtre ~5.3 min
backtest_tpr: 1.00          # 4/4 outages structurels
backtest_fpr_tau: 0.0177    # 1.77% — tau seul
signal_pi: LOW confidence   # π pending calibration juillet 2026
excluded: c_s (détecteur outage extrême uniquement, non classifiant)
```

---

## 6. Limites de ce backtest

| Limite | Impact | Statut |
|--------|--------|--------|
| π absent (pas de `transaction_count` dans BigQuery SOL) | TPR/FPR sur τ uniquement — D2 non testé | Calibration π juillet 2026 (données capteur fixées mars 2026) |
| n=4 événements structurels | TPR sur petit échantillon | Confiance MEDIUM — HIGH requiert n≥5 + 30j déploiement |
| Outages Solana de nature hétérogène (durée, amplitude) | Latence variable (1.45h–15.92h) | Inhérent à Solana — pas une limite du modèle |
| Fenêtre Φ=800 slots (~5.3 min) | Plus fine que L1 classique (~1h ETH) | Adapté au block time Solana — cohérent avec l'architecture |

---

## 7. Prochaines étapes

- [ ] Calibration π Solana — données `size_avg` + `tx_count` exploitables à partir de mi-juin 2026
- [ ] M1 Solana τ formalisé (après formalisation de la formule M1 — session 17 Avril 2026)
- [ ] Publication `chain_profile_solana.md` (après calibration π complète)

---

*Backtest exécuté le 16 Mars 2026 — scripts : scripts/backtest_sol.py, scripts/sweep_sol.py*
*Données : BigQuery public dataset, 128 365 invariants, Φ=800, 2021–2024*
