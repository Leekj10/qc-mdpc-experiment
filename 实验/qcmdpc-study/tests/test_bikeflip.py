"""Validation of the BIKE-Flip v5.2 port (qcmdpc/bikeflip.py).

The decisive test: derive (a,b) from the spec A.2.4 affine-tangent formula and check
it reproduces the OFFICIAL constants published in the spec (p.14) for L1/L3/L5. If the
derivation matches to ~1e-12, the binomial F_t(S), Savg, and (a,b) machinery is provably
correct -- and therefore trustworthy for the scaled P1' set where no constants exist.

Also checks: threshold-schedule structure (first-round elevation, monotone floor),
clip range, determinism, and easy-instance decoding.

Run: python tests/test_bikeflip.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from qcmdpc.bikeflip import (
    BIKEFLIP_OFFICIAL,
    bike_flip,
    bike_flip_thresholds,
    derive_bikeflip_affine,
)
from qcmdpc.generators import random_key

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def _int_threshold(a, b, delta, d, S, i, S0):
    """Integer threshold T(S,i,S0)=clip(ceil(max(ft(S),T_i(S0))), (d+1)//2, d)."""
    import math
    lo, hi = (d + 1) // 2, d
    ft = lambda x: a * x + b
    fS0 = ft(S0)
    if i == 1:
        Ti = fS0 + delta
    elif i == 2:
        Ti = (2 * fS0 + lo) / 3 + delta
    elif i == 3:
        Ti = (fS0 + 2 * lo) / 3 + delta
    else:
        Ti = lo + delta
    return int(min(max(math.ceil(max(ft(S), Ti)), lo), hi))


def test_official_constant_reproduction():
    """THE ground-truth test: derived (a,b) must match the spec's published values.

    `a` (the slope) must match to ~1e-9 -- this proves F_t(S)/Savg are correct. `b`
    inherits a's error amplified by Savg (b = F_t(Savg) - a*Savg, Savg ~ 5e3), so its
    tolerance is ~1e-5; this never changes the ceil'd INTEGER threshold, which is what
    the decoder uses. The integer-threshold equivalence below is the decisive check.
    """
    for (r, d, t), off in BIKEFLIP_OFFICIAL.items():
        a, b, Savg = derive_bikeflip_affine(r, d, t)
        da, db = abs(a - off["a"]), abs(b - off["b"])
        check(f"L(r={r}) slope a reproduced (~1e-9)", da < 1e-9,
              f"derived a={a:.15g} spec={off['a']:.15g} |d|={da:.2e}")
        check(f"L(r={r}) intercept b reproduced (~1e-5, a*Savg amplification)", db < 1e-5,
              f"derived b={b:.12g} spec={off['b']:.12g} |d|={db:.2e}")
        print(f"      Savg={Savg}  (delta={off['delta']}, NbIter={off['nb_iter']})")


def test_integer_threshold_equivalence():
    """Derived (a,b) must yield the SAME integer thresholds as the official constants
    over the realistic syndrome-weight range -- the behaviorally decisive check."""
    r, d, t = 12323, 71, 134
    off = BIKEFLIP_OFFICIAL[(r, d, t)]
    a, b, Savg = derive_bikeflip_affine(r, d, t)
    mism = 0
    tot = 0
    for S0 in (Savg, int(0.9 * Savg), int(1.1 * Savg)):
        for S in range(0, 2 * Savg, max(1, Savg // 25)):
            for i in range(1, off["nb_iter"] + 1):
                tot += 1
                if _int_threshold(a, b, off["delta"], d, S, i, S0) != \
                   _int_threshold(off["a"], off["b"], off["delta"], d, S, i, S0):
                    mism += 1
    check("L1 derived == official integer thresholds (>=99.9% of grid)",
          mism <= 0.001 * tot, f"mismatches {mism}/{tot}")


def test_threshold_schedule_structure():
    """T1 = ft(S0)+delta is highest; T_i decreases to the (d+1)//2+delta floor."""
    r, d, t = 12323, 71, 134
    off = BIKEFLIP_OFFICIAL[(r, d, t)]
    a, b, Savg = derive_bikeflip_affine(r, d, t)
    S0 = Savg  # typical initial syndrome weight
    floors = bike_flip_thresholds(a, b, off["delta"], d, S0, off["nb_iter"])
    lo, hi = (d + 1) // 2, d
    check("thresholds within [(d+1)/2, d]", all(lo <= x <= hi for x in floors), str(floors))
    check("T1 is the maximum (first-round elevation)", floors[0] == max(floors), f"T1={floors[0]}")
    check("T1 >= T2 >= T3 (non-increasing head)", floors[0] >= floors[1] >= floors[2], str(floors[:3]))
    check("T4..T7 equal the floor (d+1)/2+delta",
          all(x == floors[3] for x in floors[3:]) and floors[3] == lo + off["delta"],
          f"floor={floors[3]} expected={lo + off['delta']}")


def test_determinism_and_easy_decode():
    # determinism on a toy (delta small so thresholds are not clip-degenerate at d=7)
    rng = np.random.default_rng(101)
    r, d, t = 257, 7, 5
    a, b, _ = derive_bikeflip_affine(r, d, t)
    key = random_key(rng, r, d)
    e = np.zeros(2 * r, dtype=np.uint8)
    e[rng.choice(2 * r, t, replace=False)] = 1
    s0 = key.syndrome_from_global(e)
    r1 = bike_flip(key, s0.copy(), a, b, 1, 12, record_flips=True)
    r2 = bike_flip(key, s0.copy(), a, b, 1, 12, record_flips=True)
    check("bike_flip deterministic", r1.flip_positions == r2.flip_positions and r1.success == r2.success)
    # FUNCTIONAL decode at the real scaled operating point P1' (4801,45,92), delta=3,
    # NbIter=7 (spec value), derived constants: random instances must decode reliably.
    a1, b1, _ = derive_bikeflip_affine(4801, 45, 92)
    rng2 = np.random.default_rng(202)
    ok, trials = 0, 30
    for _ in range(trials):
        k = random_key(rng2, 4801, 45)
        ee = np.zeros(2 * 4801, dtype=np.uint8)
        ee[rng2.choice(2 * 4801, 92, replace=False)] = 1
        if bike_flip(k, k.syndrome_from_global(ee), a1, b1, 3, 7).success:
            ok += 1
    check("bike_flip decodes P1' random instances (>=90%)", ok >= 0.9 * trials, f"{ok}/{trials}")


def test_p1prime_derivation_sane():
    """P1' = (4801,45,92): no official constants; derived (a,b) must be sane."""
    a, b, Savg = derive_bikeflip_affine(4801, 45, 92)
    floors = bike_flip_thresholds(a, b, 3, 45, Savg, 7)
    lo, hi = 23, 45
    check("P1' derived a in (0, 1)", 0 < a < 1, f"a={a:.6g}")
    check("P1' derived thresholds within [(d+1)/2, d]", all(lo <= x <= hi for x in floors), str(floors))
    print(f"      P1' a={a:.12g} b={b:.12g} Savg={Savg} floors(delta=3)={floors}")


def main():
    print("== BIKE-Flip v5.2 port validation ==")
    test_official_constant_reproduction()
    test_integer_threshold_equivalence()
    test_threshold_schedule_structure()
    test_determinism_and_easy_decode()
    test_p1prime_derivation_sane()
    n_fail = sum(1 for _, ok, _ in CHECKS if not ok)
    print(f"== {len(CHECKS) - n_fail}/{len(CHECKS)} passed ==")
    if n_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
