# -*- coding: utf-8 -*-
"""Auditor C scratch: re-run _work_l1s for key 0, errors 0..9 at t=172 and compare
with p1pp_features.npz. Read-only over results."""


def main():
    import sys
    sys.path.insert(0, r"D:\桌面\TOUGAO - c\实验\qcmdpc-study")
    sys.path.insert(0, r"D:\桌面\TOUGAO - c\lw-vs\scripts")
    import numpy as np
    import exp_tier_upgrade as T

    out = T._work_l1s((0, 172, 10, T.L1S_ARMS, True))
    ki, fails, it_acc, feats, fail_vec = out
    d = np.load(r"D:\桌面\TOUGAO - c\lw-vs\results\tier_upgrade\p1pp_features.npz")
    print("ki:", ki)
    print("fail counts (C0,FRO-2,FRONEG):", fails)
    print("npz fail col-sums key0 first10:",
          int(d["fail_0"][0, :10].sum()), int(d["fail_2"][0, :10].sum()), int(d["fail_-1"][0, :10].sum()))
    print("npz fail bits key0[:10]:", d["fail_0"][0, :10].tolist(), d["fail_2"][0, :10].tolist(),
          d["fail_-1"][0, :10].tolist())
    for k in ("nflip", "n_true", "n_false", "w1"):
        same = np.array_equal(feats[k], d[k][0, :10, :])
        print(f"feature {k} matches npz key0[:10]:", same,
              "" if same else f" recomputed={feats[k][:2].tolist()} npz={d[k][0, :2, :].tolist()}")


if __name__ == "__main__":
    main()
