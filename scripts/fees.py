#!/usr/bin/env python3
"""Fee-market simulation: XRPL/postfiatd count-based fee model.

Implements the mechanism documented in FeeEscalation.md (postfiatd tree,
inherited from rippled) and xrpl.org fee docs:
- Reference fee 10 drops (Config.h reference_fee{10}); base fee level 256.
- Fees scale with LOAD (number of transactions in the open ledger) and
  with the NUMBER of signatures, NOT with transaction byte size.
- Beyond the open-ledger limit, required fee level =
  lastLedgerMedianFeeLevel x (txInOpenLedger^2 / limit^2) (quadratic).
- Drops for a fee level L: L / 256 x 10 drops (base level 256 = 10 drops).

The simulation shows: a 3,309-byte ML-DSA signature costs the same 10
drops as a 64-byte Ed25519 signature at base load; the cost of post-quantum
signatures shows up as ledger bytes per fee unit and as spam cost per
ledger byte, not as a higher base fee.

Usage: python3 scripts/fees.py [--output-dir outputs]
Writes outputs/fees.json. Exit code 0 only if every check passes.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    BASE_FEE_LEVEL,
    OPEN_LEDGER_LIMIT_MIN,
    OPEN_LEDGER_LIMIT_TARGET,
    REFERENCE_FEE_DROPS,
    SCHEMES,
    tx_size,
)

CHECKS = []


def check(name, condition, detail):
    CHECKS.append({"name": name, "status": "PASS" if condition else "FAIL",
                   "detail": detail})
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    return condition


def fee_level(tx_in_open_ledger, limit, last_median_level):
    """Required fee level per FeeEscalation.md (quadratic escalation)."""
    if tx_in_open_ledger <= limit:
        return BASE_FEE_LEVEL
    return last_median_level * (tx_in_open_ledger ** 2 / limit ** 2)


def drops_for_level(level):
    return level / BASE_FEE_LEVEL * REFERENCE_FEE_DROPS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()
    out_dir = Path(args.output_dir or Path(__file__).resolve().parent.parent / "outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {"reference_fee_drops": REFERENCE_FEE_DROPS,
               "base_fee_level": BASE_FEE_LEVEL,
               "open_ledger_limit_target": OPEN_LEDGER_LIMIT_TARGET,
               "open_ledger_limit_min": OPEN_LEDGER_LIMIT_MIN,
               "escalation": [], "base_fee_by_scheme": {}, "spam": {}}

    # --- Escalation curve at the target limit, median level = base level ----
    for n in [1, 10, 50, 51, 60, 100, 200, 500]:
        level = fee_level(n, OPEN_LEDGER_LIMIT_TARGET, BASE_FEE_LEVEL)
        results["escalation"].append({
            "tx_in_open_ledger": n, "limit": OPEN_LEDGER_LIMIT_TARGET,
            "required_fee_level": round(level, 1),
            "required_fee_drops": round(drops_for_level(level), 1)})
    # Worked example quoted from FeeEscalation.md (cited, not recomputed):
    # limit 6, minimal median fee -> 8th tx ~level 174,000 (~6,800 drops),
    # 20th tx ~level 1,283,000 (~50,000 drops).
    results["fee_escalation_md_worked_example_cited"] = {
        "limit": 6, "8th_tx_level_about": 174000, "8th_tx_drops_about": 6800,
        "20th_tx_level_about": 1283000, "20th_tx_drops_about": 50000,
        "note": "Quoted from FeeEscalation.md; NOT recomputed by this script "
                "(the doc's cold-start median level is not stated).",
    }

    # --- Base fee is identical for every scheme (count-based, not byte-based)
    for name in SCHEMES:
        results["base_fee_by_scheme"][name] = {
            "model_tx_bytes": tx_size(name),
            "base_fee_drops": REFERENCE_FEE_DROPS,
            "bytes_per_drop_at_base_load": round(tx_size(name) / REFERENCE_FEE_DROPS, 1),
        }

    # --- Spam resistance: cost to add 1 MB of ledger bytes at base load ------
    one_mb = 1_000_000
    for name in SCHEMES:
        size = tx_size(name)
        n_tx = one_mb // size
        cost_drops = n_tx * REFERENCE_FEE_DROPS
        results["spam"][name] = {
            "model_tx_bytes": size,
            "tx_per_1mb": n_tx,
            "drops_per_1mb_at_base_load": cost_drops,
            "xrp_per_1mb_at_base_load": cost_drops / 1_000_000,
        }

    check("reference_fee_is_10_drops",
          REFERENCE_FEE_DROPS == 10,
          "Config.h reference_fee{10}; xrpl.org Transaction Cost: 10 drops")
    check("base_fee_level_is_256",
          BASE_FEE_LEVEL == 256,
          "FeeEscalation.md: base fee level 256")
    check("no_escalation_at_or_below_limit",
          fee_level(50, OPEN_LEDGER_LIMIT_TARGET, BASE_FEE_LEVEL) == BASE_FEE_LEVEL,
          "50 tx at limit 50 -> level 256 (10 drops)")
    check("escalation_quadratic_above_limit",
          abs(fee_level(100, OPEN_LEDGER_LIMIT_TARGET, BASE_FEE_LEVEL)
              - BASE_FEE_LEVEL * 4) < 1e-6,
          "100 tx at limit 50 -> level 256 x (100/50)^2 = 1024 (40 drops)")
    check("base_fee_identical_all_schemes",
          len({v["base_fee_drops"] for v in results["base_fee_by_scheme"].values()}) == 1,
          "DERIVED: every scheme pays 10 drops at base load regardless of size")
    check("mldsa65_same_base_fee_as_ed25519",
          results["base_fee_by_scheme"]["ML-DSA-65"]["base_fee_drops"]
          == results["base_fee_by_scheme"]["Ed25519"]["base_fee_drops"],
          "a 3309 B ML-DSA-65 signature costs the same 10 drops as a 64 B Ed25519 signature")
    check("mldsa65_spam_cheaper_per_mb",
          results["spam"]["ML-DSA-65"]["drops_per_1mb_at_base_load"]
          < results["spam"]["Ed25519"]["drops_per_1mb_at_base_load"],
          f"DERIVED: 1 MB of ledger via ML-DSA-65 costs "
          f"{results['spam']['ML-DSA-65']['drops_per_1mb_at_base_load']:,} drops vs "
          f"{results['spam']['Ed25519']['drops_per_1mb_at_base_load']:,} drops via Ed25519")
    check("slh256f_spam_cheapest_per_mb",
          results["spam"]["SLH-DSA-256f"]["drops_per_1mb_at_base_load"]
          == min(v["drops_per_1mb_at_base_load"] for v in results["spam"].values()),
          "DERIVED: largest signature gives the cheapest spam per ledger byte")
    check("drops_per_level_conversion",
          abs(drops_for_level(256) - 10) < 1e-9 and abs(drops_for_level(25600) - 1000) < 1e-9,
          "level 256 = 10 drops; level 25600 = 1000 drops")

    passed = sum(1 for c in CHECKS if c["status"] == "PASS")
    results["checks"] = CHECKS
    results["summary"] = {"passed": passed, "failed": len(CHECKS) - passed,
                          "total": len(CHECKS)}
    (out_dir / "fees.json").write_text(json.dumps(results, indent=2) + "\n")

    print("\nBase fee (all schemes, at base load): 10 drops")
    print("Bytes per drop at base load (DERIVED):")
    for name, v in results["base_fee_by_scheme"].items():
        print(f"  {name:14s} {v['model_tx_bytes']:6d} B/tx  {v['bytes_per_drop_at_base_load']:7.1f} B/drop")
    print("\nSpam cost per 1 MB of ledger bytes at base load (DERIVED):")
    for name, v in results["spam"].items():
        print(f"  {name:14s} {v['tx_per_1mb']:6d} tx  {v['drops_per_1mb_at_base_load']:8,} drops"
              f"  ({v['xrp_per_1mb_at_base_load']:.4f} XRP)")
    print("\nEscalation curve (limit 50, median level 256):")
    for e in results["escalation"]:
        print(f"  {e['tx_in_open_ledger']:4d} tx in open ledger -> level {e['required_fee_level']:>10,.1f}"
              f"  ({e['required_fee_drops']:,.1f} drops)")
    print(f"\nFees: {passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
