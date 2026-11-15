# Findings: PFTL Post-Quantum Ledger Impact Assessment

All quantitative claims in this document are traceable to `outputs/`,
`scripts/`, or a primary source in `sources.md`. Labels: **MEASURED**
(produced by this harness), **MODEL** (calibrated from published
measurements), **DERIVED** (arithmetic shown), **ASSUMED** (stated
modelling input), **UNVERIFIED** (not confirmed — never stated as fact).
The claim-to-evidence index is `claims.md`.

## 1. Pinned transaction and fee sources

The ledger examined is postfiatd, a fork of rippled. Its README states
it directly: "a fork of rippled server. Shared code and documentation
will still have mentions of rippled and XRP. Any mention of rippled
applies to postfiatd and mention of XRP asset applies to the native
asset."

Fee machinery verified present in the checked tree (commit `0085a1f`,
"Merge pull request #50", checked 2026-11-15):

- `src/xrpld/core/Config.h:69` — `XRPAmount reference_fee{10};`
  (default reference fee **10 drops**).
- `src/xrpld/app/misc/FeeEscalation.md` — base fee level **256**;
  open-ledger limit minimum **5**, target **50** (grows 20% when healthy,
  shrinks 50% when unhealthy); quadratic escalation beyond the limit;
  transaction queue holds transactions for the next **20 ledgers**
  (minimum 2,000 transactions), retry up to **10** times, max **10**
  queued transactions per account, replacement requires a **25% higher**
  fee level.
- `FeeEscalation` amendment present
  (ID `42426C4D4F1009EE67080A9B7965B44656D7714D104A72F9B4369F97ABF044EE`).
- Only two signature systems exist in
  `include/xrpl/protocol/PublicKey.h`: secp256k1 and ed25519. Both are
  stored as 33-byte wire-form public keys (Ed25519 prefixed with `0xED`).

**postfiatd contains no ML-DSA code.** A case-insensitive grep for
`ML-DSA|Dilithium|MLDSA` across `src/` and `include/` at commit
`0085a1f` returned zero matches. The whitepaper's "ML-DSA-65 from
genesis" is therefore a design statement implemented (if anywhere) in the
separate postfiatl1v2 codebase, not in postfiatd. No fee,
transaction-size, or signature-related divergence from upstream rippled
was found in the files examined (a full diff against the pinned upstream
commit was not run — the claim is "no divergence found in the files
examined", not "zero divergence overall").

## 2. Signature sizes (verified, FIPS 204 / FIPS 205 / RFC 8032)

| Scheme | Public key (B) | Signature (B) | Signature vs Ed25519 |
|---|---|---|---|
| Ed25519 (RFC 8032 §7) | 32 (33 wire) | 64 | 1.0x |
| secp256k1 (compact) | 33 | 64 (DER 68–72) | 1.0x |
| ML-DSA-44 (FIPS 204) | 1,312 | 2,420 | 37.8x |
| ML-DSA-65 (FIPS 204) | 1,952 | 3,309 | 51.7x |
| ML-DSA-87 (FIPS 204) | 2,592 | 4,627 | 72.3x |
| SLH-DSA-128s (FIPS 205) | 32 | 7,856 | 122.8x |
| SLH-DSA-128f (FIPS 205) | 32 | 17,088 | 267.0x |
| SLH-DSA-192s (FIPS 205) | 48 | 16,224 | 253.5x |
| SLH-DSA-192f (FIPS 205) | 48 | 35,664 | 557.2x |
| SLH-DSA-256s (FIPS 205) | 64 | 29,792 | 465.5x |
| SLH-DSA-256f (FIPS 205) | 64 | 49,856 | 779.0x |

Security categories (FIPS 204 §4; FIPS 205 §11): ML-DSA-44 category 2,
ML-DSA-65 category 3, ML-DSA-87 category 5; SLH-DSA-128* category 1,
192* category 3, 256* category 5. A ML-DSA private key may be stored as
a 32-byte seed (FIPS 204 §4) — relevant to validator storage, not to
on-ledger size.

## 3. Measured transaction sizes and ledger growth (DERIVED)

Model transaction = ASSUMED 200-byte base overhead + wire-form public
key + signature. The base overhead is applied uniformly, so every ratio
is driven by the verified sizes. Script: `scripts/sizes.py`;
output: `outputs/sizes.json`.

| Scheme | Model tx (B) | Tx vs Ed25519 | Ledger bytes/day at 1,500 TPS |
|---|---|---|---|
| Ed25519 | 297 | 1.0x | 38,491 MB (~38.5 GB) |
| secp256k1 | 297 | 1.0x | 38,491 MB |
| ML-DSA-44 | 3,932 | 13.2x | 509,587 MB (~510 GB) |
| ML-DSA-65 | 5,461 | 18.4x | 707,746 MB (~708 GB) |
| ML-DSA-87 | 7,419 | 25.0x | 961,502 MB (~962 GB) |
| SLH-DSA-128s | 8,088 | 27.2x | 1,048,205 MB (~1.05 TB) |
| SLH-DSA-128f | 17,320 | 58.3x | 2,244,672 MB (~2.24 TB) |
| SLH-DSA-192s | 16,472 | 55.5x | 2,134,771 MB (~2.13 TB) |
| SLH-DSA-192f | 35,912 | 120.9x | 4,654,195 MB (~4.65 TB) |
| SLH-DSA-256s | 30,056 | 101.2x | 3,895,258 MB (~3.90 TB) |
| SLH-DSA-256f | 50,120 | 168.8x | 6,495,552 MB (~6.50 TB) |

Per 4-second ledger at 1,500 TPS (6,000 transactions): Ed25519
1,782,000 bytes; ML-DSA-65 32,766,000 bytes (~32.8 MB); SLH-DSA-256f
300,720,000 bytes (~301 MB). Signature bytes alone per day at 1,500
TPS: Ed25519 8,294 MB; ML-DSA-65 428,846 MB (~429 GB); SLH-DSA-256f
6,461,338 MB (~6.46 TB).

Whitepaper cross-check (DERIVED): the whitepaper (§1.11) states a
quorum of q=24 from 35 validators carries 24 × 3,309 = **79,416**
signature bytes, and that prepare and precommit sets double that before
framing. The harness reproduces 24 × 3,309 = 79,416 exactly
(`outputs/sizes.json`, check `whitepaper_quorum_arithmetic`). The
whitepaper also states "this byte cost dominates the operational price
of the choice" — consistent with the ledger-growth figures above.

The whitepaper states no throughput figure (the word "throughput" does
not appear in it), no fee schedule, and no transaction-size limit. The
1,500 TPS / 4–5 second figures are from the postfiatd README and are
used here as workload ASSUMPTIONS, not measurements.

## 4. Verification cost and throughput (MODEL + MEASURED stand-in)

No native ML-DSA library was run and no library timing was fabricated.
A pure-Python reference implementation would be orders of magnitude
slower than any production implementation and would say nothing about
validator hardware, so it was deliberately not attempted. Instead:

- **MEASURED stand-in:** `scripts/bench.py` times `hashlib.sha256` over
  deterministic signature-sized buffers (warmup 200, 2,000 iterations,
  `time.perf_counter_ns`). This measures the machine and the timing
  methodology, not ML-DSA. Median per hash: 0.64 µs (64 B) rising to
  53.61 µs (49,856 B) on this machine. Full table in
  `outputs/bench.json` and `outputs/bench.log`.
- **MODEL throughput:** per-operation verify times taken from published
  measurements, each tagged with source/hardware/implementation:
  - ML-DSA-65 verify **0.06 ms** — MDPI *Cryptography* 2025, 9, 32,
    Table 14, liboqs 0.7.2, server E1 (sign 0.11 ms).
  - ML-DSA-65 verify **24 µs** median — H33 benchmark, 2026-05-23, AWS
    Graviton4, 1,000,000 samples (sign 72 µs).
  - ML-DSA-44 verify **0.040 ms** — cryptoai.wtf, 2026-04-02, Apple M3
    Max, liboqs (sign 0.165 ms).
  - ML-DSA-65 signing **0.52 ms** per validator signature — PostFiat
    FastPay latency series, fleet hardware, CPU unspecified.
  - Ed25519 verify **0.053 ms** — DERIVED from H33 ("ML-DSA-65 verify
    latency is 2.2x faster than Ed25519 verify" on Graviton4:
    24 µs × 2.2 = 52.8 µs).

Calibrated MODEL verify throughput, single core:

| Scheme | Verify (ms) | Verifies/second/core (MODEL) |
|---|---|---|
| Ed25519 | 0.053 (DERIVED) | 18,867.9 |
| ML-DSA-44 | 0.040 | 25,000.0 |
| ML-DSA-65 | 0.060 | 16,666.7 |
| ML-DSA-87 | — (UNVERIFIED) | — |
| secp256k1 | — (UNVERIFIED) | — |

**Interpretation:** at the calibrated model values, a single core
verifies ~16,667 ML-DSA-65 signatures per second — more than 11x the
1,500 TPS workload assumption. Verification latency is not the
bottleneck; ledger byte volume is. The two published ML-DSA-65 verify
figures (0.06 ms on server E1 vs 24 µs on Graviton4) differ by 2.5x
across hardware/implementations, which bounds how precisely any
single throughput number should be trusted. No published SLH-DSA
verification time was found in the source set; SLH-DSA is excluded from
the cost model (UNVERIFIED).

## 5. Fee market (count-based, not byte-based)

Implemented in `scripts/fees.py` from `FeeEscalation.md` and
`Config.h`; output `outputs/fees.json`.

- Reference fee **10 drops**; base fee level **256** (level 256 = 10
  drops; level 25,600 = 1,000 drops).
- Required fee level beyond the open-ledger limit =
  `lastLedgerMedianFeeLevel × (txInOpenLedger² / limit²)` (quadratic).
  At limit 50 with median level 256: 50 tx → level 256 (10 drops);
  100 tx → level 1,024 (40 drops); 200 tx → level 4,096 (160 drops);
  500 tx → level 25,600 (1,000 drops).
- **Base fee is identical for every scheme: 10 drops.** A 3,309-byte
  ML-DSA-65 signature costs the same 10 drops as a 64-byte Ed25519
  signature at base load. Any claim that fees rise proportionally to
  signature size is wrong for this fee design — the mechanism is
  count-based, not byte-based.
- Bytes per drop at base load (DERIVED): Ed25519 29.7; ML-DSA-44 393.2;
  ML-DSA-65 546.1; ML-DSA-87 741.9; SLH-DSA-128s 808.8; SLH-DSA-256f
  5,012.0. Post-quantum signatures buy ~18–169x more ledger bytes per
  unit of fee destroyed.
- The `FeeEscalation.md` worked cold-start example (limit 6, minimal
  median fee: 8th transaction ~level 174,000, ~6,800 drops; 20th
  ~level 1,283,000, ~50,000 drops) is quoted in `outputs/fees.json`
  as cited, not recomputed — the doc's cold-start median level is not
  stated, so the arithmetic cannot be reproduced from the doc alone.

## 6. Spam resistance

Cost to add 1 MB of ledger bytes at base load (DERIVED, `outputs/fees.json`):

| Scheme | Transactions per 1 MB | Drops per 1 MB | XRP per 1 MB |
|---|---|---|---|
| Ed25519 | 3,367 | 33,670 | 0.0337 |
| ML-DSA-44 | 254 | 2,540 | 0.0025 |
| ML-DSA-65 | 183 | 1,830 | 0.0018 |
| ML-DSA-87 | 134 | 1,340 | 0.0013 |
| SLH-DSA-128s | 123 | 1,230 | 0.0012 |
| SLH-DSA-256f | 19 | 190 | 0.0002 |

Spamming 1 MB of ledger via ML-DSA-65 costs **~18.4x less** than via
Ed25519 (33,670 / 1,830). The count-based fee gives an attacker the
same ledger-bloat leverage as a legitimate user: the fee burn per byte
falls in direct proportion to signature size. Two consequences follow
from the mechanism itself: (a) large-signature spam reaches the
quadratic escalation sooner in *byte* terms but not in *count* terms —
the open-ledger limit counts transactions, so a ledger can fill with
far more bytes before escalation bites; (b) a size-proportional fee
would require a protocol change (a new transaction-cost rule / an
amendment), not a configuration change — no such amendment exists in
postfiatd or rippled, so it is framed here as a design option, not an
existing mechanism.

## 7. Mitigations

Full detail in `mitigations.md`; script `scripts/mitigations.py`;
output `outputs/mitigations.json`.

### Measured: compression — does not work

zlib (levels 1/6/9) on deterministic stand-in signature bytes
(MEASURED): ML-DSA-65 3,309 B → 3,320 B at level 9 (**+0.33%**, i.e.
larger); ML-DSA-44 +0.45%; ML-DSA-87 +0.24%; SLH-DSA-256f +0.05%;
Ed25519 64 B → 75 B (+17.19% — zlib framing overhead dominates at
tiny sizes). Post-quantum signatures are near-maximally compressed
lattice/hash vectors; no standardized ML-DSA compression exists in
FIPS 204. Compression is a dead end for this problem.

### Measured arithmetic: hybrid/composite signatures — larger, not smaller

Composite = ML-DSA signature + classical signature + 8 bytes ASSUMED
framing (DERIVED): ML-DSA-65+Ed25519 = **3,381 B (1.022x pure
ML-DSA)**; ML-DSA-44+Ed25519 = 2,492 B (1.030x); ML-DSA-87+Ed25519 =
4,699 B (1.016x). A composite buys migration safety (protection
against a break or catastrophic bug in ML-DSA), not size. Status:
`draft-ietf-lamps-pq-composite-sigs-19`, in IESG evaluation — **not an
RFC, not a NIST standard**. The draft's own limitation, flagged in
IESG review: composite ML-DSA offers EUF-CMA but **not SUF-CMA**
(strong existential unforgeability), unlike pure ML-DSA.

### Simulation-only: batching

FIPS 204 (§5.3) specifies **single-signature verification only**; no
batch-verification procedure exists in FIPS 204 or FIPS 205. The pack
simulates a hypothetical amortized factor of **0.8x** (ASSUMED 20%
saving) applied to the calibrated model: ML-DSA-65 16,667 →
20,833 verifies/second/core (SIMULATION ONLY). This is what a batch
mechanism would need to deliver; it is not a measured gain and not a
standardized mechanism. Parallel verification across cores is a real
deployment lever (MODEL: linear scaling with core count is an
assumption, not a measured validator result) — on the 4-core machine
used here, model throughput is ~66,667 ML-DSA-65 verifies/second.

### REJECTED: BLS aggregation

BLS (RFC 9591) supports non-interactive aggregation — many signatures
into one 96-byte aggregate — but it rests on elliptic-curve pairings
(BLS12-381). Shor's algorithm breaks elliptic-curve discrete
logarithms, so BLS offers **no quantum resistance**. It is a classical
compression technique only and cannot be the post-quantum answer. The
96-byte figure is included only as a contrast case.

### REJECTED: post-quantum aggregation

No post-quantum signature aggregation scheme is a NIST standard.
ML-DSA and SLH-DSA have no standardized aggregate form. Lattice-based
multi-signatures and hash-based aggregation via pqSNARKs are
research-stage; no deployable construction is presented here.

### Smaller parameter set

ML-DSA-44 instead of ML-DSA-65 saves 889 bytes per signature
(2,420 vs 3,309) at security category 2 instead of 3 (verified sizes).
Whether category 2 is acceptable is a policy decision, not a sourced
fact. SLH-DSA-128s has a 32-byte public key but a 7,856-byte
signature; it is only sensible where signing is rare (e.g. root or
validator admission receipts), not for per-transaction signing at
volume.

### Strongest project-grounded mitigation: off-consensus certificate lanes

The PostFiat FastPay latency series demonstrates the structural
mitigation actually measured by the project: move settlement to quorum
certificates off the consensus path (~15 KB certificates carrying 4×
ML-DSA-65 signatures; cryptography ~2% of latency, network ~96%),
so per-transaction signature bytes do not consume consensus/ledger
capacity. This addresses the byte-volume problem at the architecture
level rather than at the signature level.

## 8. Limitations

See `limitations.md` for the full list. The material ones:

- No per-transaction byte-size cap was found; admissibility of large
  post-quantum transactions is UNVERIFIED.
- No native ML-DSA timing on validator hardware; throughput figures are
  a calibrated MODEL.
- No SLH-DSA verification-time figures in the source set.
- `FeeEscalation.md` self-contradiction on the minimum
  `lastLedgerMedianFeeLevel` (128,000 vs 500) unresolved.
- Workload (1,500 TPS, 4-second ledgers) is a stated assumption from
  the postfiatd README, not a measurement.
