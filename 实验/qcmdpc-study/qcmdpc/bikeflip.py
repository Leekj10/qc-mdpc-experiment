"""BIKE-Flip v5.2 decoder -- spec-exact port.

Source: BIKE Specification v5.2 (BIKE_Spec.2024.10.10.1.pdf):
  - Algorithm 1 "BIKE-Flip" (p.11): parallel bit-flipping, FIXED NbIter iterations
    (no early exit), success = zero residual syndrome (s = e H^T).
  - Threshold rule (p.14, Sec 2.6):
        threshold(S, i, S0) = max( ft(S), T_i(S0) ),   ft(x) = a*x + b
        T_1(x) = ft(x) + delta
        T_2(x) = (2*ft(x) + (d+1)//2)/3 + delta
        T_3(x) = (ft(x) + 2*((d+1)//2))/3 + delta
        T_i(x) = (d+1)//2 + delta        for i >= 4
    with S = current syndrome weight, S0 = initial syndrome weight, d = w/2.
  - Official constants (p.14): NbIter=7 for all levels.
        L1 (r=12323,d=71,t=134):  delta=3, a=0.006254868353074983,  b=11.101432337243956
        L3 (r=24659,d=103,t=199): delta=5, a=0.004533882596007288,  b=13.282669604666431
        L5 (r=40973,d=137,t=264): delta=6, a=0.0036083738659016262, b=15.430866686308178
  - Affine derivation (p.38, Sec A.2.4): ft is the affine tangent of the binomial
    threshold F_t(S) at Savg = floor(r * sum_{i odd} C(w,i)C(n-w,t-i)/C(n,t)),
        a = F_t(Savg+1) - F_t(Savg),  b = F_t(Savg) - a*Savg.
    F_t(S) is the real-valued binomial-model threshold (== Vasseur compute_threshold
    before the ceil), so for non-official parameter sets (e.g. the scaled P1') we
    DERIVE (a,b) from the same formula. Correctness of the derivation is proven by
    reproducing the official L1/L3/L5 (a,b) to ~1e-12 (see tests/test_bikeflip.py).

Integer rounding: ft and T_i are evaluated in real arithmetic; the threshold is
ceil'd ONCE at the end and clipped to [(d+1)//2, d] (project pre-registration integer
semantics). Since the counter comparison is `ctr >= T` with integer ctr, ceil(max)
== max(ceil) and the choice is immaterial to the flip set beyond a <=1 rounding that
we fix to ceil. delta and (d+1)//2 are integers for the odd d used here (71/45/103/137).
"""
from __future__ import annotations

import math
from math import exp, lgamma, log, log1p

import numpy as np

from .ring import QCKey
from .decoders import TrajectoryResult

# Official per-level constants (spec p.14). Keyed by (r, d, t).
BIKEFLIP_OFFICIAL = {
    (12323, 71, 134): {"nb_iter": 7, "delta": 3, "a": 0.006254868353074983, "b": 11.101432337243956},
    (24659, 103, 199): {"nb_iter": 7, "delta": 5, "a": 0.004533882596007288, "b": 13.282669604666431},
    (40973, 137, 264): {"nb_iter": 7, "delta": 6, "a": 0.0036083738659016262, "b": 15.430866686308178},
}


def _lnbino(nn: int, kk: int) -> float:
    if kk == 0 or nn == kk:
        return 0.0
    if kk < 0 or kk > nn:
        return -1e300
    return lgamma(nn + 1) - lgamma(kk + 1) - lgamma(nn - kk + 1)


def _xval_and_denom(t: int, d: int, n: int) -> tuple[float, float]:
    """tau = X_val(t) and denom = sum_{i odd, i<10} C(w,i)C(n-w,t-i)/C(n,t), w=2d.

    Mirrors Vasseur threshold.c X_val (same i<10 truncation), so Savg and F_t match
    the reference conventions used to produce the official constants.
    """
    w = 2 * d
    xv, den = 0.0, 0.0
    for i in range(1, min(10, t), 2):
        e = exp(_lnbino(w, i) + _lnbino(n - w, t - i) - _lnbino(n, t))
        xv += (i - 1) * e
        den += e
    tau = 0.0 if den == 0.0 else xv / den
    return tau, den


def binomial_Ft(S: float, t: int, d: int, n: int) -> float:
    """Real-valued binomial-model threshold F_t(S) (spec A.2.4 'Tavg'), NO ceil."""
    tau, _ = _xval_and_denom(t, d, n)
    w = 2 * d
    x = tau * S
    p0 = ((w - 1) * S - x) / ((n - t) * d)   # pi0 = counters_C0
    p1 = (S + x) / (t * d)                   # pi1 = counters_C1
    if p1 >= 1.0:
        return float(d)
    p0 = min(max(p0, 1e-15), 1 - 1e-15)
    p1 = min(max(p1, 1e-15), 1 - 1e-15)
    num = d * (log1p(-p1) - log1p(-p0)) + log(t) - log(n - t)
    den = log(p0) - log(p1) + log1p(-p1) - log1p(-p0)
    if den == 0:
        return float(d)
    return num / den


def derive_bikeflip_affine(r: int, d: int, t: int) -> tuple[float, float, int]:
    """Derive (a, b, Savg) per spec A.2.4 for arbitrary (r, d, t)."""
    n = 2 * r
    _, den = _xval_and_denom(t, d, n)
    Savg = int(math.floor(r * den))
    F0 = binomial_Ft(Savg, t, d, n)
    F1 = binomial_Ft(Savg + 1, t, d, n)
    a = F1 - F0
    b = F0 - a * Savg
    return a, b, Savg


def bike_flip_thresholds(a: float, b: float, delta: int, d: int, S0: int, nb_iter: int) -> list[int]:
    """Integer threshold per iteration i=1..nb_iter, evaluated at INITIAL weight S0
    for the T_i floor and (here) at S=S0 for ft as well -- used for structural tests.
    The decoder recomputes ft at the CURRENT S each iteration; this helper exposes the
    T_i(S0) floor schedule and the iteration-1 threshold ft(S0)+delta."""
    lo = (d + 1) // 2

    def ft(S):
        return a * S + b

    fS0 = ft(S0)
    floors = []
    for i in range(1, nb_iter + 1):
        if i == 1:
            Ti = fS0 + delta
        elif i == 2:
            Ti = (2 * fS0 + lo) / 3 + delta
        elif i == 3:
            Ti = (fS0 + 2 * lo) / 3 + delta
        else:
            Ti = lo + delta
        floors.append(int(min(max(math.ceil(Ti), lo), d)))
    return floors


def bike_flip(
    key: QCKey,
    s0: np.ndarray,
    a: float,
    b: float,
    delta: int,
    nb_iter: int,
    record_flips: bool = False,
) -> TrajectoryResult:
    """BIKE-Flip v5.2 (Algorithm 1): parallel BF, fixed nb_iter, zero-syndrome success.

    threshold(S,i,S0) = clip(ceil(max(ft(S), T_i(S0))), (d+1)//2, d), ft(S)=a*S+b.
    Once the syndrome reaches zero no further flips occur (counter 0 < T >= 1), so the
    fixed-iteration loop naturally locks in a success; we record the convergence step.
    """
    d = key.d
    lo, hi = (d + 1) // 2, d
    s0 = np.asarray(s0)
    S0 = int(s0.sum())

    def ft(S: int) -> float:
        return a * S + b

    fS0 = ft(S0)
    # T_i(S0) floors (depend only on the INITIAL syndrome weight S0)
    Ti = [None] * (nb_iter + 1)
    for i in range(1, nb_iter + 1):
        if i == 1:
            Ti[i] = fS0 + delta
        elif i == 2:
            Ti[i] = (2 * fS0 + lo) / 3 + delta
        elif i == 3:
            Ti[i] = (fS0 + 2 * lo) / 3 + delta
        else:
            Ti[i] = lo + delta

    s = s0.copy()
    res = TrajectoryResult("BIKE-Flip", False, None, 0)
    success_at = None
    for i in range(1, nb_iter + 1):
        S = int(s.sum())
        if S == 0:
            if success_at is None:
                success_at = i - 1
            res.syndrome_weights.append(0)
            res.flip_counts.append(0)
            if record_flips:
                res.flip_positions.append([])
            res.n_iters_run = i
            continue
        T = int(np.clip(math.ceil(max(ft(S), Ti[i])), lo, hi))
        alpha = key.upc_fast(s)
        flips = np.nonzero(alpha >= T)[0]
        for p in flips:
            s = key.flip(s, int(p))
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(int(flips.size))
        if record_flips:
            res.flip_positions.append([int(p) for p in flips])
        res.n_iters_run = i
        if int(s.sum()) == 0 and success_at is None:
            success_at = i
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    res.extra = {"S0": S0, "delta": delta, "nb_iter": nb_iter, "a": a, "b": b}
    return res
