# Claims: claim-to-evidence index

Each testable claim → the script(s) and output file(s) that support it
and the result. "Spec" claims are supported by the cited primary source
in `sources.md` plus a harness check where one exists. Status tags:
MEASURED / MODEL / DERIVED / ASSUMED / UNVERIFIED (see README).

## Size claims

| # | Claim | Evidence | Result |
|---|---|---|---|
| C1 | ML-DSA-65 signature is 3,309 B | FIPS 204 Table 2; `scripts/sizes.py` check `mldsa65_signature_is_3309` | PASS (`outputs/sizes.json`) |
| C2 | ML-DSA-65 public key is 1,952 B | FIPS 204 Table 2; check `mldsa65_pubkey_is_1952` | PASS |
| C3 | Ed25519 signature is 64 B | RFC 8032 §7; check `ed25519_signature_is_64` | PASS |
| C4 | Smallest SLH-DSA signature is 7,856 B (128s); largest is 49,856 B (256f) | FIPS 205 Table 2; checks `slh128s_smallest_pq_signature`, `slh256f_largest_signature` | PASS |
| C5 | ML-DSA-65 signature is 51.7x Ed25519 (DERIVED: 3309/64) | `scripts/sizes.py`, `outputs/sizes.json` ratios | PASS (`mldsa65_sig_ratio_gt_50`) |
| C6 | Model ML-DSA-65 tx is 5,461 B vs Ed25519 297 B — 18.4x (DERIVED; base overhead ASSUMED 200 B) | `scripts/sizes.py`, `outputs/sizes.json` | PASS (`mldsa65_tx_larger_than_ed25519_tx`) |
| C7 | Whitepaper quorum arithmetic: 24 × 3,309 = 79,416 B | Whitepaper §1.11; check `whitepaper_quorum_arithmetic` | PASS |
| C8 | At 1,500 TPS, ML-DSA-65 adds ~708 GB/day to the ledger stream vs ~38.5 GB/day for Ed25519 (DERIVED; workload ASSUMED) | `scripts/sizes.py`, `outputs/sizes.json` ledger_growth | Computed, no separate check (see C6 inputs) |

## Fee-market claims

| # | Claim | Evidence | Result |
|---|---|---|---|
| C9 | Reference fee is 10 drops | postfiatd `Config.h:69`; xrpl.org Transaction Cost; check `reference_fee_is_10_drops` | PASS |
| C10 | Base fee level is 256 | `FeeEscalation.md`; check `base_fee_level_is_256` | PASS |
| C11 | No escalation at or below the open-ledger limit; quadratic above it (100 tx at limit 50 → level 1,024, 40 drops) | `FeeEscalation.md` formula; `scripts/fees.py`; checks `no_escalation_at_or_below_limit`, `escalation_quadratic_above_limit` | PASS |
| C12 | Base fee is identical (10 drops) for every scheme — fees are count-based, not byte-based | `scripts/fees.py`; checks `base_fee_identical_all_schemes`, `mldsa65_same_base_fee_as_ed25519` | PASS |
| C13 | 1 MB of ledger via ML-DSA-65 costs 1,830 drops vs 33,670 via Ed25519 at base load — ~18.4x cheaper spam per byte (DERIVED) | `scripts/fees.py`, `outputs/fees.json` spam | PASS (`mldsa65_spam_cheaper_per_mb`) |
| C14 | SLH-DSA-256f gives the cheapest spam per ledger byte (190 drops/MB) (DERIVED) | `scripts/fees.py` | PASS (`slh256f_spam_cheapest_per_mb`) |

## Throughput / cost-model claims

| # | Claim | Evidence | Result |
|---|---|---|---|
| C15 | Calibrated MODEL: ML-DSA-65 verify 0.06 ms → 16,666.7 verifies/s/core (MDPI 2025, liboqs 0.7.2, server E1) | `scripts/bench.py`; checks `calibrated_mldsa65_verify_0_06ms`, `model_mldsa65_verify_throughput` | PASS |
| C16 | Calibrated MODEL: ML-DSA-44 verify 0.040 ms → 25,000/s/core (cryptoai.wtf, M3 Max, liboqs) | `scripts/bench.py`; check `calibrated_mldsa44_verify_0_04ms` | PASS |
| C17 | Ed25519 verify 0.053 ms DERIVED from H33 (24 µs × 2.2) → 18,867.9/s/core | `scripts/bench.py`; check `ed25519_verify_derived_0_053ms` | PASS |
| C18 | MODEL ML-DSA-65 verify throughput is below derived Ed25519 throughput | `scripts/bench.py`; check `model_verify_slower_than_ed25519_derived` | PASS |
| C19 | FastPay ML-DSA-65 signing 0.52 ms per validator signature (fleet hardware, CPU unspecified) | FastPay article; check `fastpay_sign_0_52ms_recorded` | PASS |
| C20 | Stand-in hashing is MEASURED on this machine (median 0.64 µs at 64 B → 53.61 µs at 49,856 B); it measures the machine, not ML-DSA | `scripts/bench.py`, `outputs/bench.json` | PASS (`standin_hashing_faster_for_small_buffers`, `standin_all_iterations_completed`) |
| C21 | ML-DSA-87 and secp256k1 verify times are UNVERIFIED — excluded from the cost model | `scripts/bench.py`; check `mldsa87_verify_unverified` | PASS |
| C22 | No published SLH-DSA verify time in the source set — excluded from the cost model | `scripts/bench.py`; check `slh_timing_unverified` | PASS |

## Mitigation claims

| # | Claim | Evidence | Result |
|---|---|---|---|
| C23 | zlib-9 on ML-DSA-65 stand-in signature bytes increases size by 0.33% (MEASURED) — compression does not help | `scripts/mitigations.py`, `outputs/mitigations.json` | PASS (`compression_mldsa65_near_zero`) |
| C24 | zlib-9 on Ed25519 stand-in bytes increases size (MEASURED) | `scripts/mitigations.py` | PASS (`compression_ed25519_near_zero`) |
| C25 | Every composite signature is larger than the pure ML-DSA signature (DERIVED) | `scripts/mitigations.py` | PASS (`hybrid_larger_than_pure`) |
| C26 | ML-DSA-65+Ed25519 composite is 3,381 B (3309 + 64 + 8 framing ASSUMED) | `scripts/mitigations.py`; check `hybrid_mldsa65_ed25519_size` | PASS |
| C27 | Batching figures are simulation-only with a stated 0.8x amortized factor (ASSUMED) — FIPS 204 specifies single-signature verification only | `scripts/mitigations.py`; checks `batching_simulation_labelled`, `batching_assumed_factor_0_8` | PASS |
| C28 | BLS aggregation is REJECTED as a post-quantum mitigation (pairing-based, broken by Shor) | RFC 9591; IACR ePrint 2026/2222 SoK; check `bls_rejected` | PASS |
| C29 | Post-quantum aggregation is REJECTED as an available mitigation (no standardized scheme) | FIPS 204/205 (no aggregate form); check `pq_aggregation_rejected` | PASS |

## Ledger / implementation claims

| # | Claim | Evidence | Result |
|---|---|---|---|
| C30 | postfiatd contains no ML-DSA code at commit 0085a1f (grep over `src/` + `include/` returned zero matches) | Source grep, 2026-11-15; `sources.md` §4 | Verified by inspection (not a harness check) |
| C31 | postfiatd fee defaults match upstream rippled (reference fee 10) in the files examined | `Config.h`, `FeeEscalation.md`, `LoadFeeTrack`, `TxQ`; `sources.md` §4 | Verified by inspection; full-diff caveat in `limitations.md` |
| C32 | No per-transaction byte-size cap was found in postfiatd sources; admissibility of large post-quantum transactions is UNVERIFIED | Source greps, 2026-11-15; `sources.md` §4 | Negative result — see `limitations.md` |
| C33 | Whitepaper states no throughput figure and no fee schedule | Full-text search of whitepaper, 2026-11-15; `sources.md` §6 | Negative result |
| C34 | Composite ML-DSA is not a NIST standard and not an RFC (draft-ietf-lamps-pq-composite-sigs-19, IESG evaluation) | datatracker ballot page; `sources.md` §10 | Verified status |
| C35 | `FeeEscalation.md` contradicts itself on minimum `lastLedgerMedianFeeLevel` (128,000 vs 500) | `FeeEscalation.md` §§5/"Other Constants"; `limitations.md` | Documented inconsistency, unresolved |

## Run-level claim

| # | Claim | Evidence | Result |
|---|---|---|---|
| C36 | Full harness passes: 38/38 checks, 0 failed | `python3 scripts/run_all.py`; `outputs/run-summary.json` (overall PASS), `outputs/run.log` | PASS |
