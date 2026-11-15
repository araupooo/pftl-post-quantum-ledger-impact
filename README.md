# PFTL Post-Quantum Ledger Impact Assessment

A reproducible assessment of how ML-DSA-44/65/87 and SLH-DSA signatures
affect transaction size, throughput, fees, validator storage, and spam
resistance on a ledger of the XRPL family (postfiatd), versus
Ed25519/secp256k1.

Intended repository name: `pftl-post-quantum-ledger-impact` (name only;
no repository was created by this pack).

## Headline results

- A model ML-DSA-65 transaction is **5,461 bytes** vs **297 bytes** for
  Ed25519 — **18.4x** larger (DERIVED). The signature alone is 3,309 bytes
  vs 64 bytes — **51.7x** (FIPS 204 Table 2; RFC 8032 section 7).
- At the stated workload of 1,500 TPS, ML-DSA-65 transactions add
  **~708 GB/day** to the ledger stream vs **~38.5 GB/day** for Ed25519
  (DERIVED arithmetic from the pinned sizes).
- Fees are **count-based, not byte-based**: a 3,309-byte ML-DSA-65
  signature costs the same **10 drops** as a 64-byte Ed25519 signature at
  base load (postfiatd `Config.h` reference fee; `FeeEscalation.md`).
  The cost of post-quantum signatures shows up as ledger bytes per fee
  unit and as cheaper spam per ledger byte — 1 MB of ledger costs
  **1,830 drops** via ML-DSA-65 vs **33,670 drops** via Ed25519 (DERIVED).
- Verification cost is not the bottleneck: calibrated model throughput is
  **~16,667 ML-DSA-65 verifies/second per core** (MODEL, from published
  liboqs measurements), vs **~18,868/second** derived for Ed25519.
- postfiatd contains **no ML-DSA code** (verified by source grep at commit
  `0085a1f`); the whitepaper's "ML-DSA-65 from genesis" is a design
  statement for a separate codebase, not an implemented feature of the
  checked tree.
- Compression does not help: zlib-9 on deterministic stand-in signature
  bytes **increases** size by 0.33% for ML-DSA-65 (MEASURED).
- Composite/hybrid signatures are **larger** than pure ML-DSA
  (ML-DSA-65+Ed25519 = 3,381 bytes, 1.022x pure ML-DSA) and are not a
  NIST standard (IETF LAMPS draft, in IESG evaluation, not an RFC).
- BLS aggregation is **rejected** as a post-quantum mitigation:
  pairing-based, broken by Shor's algorithm.

## One-command reproduction

```sh
python3 scripts/run_all.py
```

Python 3 standard library only — no pip installs, no network access.
Runs four harnesses in order (`sizes`, `bench`, `fees`, `mitigations`),
each printing PASS/FAIL per check, each writing its JSON output and its
unedited log to `outputs/`, plus a combined `outputs/run.log` and
`outputs/run-summary.json`. Expected result: **38/38 checks pass**.

## File map

| File | Contents |
|---|---|
| `README.md` | This file: results, reproduction, file map, limitations summary, benchmark environment. |
| `findings.md` | Full assessment: pinned sources, measured results, mitigation comparisons, rejected approaches, limitations. |
| `index.html` | Rendered findings page (static, self-contained, no external assets), mirroring `findings.md`. |
| `measurements.md` | Benchmark methodology and pinned inputs: parameter sets, classical baselines, workload assumptions, environment. |
| `model.md` | Ledger-growth, validation-cost, fee-market, and spam-resistance model; every input tagged MEASURED or ASSUMED. |
| `mitigations.md` | Aggregation, hybrid-signature, batching, and compression: measured/simulated comparisons and explicit rejections. |
| `scripts/common.py` | Pinned inputs shared by all harnesses (sizes, fee constants, calibrated model inputs). |
| `scripts/sizes.py` | Transaction-size model and ledger-growth projections. |
| `scripts/bench.py` | Cost benchmark: measured stand-in workload + calibrated model from published measurements. |
| `scripts/fees.py` | Count-based fee model and spam-cost simulation. |
| `scripts/mitigations.py` | Compression (measured), hybrid sizing, batching simulation, rejections. |
| `scripts/run_all.py` | Runs every harness, writes `outputs/run-summary.json` and `outputs/run.log`. |
| `outputs/` | Unedited run logs and JSON outputs from the final run. |
| `sources.md` | Primary-source citations (URL + section/version/date) for every spec-derived claim. |
| `claims.md` | Claim-to-evidence index: each testable claim → script(s) + output file(s) + result. |
| `DIGESTS.txt` | SHA-256 of every deterministic file in the pack (excluding itself and the three timing-varying files listed below). |
| `limitations.md` | What was NOT verified, failed/inconclusive checks, open questions. |

## How to verify the digests

```sh
cd <pack root>
sha256sum -c DIGESTS.txt
```

Every file except `DIGESTS.txt` itself is listed, with one documented
exception: `outputs/bench.json`, `outputs/bench.log`, and `outputs/run.log`
are NOT listed because they contain wall-clock timing medians that vary
~1% between runs (timing noise). Re-running the harness re-generates them
with slightly different medians; the check outcomes (38/38 PASS) and all
other outputs are byte-identical across runs. A mismatch on a listed file
means the pack was modified after the digest was generated.

## Labels used throughout

- **MEASURED** — produced by running this harness on the stated machine.
- **MODEL** — computed from published measurements cited in `sources.md`
  (calibrated model inputs); not measured here.
- **DERIVED** — arithmetic from verified numbers, with the arithmetic shown.
- **ASSUMED** — a stated modelling input, not a measured or sourced value.
- **UNVERIFIED** — searched for, not confirmed; never stated as fact.

## Limitations summary

- No per-transaction byte-size cap was found in postfiatd/XRPL sources;
  whether a large post-quantum transaction is even admissible is
  **UNVERIFIED** — it needs an empirical test against a live node.
- No native ML-DSA timing was measured on validator hardware. All
  verification-throughput figures are a calibrated model from published
  measurements on other hardware; a pure-Python reference implementation
  was deliberately not used as a timing proxy.
- No published SLH-DSA verification time was found in the source set;
  SLH-DSA is excluded from the cost model.
- `FeeEscalation.md` contradicts itself on the minimum
  `lastLedgerMedianFeeLevel` (128,000 vs 500); neither figure is quoted
  as settled.
- The 1,500 TPS / 4-second-ledger workload is a stated assumption from
  the postfiatd README, not a measurement made here.
- Full detail: `limitations.md`.

## Benchmark environment

- Machine: Linux 7.0.0-44-generic x86_64, 4 logical CPUs
  (this run; see `outputs/bench.json` for the pinned environment record).
- Python: 3.12.3 (main, Aug 31 2026) [GCC 13.3.0], glibc 2.39.
- Timing: `time.perf_counter_ns`; warmup 200, iterations 2,000 per scheme.
- No network access during runs; all inputs pinned in `scripts/common.py`.
