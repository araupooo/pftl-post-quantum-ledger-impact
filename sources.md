# Sources: primary-source citations

Every spec-derived claim in this pack traces to one of the entries
below. Status: VERIFIED means read directly from the primary source on
2026-11-15; SECONDARY means the primary is cited by a secondary page
and the number was cross-checked where noted; NOT READ means the item
was not opened directly and is cited only via the source that states
its status — such items are never used as sole support for a claim.

## 1. NIST FIPS 204 — ML-DSA (VERIFIED)

- **Document:** NIST FIPS 204, *Module-Lattice-Based Digital Signature
  Standard*, published and effective 13 August 2024.
- **URL:** https://doi.org/10.6028/NIST.FIPS.204
- **Used for:** Table 2 sizes (ML-DSA-44/65/87 keys and signatures);
  security categories (§4); §3.6.2 length checks; 32-byte seed storage
  (§4); single-signature verification only, Algorithm 3 (§5.3).
- **Access:** full PDF text read directly, 2026-11-15.

## 2. NIST FIPS 205 — SLH-DSA (VERIFIED)

- **Document:** NIST FIPS 205, *Stateless Hash-Based Digital Signature
  Standard*, published and effective 13 August 2024.
- **URL:** https://doi.org/10.6028/NIST.FIPS.205
- **Used for:** Table 2 sizes for all 12 parameter sets (§11);
  categories (n=16 → 1, n=24 → 3, n=32 → 5); 2^64-message key-pair
  limit (footnote 22).
- **Access:** full PDF text read directly, 2026-11-15.

## 3. RFC 8032 — Ed25519 (VERIFIED)

- **Document:** RFC 8032, *Edwards-Curve Digital Signature Algorithm
  (EdDSA)*, IRTF, January 2017.
- **URL:** https://www.rfc-editor.org/rfc/rfc8032.txt
- **Used for:** §1 ("small public keys (32 or 57 bytes) and signatures
  (64 or 114 bytes)"); §7 ("private and public keys are 32 octets;
  signatures are 64 octets"); ~128-bit security (§1).
- **Access:** mirrored text read, §1 and §7, 2026-11-15.

## 4. postfiatd source tree (VERIFIED)

- **Repo:** https://github.com/postfiatorg/postfiatd
- **Commit checked:** `0085a1f` ("Merge pull request #50 from
  postfiatorg/hotfix/upstream-hardening-1.0.9"), 2026-11-15, shallow
  clone (`--depth 1 --filter=blob:none --sparse src include`).
- **Used for:**
  - `README.md` — "a fork of rippled server"; "settles transactions
    in 4 to 5 seconds, processing at a throughput of up to 1500
    transactions per second".
  - `src/xrpld/core/Config.h:69` — `XRPAmount reference_fee{10};`.
  - `src/xrpld/app/misc/FeeEscalation.md` — base fee level 256;
    open-ledger limit min 5 / target 50; quadratic escalation formula;
    worked cold-start example (limit 6, 8th tx ~level 174,000,
    ~6,800 drops; 20th ~level 1,283,000, ~50,000 drops); queue rules
    (20 ledgers, min 2,000 tx, 10 retries, 10 per account, 25%
    replacement premium); consensus "generally takes under 5 seconds",
    upper limit ~20 seconds.
  - `include/xrpl/protocol/PublicKey.h` — only secp256k1 and ed25519
    supported; both stored as 33 bytes; Ed25519 prefixed `0xED`.
  - `src/xrpld/app/misc/detail/LoadFeeTrack.cpp`, `TxQ.cpp`,
    `FeeVoteImpl.cpp` — fee machinery present, matching upstream.
  - **Negative result:** case-insensitive grep for
    `ML-DSA|Dilithium|MLDSA` across `src/` and `include/` returned
    zero matches — no ML-DSA code in the checked tree.
  - **Negative result:** no per-transaction byte-size cap found
    (greps over `src/xrpld/app/tx/`, `TxQ.cpp`, `STTx.h`); only
    count limits (`reduce_relay::MAX_TX_QUEUE_SIZE = 10000`,
    `src/xrpld/overlay/ReduceRelayCommon.h:59`).

## 5. xrpl.org documentation (VERIFIED)

- **"Fee Voting"** — https://xrpl.org/docs/concepts/consensus-protocol/fee-voting
  — reference fee 10 drops; median-of-validators voting, ~every
  15 minutes; SetFee pseudo-transaction.
- **"Transaction Cost"** — https://xrpl.org/docs/references/http-websocket-apis/public-api-methods/server-info-methods/fee
  (and docs) — "The current minimum transaction cost required by the
  network for a standard transaction is 0.00001 XRP (10 drops)."
  "The transaction cost is not paid to any party: the XRP is
  irrevocably destroyed."
- **"Cryptographic Keys"** — https://xrpl.org/docs/concepts/accounts/cryptographic-keys
  — secp256k1 (ECDSA, default) and ed25519 (EdDSA) supported;
  Ed25519 keys prefixed `0xED` so both are 33 bytes; transactions
  carry the signer's public key in `SigningPubKey`.
- **"Known Amendments"** — https://xrpl.org/resources/known-amendments
  — FeeEscalation amendment ID
  `42426C4D4F1009EE67080A9B7965B44656D7714D104A72F9B4369F97ABF044EE`.

## 6. PostFiat whitepaper (VERIFIED)

- **Document:** Post Fiat Whitepaper, "Post Fiat: A Buy-Side Internet
  of Value" — https://postfiat.org/whitepaper/ (677 lines, read
  directly, 2026-11-15).
- **Used for:** Abstract ("Accounts and validators sign with ML-DSA
  from genesis"); §1.11 ("ML-DSA-65 from genesis: 1,952-byte public
  keys, 3,309-byte signatures"; quorum q=24 from 35 carries
  24×3,309=79,416 signature bytes; "this byte cost dominates the
  operational price of the choice"); fee design ("every native fee
  burns, no validator reward exists").
- **Negative results:** the word "throughput" does not appear; no TPS,
  ledger-close-time, transaction-size-limit, per-byte-fee, or fee
  schedule statement; no discussion of SLH-DSA, aggregation, batching,
  or compression.

## 7. PostFiat FastPay latency series (VERIFIED)

- **Article:** "Latency Series II: FastPay — Removing Consensus from
  Owned-Value Settlement" —
  http://postfiat.org/blog/postfiat-l1v2-fastpay-latency/ (read
  directly, 2026-11-15).
- **Used for:** certificate ~15 KB (4× ML-DSA-65 signatures); "ML-DSA-65
  signatures are ~50x larger than ed25519 signatures"; latency shares
  (network ~96%; signatures ~2%); owned-lane p50 55 ms (n=25,000,
  3-validator Hetzner EU WAN testnet); cross-continent p50 183 ms;
  critical-path crypto ~1 ms (3 parallel validator signatures at
  0.52 ms each plus client verification); implementation in
  postfiatl1v2 branch `fastpay-m1`.

## 8. Published ML-DSA performance measurements (VERIFIED)

- **MDPI *Cryptography* 2025, 9, 32** — "A Practical Performance
  Benchmark of Post-Quantum Cryptography Across Heterogeneous
  Computing Environments" (received 25 Mar 2025, published 21 May
  2025). liboqs 0.7.2, Dilithium Level 3 (ML-DSA-65 equivalent):
  Sign 0.11 ms, Verify 0.06 ms, KeyGen 0.07 ms (Table 14).
  https://mdpi-res.com/d_attachment/cryptography/cryptography-09-00032/article_deploy/cryptography-09-00032-v2.pdf
- **H33, "ML-DSA-65 (Dilithium) Performance"**, published 2026-05-23 —
  AWS Graviton4, 1,000,000 samples, median: Sign 72 µs, Verify 24 µs
  (p99 29 µs); "ML-DSA-65 verify latency is 2.2x faster than Ed25519
  verify" on that hardware; round-3 Dilithium3 signature 3,293 B vs
  FIPS 204 ML-DSA-65 3,309 B. https://h33.ai/benchmarks/dilithium/
- **cryptoai.wtf, "The Efficiency of Post-Quantum Signature Schemes"**,
  2026-04-02 — Apple M3 Max, liboqs-based scripts: ML-DSA-44 KeyGen
  0.042 ms / Sign 0.165 ms / Verify 0.040 ms.
  https://cryptoai.wtf/blog/pqc-benchmarks/

## 9. BLS signatures (SECONDARY — RFC 9591 not directly read)

- **RFC 9591, *BLS Signatures*** (IETF CFRG, 2025): pairing-based,
  supports non-interactive aggregation; verification requires pairing
  operations. Content/status via the RFC record and secondary
  summaries; the RFC text itself was not directly read here.
- **IACR ePrint 2026/2222 SoK summary:** "BLS12-381 | Pairings |
  Broken by Shor | signature 96 B" — corroborates that BLS offers no
  quantum resistance.

## 10. Composite / hybrid signatures (VERIFIED status via datatracker)

- **draft-ietf-lamps-pq-composite-sigs** (LAMPS WG) — "Composite
  Module-Lattice-Based Digital Signature Algorithm (ML-DSA) for use in
  X.509 Public Key Infrastructure". Latest revision **-19**; in
  **IESG evaluation** (ballot opened for -14, now closed; comments
  2026-03-26 to 2026-04-10). **Not an RFC.**
  https://datatracker.ietf.org/doc/draft-ietf-lamps-pq-composite-sigs/ballot/
- **Limitation flagged in IESG review:** composite ML-DSA offers
  EUF-CMA but **not SUF-CMA**, unlike pure ML-DSA.
- **RFC 9881** (October 2025, pure ML-DSA in X.509) — cited in
  secondary sources; **not directly read here**.

## 11. Items NOT read / SECONDARY (do not use as sole support)

- **SEC 2 (SECG), v2.0, §2.4.1** — secp256k1 domain parameters. PDF
  not directly read; secp256k1 sizes in this pack come from postfiatd
  `PublicKey.h` (33-byte compressed key, read directly) and secp256k1
  crate docs (compact signature 64 B; DER 68–72 B).
- **NIST IR 8547, *Transition to Post-Quantum Cryptography
  Standards*** (final, 27 October 2026) — deprecation of RSA/ECDSA/
  EdDSA after 2030, disallowance after 2035, per secondary summaries;
  the IR itself was not opened. Not used for any pack claim.
- **liboqs official benchmark tables** — not located in this session;
  no liboqs figures are invented. The MDPI paper's liboqs 0.7.2
  figures (entry 8) are the liboqs numbers used.
- **SP 800-230** (additional SLH-DSA parameter sets) — cited only via
  FIPS 205 footnote 20; not read.
