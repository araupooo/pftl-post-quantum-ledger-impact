"""Shared pinned inputs for the PFTL post-quantum ledger-impact harness.

All specification-derived sizes come from the primary sources listed in
sources.md. Nothing in this module is fetched from the network; every value
is pinned here so a run is reproducible from a fresh copy.
"""

# --- Signature sizes (bytes) -------------------------------------------------
# ML-DSA: NIST FIPS 204, Table 2 (sizes of keys and signatures).
# SLH-DSA: NIST FIPS 205, Table 2 (SHA2 and SHAKE variants identical).
# Ed25519: RFC 8032, section 7 (32-byte keys, 64-byte signatures).
# secp256k1: postfiatd include/xrpl/protocol/PublicKey.h (33-byte wire-form
# public key for both classical schemes) and secp256k1 crate docs
# (compact signature 64 bytes; DER 68-72 bytes).
SCHEMES = {
    "Ed25519": {
        "public_key": 32, "public_key_wire": 33, "signature": 64,
        "security": "128-bit (RFC 8032, section 1)",
    },
    "secp256k1": {
        "public_key": 33, "public_key_wire": 33, "signature": 64,
        "security": "128-bit ECDSA (compact r||s; DER form 68-72 B)",
    },
    "ML-DSA-44": {
        "public_key": 1312, "public_key_wire": 1312, "signature": 2420,
        "security": "FIPS 204 category 2",
    },
    "ML-DSA-65": {
        "public_key": 1952, "public_key_wire": 1952, "signature": 3309,
        "security": "FIPS 204 category 3",
    },
    "ML-DSA-87": {
        "public_key": 2592, "public_key_wire": 2592, "signature": 4627,
        "security": "FIPS 204 category 5",
    },
    "SLH-DSA-128s": {
        "public_key": 32, "public_key_wire": 32, "signature": 7856,
        "security": "FIPS 205 category 1",
    },
    "SLH-DSA-128f": {
        "public_key": 32, "public_key_wire": 32, "signature": 17088,
        "security": "FIPS 205 category 1",
    },
    "SLH-DSA-192s": {
        "public_key": 48, "public_key_wire": 48, "signature": 16224,
        "security": "FIPS 205 category 3",
    },
    "SLH-DSA-192f": {
        "public_key": 48, "public_key_wire": 48, "signature": 35664,
        "security": "FIPS 205 category 3",
    },
    "SLH-DSA-256s": {
        "public_key": 64, "public_key_wire": 64, "signature": 29792,
        "security": "FIPS 205 category 5",
    },
    "SLH-DSA-256f": {
        "public_key": 64, "public_key_wire": 64, "signature": 49856,
        "security": "FIPS 205 category 5",
    },
}

# --- Transaction model -------------------------------------------------------
# BASE_TX_BYTES is an ASSUMED input, not a measured value: the size of a
# minimal payment-style transaction excluding the SigningPubKey and
# TxnSignature fields. 200 bytes is a stated modelling assumption used
# uniformly for every scheme, so all ratios are driven by the verified
# signature/public-key sizes, not by this assumption.
BASE_TX_BYTES = 200

# --- Ledger / throughput assumptions (ASSUMED unless noted) -------------------
# LEDGER_CLOSE_SECONDS and MAX_TPS are stated in the postfiatd README
# ("settles transactions in 4 to 5 seconds, ... up to 1500 transactions
# per second") and are used here as workload assumptions, not as
# measurements made by this harness.
LEDGER_CLOSE_SECONDS = 4.0
MAX_TPS = 1500
SECONDS_PER_DAY = 86400

# --- Fee model (XRPL / postfiatd, FeeEscalation.md + Config.h) ---------------
REFERENCE_FEE_DROPS = 10       # Config.h: XRPAmount reference_fee{10}
BASE_FEE_LEVEL = 256           # FeeEscalation.md: base fee level 256
OPEN_LEDGER_LIMIT_TARGET = 50  # FeeEscalation.md: target open-ledger limit 50
OPEN_LEDGER_LIMIT_MIN = 5      # FeeEscalation.md: minimum open-ledger limit 5

# --- Calibrated verification-cost model --------------------------------------
# These per-operation times are CALIBRATED MODEL INPUTS taken from published
# measurements (see sources.md section 7). They are NOT timings measured by
# this harness on this machine, and no native ML-DSA library is used here:
# a pure-Python reference implementation would be orders of magnitude slower
# than any production implementation and would say nothing about validator
# hardware. The harness measures its own deterministic stand-in workload
# (bench.py) and combines it with these calibrated inputs; every throughput
# figure derived from them is labelled MODEL.
#
# Sources:
#  MDPI Cryptography 2025, 9, 32, Table 14 (liboqs 0.7.2, server E1):
#    ML-DSA-65 (Dilithium Level 3) sign 0.11 ms, verify 0.06 ms.
#  H33 ML-DSA-65 benchmark, 2026-05-23 (AWS Graviton4, 1,000,000 samples,
#    median): sign 72 us, verify 24 us; "ML-DSA-65 verify latency is 2.2x
#    faster than Ed25519 verify" on that hardware.
#  cryptoai.wtf PQC benchmarks, 2026-04-02 (Apple M3 Max, liboqs):
#    ML-DSA-44 sign 0.165 ms, verify 0.040 ms.
#  PostFiat FastPay latency series (postfiatl1v2 fleet, CPU unspecified):
#    ML-DSA-65 signing 0.52 ms per validator signature.
#  Ed25519 verify 0.053 ms is DERIVED from the H33 statement above
#  (24 us x 2.2 = 52.8 us, rounded to 53 us) and is labelled DERIVED.
#  No published SLH-DSA verification time was found in the source set:
#  SLH-DSA timing is UNVERIFIED and excluded from the cost model.
CALIBRATED_VERIFY_MS = {
    "Ed25519": 0.053,     # DERIVED from H33 (see note above)
    "ML-DSA-44": 0.040,   # cryptoai.wtf, M3 Max, liboqs
    "ML-DSA-65": 0.060,   # MDPI 2025, liboqs 0.7.2, server E1
    "ML-DSA-87": None,    # UNVERIFIED: no published figure in the source set
    "secp256k1": None,    # UNVERIFIED: no published figure in the source set
}
CALIBRATED_SIGN_MS = {
    "ML-DSA-44": 0.165,   # cryptoai.wtf, M3 Max, liboqs
    "ML-DSA-65": 0.110,   # MDPI 2025, liboqs 0.7.2, server E1
    "ML-DSA-65-fastpay": 0.520,  # PostFiat FastPay, fleet hardware, CPU unspecified
    "ML-DSA-87": None,    # UNVERIFIED
}


def tx_size(scheme):
    """Model transaction size in bytes: base + wire public key + signature."""
    s = SCHEMES[scheme]
    return BASE_TX_BYTES + s["public_key_wire"] + s["signature"]


def deterministic_bytes(n, seed=b"pftl-pq-ledger-impact"):
    """Deterministic pseudo-random bytes (hashlib counter mode).

    Used as stand-in signature material for the compression check. The
    bytes are deterministic across runs and machines, so the compression
    result is reproducible.
    """
    import hashlib

    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(seed + counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])
