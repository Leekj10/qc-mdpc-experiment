"""M0 self-tests: ring arithmetic, generators, decoders, taxonomy, statistics.

Run:  python tests/test_core.py
All tests must pass before any statistics are collected (manual M0 gate).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, find_near_codeword, random_key
from qcmdpc.ring import QCKey, brute_syndrome
from qcmdpc.stats import per_key_summary, wilson_upper
from qcmdpc.taxonomy import classify_failure

CHECKS = []


def check(name: str, cond: bool, detail: str = ""):
    CHECKS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def test_syndrome_oracle():
    rng = np.random.default_rng(7)
    key = random_key(rng, 97, 5)  # small r for O(r^2 t) oracle
    for _ in range(5):
        e0 = np.zeros(97, dtype=np.uint8)
        e1 = np.zeros(97, dtype=np.uint8)
        e0[rng.choice(97, 4, replace=False)] = 1
        e1[rng.choice(97, 4, replace=False)] = 1
        fast = key.syndrome(e0, e1)
        slow = brute_syndrome(key, e0, e1)
        check("syndrome == brute-force oracle", np.array_equal(fast, slow))


def test_upc_identity():
    """alpha_k must equal #{unsatisfied checks touching position k}:
    recompute by direct definition for a small key."""
    rng = np.random.default_rng(11)
    r, d = 61, 5
    key = random_key(rng, r, d)
    e = np.zeros(2 * r, dtype=np.uint8)
    e[rng.choice(2 * r, 6, replace=False)] = 1
    s = key.syndrome_from_global(e)
    alpha = key.upc(s)
    # direct definition
    for blk in range(2):
        h = key.h0 if blk == 0 else key.h1
        for k in range(r):
            cnt = 0
            for i in range(r):
                if s[i] and h[(i - k) % r]:
                    cnt += 1
            check(f"upc direct match (block {blk}, pos {k})", alpha[blk * r + k] == cnt)


def test_flip_semantics():
    rng = np.random.default_rng(13)
    key = random_key(rng, 53, 4)
    e = np.zeros(106, dtype=np.uint8)
    pos = [2, 30, 60, 90]
    e[pos] = 1
    s = key.syndrome_from_global(e)
    s1 = key.flip(s, pos[0])
    e2 = e.copy()
    e2[pos[0]] = 0
    check("flip == syndrome recomputation", np.array_equal(s1, key.syndrome_from_global(e2)))


def test_decoder_recovers_true_error():
    """For a small correctable instance every decoder must return the exact
    error (zero syndrome) on at least the trivial no-error case, and succeed on
    most random small-weight errors."""
    rng = np.random.default_rng(17)
    r, d, t = 257, 7, 5  # far below capacity -> should decode reliably
    param = {"r": r, "d": d, "t": t}
    ok = {"BF": 0, "BGF": 0, "BFMAX": 0}
    specs = {
        "BF": {"algo": "bf_parallel", "threshold": {"type": "fixed", "b": 4}, "max_iter": 20},
        "BGF": {"algo": "bgf_lite", "threshold": {"type": "fixed", "b": 4}, "max_iter": 15},
        "BFMAX": {"algo": "bf_max", "max_iter": t},
    }
    decs = {n: build_decoder(n, sp, d, t, r) for n, sp in specs.items()}
    trials = 30
    for _ in range(trials):
        key = random_key(rng, r, d)
        e = np.zeros(2 * r, dtype=np.uint8)
        e[rng.choice(2 * r, t, replace=False)] = 1
        s = key.syndrome_from_global(e)
        for name, dec in decs.items():
            if dec(key, s.copy()).success:
                ok[name] += 1
    for name, c in ok.items():
        check(f"{name} decodes easy instances (>=90%)", c >= 0.9 * trials, f"{c}/{trials}")


def test_optional_exact_estimate_tracking():
    """Parity tracking is opt-in and returns the correction estimate."""
    from qcmdpc.decoders import build_decoder

    key = random_key(np.random.default_rng(171), 97, 5)
    spec = {"algo": "bf_parallel", "threshold": {"type": "fixed", "b": 3},
            "max_iter": 10, "fixed_iters": False}
    dec = build_decoder("BF_TRACK", spec, key.d, 3, key.r)
    e = np.zeros(key.n, dtype=np.uint8)
    s0 = key.syndrome_from_global(e)
    plain = dec(key, s0.copy())
    tracked = dec(key, s0.copy(), track_estimate=True)
    check("estimate tracking is opt-in", plain.estimated_error is None)
    check("tracked estimate has global length", tracked.estimated_error is not None and
          tracked.estimated_error.shape == (key.n,))
    check("zero-error estimate is exact", tracked.success and
          np.array_equal(tracked.estimated_error, e))


def test_type1_generator():
    param = {"r": 509, "d": 11, "t": 8}
    pool = KeyPool(3, param, "G2", {"type": "type1", "n_keys": 5, "delta": 4})
    runs = [rep["max_run_h0"] for rep in pool.reports]
    check("type1 keys satisfy structural validation", all(v >= 4 for v in runs), str(runs))


def test_ncw_generator():
    param = {"r": 509, "d": 11, "t": 8}
    pool = KeyPool(5, param, "G3", {"type": "ncw", "n_keys": 3, "kappa": 2, "max_syn_weight": None})
    check("ncw pool built with relative criterion", len(pool.keys) == 3)
    for kid, ncw in pool.ncws.items():
        key = next(k for k in pool.keys if k.key_id == kid)
        s0, s1 = key.canonical_syndromes()
        canonical_w = int(np.bitwise_xor(s0, s1).sum())
        check(f"ncw {kid} beats canonical syndrome weight", ncw.syn_weight < canonical_w,
              f"{ncw.syn_weight} < {canonical_w}")
        check(f"ncw {kid} support weight == 2d", ncw.support.size == 2 * 11)


def test_upc_fast_equivalence():
    """gather UPC must be bit-exact equal to the roll reference."""
    rng = np.random.default_rng(23)
    for r, d in [(97, 5), (257, 7), (509, 11)]:
        key = random_key(rng, r, d)
        for _ in range(4):
            e = np.zeros(2 * r, dtype=np.uint8)
            e[rng.choice(2 * r, rng.integers(1, 2 * d), replace=False)] = 1
            s = key.syndrome_from_global(e)
            check(f"upc_fast == upc (r={r})", np.array_equal(key.upc_fast(s), key.upc(s)))


def test_classic_threshold():
    from qcmdpc.decoders import make_threshold

    d, t, n = 45, 84, 2 * 4801
    th = make_threshold({"type": "classic"}, d, t, n)
    vals = [th(0, sw) for sw in range(50, 3000, 200)]
    lo = (d + 1) // 2
    check("classic threshold within [(d+1)/2, d]", all(lo <= v <= d for v in vals), f"{vals[:6]}")
    check("classic threshold non-decreasing in |s|", all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1)))


def test_bgf_vasseur_sanity():
    rng = np.random.default_rng(29)
    r, d, t = 257, 7, 5
    from qcmdpc.decoders import build_decoder

    spec = {
        "algo": "bgf_vasseur",
        "threshold": {"type": "affine_vasseur", "c0": 4.0, "c1": 0.0},
        "max_iter": 20,
    }
    dec = build_decoder("BGFV", spec, d, t, r)
    ok = 0
    trials = 20
    for _ in range(trials):
        key = random_key(rng, r, d)
        e = np.zeros(2 * r, dtype=np.uint8)
        e[rng.choice(2 * r, t, replace=False)] = 1
        if dec(key, key.syndrome_from_global(e)).success:
            ok += 1
    check("bgf_vasseur decodes easy instances (>=80%)", ok >= 0.8 * trials, f"{ok}/{trials}")


def test_bfmax_tiebreak():
    from qcmdpc.decoders import bf_max

    rng = np.random.default_rng(37)
    r, d, t = 257, 7, 6
    key = random_key(rng, r, d)
    e = np.zeros(2 * r, dtype=np.uint8)
    e[rng.choice(2 * r, t, replace=False)] = 1
    s0 = key.syndrome_from_global(e)
    # determinism: same salt twice -> identical flips
    r1 = bf_max(key, s0.copy(), t, tie_break="prf", salt=b"A", record_flips=True)
    r2 = bf_max(key, s0.copy(), t, tie_break="prf", salt=b"A", record_flips=True)
    check("bf_max prf deterministic per salt", r1.flip_positions == r2.flip_positions)
    # "first" equals legacy argmax behaviour
    r3 = bf_max(key, s0.copy(), t, tie_break="first", record_flips=True)
    r4 = bf_max(key, s0.copy(), t, record_flips=True)
    check("bf_max first == default", r3.flip_positions == r4.flip_positions)
    # salt sensitivity: some salts give different trajectories (ties exist)
    variants = set()
    for salt in [bytes([i]) for i in range(16)]:
        rr = bf_max(key, s0.copy(), t, tie_break="prf", salt=salt, record_flips=True)
        variants.add(tuple(map(tuple, rr.flip_positions)))
    check("bf_max prf salt-sensitive (>=2 distinct trajectories)", len(variants) >= 2, f"{len(variants)} variants")


def test_dris_cps():
    from qcmdpc.decoders import build_decoder

    rng = np.random.default_rng(31)
    r, d, t = 257, 7, 5
    key = random_key(rng, r, d)
    e = np.zeros(2 * r, dtype=np.uint8)
    e[rng.choice(2 * r, t, replace=False)] = 1
    s0 = key.syndrome_from_global(e)

    # DRIS table threshold: clipping to [(d+1)//2, d]
    dris = build_decoder("DRIS", {"algo": "bf_parallel", "threshold": {"type": "table", "values": [1, 99, 5, 4]}, "max_iter": 10}, d, t, r)
    res = dris(key, s0.copy())
    check("DRIS table runs and clips", res.n_iters_run > 0)

    # CPS determinism: same input twice -> identical outcome and flips
    cps_spec = {"algo": "cps", "base_threshold": {"type": "fixed", "b": 4}, "jitters": [-1, 0, 1], "max_iter": 10}
    cps = build_decoder("CPS", cps_spec, d, t, r)
    r1 = cps(key, s0.copy(), record_flips=True)
    r2 = cps(key, s0.copy(), record_flips=True)
    check("CPS deterministic (same input -> same trajectory)",
          r1.success == r2.success and r1.flip_positions == r2.flip_positions and r1.extra["coin"] == r2.extra["coin"])

    # CPS with jitters=[0] must equal plain bf_parallel with same base threshold
    cps0 = build_decoder("CPS0", {"algo": "cps", "base_threshold": {"type": "fixed", "b": 4}, "jitters": [0], "max_iter": 10}, d, t, r)
    base = build_decoder("BASE", {"algo": "bf_parallel", "threshold": {"type": "fixed", "b": 4}, "max_iter": 10}, d, t, r)
    rc = cps0(key, s0.copy(), record_flips=True)
    rb = base(key, s0.copy(), record_flips=True)
    check("CPS(jitters=[0]) == bf_parallel", rc.flip_positions == rb.flip_positions and rc.success == rb.success)

    # coin varies across different syndromes (sanity: not constant)
    coins = set()
    for _ in range(12):
        e2 = np.zeros(2 * r, dtype=np.uint8)
        e2[rng.choice(2 * r, t, replace=False)] = 1
        coins.add(cps(key, key.syndrome_from_global(e2)).extra["coin"])
    check("CPS coin takes multiple values across syndromes", len(coins) >= 2, f"coins={sorted(coins)}")


def test_stats_rules():
    check("rule of three at k=0", abs(wilson_upper(0, 1000) - 0.003) < 1e-12)
    s = per_key_summary(np.array([3, 0, 40, 1]), np.array([1000, 1000, 1000, 1000]))
    check("per-key summary overall dfr", abs(s["overall_dfr"] - 44 / 4000) < 1e-12)
    check("zero-failure keys counted", s["keys_zero_failures"] == 1)


def test_taxonomy():
    from qcmdpc.decoders import TrajectoryResult

    tr = TrajectoryResult("X", False, None, 6, syndrome_weights=[10, 12, 13, 14, 15, 16])
    check("taxonomy: divergence", classify_failure(tr) == "divergence")
    tr = TrajectoryResult("X", False, None, 6, syndrome_weights=[10, 8, 8, 8, 8, 8])
    check("taxonomy: stagnation", classify_failure(tr) == "stagnation")
    tr = TrajectoryResult("X", False, None, 8, syndrome_weights=[9, 7, 9, 7, 9, 7, 9, 7])
    check("taxonomy: period2", classify_failure(tr) == "period2")
    tr = TrajectoryResult("X", True, 3, 3, syndrome_weights=[5, 2, 0])
    check("taxonomy: success", classify_failure(tr) == "success")
    # The preregistered window is ceil(max_iter/4), rather than floor of the
    # number of logged rounds.  Two rounds are therefore inspected for a
    # six-iteration budget even when the old floor rule would inspect one.
    tr = TrajectoryResult(
        "X",
        False,
        None,
        6,
        syndrome_weights=[10, 9, 8, 7, 6, 5],
        flip_positions=[[0], [1, 2], [], [], [], []],
    )
    check(
        "taxonomy: ceil early-misflip window",
        classify_failure(tr, {0}, max_iter=6) == "early_misflip",
    )

def main():
    print("== M0 self-tests ==")
    test_syndrome_oracle()
    test_upc_identity()
    test_flip_semantics()
    test_decoder_recovers_true_error()
    test_upc_fast_equivalence()
    test_classic_threshold()
    test_bgf_vasseur_sanity()
    test_bfmax_tiebreak()
    test_dris_cps()
    test_type1_generator()
    test_ncw_generator()
    test_stats_rules()
    test_taxonomy()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print(f"== {len(CHECKS) - n_fail}/{len(CHECKS)} passed ==")
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
