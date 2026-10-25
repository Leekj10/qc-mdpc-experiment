# -*- coding: utf-8 -*-
"""Auditor C scratch: differential test of exp_l1_anchor._bike_flip_d1 vs the
frozen qcmdpc.bikeflip.bike_flip when d1 == delta (the 'spec' arm).
Compares success, iters_to_success, syndrome_weights trajectory, flip_counts.
Writes nothing. Read-only over existing files.
"""
import sys

sys.path.insert(0, r"D:\桌面\TOUGAO - c\实验\qcmdpc-study")
sys.path.insert(0, r"D:\桌面\TOUGAO - c\lw-vs\scripts")

import numpy as np
from qcmdpc.bikeflip import BIKEFLIP_OFFICIAL, bike_flip
import exp_l1_anchor as A

pool = A._pool(2)               # first 2 keys of the archived RAND pool
off = BIKEFLIP_OFFICIAL[(12323, 71, 134)]
nb, dl, a, b = off["nb_iter"], off["delta"], off["a"], off["b"]

mismatch = 0
checked = 0
for ki in range(2):
    key = pool.keys[ki]
    gen = A.make_error_generator(A.SEED, "RAND", key.key_id, A.L1, A.RAND_SPEC, key, None)
    for eid in range(15):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        r1 = A._bike_flip_d1(key, s0, a, b, dl, nb, dl)   # local copy, d1 == delta
        r0 = bike_flip(key, s0, a, b, dl, nb)             # frozen decoder
        checked += 1
        same = (r0.success == r1.success and
                r0.iters_to_success == r1.iters_to_success and
                r0.syndrome_weights == r1.syndrome_weights and
                r0.flip_counts == r1.flip_counts and
                r0.n_iters_run == r1.n_iters_run)
        if not same:
            mismatch += 1
            print("MISMATCH key", key.key_id, "eid", eid)
            print("  frozen :", r0.success, r0.iters_to_success, r0.syndrome_weights, r0.flip_counts)
            print("  local  :", r1.success, r1.iters_to_success, r1.syndrome_weights, r1.flip_counts)

print(f"checked {checked} instances, mismatches: {mismatch}")

# additionally: the ablation arms must differ from spec only via the decoupled rounds
r_ab = A._bike_flip_d1(key, s0, a, b, dl, nb, 0)      # d1=0, rest=3
r_spec = A._bike_flip_d1(key, s0, a, b, dl, nb, dl)   # d1=3, rest=3
print("last instance: spec iters_to_success", r_spec.iters_to_success,
      "| d1=0 iters_to_success", r_ab.iters_to_success,
      "| distinct trajectories:", r_spec.syndrome_weights != r_ab.syndrome_weights)
