# Measurements: methodology and pinned inputs

## Method

Four harnesses, Python 3 standard library only, no network access, no
pip installs. One command runs everything:

```sh
python3 scripts/run_all.py
```

Each harness prints one PASS/FAIL line per check, writes a JSON output
and an unedited log to `outputs/`, and exits non-zero if any check
fails. `run_all.py` writes `outputs/run-summary.json` and the combined
`outputs/run.log`. Final run: **38/38 checks passed, 0 failed**
(see `outputs/run-summary.json`).

| Harness | What it does | Output |
|---|---|---|
| `scripts/sizes.py` | Model transactions from verified sizes + ASSUMED base overhead; size ratios; ledger-growth projections | `outputs/sizes.json`, `outputs/sizes.log` |
| `scripts/bench.py` | Measured stand-in hashing workload + calibrated MODEL verify/sign throughput from published measurements | `outputs/bench.json`, `outputs/bench.log` |
| `scripts/fees.py` | Count-based fee model (quadratic escalation), base fee per scheme, spam cost per ledger MB | `outputs/fees.json`, `outputs/fees.log` |
| `scripts/mitigations.py` | Measured zlib compression; hybrid sizing arithmetic; batching simulation (labelled); parallel model; rejections | `outputs/mitigations.json`, `outputs/mitigations.log` |

## Pinned signature parameter sets

### ML-DSA — NIST FIPS 204, Table 2 (verified from the PDF text)

| Parameter set | Category (§4) | Private key (B) | Public key (B) | Signature (B) |
|---|---|---|---|---|
| ML-DSA-44 | 2 | 2,560 | 1,312 | 2,420 |
| ML-DSA-65 | 3 | 4,032 | 1,952 | 3,309 |
| ML-DSA-87 | 5 | 4,896 | 2,592 | 4,627 |

FIPS 204 §3.6.2 requires public-key and signature length checks on
verification. A private key may be stored as only the 32-byte seed
(§4). FIPS 204 defines single-signature verification only (Algorithm 3,
§5.3); no batch-verification procedure is specified.

### SLH-DSA — NIST FIPS 205, Table 2 (verified from the PDF text)

SHA2 and SHAKE variants have identical sizes.

| Parameter set | Category | Public key (B) | Signature (B) |
|---|---|---|---|
| SLH-DSA-128s | 1 | 32 | 7,856 |
| SLH-DSA-128f | 1 | 32 | 17,088 |
| SLH-DSA-192s | 3 | 48 | 16,224 |
| SLH-DSA-192f | 3 | 48 | 35,664 |
| SLH-DSA-256s | 5 | 64 | 29,792 |
| SLH-DSA-256f | 5 | 64 | 49,856 |

Each key pair may sign up to 2^64 messages (FIPS 205 footnote 22).

### Classical baselines

- **Ed25519** — RFC 8032 §7: public and private keys 32 octets,
  signatures 64 octets; ~128-bit security (§1). XRPL wire form: 33
  bytes (prefixed with `0xED`).
- **secp256k1** — 33-byte compressed public key (postfiatd
  `include/xrpl/protocol/PublicKey.h`, read directly); ECDSA signature
  64 bytes compact (r‖s) or 68–72 bytes DER-encoded (secp256k1 crate
  docs). The SEC 2 PDF itself was not directly read — see
  `limitations.md`.

## Workload assumptions (ASSUMED unless noted)

- **Base transaction overhead: 200 bytes (ASSUMED).** Size of a minimal
  payment-style transaction excluding `SigningPubKey` and `TxnSignature`.
  Applied uniformly to every scheme, so all ratios are driven by the
  verified signature/public-key sizes. Changing this assumption moves
  absolute model-transaction sizes but barely moves the ratios (e.g.
  with a 0-byte base, ML-DSA-65 vs Ed25519 is 54.2x; with 200 bytes it
  is 18.4x — the signature ratio of 51.7x is assumption-free).
- **Throughput: 1,500 TPS; ledger close: 4 seconds.** Stated in the
  postfiatd README ("settles transactions in 4 to 5 seconds,
  processing at a throughput of up to 1500 transactions per second").
  Used as a workload assumption, not a measurement made here.
- **Reference fee: 10 drops** (postfiatd `Config.h:69`,
  `XRPAmount reference_fee{10}`; xrpl.org "Transaction Cost").
  **Base fee level: 256** (`FeeEscalation.md`).
- **Composite framing: 8 bytes (ASSUMED)** for hybrid-signature sizing.
- **Batching amortized factor: 0.8x (ASSUMED, simulation only).**

## Benchmark environment (pinned)

- Machine: Linux 7.0.0-44-generic x86_64, 4 logical CPUs.
- Python: 3.12.3 (main, Aug 31 2026) [GCC 13.3.0], glibc 2.39.
  Full record in `outputs/bench.json` under `environment`.
- Timing: `time.perf_counter_ns`; warmup 200 iterations, 2,000 timed
  iterations per scheme; median/min/max/mean reported.
- Stand-in workload: `hashlib.sha256` over deterministic
  signature-sized buffers. This measures the machine and the timing
  methodology, not ML-DSA. It is labelled as a stand-in everywhere it
  appears.
- Calibrated model inputs (published measurements, not measured here):
  ML-DSA-65 verify 0.06 ms / sign 0.11 ms (MDPI *Cryptography* 2025,
  9, 32, Table 14, liboqs 0.7.2, server E1); ML-DSA-65 verify 24 µs /
  sign 72 µs median (H33, 2026-05-23, AWS Graviton4, 1,000,000
  samples); ML-DSA-44 verify 0.040 ms / sign 0.165 ms (cryptoai.wtf,
  2026-04-02, Apple M3 Max, liboqs); ML-DSA-65 signing 0.52 ms
  (PostFiat FastPay, fleet hardware, CPU unspecified); Ed25519 verify
  0.053 ms DERIVED from H33 (24 µs × 2.2).
- No native ML-DSA library was run. A pure-Python reference
  implementation was deliberately not used as a timing proxy: it would
  be orders of magnitude slower than any production implementation and
  would say nothing about validator hardware.

## What the harness does NOT measure

- Native ML-DSA sign/verify latency on any machine (no library used).
- SLH-DSA sign/verify latency (no published figures in the source set).
- Live ledger behaviour: no transaction was submitted to any node, so
  admissibility of large post-quantum transactions is UNVERIFIED.
- Real validator storage growth over time (projected arithmetically
  only — see `model.md`).
