#!/usr/bin/env python3
"""Signing/verification cost benchmark.

Methodology (read before trusting any number here):
- No native ML-DSA library is used and no library timings are fabricated.
  A pure-Python reference ML-DSA implementation would be orders of
  magnitude slower than any production implementation and would say nothing
  about validator hardware, so it is deliberately NOT attempted.
- This harness does two things, kept strictly separate:
  (a) MEASURES a deterministic stand-in workload on THIS machine: hashing
      signature-sized byte buffers with hashlib.sha256, with warmup,
      fixed iterations, and median/min/max reporting. This measures the
      machine and the harness, not ML-DSA. It exists so the run proves the
      timing methodology works and so results are reproducible.
  (b) Applies a CALIBRATED MODEL: per-operation sign/verify times taken
      from published measurements (see common.py and sources.md section 7),
      each tagged with its source, hardware, and implementation. Throughput
      figures derived from the calibrated model are labelled MODEL, never
      presented as measurements made here.
- Environment is pinned in the output: Python version, platform, CPU count,
  iteration counts, timing function (time.perf_counter_ns).

Usage: python3 scripts/bench.py [--output-dir outputs]
Writes outputs/bench.json and prints a PASS/FAIL line per check.
"""

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CALIBRATED_SIGN_MS, CALIBRATED_VERIFY_MS, SCHEMES  # noqa: E402

WARMUP = 200
ITERATIONS = 2000
CHECKS = []


def check(name, condition, detail):
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL",
                   "detail": detail})
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition


def time_hashing(data, warmup=WARMUP, iterations=ITERATIONS):
    """Median/min/max seconds per hashlib.sha256 over `data`."""
    for _ in range(warmup):
        hashlib.sha256(data).digest()
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        hashlib.sha256(data).digest()
        samples.append((time.perf_counter_ns() - t0) / 1e9)
    return {"median_s": statistics.median(samples),
            "min_s": min(samples), "max_s": max(samples),
            "mean_s": statistics.mean(samples),
            "iterations": iterations, "warmup": warmup}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()
    out_dir = Path(args.output_dir or Path(__file__).resolve().parent.parent / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    env = {"python": sys.version.split()[0], "python_full": sys.version,
           "platform": platform.platform(), "machine": platform.machine(),
           "processor": platform.processor() or "unknown",
           "cpu_count_logical": __import__("os").cpu_count(),
           "timing": "time.perf_counter_ns", "warmup": WARMUP,
           "iterations": ITERATIONS}

    # (a) Measured stand-in workload: hash signature-sized buffers.
    measured = {}
    for name, spec in SCHEMES.items():
        data = hashlib.sha256(name.encode()).digest() * (spec["signature"] // 32 + 1)
        data = data[: spec["signature"]]
        stats = time_hashing(data)
        measured[name] = {"signature_bytes": spec["signature"], **stats,
                          "hashes_per_second_median": round(1 / stats["median_s"], 1)}
    # A second probe: hashing a full model transaction is not attempted
    # because the stand-in measures hashing throughput, not verification.

    # (b) Calibrated model throughput from published verify times.
    model = {}
    for name, verify_ms in CALIBRATED_VERIFY_MS.items():
        if verify_ms is None:
            model[name] = {"verify_ms": None,
                           "status": "UNVERIFIED: no published verify time in source set",
                           "verify_per_second_single_core_model": None}
        else:
            model[name] = {"verify_ms": verify_ms,
                           "status": "MODEL (calibrated from published measurement)",
                           "verify_per_second_single_core_model": round(1000 / verify_ms, 1)}
    sign_model = {}
    for name, sign_ms in CALIBRATED_SIGN_MS.items():
        if sign_ms is None:
            sign_model[name] = {"sign_ms": None, "status": "UNVERIFIED"}
        else:
            sign_model[name] = {"sign_ms": sign_ms,
                                "sign_per_second_single_core_model": round(1000 / sign_ms, 1),
                                "status": "MODEL (calibrated from published measurement)"}

    # Checks: the methodology itself, not fabricated timings.
    check("standin_hashing_faster_for_small_buffers",
          measured["Ed25519"]["median_s"] < measured["SLH-DSA-256f"]["median_s"],
          "MEASURED: hashing a 64 B buffer is faster than hashing a 49856 B buffer")
    check("standin_all_iterations_completed",
          all(m["iterations"] == ITERATIONS for m in measured.values()),
          f"MEASURED: {ITERATIONS} iterations for each of {len(measured)} schemes")
    check("calibrated_mldsa65_verify_0_06ms",
          CALIBRATED_VERIFY_MS["ML-DSA-65"] == 0.060,
          "MODEL INPUT: MDPI 2025 liboqs 0.7.2, ML-DSA-65 verify 0.06 ms")
    check("calibrated_mldsa44_verify_0_04ms",
          CALIBRATED_VERIFY_MS["ML-DSA-44"] == 0.040,
          "MODEL INPUT: cryptoai.wtf M3 Max liboqs, ML-DSA-44 verify 0.040 ms")
    check("ed25519_verify_derived_0_053ms",
          CALIBRATED_VERIFY_MS["Ed25519"] == 0.053,
          "DERIVED: H33 Graviton4 ML-DSA-65 verify 24 us x 2.2 = 52.8 us")
    check("mldsa87_verify_unverified",
          CALIBRATED_VERIFY_MS["ML-DSA-87"] is None,
          "UNVERIFIED: no published ML-DSA-87 verify time in the source set; excluded from model")
    check("slh_timing_unverified",
          "SLH-DSA-128s" not in CALIBRATED_VERIFY_MS,
          "UNVERIFIED: no published SLH-DSA verify time in the source set; excluded from model")
    check("model_mldsa65_verify_throughput",
          model["ML-DSA-65"]["verify_per_second_single_core_model"] is not None
          and model["ML-DSA-65"]["verify_per_second_single_core_model"] > 10000,
          f"MODEL: 1000/0.06 = {model['ML-DSA-65']['verify_per_second_single_core_model']:.1f} verifies/s/core")
    check("model_verify_slower_than_ed25519_derived",
          model["ML-DSA-65"]["verify_per_second_single_core_model"]
          < model["Ed25519"]["verify_per_second_single_core_model"],
          "MODEL: calibrated ML-DSA-65 verify throughput below derived Ed25519 throughput")
    # FastPay signing cross-check: 0.52 ms per signature on their fleet.
    check("fastpay_sign_0_52ms_recorded",
          CALIBRATED_SIGN_MS["ML-DSA-65-fastpay"] == 0.520,
          "MODEL INPUT: PostFiat FastPay, ML-DSA-65 signing 0.52 ms (fleet hardware, CPU unspecified)")

    passed = sum(1 for c in CHECKS if c["status"] == "PASS")
    results = {"environment": env,
               "methodology": (
                   "Stand-in hashing is MEASURED on this machine. Per-operation "
                   "sign/verify times are a CALIBRATED MODEL from published "
                   "measurements (sources.md section 7); no native ML-DSA "
                   "library was run and no library timing was fabricated. "
                   "Throughput figures are MODEL throughput, single core, "
                   "derived as 1000 / verify_ms."),
               "measured_standin_hashing": measured,
               "calibrated_verify_model": model,
               "calibrated_sign_model": sign_model,
               "checks": CHECKS,
               "summary": {"passed": passed, "failed": len(CHECKS) - passed,
                           "total": len(CHECKS)}}
    (out_dir / "bench.json").write_text(json.dumps(results, indent=2) + "\n")

    print("\nMeasured stand-in (hashlib.sha256 over signature-sized buffer):")
    for name, m in measured.items():
        print(f"  {name:14s} {m['signature_bytes']:6d} B  median {m['median_s']*1e6:8.2f} us"
              f"  ({m['hashes_per_second_median']:,.0f} hashes/s)")
    print("\nCalibrated MODEL verify throughput (single core, from published times):")
    for name, m in model.items():
        v = m["verify_per_second_single_core_model"]
        print(f"  {name:14s} {m['verify_ms']} ms  -> "
              f"{f'{v:,.1f} verifies/s' if v else 'UNVERIFIED'}")
    print(f"\nBench: {passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
