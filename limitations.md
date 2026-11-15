# Limitations: what was NOT verified

## Unverified items (never stated as fact elsewhere in the pack)

1. **Per-transaction byte-size cap — unknown.** No explicit
   per-transaction byte-size cap was found in the postfiatd source
   (shallow clone, HEAD `0085a1f`, greps over `src/xrpld/app/tx/`,
   `TxQ.cpp`, `STTx.h`): only queue-count limits exist
   (`reduce_relay::MAX_TX_QUEUE_SIZE = 10000` transactions,
   `src/xrpld/overlay/ReduceRelayCommon.h:59`; TxQ dynamic size limit;
   10 queued transactions per account). Whether the peer overlay
   imposes a maximum message/blob size that would cap a single
   transaction was not verified. Admissibility of a large ML-DSA-signed
   transaction is therefore UNVERIFIED. The honest empirical test —
   submit a large ML-DSA-signed transaction to a devnet node and
   observe accept/reject — was not run (no live node was available to
   this pack).

2. **No native ML-DSA timing on validator hardware.** All
   verification-throughput figures are a calibrated MODEL from
   published measurements on other hardware (MDPI 2025 server E1;
   H33 AWS Graviton4; cryptoai.wtf Apple M3 Max; FastPay fleet,
   CPU unspecified). No ML-DSA library was run here, and a pure-Python
   reference implementation was deliberately not used as a timing
   proxy. The two published ML-DSA-65 verify figures differ by 2.5x
   (0.06 ms vs 24 µs), which bounds the precision of any single
   throughput number in this pack.

3. **No SLH-DSA performance numbers.** No published SLH-DSA
   verification (or signing) time was extracted in the source set.
   SLH-DSA is excluded from the cost model entirely; its size impact
   is assessed, its time impact is not.

4. **No ML-DSA-87 or secp256k1 verify times** in the source set;
   both are excluded from the calibrated model.

5. **No batch verification for ML-DSA/SLH-DSA** exists in the
   standards (FIPS 204 §5.3, FIPS 205: single-signature verification
   only). Batching figures in this pack are simulation-only with a
   stated 0.8x amortized factor (ASSUMED), not a measured gain.

6. **No post-quantum aggregation scheme is standardized.** Any
   lattice-based multi-signature or hash-based aggregation proposal is
   research-stage; none is presented as deployable.

7. **No size-proportional fee exists.** XRPL/postfiatd fees are
   count-based; a size-proportional fee would require a protocol
   change (new transaction-cost rule / amendment). Framed here as a
   design option, not an existing mechanism.

## Inconsistencies and caveats found (disclosed, not resolved)

8. **`FeeEscalation.md` self-contradiction.** §"Fee Escalation" step 5
   states a minimum `lastLedgerMedianFeeLevel` of **128,000**, while
   §"Other Constants" states "Minimum `lastLedgerMedianFeeLevel`. The
   value of **500** was chosen…". The two figures disagree (possibly
   different units/versions of the doc). Neither is quoted as settled
   anywhere in this pack; resolving it requires reading `TxQ` /
   `LoadFeeTrack` code, which was not done.

9. **`FeeEscalation.md` worked example not reproducible from the doc
   alone.** The cold-start example (limit 6, 8th transaction ~level
   174,000, ~6,800 drops; 20th ~level 1,283,000, ~50,000 drops) is
   quoted as cited, not recomputed, because the doc's cold-start
   median fee level is not stated. The harness implements the formula
   and verifies it against its own stated inputs instead.

10. **SEC 2 PDF not directly read.** secp256k1 sizes in this pack come
    from postfiatd `PublicKey.h` (33-byte compressed key, read
    directly) and secp256k1 crate docs (compact signature 64 B; DER
    68–72 B). Any direct SEC 2 page citation would be UNVERIFIED.

11. **RFC 9881 and RFC 9591 not directly read.** RFC 9881 (pure
    ML-DSA in X.509) is cited via secondary sources; RFC 9591 (BLS)
    content/status via the RFC record and secondary summaries. The BLS
    rejection rests on the pairing-based construction (stated in the
    RFC record) plus the IACR SoK summary, not on a direct reading.

12. **NIST IR 8547 not directly read.** The transition timeline
    (deprecation after 2030, disallowance after 2035) is per secondary
    summaries; the IR itself was not opened and is not used for any
    pack claim.

13. **No full diff of postfiatd against upstream rippled was run.**
    The claim is "no fee/transaction-size/signature divergence found
    in the files examined", not "zero divergence overall".

14. **GitHub code search returned 0 results even for terms known to
    exist in the repo** (e.g. `LoadFeeTrack`) during research; code-search
    negatives were treated as unreliable and the local grep was relied
    on instead.

15. **Workload assumption.** 1,500 TPS and 4-second ledgers come from
    the postfiatd README, not from a measurement here. Real traffic
    mixes transaction types, multi-signing, and idle periods; ledger
    growth on a live network will differ from the projections.

16. **Stand-in hashing is not verification.** The measured hashing
    workload in `bench.py` times `hashlib.sha256` over signature-sized
    buffers. It measures the machine and the timing methodology; it
    says nothing about ML-DSA verification cost. It is labelled as a
    stand-in everywhere it appears.

17. **Compression test uses stand-in bytes.** zlib was applied to
    deterministic pseudo-random bytes (hashlib counter mode), not to
    real ML-DSA signatures. Real ML-DSA signatures are also
    near-uniform lattice vectors, so the ~0% result is expected to
    transfer — but it is a stand-in measurement, and it is labelled as
    one. Compression of the full transaction (including structured
    fields) was not tested; structured fields may compress slightly,
    but the signature bytes — the dominant share — will not.

## Failed / inconclusive checks

None. The final run passed **38/38 checks** (`outputs/run-summary.json`,
overall PASS). The items above are gaps in what could be verified, not
harness failures; they are listed here precisely so they are not
mistaken for established facts.

## Reproducibility note: timing-varying outputs

`outputs/bench.json`, `outputs/bench.log`, and `outputs/run.log` contain
wall-clock timing medians that vary ~1% between runs (timing noise).
Re-running `python3 scripts/run_all.py` regenerates them with slightly
different medians; the check outcomes (38/38 PASS) and all other outputs
are byte-identical across runs. Those three files are therefore excluded
from `DIGESTS.txt` (see its header); every other file is digested and
`sha256sum -c DIGESTS.txt` passes after any re-run. `run-summary.json`
is timestamp-free by design so that it, too, is byte-identical.
