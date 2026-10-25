"""Hierarchical / cluster-robust sensitivity analysis (review round-3, Q2 priority-5).

Zero-decoding: reuses the archived per-key failure counts. Adds two hierarchical
layers that the sample-level Wilson/McNemar and the cluster bootstrap complement:

  1. Paired RANDOM-INTERCEPT logistic regression per key:
         y_{i,a} ~ Binomial(n, p_{i,a}),  logit p_{i,a} = b0 + b1*a + sigma*u_i,
         u_i ~ N(0,1)  (key-level random intercept), a in {0=base, 1=FRO-2}.
     Fitted by MLE with Gauss-Hermite quadrature over u. Reports the cross-key
     arm effect b1 (log odds ratio), its 95% CI (numerical Hessian), the
     between-key SD sigma, and a likelihood-ratio test of sigma>0 (key-level
     heterogeneity beyond binomial; boundary => 0.5*chi2_1 mixture).

  2. Per-arm BETA-BINOMIAL overdispersion: p_i ~ Beta(a,b) with mean mu and
     intra-class rho = 1/(a+b+1). Reports rho and an LR test vs the plain
     binomial (rho=0 boundary => 0.5*chi2_1 mixture). rho~0 means key-level
     dispersion is binomial/Poisson-consistent (no extra heterogeneity).

These are SENSITIVITY analyses supporting the pre-registered gate; they change no
decision rule, parameter, metric definition or headline number.

Outputs: results/m5_formal/hierarchical.json
Usage : python analyze_hierarchical.py [m5_formal/report.json] [fresh_only_verification.json]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import betaln, expit, logit, roots_hermite
from scipy.stats import chi2

REPORT = sys.argv[1] if len(sys.argv) > 1 else "results/m5_formal/report.json"
FRESH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(REPORT), "fresh_only_verification.json")
OUT = os.path.join(os.path.dirname(REPORT), "hierarchical.json")

GIDS = ["G0", "G2_d12", "G3"]
BASE, TREAT = "C0_base", "C4_first_p2"
GH_NODES = 41


def _gh():
    x, w = roots_hermite(GH_NODES)
    return np.sqrt(2.0) * x, w / np.sqrt(np.pi)


_U, _W = _gh()
_LOGW = np.log(np.where(_W > 0, _W, 1e-300))


def _binom_logpmf(y, n, p):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    from scipy.special import gammaln
    return (gammaln(n + 1) - gammaln(y + 1) - gammaln(n - y + 1)
            + y * np.log(p) + (n - y) * np.log1p(-p))


def _bb_logpmf(y, n, mu, rho):
    """Beta-binomial log-pmf: p_i ~ Beta(a,b), mu=a/(a+b), rho=1/(a+b+1)."""
    rho = min(max(float(rho), 1e-9), 1 - 1e-9)
    mu = min(max(float(mu), 1e-9), 1 - 1e-9)
    a = mu * (1 - rho) / rho
    b = (1 - mu) * (1 - rho) / rho
    from scipy.special import gammaln
    comb = gammaln(n + 1) - gammaln(y + 1) - gammaln(n - y + 1)
    return comb + betaln(y + a, n - y + b) - betaln(a, b)


def bb_reg_nll(params, y0, y1, n, fix_rho_zero=False):
    """Negative log-lik of a beta-binomial REGRESSION with an arm covariate:
    logit mu_{i,a} = b0 + b1*a, key-level extra-binomial variation via rho.
    fix_rho_zero reduces it to the plain (binomial) logistic model."""
    b0, b1 = params[0], params[1]
    if fix_rho_zero:
        p0 = expit(b0); p1 = expit(b0 + b1)
        ll = _binom_logpmf(y0, n, p0).sum() + _binom_logpmf(y1, n, p1).sum()
        return -float(ll)
    rho = expit(params[2])
    ll = (_bb_logpmf(y0, n, expit(b0), rho).sum()
          + _bb_logpmf(y1, n, expit(b0 + b1), rho).sum())
    return -float(ll)


def _hessian_se(fun, x, args, idx=1, h=1e-4):
    k = len(x)
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(i, k):
            xp = x.copy(); xp[i] += h; xp[j] += h
            xm = x.copy(); xm[i] -= h; xm[j] -= h
            xpj = x.copy(); xpj[i] += h; xpj[j] -= h
            xmj = x.copy(); xmj[i] -= h; xmj[j] += h
            H[i, j] = H[j, i] = (fun(xp, *args) - fun(xpj, *args)
                                 - fun(xmj, *args) + fun(xm, *args)) / (4 * h * h)
    cov = np.linalg.pinv(H)
    se = float(np.sqrt(max(cov[idx, idx], 0.0)))
    return se if (np.isfinite(se) and se > 0) else float("nan")


def fit_bb_reg(y0, y1, n):
    """Hierarchical (beta-binomial regression) cross-key arm effect."""
    y0 = np.asarray(y0, float); y1 = np.asarray(y1, float)
    p_base = max(y0.sum() / (len(y0) * n), 1e-6)
    p_tr = max(y1.sum() / (len(y1) * n), 1e-6)
    init = [logit(p_base), np.log(p_tr / p_base), logit(0.05)]
    res = minimize(bb_reg_nll, init, args=(y0, y1, n), method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-9, "fatol": 1e-9})
    res = minimize(bb_reg_nll, res.x, args=(y0, y1, n), method="BFGS",
                   options={"maxiter": 500})
    ll_full = -res.fun
    se_b1 = _hessian_se(bb_reg_nll, res.x, (y0, y1, n), idx=1)
    # LR test rho>0 (key-level overdispersion; boundary => 0.5*chi2_1)
    res0 = minimize(lambda p: bb_reg_nll(np.array([p[0], p[1], 0.0]), y0, y1, n, True),
                    [res.x[0], res.x[1]], method="Nelder-Mead", options={"maxiter": 3000})
    ll_null = -res0.fun
    lr = max(0.0, 2 * (ll_full - ll_null))
    b1 = float(res.x[1]); rho = float(expit(res.x[2]))
    ci = [float(np.exp(b1 - 1.96 * se_b1)), float(np.exp(b1 + 1.96 * se_b1))] if se_b1 == se_b1 else [None, None]
    return {
        "log_or_arm": b1,
        "odds_ratio_arm": float(np.exp(b1)),
        "or_ci95": ci,
        "se_log_or": se_b1,
        "rho_intra_class": rho,
        "lr_rho": float(lr), "p_rho_gt0": float(0.5 * chi2.sf(lr, 1)),
        # FRO-2 reduces failures => OR<1; significant iff the whole CI lies BELOW 1
        "or_excludes_1": bool(se_b1 == se_b1 and (b1 + 1.96 * se_b1) < 0),
    }


def betabinom_arm(y, n):
    y = np.asarray(y, float)
    mu0 = max(y.sum() / (len(y) * n), 1e-6)

    def nll(theta):
        lm, lrho = theta
        mu = expit(lm); rho = expit(lrho)
        denom = max(1e-9, rho)
        a = mu * (1 - rho) / denom
        b = (1 - mu) * (1 - rho) / denom
        a = max(a, 1e-8); b = max(b, 1e-8)
        ll = (betaln(y + a, n - y + b) - betaln(a, b)).sum()
        return -float(ll)

    res = minimize(nll, [logit(mu0), logit(0.05)], method="Nelder-Mead",
                   options={"maxiter": 3000, "xatol": 1e-8, "fatol": 1e-8})
    mu = expit(res.x[0]); rho = expit(res.x[1])
    ll_full = -res.fun
    # null: binomial (rho=0) with pooled p
    p = y.sum() / (len(y) * n)
    ll_null = float(_binom_logpmf(y, n, p).sum())
    lr = max(0.0, 2 * (ll_full - ll_null))
    return {"mu": float(mu), "rho_intra_class": float(rho),
            "lr_rho": float(lr), "p_rho_gt0": float(0.5 * chi2.sf(lr, 1))}


def analyse(groups, e_per_key):
    out = {"E_per_key": e_per_key, "groups": {}}
    for gid in GIDS:
        g = groups[gid]
        y0 = np.array(g[BASE]["per_key_failures"], float)
        y1 = np.array(g[TREAT]["per_key_failures"], float)
        out["groups"][gid] = {
            "bb_regression": fit_bb_reg(y0, y1, e_per_key),
            "betabinom_base": betabinom_arm(y0, e_per_key),
            "betabinom_treat": betabinom_arm(y1, e_per_key),
        }
    return out


def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    e_full = int(rep.get("E_per_key", 3000))
    result = {"source": {"formal": REPORT}, "full_formal": analyse(rep["groups"], e_full)}
    if os.path.exists(FRESH):
        fr = json.load(open(FRESH, encoding="utf-8"))
        e_f = int(fr.get("E_per_key", 3000))
        result["source"]["pure_fresh"] = FRESH
        result["pure_fresh"] = analyse(fr["groups"], e_f)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    for pool in ["full_formal", "pure_fresh"]:
        if pool not in result:
            continue
        print(f"\n== hierarchical sensitivity: {pool} ==")
        for gid in GIDS:
            e = result[pool]["groups"][gid]
            r = e["bb_regression"]
            bb = e["betabinom_base"]
            ci = r["or_ci95"]
            ci_s = "n/a" if ci[0] is None else f"[{ci[0]:.3f},{ci[1]:.3f}]"
            print(f"[{gid:8s}] BB-reg OR(FRO vs C0)={r['odds_ratio_arm']:.3f} "
                  f"CI{ci_s} excl1={r['or_excludes_1']} "
                  f"rho={r['rho_intra_class']:.4f} p(rho>0)={r['p_rho_gt0']:.2e}")
            print(f"           beta-binom base rho={bb['rho_intra_class']:.4f} p(rho>0)={bb['p_rho_gt0']:.2e} | "
                  f"treat rho={e['betabinom_treat']['rho_intra_class']:.4f} p={e['betabinom_treat']['p_rho_gt0']:.2e}")
    print("\nsaved ->", OUT)


if __name__ == "__main__":
    main()
