# Model: ledger growth, validation cost, fee market, spam resistance

Every model input is tagged **MEASURED**, **MODEL** (calibrated from a
published measurement), **DERIVED** (arithmetic shown), or **ASSUMED**
(stated input). The model is built from the harness outputs
(`outputs/sizes.json`, `outputs/bench.json`, `outputs/fees.json`) and
nothing else. Scripts: `scripts/sizes.py`, `scripts/bench.py`,
`scripts/fees.py`.

## Inputs

| Input | Value | Tag | Source |
|---|---|---|---|
| ML-DSA-65 signature | 3,309 B | MEASURED (spec) | FIPS 204 Table 2 |
| ML-DSA-65 public key | 1,952 B | MEASURED (spec) | FIPS 204 Table 2 |
| Ed25519 signature / wire key | 64 B / 33 B | MEASURED (spec) | RFC 8032 §7; PublicKey.h |
| SLH-DSA signatures | 7,856–49,856 B | MEASURED (spec) | FIPS 205 Table 2 |
| Base transaction overhead | 200 B | ASSUMED | Uniform modelling input |
| Throughput | 1,500 TPS | ASSUMED | postfiatd README |
| Ledger close time | 4 s | ASSUMED | postfiatd README |
| Reference fee | 10 drops | MEASURED (source) | Config.h; xrpl.org |
| Base fee level | 256 | MEASURED (source) | FeeEscalation.md |
| Open-ledger limit (target / min) | 50 / 5 | MEASURED (source) | FeeEscalation.md |
| ML-DSA-65 verify | 0.06 ms | MODEL | MDPI 2025, liboqs 0.7.2 |
| ML-DSA-44 verify | 0.040 ms | MODEL | cryptoai.wtf, M3 Max |
| Ed25519 verify | 0.053 ms | DERIVED | H33 (24 µs × 2.2) |
| ML-DSA-87 / secp256k1 verify | — | UNVERIFIED | No figure in source set |
| SLH-DSA verify | — | UNVERIFIED | No figure in source set |

## 1. Ledger growth

Model: `bytes/day = model_tx_bytes × TPS × 86,400`, with
`model_tx_bytes = 200 + wire_public_key + signature` (DERIVED).

At 1,500 TPS (ASSUMED):

| Scheme | Model tx (B) | Bytes/ledger (4 s) | Bytes/day |
|---|---|---|---|
| Ed25519 | 297 | 1,782,000 | 38,491 MB |
| ML-DSA-44 | 3,932 | 23,592,000 | 509,587 MB |
| ML-DSA-65 | 5,461 | 32,766,000 | 707,746 MB |
| ML-DSA-87 | 7,419 | 44,514,000 | 961,502 MB |
| SLH-DSA-128s | 8,088 | 48,528,000 | 1,048,205 MB |
| SLH-DSA-256f | 50,120 | 300,720,000 | 6,495,552 MB |

Signature bytes alone per day at 1,500 TPS (DERIVED): Ed25519 8,294
MB; ML-DSA-65 428,846 MB; SLH-DSA-256f 6,461,338 MB. At 1,500 TPS a
single day of ML-DSA-65 transactions is ~708 GB of ledger stream, vs
~38.5 GB for Ed25519 — an 18.4x increase that compounds every day a
validator must store, relay, and re-verify history. This is a
bandwidth/storage arithmetic consequence, not a measurement on a live
ledger (see `limitations.md`).

Sensitivity: the 200-byte base overhead is the only ASSUMED input in
this table. At 0-byte base the ML-DSA-65/Ed25519 transaction ratio is
54.2x; at 200 bytes it is 18.4x; at 1,000 bytes it would be 6.4x.
The signature ratio (51.7x) is assumption-free and bounds the
worst case: as transactions get larger for other reasons, the
signature share shrinks, but the absolute extra bytes per transaction
(5,164 B for ML-DSA-65 vs Ed25519) never change.

Validator-storage note: a ML-DSA private key may be stored as a
32-byte seed (FIPS 204 §4), so key storage is not the problem — the
problem is the per-transaction signature bytes replicated to every
validator and stored in every ledger.

## 2. Validation cost

Model: `verifies/second/core = 1,000 / verify_ms` (DERIVED from the
calibrated MODEL inputs).

| Scheme | Verify (ms) | Verifies/s/core (MODEL) | Share of 1,500 TPS on 1 core |
|---|---|---|---|
| Ed25519 | 0.053 | 18,868 | 7.9% |
| ML-DSA-44 | 0.040 | 25,000 | 6.0% |
| ML-DSA-65 | 0.060 | 16,667 | 9.0% |

At the calibrated values, one core verifies ~16,667 ML-DSA-65
signatures per second — 11.1x the 1,500 TPS workload. Validation
latency is not the binding constraint at this workload; ledger byte
volume is. The model is sensitive to the hardware spread in the
published figures: H33 measured 24 µs median ML-DSA-65 verify on
Graviton4 (41,667/s/core), 2.5x faster than the 0.06 ms server-E1
figure used as the primary calibration. Either figure leaves the same
conclusion (verification keeps up; bytes do not).

Caveats: the model assumes verification cost scales linearly with
transaction count and ignores deserialization, ledger-state access,
and network relay, all of which grow with transaction size. Parallel
verification across cores is a deployment lever (MODEL: linear scaling
assumed, not measured on validator hardware). Multi-signature
transactions pay a multiple of the reference fee and a multiple of
the verification cost — the model above is single-signature.

## 3. Fee market

Model (from `FeeEscalation.md`, implemented in `scripts/fees.py`):

- Base: fee level 256 = 10 drops for a reference transaction.
- Beyond the open-ledger limit L, required level =
  `median_level × (n/L)²` where n is transactions in the open ledger.
- Drops = `level / 256 × 10`.

Worked curve at limit 50, median level 256 (DERIVED):

| Transactions in open ledger | Required level | Required fee (drops) |
|---|---|---|
| ≤ 50 | 256 | 10 |
| 51 | 266.3 | 10.4 |
| 60 | 368.6 | 14.4 |
| 100 | 1,024 | 40 |
| 200 | 4,096 | 160 |
| 500 | 25,600 | 1,000 |

Key structural result: the fee depends on the *count* of transactions
in the open ledger, not on their byte size. A ledger at the 50-tx
limit holds 14,850 bytes of Ed25519 transactions or 273,050 bytes of
ML-DSA-65 transactions — an 18.4x difference in bytes admitted before
any escalation — for the same 10-drop fee. Escalation bites later in
byte terms under post-quantum signatures, because the limit counts
transactions. The queue (next 20 ledgers, minimum 2,000 transactions,
max 10 per account) likewise counts transactions, not bytes.

A size-proportional fee would require a protocol change (a new
transaction-cost rule, presumably via amendment). No such amendment
exists in postfiatd or rippled. It is a design option, not an existing
mechanism, and this pack does not claim otherwise.

## 4. Spam resistance

Model: `drops per 1 MB = (1,000,000 / model_tx_bytes) × 10` at base
load (DERIVED).

| Scheme | Tx per 1 MB | Drops per 1 MB | Cost ratio vs Ed25519 |
|---|---|---|---|
| Ed25519 | 3,367 | 33,670 | 1.0x |
| ML-DSA-44 | 254 | 2,540 | 13.3x cheaper |
| ML-DSA-65 | 183 | 1,830 | 18.4x cheaper |
| ML-DSA-87 | 134 | 1,340 | 25.1x cheaper |
| SLH-DSA-128s | 123 | 1,230 | 27.4x cheaper |
| SLH-DSA-256f | 19 | 190 | 177.2x cheaper |

Under a count-based fee, the cost of adding a megabyte of ledger
falls in direct proportion to signature size. An attacker buying
ledger bloat gets the same leverage as a legitimate user. The
mitigations that address this are structural (off-consensus
certificate lanes, a size-aware fee rule via protocol change), not
cryptographic — no signature scheme makes a megabyte cheaper to
verify, and compression (measured: no reduction) does not help.

## 5. What the model cannot say

- Whether a 5,461-byte (or 50,120-byte) transaction is admissible at
  all: no per-transaction byte cap was found; admissibility is
  UNVERIFIED.
- Real validator throughput under post-quantum load: the cost model is
  calibrated from other hardware, not measured on a validator.
- Ledger growth on a live network: projections assume a sustained
  1,500 TPS of single-signature payment-style transactions; real
  traffic mixes transaction types, multi-signing, and idle periods.
- Fee behaviour under sustained overload: the escalation curve is
  implemented from the documented formula, but the doc's own worked
  cold-start example could not be reproduced from the doc alone
  (median level unstated), and the doc contradicts itself on the
  minimum median fee level (see `limitations.md`).
