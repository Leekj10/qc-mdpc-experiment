#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fair modern-decoder comparison at the production code parameters (design B).

Design (frozen before run; see the 2026-10-10 audit workflow, design B of F2):
  - Operating point: (r,d)=(12323,71) -- EXACTLY the BIKE Level-1 code parameters --
    with only the error weight raised to t*=172 (the preregistered P1PP point).
  - Instances: the IDENTICAL 32 keys x 1500 errors used by results/tier_upgrade/
    p1pp_main.json, reconstructed from KeyPool(20260901, "L1", "RAND") and the same
    error generator, in the same order.
  - Pipeline gate: C0 / FRO-2 / FRONEG MUST reproduce the archived failure totals
    94 / 21 / 582 of 48,000. This proves instance identity before any new arm is read.

New arms (all on the same paired instances, static semantics, zero-syndrome success):
  - BIKE-Flip with the OFFICIAL L1 constants (spec v5.2 p.14:
    a=0.006254868353074983, b=11.101432337243956, delta=3, NbIter=7) at BOTH its
    spec budget (7) and the study's matched budget (20); the constants were fitted
    for t=134 and are therefore off-design at t=172 -- that off-design status is the
    quantity being documented.
  - BIKE-Flip with constants RE-DERIVED by the specification's own A.2.4 tangent rule
    at (12323,71,172) (delta=3 borrowed from Level 1, documented choice; the spec
    leaves delta and NbIter unspecified outside its official table), again at 7 and
    20 iterations.
  - GRAY_BGF with the literature constants (c0=13.53, c1=0.0069722; BGF's L1 fit,
    FROZEN_REFERENCE_SEMANTICS.md sec 4b), gray_delta=3, max_iter=20, plus a variant
    driven by the specification's A.2.4 tangent at this point -- the best a-priori
    constants constructible, since BGF itself has no published derivation rule.

Reading rules fixed in advance:
  - This point measures the production CODE at a raised error weight, not the
    production operating point. No production-weight claim follows from it.
  - BIKE-Flip's spec budget is 7; the matched layer grants every arm 20. Both are
    reported, never mixed.
  - DFRs are observed; zero-failure arms get rule-of-three bounds only.

Run:  python lw-vs/scripts/exp_fair_l1.py [--smoke]
Output: lw-vs/results/fair_l1/report.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "fair_l1"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.bikeflip import bike_flip, derive_bikeflip_affine   # noqa: E402
from qcmdpc.decoders import build_decoder                        # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator      # noqa: E402
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)

SEED = 20260901
T_STAR = 172                      # preregistered P1PP point (tier_upgrade/p1pp_main.json)
R, D = 12323, 71
N_KEYS, E_PER_KEY = 32, 1500
N_WORKERS = int(os.environ.get("FAIR_WORKERS", "6"))
MAX_ITER = 20                     # the study's common budget (carrier max_iter)

PARAM = {"id": "L1", "r": R, "d": D, "t": T_STAR, "n0": 2}
POOL_SPEC = {"type": "random", "n_keys": N_KEYS}

# Official BIKE-Flip L1 constants (spec p.14); the (r,d,t) key is L1's own point.
BF_OFFICIAL = {"a": 0.006254868353074983, "b": 11.101432337243956, "delta": 3}

CARRIER_ARMS = {"C0": [0], "FRO-2": [2, 0], "FRONEG": [-1, 0]}
EXPECTED = {"C0": 94, "FRO-2": 21, "FRONEG": 582}   # p1pp_main.json, of 48,000

BGF_OFFICIAL = {"c0": 13.53, "c1": 0.0069722, "gray_delta": 3}


def _mcnemar(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n))


def _work(job):
    """One key: carrier arms + all new arms on the same (H, e, s) instances."""
    ki, n_err = job
    pool = KeyPool(SEED, PARAM, "RAND", POOL_SPEC)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, PARAM, POOL_SPEC, key, None)

    # Constants derived at run time by the spec's own A.2.4 rule (no hardcoding).
    a_d, b_d, savg = derive_bikeflip_affine(R, D, T_STAR)

    decs = {nm: build_decoder(nm, {"algo": "bf_parallel",
                                   "threshold": {"type": "offset",
                                                 "base": {"type": "classic"},
                                                 "offsets": off},
                                   "max_iter": MAX_ITER}, D, T_STAR, R)
            for nm, off in CARRIER_ARMS.items()}
    decs["BGF-official"] = build_decoder("BGF-official",
                                         {"algo": "bgf_vasseur",
                                          "threshold": {"type": "affine_vasseur",
                                                        "c0": BGF_OFFICIAL["c0"],
                                                        "c1": BGF_OFFICIAL["c1"]},
                                          "max_iter": MAX_ITER,
                                          "gray_delta": BGF_OFFICIAL["gray_delta"]},
                                         D, T_STAR, R)
    # BGF has no published derivation rule, so the best a-priori constants one can
    # construct are the specification's A.2.4 tangent at this point (the same (a,b)
    # the derived BIKE-Flip arm uses). This arm documents that variant.
    decs["BGF-tangent"] = build_decoder("BGF-tangent",
                                        {"algo": "bgf_vasseur",
                                         "threshold": {"type": "affine_vasseur",
                                                       "c0": b_d, "c1": a_d},
                                         "max_iter": MAX_ITER,
                                         "gray_delta": BGF_OFFICIAL["gray_delta"]},
                                        D, T_STAR, R)

    bf_arms = {
        "BF-official-7": (BF_OFFICIAL["a"], BF_OFFICIAL["b"], BF_OFFICIAL["delta"], 7),
        "BF-official-20": (BF_OFFICIAL["a"], BF_OFFICIAL["b"], BF_OFFICIAL["delta"], 20),
        "BF-derived-7": (a_d, b_d, BF_OFFICIAL["delta"], 7),
        "BF-derived-20": (a_d, b_d, BF_OFFICIAL["delta"], 20),
    }

    names = list(decs) + list(bf_arms)
    fails = {n: np.zeros(n_err, dtype=np.uint8) for n in names}
    it_sum = {n: 0 for n in names}
    it_hist = {n: {} for n in names}      # successes keyed by convergence iteration

    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for nm, dec in decs.items():
            tr = dec(key, s0.copy())
            it_sum[nm] += tr.n_iters_run
            if not tr.success:
                fails[nm][eid] = 1
            elif tr.iters_to_success is not None:
                k = str(int(tr.iters_to_success))
                it_hist[nm][k] = it_hist[nm].get(k, 0) + 1
        for nm, (a, b, delta, nbi) in bf_arms.items():
            tr = bike_flip(key, s0, a, b, delta, nbi)
            it_sum[nm] += tr.n_iters_run
            if not tr.success:
                fails[nm][eid] = 1
            elif tr.iters_to_success is not None:
                k = str(int(tr.iters_to_success))
                it_hist[nm][k] = it_hist[nm].get(k, 0) + 1
    return ki, fails, it_sum, it_hist


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    global N_KEYS, E_PER_KEY, N_WORKERS
    if args.smoke:
        N_KEYS, E_PER_KEY, N_WORKERS = 2, 40, 2

    started = time.time()
    print(f"fair L1 comparison: (r,d,t)=({R},{D},{T_STAR})  keys={N_KEYS} "
          f"errors/key={E_PER_KEY}  workers={N_WORKERS}")
    a_d, b_d, savg = derive_bikeflip_affine(R, D, T_STAR)
    print(f"  A.2.4-derived constants at ({R},{D},{T_STAR}): "
          f"a={a_d!r} b={b_d!r} Savg={savg}")
    assert abs(a_d - 0.0050361944) < 1e-8 and abs(b_d - 17.654858) < 1e-5, \
        "A.2.4 derivation drifted; expected (0.0050361944, 17.654858)"
    print(f"  official L1 constants: a={BF_OFFICIAL['a']!r} b={BF_OFFICIAL['b']!r}")

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        res = list(ex.map(_work, [(ki, E_PER_KEY) for ki in range(N_KEYS)]))
    res.sort(key=lambda r: r[0])
    n = N_KEYS * E_PER_KEY

    names = list(res[0][1])
    per_key = {nm: np.array([r[1][nm].sum() for r in res], dtype=np.int64)
               for nm in names}
    fail_vec = {nm: np.concatenate([r[1][nm] for r in res]) for nm in names}
    it_sum = {nm: sum(r[2][nm] for r in res) for nm in names}
    it_hist = {}
    for nm in names:
        h = {}
        for r in res:
            for k, v in r[3][nm].items():
                h[k] = h.get(k, 0) + v
        it_hist[nm] = h

    gate = {}
    for nm in CARRIER_ARMS:
        gate[nm] = {"got": int(per_key[nm].sum()),
                    "expected": EXPECTED[nm] if not args.smoke else None,
                    "ok": (int(per_key[nm].sum()) == EXPECTED[nm]) if not args.smoke
                          else None}

    out = {"point": {"r": R, "d": D, "t": T_STAR},
           "protocol": {"instances": "results/tier_upgrade/p1pp_main.json (identical)",
                        "budget": "study common 20; BIKE-Flip spec budget 7 reported "
                                  "separately",
                        "success": "zero residual syndrome",
                        "bf_constants_source": "spec v5.2 p.14 (official) / A.2.4 "
                                               "tangent at t*=172 (derived)",
                        "delta_note": "delta=3 is the L1 official value; the spec "
                                      "defines no delta rule outside its table",
                        "bgf_constants_source": "FROZEN_REFERENCE_SEMANTICS.md sec 4b "
                                                "(BGF literature fit at L1; no BGF "
                                                "derivation rule exists)"},
           "pipeline_gate": gate,
           "arms": {}, "wall_seconds": round(time.time() - t0, 1)}
    if args.smoke:
        out["smoke"] = True

    for nm in names:
        k = int(per_key[nm].sum())
        cell = {"failures": k, "trials": n, "dfr": k / n,
                "upper95": wilson_upper(k, n),
                "mean_iters": it_sum[nm] / n,
                "per_key_failures": per_key[nm].tolist(),
                "iters_hist_success": it_hist[nm]}
        for ref in ("C0", "FRO-2"):
            if nm == ref:
                continue
            if per_key[ref].sum() > 0 and per_key[nm].sum() > 0:
                boot = cluster_bootstrap_paired(per_key[ref], per_key[nm], E_PER_KEY,
                                                B=10000, seed=20260905)
                cell[f"vs_{ref}"] = {
                    "rr": boot["point"]["risk_ratio"],
                    "rr_ci95": boot["ci"]["risk_ratio"],
                    "rr_excludes_1": boot["rr_excludes_1"],
                    "sign_test": sign_test_paired(per_key[ref], per_key[nm])}
                b = int(np.sum((fail_vec[ref] == 1) & (fail_vec[nm] == 0)))
                c = int(np.sum((fail_vec[ref] == 0) & (fail_vec[nm] == 1)))
                cell[f"vs_{ref}"]["mcnemar"] = {"b_only": b, "c_only": c,
                                                "p": _mcnemar(b, c)}
        out["arms"][nm] = cell
        line = f"  {nm:16s} {k:5d}/{n}  DFR={k/n:.3e}  iters={cell['mean_iters']:.3f}"
        if "vs_C0" in cell:
            v = cell["vs_C0"]
            line += (f"  vsC0 RR={v['rr']:.3f} [{v['rr_ci95'][0]:.3f}, "
                     f"{v['rr_ci95'][1]:.3f}] McNemar p={v['mcnemar']['p']:.4f}")
        print(line, flush=True)

    gate_ok = all(g["ok"] for g in gate.values() if g["ok"] is not None)
    out["pipeline_gate_passed"] = gate_ok
    path = OUT / ("report_smoke.json" if args.smoke else "report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\npipeline gate: "
          f"{'PASS' if gate_ok else 'N/A (smoke)' if args.smoke else 'FAIL'}")
    print(f"[done] {path}  ({out['wall_seconds']:.0f} s)")
    return 0 if (gate_ok or args.smoke) else 1


if __name__ == "__main__":
    raise SystemExit(main())
