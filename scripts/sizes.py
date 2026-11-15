#!/usr/bin/env python3
"""Transaction-size model: classical vs post-quantum signature sizes.

Builds model transactions for each scheme from the verified FIPS/RFC sizes
plus the pinned base-transaction overhead (ASSUMED, 200 bytes), then
computes size ratios and ledger-growth projections at the stated workload
(1500 TPS, 4-second ledgers, postfiatd README).

Usage: python3 scripts/sizes.py [--output-dir outputs]
Writes outputs/sizes.json and prints a PASS/FAIL line per check.
Exit code 0 only if every check passes.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BASE_TX_BYTES,
    LEDGER_CLOSE_SECONDS,
    MAX_TPS,
    SCHEMES,
    SECONDS_PER_DAY,
    tx_size,
)

CHECKS = []


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

    results = {"base_tx_bytes_assumed": BASE_TX_BYTES,
               "workload": {"max_tps_assumed": MAX_TPS,
                            "ledger_close_seconds": LEDGER_CLOSE_SECONDS},
               "schemes": {}, "ratios": {}, "ledger_growth": {}}

    ed_tx = tx_size("Ed25519")
    for name, spec in SCHEMES.items():
        size = tx_size(name)
        results["schemes"][name] = {
            "public_key_bytes": spec["public_key"],
            "public_key_wire_bytes": spec["public_key_wire"],
            "signature_bytes": spec["signature"],
            "model_tx_bytes": size,
            "security": spec["security"],
        }
        results["ratios"][name] = {
            "signature_ratio_vs_ed25519": round(spec["signature"] / 64, 2),
            "tx_ratio_vs_ed25519": round(size / ed_tx, 2),
        }

    # --- Checks against the verified source numbers --------------------------
    check("mldsa65_signature_is_3309",
          SCHEMES["ML-DSA-65"]["signature"] == 3309,
          "FIPS 204 Table 2: ML-DSA-65 signature 3309 B")
    check("mldsa65_pubkey_is_1952",
          SCHEMES["ML-DSA-65"]["public_key"] == 1952,
          "FIPS 204 Table 2: ML-DSA-65 public key 1952 B")
    check("ed25519_signature_is_64",
          SCHEMES["Ed25519"]["signature"] == 64,
          "RFC 8032 section 7: Ed25519 signature 64 B")
    check("slh128s_smallest_pq_signature",
          SCHEMES["SLH-DSA-128s"]["signature"] == 7856,
          "FIPS 205 Table 2: smallest SLH-DSA signature 7856 B")
    check("slh256f_largest_signature",
          SCHEMES["SLH-DSA-256f"]["signature"] == 49856,
          "FIPS 205 Table 2: largest SLH-DSA signature 49856 B")
    check("mldsa65_sig_ratio_gt_50",
          SCHEMES["ML-DSA-65"]["signature"] / 64 > 50,
          f"DERIVED: 3309/64 = {3309 / 64:.1f}x")
    check("mldsa65_tx_larger_than_ed25519_tx",
          tx_size("ML-DSA-65") > ed_tx,
          f"DERIVED: model tx {tx_size('ML-DSA-65')} B vs Ed25519 {ed_tx} B")
    check("slh256f_tx_larger_than_mldsa87_tx",
          tx_size("SLH-DSA-256f") > tx_size("ML-DSA-87"),
          "DERIVED: largest SLH-DSA model tx exceeds ML-DSA-87 model tx")
    check("all_model_tx_positive",
          all(tx_size(n) > BASE_TX_BYTES for n in SCHEMES),
          "every model transaction exceeds the base overhead")

    # --- Ledger-growth projections (DERIVED arithmetic) -----------------------
    for name in SCHEMES:
        size = tx_size(name)
        sig_only = SCHEMES[name]["signature"]
        per_ledger = size * MAX_TPS * LEDGER_CLOSE_SECONDS
        per_day = size * MAX_TPS * SECONDS_PER_DAY
        sig_per_day = sig_only * MAX_TPS * SECONDS_PER_DAY
        results["ledger_growth"][name] = {
            "model_tx_bytes": size,
            "bytes_per_ledger_4s_at_1500tps": per_ledger,
            "bytes_per_day_at_1500tps": per_day,
            "signature_bytes_per_day_at_1500tps": sig_per_day,
            "mb_per_day_at_1500tps": round(per_day / 1e6, 1),
            "sig_mb_per_day_at_1500tps": round(sig_per_day / 1e6, 1),
        }

    # Whitepaper quorum arithmetic cross-check (DERIVED, postfiat.org
    # whitepaper section 1.11: 24 x 3309 = 79416).
    quorum = 24 * SCHEMES["ML-DSA-65"]["signature"]
    check("whitepaper_quorum_arithmetic",
          quorum == 79416,
          f"DERIVED: 24 x 3309 = {quorum} B (whitepaper section 1.11: 79416 B)")
    results["whitepaper_quorum_bytes_24_of_35"] = quorum
    results["whitepaper_quorum_prepare_precommit_double_bytes"] = quorum * 2

    passed = sum(1 for c in CHECKS if c["status"] == "PASS")
    results["checks"] = CHECKS
    results["summary"] = {"passed": passed, "failed": len(CHECKS) - passed,
                          "total": len(CHECKS)}
    (out_dir / "sizes.json").write_text(json.dumps(results, indent=2) + "\n")

    print(f"\nModel transaction sizes (base overhead ASSUMED {BASE_TX_BYTES} B):")
    for name in SCHEMES:
        r = results["ratios"][name]
        g = results["ledger_growth"][name]
        print(f"  {name:14s} tx {results['schemes'][name]['model_tx_bytes']:6d} B"
              f"  sig {r['signature_ratio_vs_ed25519']:6.1f}x Ed25519"
              f"  tx {r['tx_ratio_vs_ed25519']:5.1f}x"
              f"  {g['mb_per_day_at_1500tps']:8.1f} MB/day at 1500 TPS")
    print(f"\nSizes: {passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
