"""Unified decoder interface with trajectory logging (Python reference).

All decoders share the contract:
    decode(key, s0, ctx) -> TrajectoryResult
where s0 is the initial syndrome and ctx carries frozen, pre-registered
parameters (threshold spec, iteration budget, fixed-iteration flag).

Integer threshold semantics (pre-registered, manual section 3.2):
- affine thresholds: th = ceil(a * |s| + b)
- final threshold clipped to [(d+1)//2, d]
- threshold >= 1 always.

NOTE: BGF below is a PRELIMINARY black/gray implementation; the final M0
cross-check against vvasseur/qcmdpc_decoder (GRAY_BGF) is mandatory before
any headline statistics are reported with it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .ring import QCKey


@dataclass
class TrajectoryResult:
    decoder: str
    success: bool
    iters_to_success: int | None
    n_iters_run: int
    syndrome_weights: list[int] = field(default_factory=list)
    flip_counts: list[int] = field(default_factory=list)
    flip_positions: list[list[int]] = field(default_factory=list)  # only if requested
    estimated_error: np.ndarray | None = None  # populated only by explicit parity tracking
    extra: dict = field(default_factory=dict)


def make_threshold(spec: dict, d: int, t: int | None = None, n: int | None = None):
    """Build the frozen integer threshold function th(iter_idx, syn_weight)."""
    lo = max(1, (d + 1) // 2)
    hi = d

    if spec["type"] == "fixed":
        b = int(round(spec["b"]))

        def th(it: int, sw: int) -> int:
            return int(np.clip(b, lo, hi))

        return th
    if spec["type"] == "affine":
        a, b = float(spec["a"]), float(spec["b"])

        def th(it: int, sw: int) -> int:
            v = math.ceil(a * sw + b)  # ceil semantics, pre-registered
            return int(np.clip(v, lo, hi))

        return th
    if spec["type"] == "affine_vasseur":
        # FROZEN: exact GRAY_BGF affine semantics from vvasseur/qcmdpc_decoder
        # (reference/FROZEN_REFERENCE_SEMANTICS.md section 3):
        # thr = trunc(C0 + C1*|s|), lower bound (d+1)//2, NO upper clip.
        c0, c1 = float(spec["c0"]), float(spec["c1"])

        def th(it: int, sw: int) -> int:
            v = int(c0 + c1 * sw)  # truncation toward zero (C unsigned cast)
            return max(v, lo)

        return th
    if spec["type"] == "classic":
        # FROZEN: exact port of compute_threshold (threshold.c): binomial-model
        # threshold, parameter-free (uses t, d, n), ceil + clip [(d+1)/2, d].
        assert t is not None and n is not None, "classic threshold needs t and n"
        return _classic_threshold_factory(d, t, n, lo, hi)
    if spec["type"] == "table":
        # DRIS carrier: per-iteration integer threshold table (monotonicity NOT
        # enforced here; the search stage proposes candidates, the clip is).
        vals = [int(v) for v in spec["values"]]
        assert vals, "empty threshold table"

        def th(it: int, sw: int) -> int:
            v = vals[min(it, len(vals) - 1)]
            return int(np.clip(v, lo, hi))

        return th
    if spec["type"] == "offset":
        # DRIS two-bias family: thr(it, sw) = clip(base(sw) + offsets[min(it, len-1)], lo, hi).
        # offsets are integers searched by M4; base is any other threshold spec
        # (typically "classic"). This realizes the pre-registered "two integer
        # biases on a strong base schedule" design without searching full tables.
        base = make_threshold(spec["base"], d, t, n)
        offs = [int(v) for v in spec["offsets"]]
        assert offs, "empty offsets"

        def th(it: int, sw: int) -> int:
            return int(np.clip(base(it, sw) + offs[min(it, len(offs) - 1)], lo, hi))

        return th
    raise ValueError(f"unknown threshold spec {spec}")


def _classic_threshold_factory(d: int, t: int, n: int, lo: int, hi: int):
    """Faithful Python port of Vasseur's compute_threshold (threshold.c)."""
    from math import exp, lgamma, log, log1p

    def lnbino(nn: int, kk: int) -> float:
        if kk == 0 or nn == kk:
            return 0.0
        if kk < 0 or kk > nn:
            return -1e300  # lnbinomialpmf-guard: negligible
        return lgamma(nn + 1) - lgamma(kk + 1) - lgamma(nn - kk + 1)

    total_w = 2 * d  # INDEX * BLOCK_WEIGHT

    def logE(i: int) -> float:
        return lnbino(total_w, i) + lnbino(n - total_w, t - i) - lnbino(n, t)

    x_val = 0.0
    denom = 0.0
    for i in range(1, min(10, t), 2):  # i = 1,3,5,7,9 (<10 per C code)
        e = exp(logE(i))
        x_val += (i - 1) * e
        denom += e
    X = 0.0 if denom == 0.0 else x_val / denom
    lt, ltbar = log(t), log(n - t)

    def th(it: int, sw: int) -> int:
        S = float(sw)
        x = X * S
        p = ((total_w - 1) * S - x) / (n - t) / d   # counters_C0
        q = (S + x) / t / d                          # counters_C1
        if q >= 1.0:
            return hi
        p = min(max(p, 1e-15), 1 - 1e-15)
        q = min(max(q, 1e-15), 1 - 1e-15)
        num = d * (log1p(-q) - log1p(-p)) + lt - ltbar
        den = log(p) - log(q) + log1p(-q) - log1p(-p)
        if den == 0:
            return hi
        v = math.ceil(num / den)
        return int(np.clip(v, lo, hi))

    return th


def _classic_threshold_value(S: int, t: int, d: int, n: int, lo: int, hi: int, xcache: dict) -> int:
    """compute_threshold(S, t) with dynamic t (current distance), per threshold.c."""
    from math import exp, lgamma, log, log1p
    if t < 1:
        return hi
    if t not in xcache:
        def lnbino(nn, kk):
            if kk == 0 or nn == kk:
                return 0.0
            if kk < 0 or kk > nn:
                return -1e300
            return lgamma(nn + 1) - lgamma(kk + 1) - lgamma(nn - kk + 1)
        total_w = 2 * d
        xv, den = 0.0, 0.0
        for i in range(1, min(10, t), 2):
            e = exp(lnbino(total_w, i) + lnbino(n - total_w, t - i) - lnbino(n, t))
            xv += (i - 1) * e
            den += e
        xcache[t] = 0.0 if den == 0.0 else xv / den
    X = xcache[t]
    Sf = float(S)
    x = X * Sf
    p = ((2 * d - 1) * Sf - x) / (n - t) / d
    q = (Sf + x) / t / d
    if q >= 1.0:
        return hi
    p = min(max(p, 1e-15), 1 - 1e-15)
    q = min(max(q, 1e-15), 1 - 1e-15)
    num = d * (log1p(-q) - log1p(-p)) + log(t) - log(n - t)
    den = log(p) - log(q) + log1p(-q) - log1p(-p)
    if den == 0:
        return hi
    return int(np.clip(math.ceil(num / den), lo, hi))


def bf_classic_dynamic(key: QCKey, s0: np.ndarray, e_true: np.ndarray, max_iter: int = 100) -> TrajectoryResult:
    """Faithful port of the C reference CLASSIC decoder (decoder.c + threshold.c).

    Key semantic differences vs our study carrier (bf_parallel + static-t classic):
    - threshold uses the CURRENT distance to the true error (simulation-privileged
      information available in the C reference), not the static t;
    - success = exact error recovery (distance 0), not merely zero syndrome;
    - blocked exit when an iteration performs no flips.
    Used ONLY for cross-validation against the C binary (statistical parity).
    """
    n, d = key.n, key.d
    lo, hi = max(1, (d + 1) // 2), d
    xcache: dict = {}
    bits = np.zeros(n, dtype=np.uint8)
    e_true = np.asarray(e_true, dtype=np.uint8)
    dist = int(e_true.sum())
    s = s0.copy()
    res = TrajectoryResult("CLASSIC-DYN", False, None, 0)
    it = 0
    blocked = False
    while it < max_iter and s.sum() != 0 and not blocked:
        it += 1
        alpha = key.upc_fast(s)
        th = _classic_threshold_value(int(s.sum()), dist, d, n, lo, hi, xcache)
        blocked = True
        flips = np.nonzero(alpha >= th)[0]
        for p in flips:
            pi = int(p)
            s = key.flip(s, pi)
            bits[pi] ^= 1
            dist += 2 * int(bits[pi] ^ e_true[pi]) - 1
        if flips.size:
            blocked = False
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(int(flips.size))
        res.n_iters_run = it
    res.success = dist == 0
    res.extra = {"final_dist": dist}
    return res


# --------------------------------------------------------------------- BF
def bf_parallel(
    key: QCKey,
    s0: np.ndarray,
    thr,
    max_iter: int,
    fixed_iters: bool = False,
    record_flips: bool = False,
    track_estimate: bool = False,
) -> TrajectoryResult:
    """Classic parallel bit-flipping: flip all positions with UPC >= threshold."""
    s = s0.copy()
    res = TrajectoryResult("BF", False, None, 0)
    estimate = np.zeros(key.n, dtype=np.uint8) if track_estimate else None
    success_at = None
    for it in range(max_iter):
        if s.sum() == 0:
            if success_at is None:
                success_at = it
            if not fixed_iters:
                break
        alpha = key.upc_fast(s)
        th = thr(it, int(s.sum()))
        flips = np.nonzero(alpha >= th)[0]
        for p in flips:
            s = key.flip(s, int(p))
        if estimate is not None and flips.size:
            estimate[flips] ^= 1
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(int(flips.size))
        if record_flips:
            res.flip_positions.append([int(p) for p in flips])
        res.n_iters_run = it + 1
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    res.estimated_error = estimate
    return res


# --------------------------------------------------------------------- BGF (exact GRAY_BGF port)
def bgf_vasseur(
    key: QCKey,
    s0: np.ndarray,
    thr,
    max_iter: int,
    gray_delta: int = 3,
    fixed_iters: bool = False,
    record_flips: bool = False,
) -> TrajectoryResult:
    """Exact port of GRAY_BGF (decoder.c) per FROZEN_REFERENCE_SEMANTICS.md.

    Main step: flip counters >= thr (black), collect thr-gray_delta <= counter
    < thr (gray). After the FIRST main step only: black re-check (flip back if
    counter >= (d+1)/2 + 1) then gray step (flip if counter >= (d+1)/2 + 1);
    each substep counts as one iteration. Exits on zero syndrome, max_iter, or
    a fully blocked round (no flips anywhere).
    """
    s = s0.copy()
    res = TrajectoryResult("BGF", False, None, 0)
    it = 0
    blocked = False
    success_at = None
    recheck_bound = (key.d + 1) // 2 + 1

    def log_step(flips_list):
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(len(flips_list))
        if record_flips:
            res.flip_positions.append(list(flips_list))

    while it < max_iter and s.sum() != 0 and not blocked:
        it += 1
        alpha = key.upc_fast(s)
        threshold = thr(it, int(s.sum()))
        blocked = True
        flips = np.nonzero(alpha >= threshold)[0]
        black = [int(p) for p in flips]
        gray = [int(p) for p in np.nonzero((alpha < threshold) & (alpha + gray_delta >= threshold))[0]]
        for p in black:
            s = key.flip(s, p)
        if black:
            blocked = False
        log_step(black)
        if s.sum() == 0 and success_at is None:
            success_at = it
        # black + gray substeps only after the first main step (GRAY_BGF)
        if it < 2 and it < max_iter and s.sum() != 0:
            it += 1
            alpha2 = key.upc_fast(s)
            reflip = [p for p in black if alpha2[p] >= recheck_bound]
            for p in reflip:
                s = key.flip(s, p)
            if reflip:
                blocked = False
            log_step(reflip)
            if s.sum() == 0 and success_at is None:
                success_at = it
            if it < max_iter and s.sum() != 0:
                it += 1
                alpha3 = key.upc_fast(s)
                gflip = [p for p in gray if alpha3[p] >= recheck_bound]
                for p in gflip:
                    s = key.flip(s, p)
                if gflip:
                    blocked = False
                log_step(gflip)
                if s.sum() == 0 and success_at is None:
                    success_at = it
        res.n_iters_run = it
        if success_at is not None and not fixed_iters and s.sum() == 0:
            break
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    return res


# --------------------------------------------------------------------- BGF-lite
def bgf_lite(
    key: QCKey,
    s0: np.ndarray,
    thr,
    max_iter: int,
    fixed_iters: bool = False,
    record_flips: bool = False,
) -> TrajectoryResult:
    """Preliminary black/gray flip (see module docstring for M0 caveat).

    black: positions with UPC >= th are flipped;
    gray:  positions with UPC == th-1 are remembered; next round they are
           flipped if their UPC >= max(1, th-1).
    """
    s = s0.copy()
    res = TrajectoryResult("BGF", False, None, 0)
    gray: set[int] = set()
    success_at = None
    for it in range(max_iter):
        if s.sum() == 0:
            if success_at is None:
                success_at = it
            if not fixed_iters:
                break
        alpha = key.upc_fast(s)
        th = thr(it, int(s.sum()))
        black = set(int(p) for p in np.nonzero(alpha >= th)[0])
        new_gray = set(int(p) for p in np.nonzero(alpha == th - 1)[0])
        flips = sorted(black | {g for g in gray if alpha[g] >= max(1, th - 1)})
        for p in flips:
            s = key.flip(s, p)
        gray = new_gray
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(len(flips))
        if record_flips:
            res.flip_positions.append(flips)
        res.n_iters_run = it + 1
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    return res


# --------------------------------------------------------------------- BF-Max
def bf_max(
    key: QCKey,
    s0: np.ndarray,
    budget: int,
    fixed_iters: bool = False,
    record_flips: bool = False,
    tie_break: str = "first",
    salt: bytes = b"",
) -> TrajectoryResult:
    """BF-Max (Baldelli et al., arXiv:2506.09689): each iteration flips exactly
    one bit - the maximum-UPC (least reliable) position.

    Tie-break modes (pre-registered):
    - "first": smallest global index (deterministic; default);
    - "prf":   uniform among tied positions via PRF(salt || s0 || iteration),
              deterministic given (s0, salt) => reproducible independent draws
              by varying salt. Needed because high-UPC ties are common at
              d=71 and the original paper's tie handling must be verified.
    Budget: default = error weight t (caller decides).
    """
    import hashlib

    s = s0.copy()
    res = TrajectoryResult("BF-Max", False, None, 0)
    res.extra = {"tie_break": tie_break}
    prf_state = None
    if tie_break == "prf":
        prf_state = hashlib.sha256(salt + np.ascontiguousarray(s0).tobytes()).digest()
    success_at = None
    for it in range(budget):
        if s.sum() == 0:
            if success_at is None:
                success_at = it
            if not fixed_iters:
                break
        alpha = key.upc_fast(s)
        mx = int(alpha.max())
        if mx <= 0:  # no unsatisfied check touches any position: hopeless
            res.syndrome_weights.append(int(s.sum()))
            res.flip_counts.append(0)
            res.n_iters_run = it + 1
            break
        cand = np.flatnonzero(alpha == mx)
        if cand.size == 1 or tie_break == "first":
            p = int(cand[0])
        else:
            digest = hashlib.sha256(prf_state + it.to_bytes(2, "big")).digest()
            p = int(cand[int.from_bytes(digest[:4], "big") % cand.size])
        s = key.flip(s, p)
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(1)
        if record_flips:
            res.flip_positions.append([p])
        res.n_iters_run = it + 1
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    return res


DECODERS = {"bf_parallel": bf_parallel, "bgf_lite": bgf_lite, "bgf_vasseur": bgf_vasseur, "bf_max": bf_max}


# --------------------------------------------------------------------- CPS
def cps_bf(
    key: QCKey,
    s0: np.ndarray,
    base_thr,
    jitters: list[int],
    max_iter: int,
    d: int,
    fixed_iters: bool = False,
    record_flips: bool = False,
) -> TrajectoryResult:
    """Constrained pseudorandom schedule (research prototype, pre-registered).

    coin = SHA-256(syndrome bytes)[0] mod |jitters|   (deterministic given the
    input; in the Niederreiter setting the syndrome IS the ciphertext, so this
    realizes salt = H(ciphertext) without touching the KEM interface).
    Threshold: thr(it, sw) = clip(base_thr(it, sw) + jitters[coin], lo, hi).
    Fixed iteration budget and integer thresholds are inherited from base_thr.
    """
    import hashlib

    coin = int(hashlib.sha256(np.ascontiguousarray(s0).tobytes()).digest()[0]) % len(jitters)
    delta = int(jitters[coin])
    lo = max(1, (d + 1) // 2)
    hi = d

    def thr(it: int, sw: int) -> int:
        return int(np.clip(base_thr(it, sw) + delta, lo, hi))

    res = bf_parallel(key, s0, thr, max_iter, fixed_iters, record_flips)
    res.decoder = "CPS"
    res.extra = {"coin": coin, "delta": delta}
    return res


def build_decoder(name: str, spec: dict, d: int, t: int, r: int | None = None):
    """Instantiate decoder callable from config spec."""
    algo = spec["algo"]
    max_iter = int(spec.get("max_iter", t))
    fixed_iters = bool(spec.get("fixed_iters", False))
    if algo == "bf_max":
        tie_break = str(spec.get("tie_break", "first"))

        def run(key: QCKey, s0: np.ndarray, record_flips: bool = False, salt: bytes = b"") -> TrajectoryResult:
            return bf_max(key, s0, max_iter, fixed_iters, record_flips, tie_break, salt)

        return run
    n = 2 * r if r is not None else None
    if algo == "cps":
        base_thr = make_threshold(spec["base_threshold"], d, t, n)
        jitters = [int(x) for x in spec["jitters"]]

        def run(key: QCKey, s0: np.ndarray, record_flips: bool = False) -> TrajectoryResult:
            return cps_bf(key, s0, base_thr, jitters, max_iter, d, fixed_iters, record_flips)

        return run
    thr = make_threshold(spec["threshold"], d, t, n)
    if algo == "bgf_vasseur":
        gray_delta = int(spec.get("gray_delta", 3))  # GRAY_DELTA default per param.h

        def run(key: QCKey, s0: np.ndarray, record_flips: bool = False) -> TrajectoryResult:
            return bgf_vasseur(key, s0, thr, max_iter, gray_delta, fixed_iters, record_flips)

        return run
    fn = DECODERS[algo]

    if algo == "bf_parallel":
        def run(key: QCKey, s0: np.ndarray, record_flips: bool = False,
                track_estimate: bool = False) -> TrajectoryResult:
            return fn(key, s0, thr, max_iter, fixed_iters, record_flips, track_estimate)

        return run

    def run(key: QCKey, s0: np.ndarray, record_flips: bool = False) -> TrajectoryResult:
        return fn(key, s0, thr, max_iter, fixed_iters, record_flips)

    return run
