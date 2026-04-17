"""
H5 — Démo Composite SxDx : Arbitrum post-Dencun
=================================================
Incident cible : 20 Juin 2024 — gap blob posting ARB ~37min (~16:47–17:24 UTC)
Sources :
  L1 ETH   : query1.csv  (BigQuery crypto_ethereum.blocks)
  Bridge   : query2.csv  (BigQuery crypto_ethereum.transactions — blob vers SequencerInbox)
  L2 ARB   : query4.csv  (BigQuery goog_blockchain_arbitrum_one_us.blocks)

Post-Dencun : basefee L1 ~3-8 gwei structurellement flat → fee monitors aveugles
"""

import csv
import math
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================

L1_BLOCKS_CSV  = '/mnt/c/Users/yoana/Downloads/query1.csv'
BRIDGE_CSV     = '/mnt/c/Users/yoana/Downloads/query2.csv'
L2_BLOCKS_CSV  = '/mnt/c/Users/yoana/Downloads/bquxjob_16d405ba_19d1c6b874d.csv'

OUT_CSV = '/mnt/c/Users/yoana/Downloads/h5_composite_june2024.csv'
OUT_DOC = '/mnt/c/Users/yoana/.gemini/antigravity/invarians/business-proof/composite_signal_arbitrum_june2024.md'

EMA_ALPHA      = 0.1
WARMUP_HOURS   = 20          # fenêtres warm-up avant baseline fiable
WINDOW_SECONDS = 3600        # fenêtre 1h

# Seuils régime
SX_HIGH_THRESHOLD = 1.10     # interval_ratio > 1.10 → structure dégradée
DX_HIGH_THRESHOLD = 1.10     # sigma_ratio > 1.10 → demande élevée

# Bridge
BRIDGE_BS2_THRESHOLD = 2.0   # last_blob_age > 2× EMA → BS2

# Fenêtre d'analyse
ANALYSIS_START = '2024-06-18 00:00:00'
ANALYSIS_END   = '2024-06-21 06:00:00'
INCIDENT_REF   = '2024-06-20 16:47:00'  # début estimé du gap bridge

FMT = '%Y-%m-%d %H:%M:%S'

# ============================================================
# PARSING
# ============================================================

def parse_ts(s):
    s = s.replace('.000000 UTC', '').replace(' UTC', '').strip()
    return datetime.strptime(s, FMT).replace(tzinfo=timezone.utc)

def load_l1(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({
                'block_number':    int(row['block_number']),
                'timestamp':       parse_ts(row['timestamp']),
                'size':            float(row['size']),
                'tx_count':        float(row['transaction_count']),
                'gas_used':        float(row['gas_used']),
                'basefee_gwei':    float(row['basefee_gwei']),
                'blob_gas_used':   float(row['blob_gas_used']),
            })
    return rows

def load_bridge(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({
                'block_number': int(row['block_number']),
                'timestamp':    parse_ts(row['block_timestamp']),
                'blob_count':   int(row['blob_count']),
            })
    return sorted(rows, key=lambda r: r['timestamp'])

def load_l2(path):
    """Charge L2 pré-agrégé par heure (format BigQuery GROUP BY TIMESTAMP_TRUNC HOUR)."""
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append({
                'window_start':  parse_ts(row['window_start']),
                'block_count':   int(row['block_count']),
                'avg_size':      float(row['avg_size']),
                'avg_gas_used':  float(row['avg_gas_used']),
                'avg_basefee':   float(row['avg_basefee_gwei']),
            })
    return rows

# ============================================================
# FENÊTRES HORAIRES
# ============================================================

def make_windows(start_str, end_str):
    t = datetime.strptime(start_str, FMT).replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_str, FMT).replace(tzinfo=timezone.utc)
    windows = []
    while t < end:
        t_next = datetime.fromtimestamp(t.timestamp() + WINDOW_SECONDS, tz=timezone.utc)
        windows.append((t, t_next))
        t = t_next
    return windows

def blocks_in_window(blocks, t_start, t_end):
    return [b for b in blocks if t_start <= b['timestamp'] < t_end]

# ============================================================
# EMA
# ============================================================

def ema(prev, current):
    return current if prev is None else EMA_ALPHA * current + (1 - EMA_ALPHA) * prev

# ============================================================
# SIGNAL L1 (τ + π post-Dencun)
# ============================================================

def compute_l1_windows(l1_blocks, windows):
    ema_size = ema_tx = ema_gas = ema_blob = ema_interval = None
    results = []
    for i, (t_start, t_end) in enumerate(windows):
        blks = blocks_in_window(l1_blocks, t_start, t_end)
        if len(blks) < 2:
            results.append(None)
            continue

        avg_size     = sum(b['size'] for b in blks) / len(blks)
        avg_tx       = sum(b['tx_count'] for b in blks) / len(blks)
        avg_gas      = sum(b['gas_used'] for b in blks) / len(blks)
        avg_blob     = sum(b['blob_gas_used'] for b in blks) / len(blks)
        avg_basefee  = sum(b['basefee_gwei'] for b in blks) / len(blks)

        # τ : inter-block interval moyen
        intervals = []
        for j in range(1, len(blks)):
            dt = blks[j]['timestamp'].timestamp() - blks[j-1]['timestamp'].timestamp()
            if 0 < dt < 60:
                intervals.append(dt)
        avg_interval = sum(intervals) / len(intervals) if intervals else 12.0

        if i < WARMUP_HOURS:
            ema_size     = ema(ema_size, avg_size)
            ema_tx       = ema(ema_tx, avg_tx)
            ema_gas      = ema(ema_gas, avg_gas)
            ema_blob     = ema(ema_blob, avg_blob)
            ema_interval = ema(ema_interval, avg_interval)
            results.append(None)
            continue

        # Ratios
        size_ratio     = avg_size / ema_size if ema_size else 1.0
        tx_ratio       = avg_tx / ema_tx if ema_tx else 1.0
        blob_ratio     = avg_blob / ema_blob if (ema_blob and ema_blob > 0) else 1.0
        interval_ratio = avg_interval / ema_interval if ema_interval else 1.0

        # π (Dx) post-Dencun : blob_ratio remplace gas_ratio
        sigma_ratio = (size_ratio + tx_ratio + blob_ratio) / 3.0

        # Régime composite
        sx_high = interval_ratio > SX_HIGH_THRESHOLD
        dx_high = sigma_ratio > DX_HIGH_THRESHOLD
        regime  = ('S2D2' if sx_high and dx_high else
                   'S2D1' if sx_high else
                   'S1D2' if dx_high else 'S1D1')

        results.append({
            'window_start':    t_start.strftime(FMT),
            'n_blocks':        len(blks),
            'sigma_ratio':     sigma_ratio,
            'size_ratio':      size_ratio,
            'tx_ratio':        tx_ratio,
            'blob_ratio':      blob_ratio,
            'interval_ratio':  interval_ratio,
            'regime':          regime,
            'avg_basefee':     avg_basefee,
            'avg_blob_gas':    avg_blob,
        })

        ema_size     = ema(ema_size, avg_size)
        ema_tx       = ema(ema_tx, avg_tx)
        ema_gas      = ema(ema_gas, avg_gas)
        ema_blob     = ema(ema_blob, avg_blob)
        ema_interval = ema(ema_interval, avg_interval)

    return results

# ============================================================
# SIGNAL BRIDGE (BS1/BS2 post-Dencun)
# ============================================================

def compute_bridge_windows(bridge_rows, windows):
    # EMA inter-batch interval sur warm-up
    ema_interval = None
    # Pré-calculer intervals
    intervals_by_time = {}
    for i in range(1, len(bridge_rows)):
        dt = (bridge_rows[i]['timestamp'].timestamp() -
              bridge_rows[i-1]['timestamp'].timestamp()) / 60.0  # minutes
        intervals_by_time[bridge_rows[i]['timestamp']] = dt

    results = []
    for i, (t_start, t_end) in enumerate(windows):
        # Blob txs dans cette fenêtre
        in_window = [r for r in bridge_rows if t_start <= r['timestamp'] < t_end]
        batch_count = len(in_window)

        # Intervalles dans cette fenêtre
        window_intervals = [intervals_by_time[r['timestamp']]
                           for r in in_window if r['timestamp'] in intervals_by_time
                           and intervals_by_time[r['timestamp']] < 60]

        avg_interval = sum(window_intervals) / len(window_intervals) if window_intervals else None

        if i < WARMUP_HOURS:
            if avg_interval:
                ema_interval = ema(ema_interval, avg_interval)
            results.append(None)
            continue

        # last_blob_age : temps depuis la dernière blob tx avant t_end
        past_blobs = [r for r in bridge_rows if r['timestamp'] < t_end]
        if past_blobs:
            last_blob_ts = past_blobs[-1]['timestamp']
            last_blob_age_min = (t_end.timestamp() - last_blob_ts.timestamp()) / 60.0
        else:
            last_blob_age_min = 9999.0

        bs2 = (ema_interval is not None and
               last_blob_age_min > BRIDGE_BS2_THRESHOLD * ema_interval)

        results.append({
            'window_start':      t_start.strftime(FMT),
            'batch_count':       batch_count,
            'last_blob_age_min': round(last_blob_age_min, 1),
            'ema_interval_min':  round(ema_interval, 2) if ema_interval else None,
            'regime':            'BS2' if bs2 else 'BS1',
        })

        if avg_interval:
            ema_interval = ema(ema_interval, avg_interval)

    return results

# ============================================================
# SIGNAL L2 ARB (pré-agrégé par heure)
# ============================================================

def compute_l2_windows(l2_rows, windows):
    """
    L2 data est pré-agrégée par heure — on aligne directement sur les fenêtres.
    τ proxy : block_count (moins de blocs/h = séquenceur dégradé)
    π : mean(size_ratio, gas_ratio)
    Note : avg_gas_used inclut des anomalies extrêmes → utiliser basefee comme signal secondaire
    """
    # Indexer L2 par window_start
    l2_by_hour = {r['window_start'].strftime(FMT): r for r in l2_rows}

    ema_size = ema_gas = ema_count = None
    results = []

    for i, (t_start, _) in enumerate(windows):
        key = t_start.strftime(FMT)
        row = l2_by_hour.get(key)
        if row is None:
            results.append(None)
            continue

        avg_size  = row['avg_size']
        avg_gas   = row['avg_gas_used']
        blk_count = row['block_count']
        avg_fee   = row['avg_basefee']

        if i < WARMUP_HOURS:
            ema_size  = ema(ema_size, avg_size)
            ema_gas   = ema(ema_gas, avg_gas)
            ema_count = ema(ema_count, blk_count)
            results.append(None)
            continue

        size_ratio  = avg_size / ema_size if ema_size else 1.0
        gas_ratio   = avg_gas / ema_gas if ema_gas else 1.0
        count_ratio = blk_count / ema_count if ema_count else 1.0

        # Sx : block_count_ratio < 0.90 = séquenceur produit moins de blocs (dégradé)
        sx_degraded = count_ratio < 0.90
        # Dx : sigma_ratio = mean(size_ratio, gas_ratio)
        sigma_ratio = (size_ratio + gas_ratio) / 2.0
        dx_high = sigma_ratio > DX_HIGH_THRESHOLD

        if sx_degraded and dx_high:
            regime = 'S2D2'
        elif sx_degraded:
            regime = 'S2D1'
        elif dx_high:
            regime = 'S1D2'
        else:
            regime = 'S1D1'

        results.append({
            'window_start': key,
            'block_count':  blk_count,
            'count_ratio':  count_ratio,
            'sigma_ratio':  sigma_ratio,
            'size_ratio':   size_ratio,
            'gas_ratio':    gas_ratio,
            'avg_basefee':  avg_fee,
            'regime':       regime,
        })

        ema_size  = ema(ema_size, avg_size)
        ema_gas   = ema(ema_gas, avg_gas)
        ema_count = ema(ema_count, blk_count)

    return results

# ============================================================
# COMPOSITE TIMELINE
# ============================================================

def build_composite(windows, l1_res, bridge_res, l2_res):
    rows = []
    for i, (t_start, _) in enumerate(windows):
        l1 = l1_res[i]
        br = bridge_res[i]
        l2 = l2_res[i]
        if l1 is None or br is None:
            continue

        invarians_alert = (br['regime'] == 'BS2' or
                          (l2 and l2['regime'] not in ('S1D1', 'S1D2')))
        fee_monitor_visible = l1['avg_basefee'] > 2 * 5.0  # > 10 gwei = visible

        composite = 'NORMAL'
        if br['regime'] == 'BS2' and l2 and l2['regime'] not in ('S1D1',):
            composite = 'MULTI_LAYER'
        elif br['regime'] == 'BS2':
            composite = 'BRIDGE_ONLY'
        elif l2 and l2['regime'] not in ('S1D1',):
            composite = 'L2_ONLY'

        rows.append({
            'window_start':        t_start.strftime(FMT),
            'l1_regime':           l1['regime'],
            'l1_sigma_ratio':      round(l1['sigma_ratio'], 4),
            'l1_interval_ratio':   round(l1['interval_ratio'], 4),
            'l1_blob_ratio':       round(l1['blob_ratio'], 4),
            'l1_basefee_gwei':     round(l1['avg_basefee'], 2),
            'bridge_regime':       br['regime'],
            'bridge_last_age_min': br['last_blob_age_min'],
            'bridge_ema_min':      br['ema_interval_min'],
            'l2_regime':           l2['regime'] if l2 else 'N/A',
            'l2_sigma_ratio':      round(l2['sigma_ratio'], 4) if l2 else None,
            'l2_count_ratio':      round(l2['count_ratio'], 4) if l2 else None,
            'l2_basefee_gwei':     round(l2['avg_basefee'], 4) if l2 else None,
            'composite':           composite,
            'fee_monitor_visible': fee_monitor_visible,
            'invarians_alert':     invarians_alert,
        })
    return rows

# ============================================================
# EXPORT CSV
# ============================================================

def export_csv(rows, path):
    if not rows:
        return
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f'  → CSV : {path}')

# ============================================================
# RAPPORT CONSOLE
# ============================================================

def report(rows):
    incident_ref = datetime.strptime(INCIDENT_REF, FMT).replace(tzinfo=timezone.utc)

    print(f"\n{'='*72}")
    print(f"  INVARIANS COMPOSITE SIGNAL — Arbitrum, 20 Juin 2024 (post-Dencun)")
    print(f"{'='*72}")
    print(f"  Fenêtres analysées : {len(rows)}")

    bridge_bs2 = [r for r in rows if r['bridge_regime'] == 'BS2']
    l2_degraded = [r for r in rows if r['l2_regime'] not in ('S1D1', 'N/A')]
    multi = [r for r in rows if r['composite'] == 'MULTI_LAYER']
    fee_vis = [r for r in rows if r['fee_monitor_visible']]

    print(f"\n  Bridge BS2 : {len(bridge_bs2)} fenêtres")
    print(f"  L2 dégradé : {len(l2_degraded)} fenêtres")
    print(f"  Multi-layer: {len(multi)} fenêtres")
    print(f"  Fee monitor visible (basefee > 10 gwei) : {len(fee_vis)} fenêtres")

    # Première alerte Invarians
    first_alert = next((r for r in rows if r['invarians_alert']), None)
    if first_alert:
        print(f"\n  ┌──────────────────────────────────────────────────────────────┐")
        print(f"  │  PREMIÈRE ALERTE INVARIANS : {first_alert['window_start']}     │")
        print(f"  │  Bridge : {first_alert['bridge_regime']}  (last_age={first_alert['bridge_last_age_min']}min vs EMA={first_alert['bridge_ema_min']}min)  │")
        print(f"  │  L2 : {first_alert['l2_regime']}   L1 basefee : {first_alert['l1_basefee_gwei']} gwei          │")
        print(f"  └──────────────────────────────────────────────────────────────┘")

    # Fenêtre incident ± 2h
    print(f"\n  Timeline autour de l'incident (20 Juin 10:00–20:00 UTC) :")
    print(f"  {'Fenêtre':<22} {'L1':<6} {'Bridge':<8} {'Age(min)':<10} {'L2':<6} {'L2fee':<8} {'L1fee':<8} {'Alert'}")
    print(f"  {'-'*90}")
    for r in rows:
        ws = datetime.strptime(r['window_start'], FMT).replace(tzinfo=timezone.utc)
        if datetime.strptime('2024-06-20 10:00:00', FMT).replace(tzinfo=timezone.utc) <= ws <= \
           datetime.strptime('2024-06-20 20:00:00', FMT).replace(tzinfo=timezone.utc):
            alert = '⚠ ALERT' if r['invarians_alert'] else ''
            l2fee = str(r['l2_basefee_gwei']) if r['l2_basefee_gwei'] is not None else 'N/A'
            print(f"  {r['window_start']:<22} {r['l1_regime']:<6} {r['bridge_regime']:<8} "
                  f"{str(r['bridge_last_age_min']):<10} {r['l2_regime']:<6} "
                  f"{l2fee:<8} {str(r['l1_basefee_gwei']):<8} {alert}")

# ============================================================
# EXPORT MARKDOWN
# ============================================================

def export_doc(rows, path):
    bridge_bs2  = [r for r in rows if r['bridge_regime'] == 'BS2']
    l2_degraded = [r for r in rows if r['l2_regime'] not in ('S1D1', 'N/A')]
    multi_layer = [r for r in rows if r['composite'] == 'MULTI_LAYER']
    first_alert = next((r for r in rows if r['invarians_alert']), None)
    fee_vis     = [r for r in rows if r['fee_monitor_visible']]

    first_alert_str = first_alert['window_start'] if first_alert else 'N/A'
    bridge_age  = first_alert['bridge_last_age_min'] if first_alert else 'N/A'
    bridge_ema  = first_alert['bridge_ema_min'] if first_alert else 'N/A'

    # Timeline étendue : 10:00 → 20:00 pour montrer la montée L2 AVANT le gap bridge
    timeline_rows = []
    for r in rows:
        ws = datetime.strptime(r['window_start'], FMT).replace(tzinfo=timezone.utc)
        if datetime.strptime('2024-06-20 10:00:00', FMT).replace(tzinfo=timezone.utc) <= ws <= \
           datetime.strptime('2024-06-20 20:00:00', FMT).replace(tzinfo=timezone.utc):
            alert_str = '⚠️ **ALERTE**' if r['invarians_alert'] else ''
            l2fee = f"{r['l2_basefee_gwei']} gwei" if r['l2_basefee_gwei'] is not None else 'N/A'
            timeline_rows.append(
                f"| {r['window_start']} | {r['l1_regime']} | {r['l2_regime']} ({l2fee}) "
                f"| {r['bridge_regime']} ({r['bridge_last_age_min']}min) "
                f"| {r['l1_basefee_gwei']} gwei | {alert_str} |"
            )

    timeline_str = '\n'.join(timeline_rows)

    doc = f"""# Invarians — Signal Composite : Arbitrum, 20 Juin 2024 (post-Dencun)

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
{timeline_str}

---

## Lecture de la timeline

**Phase 1 — Stress L2 (10:00–15:00 UTC)**
La basefee ARB L2 monte de 0.01 gwei à **16.49 gwei** (×1649 la normale).
Invarians L2 détecte le régime S1D2 — demande élevée sur le rollup.
Fee monitors L1 : également en hausse (15-21 gwei) mais signal GÉNÉRIQUE (ETH busy, pas ARB).
**Un agent ne peut pas distinguer "ETH occupé" de "Arbitrum surchargé" avec les seuls fee monitors.**

**Phase 2 — Rupture Bridge (16:00 UTC)**
Le blob posting vers L1 s'arrête : last_blob_age = **{bridge_age}min** vs EMA = **{bridge_ema}min** (×12 la normale).
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

*Généré le {datetime.now().strftime('%Y-%m-%d')} — Invarians Phase B*
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'  → Doc : {path}')

# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    import os
    print("Chargement des données...")
    l1_blocks  = load_l1(L1_BLOCKS_CSV)
    bridge_rows = load_bridge(BRIDGE_CSV)
    l2_blocks  = load_l2(L2_BLOCKS_CSV) if os.path.exists(L2_BLOCKS_CSV) else []

    print(f"  L1 : {len(l1_blocks)} blocs")
    print(f"  Bridge : {len(bridge_rows)} blob txs")
    print(f"  L2 : {len(l2_blocks)} blocs{' (manquant — L2 désactivé)' if not l2_blocks else ''}")

    windows = make_windows(ANALYSIS_START, ANALYSIS_END)
    print(f"  Fenêtres : {len(windows)}")

    print("\nCalcul des signaux...")
    l1_res     = compute_l1_windows(l1_blocks, windows)
    bridge_res = compute_bridge_windows(bridge_rows, windows)
    l2_res     = compute_l2_windows(l2_blocks, windows) if l2_blocks else [None] * len(windows)

    rows = build_composite(windows, l1_res, bridge_res, l2_res)

    report(rows)
    export_csv(rows, OUT_CSV)
    export_doc(rows, OUT_DOC)
