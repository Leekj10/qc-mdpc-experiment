"""Statistical verification for the extended gate results.

Replaces back-of-envelope numbers with computed values:
1. Poisson dispersion ratio (var/mean of per-key failure counts) per group/decoder
   + 95% CI via chi-square-free normal approximation on the dispersion index;
2. Key-level PAIRED analysis: improved / worse / tied keys, exact two-sided
   sign test (binomial) on discordant keys;
3. Group gradient tests vs G0 for the base decoder (Poisson rate ratio z).
Output: results/gate_h2_extended/stats_verification.json
"""
from __future__ import annotations

import json
import math
import os
import sys

REPORT = sys.argv[1] if len(sys.argv) > 1 else "results/gate_h2_extended/report.json"
OUT = os.path.join(os.path.dirname(REPORT), "stats_verification.json")


def dispersion(counts):
    n = len(counts)
    mean = sum(counts) / n
    var = sum((c - mean) ** 2 for c in counts) / (n - 1) if n > 1 else float("nan")
    ratio = var / mean if mean > 0 else float("nan")
    # normal approx for dispersion index D = (n-1)*var/mean ~ chi2(n-1);
    # z = (D - (n-1)) / sqrt(2(n-1))
    if mean > 0:
        D = (n - 1) * var / mean
        z = (D - (n - 1)) / math.sqrt(2 * (n - 1))
    else:
        z = float("nan")
    return {"n_keys": n, "mean": mean, "var": var, "dispersion_ratio": ratio, "dispersion_z": z}


def sign_test_paired(a, b):
    """a=base counts, b=treatment counts per key. Exact two-sided binomial sign test."""
    imp = sum(1 for x, y in zip(a, b) if y < x)
    wor = sum(1 for x, y in zip(a, b) if y > x)
    tie = sum(1 for x, y in zip(a, b) if y == x)
    n = imp + wor
    if n == 0:
        return {"improved": imp, "worse": wor, "tied": tie, "p_two_sided": 1.0}
    k = min(imp, wor)
    # exact binomial tail *2 (two-sided), p=0.5
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    p = min(1.0, 2 * tail)
    return {"improved": imp, "worse": wor, "tied": tie, "n_discordant": n, "p_two_sided": p}


def poisson_z(f1, n1, f2, n2):
    """Two-sample Poisson rate z-test (f1/n1 vs f2/n2), CONDITIONAL on the total.

    Corrected 2026-09-03 (review round-2, P0-4): under H0 (equal rates),
    f1 | tot ~ Binomial(tot, p=n1/(n1+n2)), so Var = tot*p*(1-p), NOT tot*p (=e1).
    The previous sqrt(e1) omitted the (1-p) factor and understated |z| by
    1/sqrt(1-p) (~1.41x when n1~n2), i.e. it was CONSERVATIVE. This statistic is
    DESCRIPTIVE (condition ordering) and is NOT part of the pre-registered gate
    (which uses Wilson U95 only), so the correction changes no decision.
    """
    r1, r2 = f1 / n1, f2 / n2
    tot = f1 + f2
    if tot == 0:
        return float("nan"), float("nan")
    p = n1 / (n1 + n2)
    e1 = tot * p
    z = (f1 - e1) / math.sqrt(e1 * (1.0 - p))
    return r1 / r2 if r2 > 0 else float("inf"), z


def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    out = {"source": REPORT, "groups": {}}
    for gid, g in rep["groups"].items():
        c0 = g["C0_base"]["per_key_failures"]
        c4 = g["C4_first_p2"]["per_key_failures"]
        entry = {
            "dispersion_C0": dispersion(c0),
            "dispersion_C4": dispersion(c4),
            "paired_sign_test": sign_test_paired(c0, c4),
        }
        out["groups"][gid] = entry
    # gradient vs G0 for base decoder
    g0 = rep["groups"]["G0"]["C0_base"]
    grads = {}
    for gid in ["G2_d12", "G3"]:
        gx = rep["groups"][gid]["C0_base"]
        rr, z = poisson_z(gx["failures"], gx["trials"], g0["failures"], g0["trials"])
        grads[gid] = {"rate_ratio_vs_G0": rr, "z": z}
    out["base_gradient_vs_G0"] = grads
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    # console summary
    for gid, e in out["groups"].items():
        d0, d4, st = e["dispersion_C0"], e["dispersion_C4"], e["paired_sign_test"]
        print(f"[{gid}] disp C0={d0['dispersion_ratio']:.2f} (z={d0['dispersion_z']:+.2f}) | "
              f"C4={d4['dispersion_ratio']:.2f} (z={d4['dispersion_z']:+.2f}) | "
              f"paired: imp={st['improved']} wor={st['worse']} tie={st['tied']} p={st['p_two_sided']:.2e}")
    for gid, gg in grads.items():
        print(f"[gradient] {gid}/G0 rate ratio={gg['rate_ratio_vs_G0']:.2f} z={gg['z']:+.2f}")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
