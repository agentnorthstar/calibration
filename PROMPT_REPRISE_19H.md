# Prompt de reprise — Session 19h00, 17 Avril 2026

---

## Ce qui a été fait aujourd'hui (ne pas refaire)

- `CALIBRATION/publiable/` créé et peuplé — 7 documents + scripts/
- `methodology.md` v0.4 — pipeline OFFLINE/ONLINE + section M1 formalisée
- `backtest_ethereum.md` + `backtest_solana.md` — validés, dans publiable/
- `composite_signal_arbitrum_june2024.md` — case study ARB, dans publiable/
- **Formule M1 confirmée :** `(max_event − p50) / p50 / CV(signal < 1.05)`
  - ETH = 5.07 ✅ | POL = 7.37 ✅
- `AgentNorthStar.com/index.html` mis à jour (ETH 5.05→5.07, POL 8.06→7.37)
- `attestation/index.ts` commentaires M1 mis à jour — **PAS encore déployé**
- `PLANNING_2026.md` mis à jour

---

## 3 tâches ce soir — dans cet ordre

### Tâche 1 — TOIT (utilisateur) : lancer les scripts POL

```bash
cd C:\Users\yoana\.gemini\antigravity\invarians\BIGDATA
python backtest_pol.py
python sweep_pol.py
python sweep_pol_d2.py
```

Résultats attendus dans BIGDATA/ :
- `pol_backtest_results.csv`
- `pol_sweep_results.csv`
- `pol_sweep_d2_results.csv`
- `pol_backtest_chart.png`

→ Coller les résultats CSV ou le résumé dans le chat
→ Je crée `CALIBRATION/publiable/backtest_polygon.md` depuis ces résultats

---

### Tâche 2 — Déployer attestation/index.ts sur Supabase

Fichier modifié : `invarians-oracle/supabase/functions/attestation/index.ts`
Changements : commentaires M1 uniquement (ETH 5.05→5.07, POL 8.06→7.37)
**Aucun changement fonctionnel — déploiement sans risque**

```bash
cd invarians-oracle
supabase functions deploy attestation
```

Vérification post-déploiement : appel API `/execution-context?l1=ethereum` → confirmer réponse normale

---

### Tâche 3 — Pusher publiable/ sur GitHub

Repo cible : à confirmer (nouveau repo `invarians-calibration` ou dossier dans repo existant)

Contenu de `CALIBRATION/publiable/` :
```
README.md
methodology.md
backtest_ethereum.md
backtest_solana.md
backtest_polygon.md         ← créé après Tâche 1
composite_signal_arbitrum_june2024.md
calibration_log.md
protocol_watch.md
scripts/
  README.md
  backtest_eth.py + sweeps ETH
  backtest_pol.py + sweep_pol.py
  backtest_sol.py + sweep_sol.py
  extract_pol.sql + extract_sol.sql
  h5_composite_demo.py
```

**Question à trancher avant push :**
- Repo séparé `InvariansLabs/invarians-calibration` (propre, citable) ?
- Ou dossier `calibration/` dans un repo existant ?

---

## Contexte clé à garder en tête

- `calibrage.md` = audit interne, jamais publié
- `publiable/` = ce qui va sur ANS + GitHub
- Les seuils L2 (BASE=1.20, OP=1.12) sont en prod mais NOT publiés — calibration event-based Phase D pending
- M1 formule : `(max_event − p50) / p50 / CV(signal < 1.05)` — validée sur ETH
- Prochaine tâche technique : epsilon(t) / deformation_score → 2026-04-18
- Phase 2C Bridge → 2026-04-22

---

*Créé le 17 Avril 2026 — fin de session matin*
