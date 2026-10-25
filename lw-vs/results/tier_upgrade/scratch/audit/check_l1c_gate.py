# -*- coding: utf-8 -*-
"""Auditor D: independent bit-level check of the L1c equivalence claim.

The REPORT says the local bike_flip copy is bit-identical to the frozen
implementation when d1=delta.  The coded gate only compares success and
n_iters_run.  Here we additionally compare the full trajectory fields
(syndrome_weights, flip_counts) on a sample of instances.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/桌面/TOUGAO - c")
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))

from qcmdpc.generators import KeyPool, make_error_generator          # noqa: E402
from qcmdpc.bikeflip import BIKEFLIP_OFFICIAL, bike_flip             # noqa: E402
sys.path.insert(0, str(ROOT / "lw-vs" / "scripts"))
from exp_l1_anchor import _bike_flip_d1, L1, RAND_SPEC               # noqa: E402

pool = KeyPool(20260901, L1, "RAND", {"type": "random", "n_keys": 32})
off = BIKEFLIP_OFFICIAL[(12323, 71, 134)]
nb, dl, a, b = off["nb_iter"], off["delta"], off["a"], off["b"]

n_checked = n_match = 0
mismatch = []
for ki in (0, 1, 2):
    key = pool.keys[ki]
    gen = make_error_generator(20260901, "RAND", key.key_id, L1, RAND_SPEC, key, None)
    for eid in range(25):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        r_new = _bike_flip_d1(key, s0, a, b, dl, nb, dl)
        r_ref = bike_flip(key, s0, a, b, dl, nb)
        n_checked += 1
        same = (r_new.success == r_ref.success and
                r_new.n_iters_run == r_ref.n_iters_run and
                list(r_new.syndrome_weights) == list(r_ref.syndrome_weights) and
                list(r_new.flip_counts) == list(r_ref.flip_counts))
        if same:
            n_match += 1
        else:
            mismatch.append((ki, eid,
                             r_new.syndrome_weights, r_ref.syndrome_weights,
                             r_new.flip_counts, r_ref.flip_counts))

print(f"instances checked: {n_checked}, full-trajectory matches: {n_match}")
for m in mismatch[:5]:
    print("MISMATCH", m)
print("VERDICT:", "PASS (bit-level trajectory identical)" if n_match == n_checked
      else "FAIL (trajectory mismatch found)")
