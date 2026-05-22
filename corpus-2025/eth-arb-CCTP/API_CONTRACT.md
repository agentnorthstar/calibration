# v2.0 API Contract Reference

This document maps the columns used in the analysis to the production v2.0 API output, so a reader can verify that the analysis uses only observables that the public API exposes.

## API endpoint

Primary endpoint:

```
GET https://api.invarians.com/v2/panel
Authorization: Bearer inv_...
```

Optional query parameters:

- `?include=core` (default): returns regime + status + Delta composite (axis-level `drift` block) per chain, BS1/BS2 per bridge.
- `?include=diagnostic`: adds the full Delta per-metric layer (`ratio_long`, `shift`, `shift_delta`, `shift_magnitude_delta`).
- `?include=full`: adds extended fields.

Response is JSON with HMAC SHA-256 signature in the header for integrity verification.

Verification endpoint:

```
POST https://api.invarians.com/v2/verify
```

Returns the canonical payload and verifies the signature against the published key.

## Reference implementations

- API service: Supabase Edge Functions (TypeScript on Deno), reached through the Cloudflare Worker proxy at `https://api.invarians.com`. The server-side source is not publicly distributed at this time. The API contract is fully documented at `https://invarians.com/developers.html` and the verification flow is reproducible from any client.
- Python SDK: https://pypi.org/project/invarians/ (open-source on PyPI).

## Endpoint behavior covered by this analysis

The analysis reconstructs the equivalent of the `?include=diagnostic` panel output, applied retrospectively to 2025 hours via BigQuery-derived chain data. The reconstruction matches the production output one-to-one except for one observable (beacon participation, see `LIMITATIONS.md`).

## Signed execution context wrapper

The entire panel response is wrapped in a `signed_execution_context` envelope with four fields, exposing Primitive 1 (Attestation):

```jsonc
{
  "signed_execution_context": {
    "payload_hash": "0x...",        // SHA-256 of canonical JSON of the panel
    "signature":    "hmac-sha256:...", // HMAC SHA-256 over payload_hash
    "key_id":       "invarians-v1",    // identifier of the verification key
    "anchor":       null              // null for the panel; populated for per-message CCTP/CCIP attestations
  },
  "panel": { ... }
}
```

Verification:
- `POST /v2/verify` accepts the payload + signature and returns the canonical payload validated against the published key for `key_id`.
- Per-message endpoints (`/v2/cctp/attestation/{message_hash}`, `/v2/ccip/message/{message_id}`) expose the underlying cryptographic anchor: Circle ECDSA signature for CCTP V1, DON threshold signature for CCIP once `CommitReport` capture reaches production.

## Schema mapping for L1 (Ethereum entry)

```jsonc
{
  "panel": {
    "l1": [
      {
        "chain": "ethereum",
        "regime": "S1D1",        // 12 codes
        "status": "OK",
        "structural": {
          "rhythm": {
            "ratio": 1.001,
            "ratio_long": 0.999,
            "shift": 0.0017,                // mapped to eth_struct_rhythm_shift
            "shift_delta": 0.0008,
            "shift_magnitude_delta": 0.0008
          },
          "continuity": { ... },            // mapped to eth_struct_continuity_shift
          "beacon_participation": { ... }   // NOT in 2025 historical, see LIMITATIONS.md
        },
        "demand": {
          "sigma": { ... },                 // mapped to eth_demand_sigma_shift
          "size":  { ... },                 // mapped to eth_demand_size_shift
          "tx":    { ... }                  // mapped to eth_demand_tx_shift
        },
        "drift": {
          "structural": ...,
          "demand": ...,
          "demand_magnitude_delta": ...,
          "structural_magnitude_delta": ...
        }
      }
    ]
  }
}
```

## Schema mapping for L2 (Arbitrum entry)

```jsonc
{
  "panel": {
    "l2": [
      {
        "chain": "arbitrum",
        "regime": "S1D1",
        "status": "OK",
        "structural": {
          "rhythm": { ... },                              // mapped to arb_struct_rhythm_shift
          "continuity": { ... },                          // mapped to arb_struct_continuity_shift
          "sequencer_publish_latency": { ... }            // mapped to arb_struct_seq_publish_latency_shift
        },
        "demand": {
          "sigma":          { ... },   // mapped to arb_demand_sigma_shift (blindspot, Nitro)
          "size":           { ... },   // mapped to arb_demand_size_shift
          "tx":             { ... },   // mapped to arb_demand_tx_shift
          "complexity":     { ... },   // mapped to arb_demand_complexity_shift
          "gas_complexity": { ... }    // mapped to arb_demand_gas_complexity_shift
        },
        "drift": { ... }
      }
    ]
  }
}
```

## Schema mapping for bridges (CCTP V1 route entries)

```jsonc
{
  "panel": {
    "bridges": [
      {
        "type": "cctp",
        "lane": "eth-arb",
        "state": "BS1",                              // mapped to bridge_state_eth_arb
        "calibrated": false,                         // production calibration pending
        "metrics": {
          "latency_p50_s": 1200.0,                   // mapped to cctp_eth_arb_latency_p50_s
          "latency_p90_s": 1500.0,                   // mapped to cctp_eth_arb_latency_p90_s
          "latency_p99_s": 1800.0,                   // mapped to cctp_eth_arb_latency_p99_s
          "messages_observed_1h": 16                 // mapped to cctp_eth_arb_messages_1h
        },
        "capability_level": "per_message_attested",  // since 2026-05-11 for CCTP V1 EVM
        "crypto": {
          "anchor": "circle_ecdsa"
        },
        "status": "OK"
      }
      // ... and the symmetric route for arb-eth
    ]
  }
}
```

## What is included in the analysis but NOT in the v2.0 API

None. Every column used in the analysis is present in the v2.0 API output, with the documented exception of beacon participation, which is in the API but absent from the 2025 historical reconstruction.

## What is in the v2.0 API but NOT used in this analysis

- `shift_delta`, `shift_magnitude_delta` per metric: these are first and second derivatives of the shift signal, omitted from the plot panels for visual clarity but retained in the data dictionary as future-work signals.
- `drift.structural`, `drift.demand`, and their `_magnitude_delta` aggregates: these are summaries of the underlying shifts already plotted. Including them would duplicate information.
- `status` field per item: "OK", "STALE", "UNAVAILABLE", "UNCALIBRATED". Always "OK" in the reconstruction since the input parquets cover the full 2025 window with no gaps.

## Documentation references

- API user guide: https://invarians.com/developers.html
- Glossary: https://invarians.com/glossary.html
- Foundations: https://invarians.com/foundations.html
