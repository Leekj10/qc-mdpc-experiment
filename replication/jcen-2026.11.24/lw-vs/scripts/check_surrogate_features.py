#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Bit-exactness check for the no-decode counterfactual feature recipe.

The surrogate model (tier-upgrade G1) rests on one load-bearing claim: the
first-round flip set and post-round-1 syndrome of ANY first-round offset delta
can be computed WITHOUT running the decoder, as

    alpha = key.upc_fast(s0)
    tau1  = clip(classic_th(0, |s0|) + delta, lo, hi)
    F     = { i : alpha_i >= tau1 }
    s1    = s0 XOR (XOR of H-columns at F)

This script verifies that against the frozen carrier (bf_parallel with the
offset threshold spec), for delta in {-1, 0, 1, 2, 3} and for every key/error
sampled, at P1' (4801,45,92) and at a larger (6007,56,100) point:

  (a) F equals the flip set the decoder actually applies in iteration 1
      (res.flip_positions[0], record_flips=True);
  (b) |s1| equals the decoder's post-iteration-1 syndrome weight
      (res.syndrome_weights[0] with max_iter=1);
  (c) the clip (lo=ceil((d+1)/2), hi=d) does not bite at delta in {-1..3}
      unless the raw value is outside [lo,hi] -- reported both ways.

Exit code 0 iff zero mismatches.

Run:  python lw-vs/scripts/check_surrogate_features.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder, make_threshold   # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,  # noqa: E402
                               uniform_fixed_weight, _child_seed)  # noqa: E402

SEED = 20260901
DELTAS = (-1, 0, 1, 2, 3)
POINTS = [
    {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n_keys": 3, "n_err": 25},
    {"id": "BIG", "r": 6007, "d": 56, "t": 100, "n_keys": 2, "n_err": 15},
]


def check_point(pt) -> tuple[int, int, list]:
    r, d, t = pt["r"], pt["d"], pt["t"]
    lo, hi = max(1, (d + 1) // 2), d
    spec = {"type": "random", "n_keys": pt["n_keys"]}
    pool = KeyPool(SEED, pt, f"featchk-{pt['id']}", spec)
    classic = make_threshold({"type": "classic"}, d, t, 2 * r)
    decs = {dl: build_decoder(f"d{dl}", {"algo": "bf_parallel",
                                         "threshold": {"type": "offset",
                                                       "base": {"type": "classic"},
                                                       "offsets": [dl, 0]},
                                         "max_iter": 1}, d, t, r)
            for dl in DELTAS}
    n_ok = n_bad = 0
    clips = []
    for key in pool.keys:
        gen = make_error_generator(SEED, f"featchk-{pt['id']}", key.key_id,
                                   pt, spec, key, None)
        for eid in range(pt["n_err"]):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            alpha = key.upc_fast(s0)
            raw_tau1 = classic(0, int(s0.sum()))
            for dl in DELTAS:
                tau = int(np.clip(raw_tau1 + dl, lo, hi))
                clips.append((raw_tau1 + dl) != tau)
                F = np.nonzero(alpha >= tau)[0]
                # ground truth: what the frozen decoder actually does in iter 1
                res = decs[dl](key, s0.copy(), record_flips=True)
                Ftrue = np.array(res.flip_positions[0], dtype=np.int64) if res.flip_positions else np.array([], dtype=np.int64)
                # (b) recompute s1 by applying the same flips
                s1 = s0.copy()
                for p in F:
                    s1 = key.flip(s1, int(p))
                w1_true = res.syndrome_weights[0] if res.syndrome_weights else int(s0.sum())
                ok = (np.array_equal(F, Ftrue) and int(s1.sum()) == int(w1_true))
                if ok:
                    n_ok += 1
                else:
                    n_bad += 1
                    print(f"  MISMATCH {pt['id']} {key.key_id} eid={eid} delta={dl}: "
                          f"|F|={F.size} |Ftrue|={Ftrue.size} "
                          f"w1={int(s1.sum())} w1true={w1_true}")
    return n_ok, n_bad, clips


def main() -> int:
    total_ok = total_bad = 0
    all_clips = []
    for pt in POINTS:
        ok, bad, clips = check_point(pt)
        total_ok += ok
        total_bad += bad
        all_clips += clips
        print(f"[{pt['id']}] (r,d,t)=({pt['r']},{pt['d']},{pt['t']}): "
              f"{ok} exact, {bad} mismatched")
    print(f"\ntotal: {total_ok} exact / {total_bad} mismatched")
    print(f"threshold-clip events (raw != clipped): {sum(all_clips)} of {len(all_clips)} "
          f"= {100.0*sum(all_clips)/max(1,len(all_clips)):.1f}%")
    print("VERDICT:", "PASS" if total_bad == 0 else "FAIL")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
