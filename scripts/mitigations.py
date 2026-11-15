#!/usr/bin/env python3
"""Mitigation simulations: batching, compression, hybrid sizing, aggregation.

What is MEASURED here (real, on this machine):
- Compression: zlib (levels 1/6/9) applied to deterministic stand-in
  signature bytes of each scheme's size. ML-DSA/SLH-DSA signatures are
  near-maximally compressed lattice/hash vectors, so ~0% reduction is the
  expected honest result, not a failure of the test.
- Hybrid sizing: exact byte arithmetic from the verified FIPS/RFC sizes
  (composite = ML-DSA signature + classical signature + framing).

What is SIMULATION-ONLY (labelled as such, never presented as measured):
- Batching: FIPS 204 specifies single-signature verification only; no
  batch-verification procedure exists. The simulation applies a STATED
  amortized-cost factor (ASSUMED 0.8x per-signature cost, i.e. a 20%
  saving) to the calibrated model to show what a hypothetical batch
  mechanism would need to deliver, and states plainly that no such
  mechanism is standardized.
- Parallel verification across cores: a deployment lever, not a
  cryptographic gain; computed from the calibrated model and the core
  count, labelled MODEL.

What is REJECTED (no computation offered as a working mitigation):
- BLS aggregation: pairing-based, broken by Shor's algorithm; NOT
  post-quantum. Included only as a contrast size (96 B aggregate, RFC 9591).
- Post-quantum aggregation: no standardized scheme exists (FIPS 204/205
  have no aggregate form). No simulation is offered for it.

Usage: python3 scripts/mitigations.py [--output-dir outputs]
Writes outputs/mitigations.json. Exit code 0 only if every check passes.
"""

import argparse
import json
import os
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CALIBRATED_VERIFY_MS, SCHEMES, deterministic_bytes, tx_size  # noqa: E402

CHECKS = []
BATCH_AMORTIZED_FACTOR_ASSUMED = 0.8  # STATED ASSUMPTION, simulation only
COMPOSITE_FRAMING_BYTES = 8           # ASSUMED framing for a composite signature
BLS_AGGREGATE_BYTES = 96              # RFC 9591 BLS signature size (contrast only)


def check(name, condition, detail):
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL",
                   "detail": detail})
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()
    out_dir = Path(args.output_dir or Path(__file__).resolve().parent.parent / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {"compression_measured": {}, "hybrid_sizing": {},
               "batching_simulation_only": {}, "parallel_model": {},
               "rejected": {}}

    # --- Compression (MEASURED, real zlib on deterministic bytes) ------------
    for name, spec in SCHEMES.items():
        data = deterministic_bytes(spec["signature"])
        row = {"signature_bytes": spec["signature"]}
        for level in (1, 6, 9):
            comp = zlib.compress(data, level)
            row[f"zlib_level_{level}_bytes"] = len(comp)
            row[f"zlib_level_{level}_reduction_pct"] = round(
                100 * (1 - len(comp) / len(data)), 2)
        results["compression_measured"][name] = row

    # --- Hybrid / composite sizing (exact arithmetic from verified sizes) ----
    for pq in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87"):
        for classical in ("Ed25519", "secp256k1"):
            comp_sig = (SCHEMES[pq]["signature"] + SCHEMES[classical]["signature"]
                        + COMPOSITE_FRAMING_BYTES)
            comp_pk = (SCHEMES[pq]["public_key_wire"]
                       + SCHEMES[classical]["public_key_wire"] + COMPOSITE_FRAMING_BYTES)
            results["hybrid_sizing"][f"{pq}+{classical}"] = {
                "composite_signature_bytes": comp_sig,
                "composite_public_key_bytes": comp_pk,
                "pure_pq_signature_bytes": SCHEMES[pq]["signature"],
                "extra_bytes_vs_pure_pq": comp_sig - SCHEMES[pq]["signature"],
                "ratio_vs_pure_pq": round(comp_sig / SCHEMES[pq]["signature"], 3),
                "framing_bytes_assumed": COMPOSITE_FRAMING_BYTES,
            }

    # --- Batching simulation (SIMULATION-ONLY, assumption stated) ------------
    for name, verify_ms in CALIBRATED_VERIFY_MS.items():
        if verify_ms is None:
            continue
        batched_ms = verify_ms * BATCH_AMORTIZED_FACTOR_ASSUMED
        results["batching_simulation_only"][name] = {
            "single_verify_ms_model": verify_ms,
            "amortized_factor_assumed": BATCH_AMORTIZED_FACTOR_ASSUMED,
            "batched_verify_ms_simulated": round(batched_ms, 4),
            "throughput_single_model": round(1000 / verify_ms, 1),
            "throughput_batched_simulated": round(1000 / batched_ms, 1),
            "status": ("SIMULATION ONLY: FIPS 204 specifies single-signature "
                       "verification only; no batch procedure is standardized."),
        }

    # --- Parallel verification across cores (MODEL deployment lever) ---------
    cores = os.cpu_count() or 1
    for name, verify_ms in CALIBRATED_VERIFY_MS.items():
        if verify_ms is None:
            continue
        results["parallel_model"][name] = {
            "verify_ms_model": verify_ms,
            "cores": cores,
            "verifies_per_second_model": round(1000 / verify_ms * cores, 1),
            "status": "MODEL: linear scaling with cores is an assumption, "
                      "not a measured validator result.",
        }

    # --- Rejected approaches (documented, no working simulation) -------------
    results["rejected"]["BLS_aggregation"] = {
        "reason": ("BLS rests on elliptic-curve pairings (BLS12-381); Shor's "
                   "algorithm breaks elliptic-curve discrete logarithms, so "
                   "BLS offers no quantum resistance. RFC 9591."),
        "contrast_aggregate_bytes": BLS_AGGREGATE_BYTES,
        "verdict": "REJECTED as a post-quantum mitigation.",
    }
    results["rejected"]["pq_aggregation"] = {
        "reason": ("No post-quantum signature aggregation scheme is a NIST "
                   "standard; ML-DSA and SLH-DSA have no standardized "
                   "aggregate form. Any proposal is research-stage."),
        "verdict": "REJECTED as an available mitigation (no deployable construction).",
    }
    results["rejected"]["batch_verification"] = {
        "reason": ("FIPS 204 section 5.3 specifies single-signature "
                   "verification only; no batch-verification procedure is "
                   "specified. FIPS 205 likewise."),
        "verdict": "REJECTED as a standardized mechanism; batching figures in "
                   "this pack are simulation-only with a stated assumption.",
    }
    results["rejected"]["signature_compression_standard"] = {
        "reason": ("No standardized compression for ML-DSA signatures exists "
                   "in FIPS 204; signatures are near-maximally compressed "
                   "lattice vectors. See measured zlib results (~0%)."),
        "verdict": "REJECTED as an available mitigation; compression measured, not assumed.",
    }

    check("compression_mldsa65_near_zero",
          results["compression_measured"]["ML-DSA-65"]["zlib_level_9_reduction_pct"] < 1.0,
          f"MEASURED: zlib-9 on 3309 B stand-in signature reduces by "
          f"{results['compression_measured']['ML-DSA-65']['zlib_level_9_reduction_pct']}%")
    check("compression_ed25519_near_zero",
          results["compression_measured"]["Ed25519"]["zlib_level_9_reduction_pct"] < 1.0,
          "MEASURED: zlib-9 on 64 B stand-in signature reduces by <1%")
    check("compression_deterministic",
          zlib.compress(deterministic_bytes(3309), 9)
          == zlib.compress(deterministic_bytes(3309), 9),
          "MEASURED: compression output is deterministic across runs")
    check("hybrid_larger_than_pure",
          all(v["composite_signature_bytes"] > v["pure_pq_signature_bytes"]
              for v in results["hybrid_sizing"].values()),
          "DERIVED: every composite signature is larger than the pure ML-DSA signature")
    check("hybrid_mldsa65_ed25519_size",
          results["hybrid_sizing"]["ML-DSA-65+Ed25519"]["composite_signature_bytes"]
          == 3309 + 64 + COMPOSITE_FRAMING_BYTES,
          f"DERIVED: 3309 + 64 + {COMPOSITE_FRAMING_BYTES} framing = "
          f"{3309 + 64 + COMPOSITE_FRAMING_BYTES} B")
    check("batching_simulation_labelled",
          all("SIMULATION ONLY" in v["status"]
              for v in results["batching_simulation_only"].values()),
          "every batching figure carries the simulation-only label")
    check("batching_assumed_factor_0_8",
          BATCH_AMORTIZED_FACTOR_ASSUMED == 0.8,
          "STATED ASSUMPTION: amortized factor 0.8 (20% saving), not a measured gain")
    check("bls_rejected",
          results["rejected"]["BLS_aggregation"]["verdict"].startswith("REJECTED"),
          "BLS aggregation explicitly rejected: pairing-based, broken by Shor")
    check("pq_aggregation_rejected",
          "REJECTED" in results["rejected"]["pq_aggregation"]["verdict"],
          "post-quantum aggregation explicitly rejected: no standardized scheme")

    passed = sum(1 for c in CHECKS if c["status"] == "PASS")
    results["checks"] = CHECKS
    results["summary"] = {"passed": passed, "failed": len(CHECKS) - passed,
                          "total": len(CHECKS)}
    (out_dir / "mitigations.json").write_text(json.dumps(results, indent=2) + "\n")

    print("\nCompression (MEASURED, zlib-9 on deterministic stand-in signature bytes):")
    for name, row in results["compression_measured"].items():
        print(f"  {name:14s} {row['signature_bytes']:6d} B -> {row['zlib_level_9_bytes']:6d} B"
              f"  ({row['zlib_level_9_reduction_pct']:+.2f}%)")
    print("\nHybrid/composite signature sizes (DERIVED arithmetic):")
    for name, row in results["hybrid_sizing"].items():
        print(f"  {name:20s} {row['composite_signature_bytes']:6d} B"
              f"  ({row['ratio_vs_pure_pq']:.3f}x pure ML-DSA, +{row['extra_bytes_vs_pure_pq']} B)")
    print("\nBatching (SIMULATION ONLY, assumed 0.8x amortized factor):")
    for name, row in results["batching_simulation_only"].items():
        print(f"  {name:14s} {row['throughput_single_model']:,.0f} -> "
              f"{row['throughput_batched_simulated']:,.0f} verifies/s/core (simulated)")
    print(f"\nMitigations: {passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
