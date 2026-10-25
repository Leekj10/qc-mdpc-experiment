"""Statistics: per-key DFR, one-sided 95% upper bounds, heterogeneity indices.

Pre-registered rules:
- zero failures -> report Wilson/`3/N` upper bound, never "DFR = 0"
- Wilson one-sided 95% upper bound (z = 1.6449) for k > 0
- rule of three (3/N) when k = 0
- heterogeneity primary index: P90/P10 over log10(DFR) among keys with k > 0
- coefficient of variation (CV) is NOT used (degenerate near zero DFR)
"""
from __future__ import annotations

import math

import numpy as np

Z95_ONE_SIDED = 1.6448536269514722


def wilson_upper(k: int, n: int, z: float = Z95_ONE_SIDED) -> float:
    """One-sided Wilson upper confidence bound for a binomial proportion."""
    if n <= 0:
        return 1.0
    if k == 0:
        return min(1.0, 3.0 / n)  # rule of three, pre-registered
    p = k / n
    z2 = z * z
    center = p + z2 / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return min(1.0, (center + half) / (1 + z2 / n))


def dfr_interval(k: int, n: int) -> tuple[float, float]:
    """(point estimate, one-sided 95% upper bound)."""
    return (k / n if n else float("nan")), wilson_upper(k, n)


def per_key_summary(failures: np.ndarray, trials: np.ndarray) -> dict:
    """failures/trials are per-key counts (arrays of equal length)."""
    failures = np.asarray(failures, dtype=np.int64)
    trials = np.asarray(trials, dtype=np.int64)
    p = np.where(trials > 0, failures / np.maximum(trials, 1), np.nan)
    ub = np.array([wilson_upper(int(k), int(n)) for k, n in zip(failures, trials)])
    nonzero = failures > 0
    log10_p = np.full(len(failures), np.nan)
    log10_p[nonzero] = np.log10(p[nonzero])
    out = {
        "n_keys": int(len(failures)),
        "keys_zero_failures": int((~nonzero).sum()),
        "total_trials": int(trials.sum()),
        "total_failures": int(failures.sum()),
        "overall_dfr": float(failures.sum() / max(1, trials.sum())),
        "log10_dfr_mean_nonzero": float(np.nanmean(log10_p)) if nonzero.any() else None,
        "log10_dfr_std_nonzero": float(np.nanstd(log10_p)) if nonzero.any() else None,
    }
    if nonzero.sum() >= 10:
        p90, p10 = np.percentile(log10_p[nonzero], [90, 10])
        out["log10_p90"] = float(p90)
        out["log10_p10"] = float(p10)
        out["p90_minus_p10_log10"] = float(p90 - p10)  # >= 1 means >= 10x span
    return out


def heterogeneity_gate(summary: dict, min_span_log10: float = 1.0) -> bool | None:
    """H1 quick gate on the P90-P10 span (pre-registered threshold: log10 >= 1,
    i.e. P90/P10 >= 10; the full plan gate also accepts structured-group gaps)."""
    v = summary.get("p90_minus_p10_log10")
    if v is None:
        return None
    return bool(v >= min_span_log10)


# =====================================================================
# Cluster-robust inference (review round-3, P0-6 / P0-7 / P0-8).
#
# The independent sampling unit for CROSS-KEY inference is the KEY, not the
# individual error sample: each key contributes E paired error draws, so the
# sample-level Wilson bound and exact McNemar are conditional on the sampled
# keys. The helpers below resample KEYS (cluster bootstrap) and apply Holm
# multiplicity correction; they SUPPORT the pre-registered gate (which uses the
# worst-group Wilson U_0.95 only) and change no decision rule, no parameter and
# no headline number.
# =====================================================================


def sign_test_paired(base_counts, treat_counts) -> dict:
    """Exact two-sided binomial sign test on per-key paired failure counts.

    base_counts / treat_counts are equal-length arrays of per-key failures.
    A key 'improves' when treat < base; ties are dropped. This is the key-level
    (cluster) counterpart to the sample-level exact McNemar.
    """
    imp = sum(1 for x, y in zip(base_counts, treat_counts) if y < x)
    wor = sum(1 for x, y in zip(base_counts, treat_counts) if y > x)
    tie = sum(1 for x, y in zip(base_counts, treat_counts) if y == x)
    n = imp + wor
    if n == 0:
        return {"improved": imp, "worse": wor, "tied": tie, "n_discordant": 0, "p_two_sided": 1.0}
    k = min(imp, wor)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return {"improved": imp, "worse": wor, "tied": tie, "n_discordant": n,
            "p_two_sided": min(1.0, 2 * tail)}


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar on per-sample discordant counts (b=base-only,
    c=treat-only failures). Sample-level, conditional on the sampled keys.
    For large discordant n the binomial tail is accumulated in log-space to
    avoid int->float overflow (small n keeps the original integer path so
    archived values are bit-identical)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    if n <= 500:
        tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
        return min(1.0, 2 * tail)
    ln2 = math.log(2.0)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) - n * ln2
             for i in range(k + 1)]
    m = max(terms)
    tail = math.exp(m) * sum(math.exp(t - m) for t in terms)
    return min(1.0, 2 * tail)


def holm_adjust(pvals) -> list:
    """Holm-Bonferroni step-down adjusted p-values, returned in input order.

    adj_(i) = max_{j <= i} (n - j) * p_(j) over the ascending-sorted p-values,
    capped at 1 and made monotone. Controls the family-wise error rate across
    the three condition groups (RAND / WEAK-12 / NCW-intersecting).
    """
    p = [float(x) for x in pvals]
    n = len(p)
    order = sorted(range(n), key=lambda i: p[i])
    adj = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (n - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def cluster_bootstrap_paired(base_counts, treat_counts, E: int, B: int = 10000,
                             seed: int = 20260905, ci: float = 0.95) -> dict:
    """Cluster bootstrap over KEYS for the paired base-vs-treatment contrast.

    Keys are resampled with replacement B times; each replicate pools the drawn
    keys' failure counts and recomputes the risk ratio RR = DFR_base/DFR_treat
    (>1 favours treatment), the DFR difference DFR_base - DFR_treat (>0 favours
    treatment), and log10(RR). Percentile CIs are returned. The 'no improvement'
    reference (RR=1, diff=0, log10RR=0) lying OUTSIDE the CI is the cross-key
    significance criterion (review P0-6). Deterministic given `seed`.
    """
    base = np.asarray(base_counts, dtype=np.int64)
    treat = np.asarray(treat_counts, dtype=np.int64)
    n = int(base.size)
    if n == 0 or treat.size != n:
        raise ValueError("per-key counts must be non-empty and equal length")
    rng = np.random.default_rng(seed)
    alpha = 1.0 - float(ci)
    lo_q, hi_q = 100.0 * alpha / 2.0, 100.0 * (1.0 - alpha / 2.0)
    trials = n * E  # each replicate draws n keys, each with E paired errors

    def _safe(x):
        x = float(x)
        return None if (math.isnan(x) or math.isinf(x)) else x

    # observed point estimates (all keys, weight 1)
    b0, t0 = float(base.sum()), float(treat.sum())
    dfr_b0, dfr_t0 = b0 / trials, t0 / trials
    rr0 = (dfr_b0 / dfr_t0) if dfr_t0 > 0 else float("nan")
    lrr0 = math.log10(rr0) if (dfr_t0 > 0 and rr0 > 0) else float("nan")

    # bootstrap replicates (vectorised): draw (B, n) key indices with replacement
    idx = rng.integers(0, n, size=(B, n))
    b_sums = base[idx].sum(axis=1).astype(np.float64)
    t_sums = treat[idx].sum(axis=1).astype(np.float64)
    dfr_b = b_sums / trials
    dfr_t = t_sums / trials
    with np.errstate(divide="ignore", invalid="ignore"):
        rr = dfr_b / dfr_t
        lrr = np.log10(rr)
    diff = dfr_b - dfr_t
    rr[~np.isfinite(rr)] = np.nan
    lrr[~np.isfinite(lrr)] = np.nan

    def _ci(arr):
        a = arr[~np.isnan(arr)]
        if a.size == 0:
            return [None, None]
        return [float(np.percentile(a, lo_q)), float(np.percentile(a, hi_q))]

    return {
        "n_keys": n, "E_per_key": int(E), "B": int(B), "seed": int(seed), "ci_level": float(ci),
        "point": {
            "dfr_base": dfr_b0, "dfr_treat": dfr_t0,
            "risk_ratio": _safe(rr0), "dfr_diff": dfr_b0 - dfr_t0,
            "log10_risk_ratio": _safe(lrr0),
        },
        "ci": {"risk_ratio": _ci(rr), "dfr_diff": _ci(diff), "log10_risk_ratio": _ci(lrr)},
        "n_nonfinite_rr": int(np.isnan(rr).sum()),
        # cross-key significance: 'no improvement' reference excluded from the CI
        "rr_excludes_1": bool(_ci(rr)[0] is not None and _ci(rr)[0] > 1.0),
        "diff_excludes_0": bool(_ci(diff)[0] is not None and _ci(diff)[0] > 0.0),
        "log10rr_excludes_0": bool(_ci(lrr)[0] is not None and _ci(lrr)[0] > 0.0),
    }
