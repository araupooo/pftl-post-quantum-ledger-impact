#!/usr/bin/env python3
"""Run the whole harness and write the run summary.

Usage: python3 scripts/run_all.py
Runs sizes.py, bench.py, fees.py, mitigations.py in order, each writing
its own JSON output plus its own unedited log, then writes
outputs/run-summary.json and a combined log outputs/run.log.
Exit code 0 only if every sub-harness passes.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent
OUT = PACK / "outputs"
STEPS = ["sizes", "bench", "fees", "mitigations"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    combined = []
    step_results = {}
    overall_ok = True

    for step in STEPS:
        proc = subprocess.run(
            [sys.executable, "-B", str(HERE / f"{step}.py"), "--output-dir", str(OUT)],
            capture_output=True, text=True)
        log_name = f"{step}.log"
        (OUT / log_name).write_text(proc.stdout + proc.stderr)
        combined.append(f"===== {step}.py (exit {proc.returncode}) =====\n")
        combined.append(proc.stdout)
        if proc.stderr:
            combined.append("--- stderr ---\n" + proc.stderr)
        data = json.loads((OUT / f"{step}.json").read_text())
        step_results[step] = {
            "exit_code": proc.returncode,
            "passed": data["summary"]["passed"],
            "failed": data["summary"]["failed"],
            "total": data["summary"]["total"],
            "log": log_name,
            "output": f"{step}.json",
        }
        if proc.returncode != 0:
            overall_ok = False

    # run-summary.json is intentionally timestamp-free so it is byte-identical
    # across runs. Wall-clock timing medians live only in bench.json /
    # bench.log / run.log, which vary ~1% between runs (timing noise) and are
    # therefore excluded from DIGESTS.txt (see its header).
    total_passed = sum(s["passed"] for s in step_results.values())
    total_failed = sum(s["failed"] for s in step_results.values())
    total = sum(s["total"] for s in step_results.values())
    summary = {
        "python": sys.version.split()[0],
        "steps": step_results,
        "totals": {"passed": total_passed, "failed": total_failed, "total": total},
        "overall": "PASS" if overall_ok and total_failed == 0 else "FAIL",
    }
    (OUT / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    combined.append(f"\n===== run summary: {total_passed}/{total} checks passed, "
                    f"{total_failed} failed, overall {summary['overall']} =====\n")
    (OUT / "run.log").write_text("".join(combined))
    print("".join(combined))
    return 0 if summary["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
