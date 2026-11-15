# Mitigations: aggregation, hybrid signatures, batching, compression

Script: `scripts/mitigations.py`. Output: `outputs/mitigations.json`.
Each mitigation is reported with what was actually done — measured,
simulated with a stated assumption, or rejected with the reason — and
nothing is implied to work that was not shown to work.

## 1. Compression — MEASURED, does not work

Method: zlib (levels 1/6/9) applied to deterministic stand-in signature
bytes of each scheme's size (hashlib counter mode, fixed seed), so the
result is reproducible. Real `zlib.compress` output, not a model.

Results (zlib level 9):

| Scheme | Signature (B) | Compressed (B) | Change |
|---|---|---|---|
| Ed25519 | 64 | 75 | +17.19% (larger) |
| secp256k1 | 64 | 75 | +17.19% (larger) |
| ML-DSA-44 | 2,420 | 2,431 | +0.45% (larger) |
| ML-DSA-65 | 3,309 | 3,320 | +0.33% (larger) |
| ML-DSA-87 | 4,627 | 4,638 | +0.24% (larger) |
| SLH-DSA-128s | 7,856 | 7,867 | +0.14% (larger) |
| SLH-DSA-128f | 17,088 | 17,104 | +0.09% (larger) |
| SLH-DSA-192s | 16,224 | 16,235 | +0.07% (larger) |
| SLH-DSA-192f | 35,664 | 35,685 | +0.06% (larger) |
| SLH-DSA-256s | 29,792 | 29,808 | +0.05% (larger) |
| SLH-DSA-256f | 49,856 | 49,882 | +0.05% (larger) |

Every scheme gets *larger* after compression; zlib framing overhead
exceeds any redundancy it can find. This is the expected result:
post-quantum signatures are near-maximally compressed lattice/hash
vectors with negligible redundancy. No standardized compression for
ML-DSA signatures exists in FIPS 204. **Verdict: compression is not a
viable mitigation.** The Ed25519 figure (+17.19%) is zlib framing
overhead dominating at 64 bytes, not a property of Ed25519 signatures.

## 2. Hybrid / composite signatures — DERIVED sizing, larger not smaller

Method: exact byte arithmetic from the verified sizes —
composite signature = ML-DSA signature + classical signature + 8 bytes
ASSUMED framing; composite public key likewise.

| Composite | Signature (B) | vs pure ML-DSA | Extra bytes |
|---|---|---|---|
| ML-DSA-44 + Ed25519 | 2,492 | 1.030x | +72 |
| ML-DSA-44 + secp256k1 | 2,492 | 1.030x | +72 |
| ML-DSA-65 + Ed25519 | 3,381 | 1.022x | +72 |
| ML-DSA-65 + secp256k1 | 3,381 | 1.022x | +72 |
| ML-DSA-87 + Ed25519 | 4,699 | 1.016x | +72 |
| ML-DSA-87 + secp256k1 | 4,699 | 1.016x | +72 |

A composite signature is always larger than the pure ML-DSA signature
it contains. It buys migration safety — protection against a break or
catastrophic bug in ML-DSA — not size. Status:
`draft-ietf-lamps-pq-composite-sigs`, latest revision -19, in IESG
evaluation; **not an RFC and not a NIST standard**. The draft's own
limitation, flagged in IESG review: composite ML-DSA offers EUF-CMA
but **not SUF-CMA** (strong existential unforgeability), unlike pure
ML-DSA. Pure ML-DSA in X.509 is RFC 9881 (October 2025) — not directly
read here; see `limitations.md`. **Verdict: hybrid signatures are a
migration-safety tool, not a size mitigation.**

## 3. Batching — SIMULATION ONLY, no standardized mechanism

FIPS 204 (§5.3) specifies single-signature verification only (Algorithm
3, ML-DSA.Verify). No batch-verification procedure for ML-DSA exists in
FIPS 204, and FIPS 205 likewise specifies single-signature verification
only. No batch-verification performance figure was found in the sources
read.

What this pack does instead: apply a **stated ASSUMED amortized factor
of 0.8x** (a hypothetical 20% per-signature saving) to the calibrated
model, to show what a batch mechanism would need to deliver. Every
batching figure is labelled SIMULATION ONLY.

| Scheme | Single verify (MODEL) | Simulated batched (0.8x) |
|---|---|---|
| Ed25519 | 18,868 /s/core | 23,585 /s/core |
| ML-DSA-44 | 25,000 /s/core | 31,250 /s/core |
| ML-DSA-65 | 16,667 /s/core | 20,833 /s/core |

**Verdict: batch verification is rejected as a standardized mechanism.**
The simulated figures are an illustration of the required gain, not a
measured gain and not an available optimization. Any real batching
claim for ML-DSA would need a cited construction outside the standard.

Parallel verification across cores is a separate, real deployment
lever: verification of independent transactions parallelizes, and the
MODEL scales linearly with core count (an assumption, not a measured
validator result). On the 4-core machine used here the model gives
~66,667 ML-DSA-65 verifies/second. This is a deployment fact, not a
cryptographic batching gain.

## 4. Aggregation — REJECTED

### BLS aggregation: rejected (not post-quantum)

BLS (RFC 9591, IETF CFRG 2025) supports non-interactive aggregation:
many signatures combine into one short aggregate (96 bytes). But BLS
rests on elliptic-curve pairings (BLS12-381), and Shor's algorithm
breaks elliptic-curve discrete logarithms. BLS therefore offers **no
quantum resistance**. Corroborated by the IACR ePrint 2026/2222 SoK
summary ("BLS12-381 | Pairings | Broken by Shor | signature 96 B").
**Verdict: rejected as a post-quantum mitigation.** It is a classical
compression technique only. The 96-byte aggregate is shown here only
as a contrast case: it illustrates what aggregation *could* do if a
post-quantum aggregate scheme existed — it does not.

### Post-quantum aggregation: rejected (no standardized scheme)

No post-quantum signature aggregation scheme is a NIST standard.
ML-DSA and SLH-DSA have no standardized aggregate form. Lattice-based
multi-signatures and hash-based aggregation via pqSNARKs are
research-stage. **Verdict: rejected as an available mitigation.** No
simulation is offered for a construction that does not exist in
deployable form.

## 5. Smaller parameter set — viable, with a policy cost

ML-DSA-44 instead of ML-DSA-65 saves **889 bytes per signature**
(2,420 vs 3,309; DERIVED) and reduces the model transaction from
5,461 to 3,932 bytes. The cost is security category 2 instead of 3
(FIPS 204 §4). Whether category 2 is acceptable for this ledger is a
policy decision, not a sourced fact. SLH-DSA-128s has a 32-byte public
key but a 7,856-byte signature; it is only sensible where signing is
rare (root keys, validator admission receipts), not for
per-transaction signing at volume.

## 6. Off-consensus certificate lanes — strongest project-grounded option

The PostFiat FastPay latency series measures the structural mitigation
the project itself uses: move settlement to quorum certificates off
the consensus path. Measured there: certificates ~15 KB (4× ML-DSA-65
signatures); cryptography ~2% of latency, network ~96%; owned-lane
p50 55 ms (n=25,000, 3-validator Hetzner EU WAN testnet). Per-transaction
signature bytes stop consuming consensus/ledger capacity because the
ledger records the certificate, not every individual signature. This
addresses the byte-volume problem at the architecture level — the level
where the problem actually lives, since the fee mechanism prices
transactions, not bytes, and verification is not the bottleneck.

## Summary table

| Mitigation | Status | Effect on size / cost |
|---|---|---|
| Compression (zlib) | MEASURED — fails | +0.33% for ML-DSA-65 (larger) |
| Hybrid/composite | DERIVED — larger | ML-DSA-65+Ed25519 3,381 B (1.022x pure) |
| Batch verification | REJECTED as standardized; simulation only | Hypothetical 0.8x factor → 20,833/s/core (simulated) |
| Parallel verification | MODEL deployment lever | Linear with cores (assumed) |
| BLS aggregation | REJECTED — not post-quantum | 96 B aggregate, but broken by Shor |
| PQ aggregation | REJECTED — no standard | No deployable construction |
| Smaller parameter set (ML-DSA-44) | Viable, policy cost | −889 B/signature; category 2 vs 3 |
| Off-consensus certificate lanes | Measured by the project (FastPay) | Removes per-tx bytes from consensus path |
| Size-proportional fee | Design option, needs protocol change | No such amendment exists |
