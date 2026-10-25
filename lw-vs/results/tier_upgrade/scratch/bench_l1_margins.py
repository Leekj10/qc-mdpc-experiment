#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Adversary scratch probe (read-only w.r.t. study archives).

Answers three feasibility questions for the proposed upgrades:
  U1  are the round-1 counterfactual features computable per instance (UPC pass,
      flip set, correct/incorrect counts, residual, post-round-1 syndrome weight)?
  U2a how cheap are first-round margin/exchange statistics at true BIKE L1
      (r=12323, d=71, t=134), with NO decoding?
  U2b/d what does a Python decode cost at L1 vs P1' (for sizing the L1 arms)?

Run: python lw-vs/results/tier_upgrade/scratch/bench_l1_margins.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/桌面/TOUGAO - c")
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder, make_threshold  # noqa: E402
from qcmdpc.generators import _child_seed, random_key, uniform_fixed_weight  # noqa: E402

SEED = 20260901


def probe(tag: str, r: int, d: int, t: int, n_err: int, n_dec: int) -> dict:
    rng = np.random.default_rng(_child_seed(SEED, f"advprobe|{tag}", 0))
    key = random_key(rng, r, d, f"adv-{tag}")
    thr0 = make_threshold({"type": "classic"}, d, t, 2 * r)
    thr2 = make_threshold({"type": "offset", "base": {"type": "classic"},
                           "offsets": [2, 0]}, d, t, 2 * r)
    dec0 = build_decoder("C0", {"algo": "bf_parallel",
                                "threshold": {"type": "classic"},
                                "max_iter": 20}, d, t, r)
    dec2 = build_decoder("FRO2", {"algo": "bf_parallel",
                                  "threshold": {"type": "offset",
                                                "base": {"type": "classic"},
                                                "offsets": [2, 0]},
                                  "max_iter": 20}, d, t, r)
    lo, hi = max(1, (d + 1) // 2), d
    out = {"tag": tag, "r": r, "d": d, "t": t, "n_err": n_err, "n_dec": n_dec}
    sws, tau1s, clip_frac2 = [], [], 0
    nflip = {0: [], 2: []}
    nfalse = {0: 0, 2: 0}
    ntrue = {0: 0, 2: 0}
    res_w = {0: [], 2: []}
    upc_time = 0.0
    errors = []
    t0 = time.time()
    for eid in range(n_err):
        erng = np.random.default_rng(_child_seed(SEED, f"advprobe|{tag}|err", eid))
        e = uniform_fixed_weight(erng, 2 * r, t)
        s = key.syndrome_from_global(e)
        errors.append((e, s.copy()))
        t1 = time.time()
        u = key.upc_fast(s)
        upc_time += time.time() - t1
        sw = int(s.sum())
        tau1 = thr0(0, sw)
        sws.append(sw)
        tau1s.append(tau1)
        if tau1 + 2 > hi:
            clip_frac2 += 1
        sup = e.astype(bool)
        for dl in (0, 2):
            F = u >= (tau1 + dl)
            nflip[dl].append(int(F.sum()))
            nfalse[dl] += int(np.count_nonzero(F & ~sup))
            ntrue[dl] += int(np.count_nonzero(F & sup))
            # residual weight |e XOR F| and post-round-1 syndrome weight
            if dl == 0:
                rw0 = int(np.count_nonzero(sup ^ F))
                res_w[0].append(rw0)
            else:
                rw2 = int(np.count_nonzero(sup ^ F))
                res_w[2].append(rw2)
    out["margins"] = {
        "mean_s0_weight": float(np.mean(sws)),
        "mean_tau1": float(np.mean(tau1s)),
        "frac_tau1_plus2_clipped_at_d": clip_frac2 / n_err,
        "mean_flips_delta0": float(np.mean(nflip[0])),
        "mean_flips_delta2": float(np.mean(nflip[2])),
        "mean_false_delta0": nfalse[0] / n_err,
        "mean_false_delta2": nfalse[2] / n_err,
        "mean_true_delta0": ntrue[0] / n_err,
        "mean_true_delta2": ntrue[2] / n_err,
        "mean_residual_delta0": float(np.mean(res_w[0])),
        "mean_residual_delta2": float(np.mean(res_w[2])),
        "sec_per_upc_pass": upc_time / n_err,
    }
    # paired decode timing (same instances, both arms)
    f0 = f2 = 0
    it0 = it2 = 0
    t0 = time.time()
    for eid in range(n_dec):
        e, s = errors[eid]
        r0 = dec0(key, s.copy())
        r2 = dec2(key, s.copy())
        f0 += 0 if r0.success else 1
        f2 += 0 if r2.success else 1
        it0 += r0.n_iters_run
        it2 += r2.n_iters_run
    dt = time.time() - t0
    out["decoding"] = {
        "wall_seconds_paired": dt,
        "decodes_total": 2 * n_dec,
        "ms_per_decode": 1000 * dt / (2 * n_dec),
        "mean_iters_c0": it0 / n_dec,
        "mean_iters_fro2": it2 / n_dec,
        "failures_c0": f0, "failures_fro2": f2,
    }
    return out


def main() -> int:
    res = [
        probe("p1p", 4801, 45, 92, n_err=200, n_dec=20),
        probe("l1", 12323, 71, 134, n_err=100, n_dec=10),
    ]
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
